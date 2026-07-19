# AIOps Drift Detection & IaC Security Scan

> Detect config drift and risky infrastructure patterns from Terraform plans before they reach `apply`. Follows the dry-run → gate → apply → validate pattern.

## Table of Contents

1. [Overview](#overview)
2. [Drift Detection](#drift-detection)
3. [IaC Security Scan](#iac-security-scan)
4. [Dry-Run → Gate → Apply → Validate](#dry-run--gate--apply--validate)
5. [See Also](#see-also)

## Overview

Terraform state is the source of truth, but real GCP resources drift from state when changed outside Terraform (console, `gcloud`, other pipelines). Unnoticed drift causes surprise recreates/destroys on next `apply`. Separately, planned resources may introduce security risks (public buckets, missing encryption, open firewalls) that should be caught at plan time, not after `apply`.

This runbook covers both as agent-executable, token-efficient steps.

## Drift Detection

Use `terraform plan -detailed-exitcode` to detect drift without applying:

```bash
cd environments/{{user.environment}}/

# Refresh state and detect drift; exit code tells you the result
terraform plan -detailed-exitcode -out=/tmp/drift-{env}.tfplan
#   0 = no changes (in sync)
#   1 = error
#   2 = changes present (drift or pending changes)
echo "exit=$?"
```

Scheduled drift runs (cron / CI schedule):

```bash
#!/bin/bash
# drift-check.sh — run on schedule (e.g. hourly) per environment
set -euo pipefail
for env in dev staging prod; do
  cd "environments/$env"
  terraform init -backend=false >/dev/null 2>&1
  if terraform plan -detailed-exitcode -out="/tmp/drift-$env.tfplan" >"/tmp/drift-$env.log" 2>&1; then
    echo "$env: in sync"
  else
    code=$?
    if [ "$code" -eq 2 ]; then
      echo "ALERT: $env has drift — plan non-empty"
      # surface the diff for AIOps alerting
      terraform show -json "/tmp/drift-$env.tfplan" | jq '{changes: (.resource_changes | length)}'
    fi
  fi
  cd - >/dev/null
done
```

Alert on non-empty plan: any exit code `2` means the planned infrastructure differs from actual state → page the owning team.

## IaC Security Scan

No external scanner required. Parse the plan JSON for risky patterns using `terraform plan -out` + `jq`/`grep`. The plan JSON (`terraform show -json <plan>`) contains the full resource graph including planned values.

### Generate scannable plan JSON

```bash
cd environments/{{user.environment}}/
terraform init
terraform plan -out=/tmp/sec-{env}.tfplan
terraform show -json /tmp/sec-{env}.tfplan > /tmp/sec-{env}.json
```

### Checks (agent-executable)

| Risk | Detection | Action |
|------|-----------|--------|
| Public Storage bucket | `google_storage_bucket` with `force_destroy = true` or `uniform_bucket_level_access = false` / public ACL | HALT — require private ACL + versioning |
| Missing encryption | resource has no `encryption` block or `kms_key_name = ""` | HALT — require CMEK / default encryption |
| Open firewall | `google_compute_firewall` with `source_ranges` containing `0.0.0.0/0` on `tcp:22`/`3389`/`all` | HALT — restrict source ranges |
| Public dataset / instance | `google_bigquery_dataset` `access` with `specialGroup: "allAuthenticatedUsers"` or `iam_policy` binding `allUsers` | HALT — remove public principals |
| Unrestricted DB access | `google_sql_database_instance` with no `authorized_networks` or `0.0.0.0/0` | HALT — scope authorized networks |

### Example: scan for public buckets and open firewalls

```bash
PLAN=/tmp/sec-{env}.json

# Public / force-destroy buckets
jq -r '.resource_changes[]
  | select(.type=="google_storage_bucket")
  | select(.change.actions[]?=="create" or .change.actions[]?=="update")
  | .change.after
  | select(.force_destroy==true or (.iam_policy//""|test("allUsers")))' "$PLAN" \
  && echo "WARN: risky storage bucket detected"

# Open firewall to the world
jq -r '.resource_changes[]
  | select(.type=="google_compute_firewall")
  | .change.after.allow[]?
  | select(.range[]?=="0.0.0.0/0" and (.ports[]?|test("22|3389|all")))
  | "OPEN_FIREWALL: \(.)"' "$PLAN" \
  && echo "HALT: world-open firewall on admin port"
```

If any check returns a match, the plan FAILS the security gate → do not `apply`; route IAM/policy fixes to gcp-iam-ops.

### Security-scan note

A dedicated scanner (e.g. Checkov, TFSec, or GCP Security Command Center) MAY be layered on top for deeper policy coverage. This runbook's `jq`/`grep` checks are the minimum agent-executable baseline and require no extra tooling. See [validation-scripts-ci-cd.md](./validation-scripts-ci-cd.md) for CI-integrated scanner setup.

## Dry-Run → Gate → Apply → Validate

```
1. DRY-RUN   terraform plan -out=<plan>            # no mutation
2. GATE      run drift check + IaC security scan   # abort on non-empty risky plan
3. APPLY     terraform apply <plan>              # only after GCL PASS + human confirm
4. VALIDATE  terraform show / terraform state list  # confirm actual == planned
```

- Drift detected at step 2 → alert, do NOT auto-apply; reconcile state first.
- Security scan fails at step 2 → HALT, fix HCL (delegate IAM to gcp-iam-ops), re-plan.
- Apply must always follow a reviewed plan file — never `terraform apply` without `-out` plan.

## See Also

- [Error Taxonomy](../docs/error-taxonomy.md) — Terraform error codes and HALT/retry guidance
- [Cross-Skill Blast Radius](../docs/cross-skill-blast-radius.md) — how a destroy in one skill cascades to dependent resources
- [rubric.md](../rubric.md) — GCL safety gate for apply/destroy/import/state
- [finops-cost-from-plan.md](./finops-cost-from-plan.md) — cost estimation from the same plan JSON
- [validation-scripts-ci-cd.md](./validation-scripts-ci-cd.md) — CI-integrated validation + security scanning
