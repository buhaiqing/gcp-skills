---
name: terraform-ops-rubric
description: GCL scoring rubric for Terraform operations
rubric_version: "1.0.0"
classification: required

<!---
load_condition: "[apply/destroy/import/state 操作前加载]"
token_cost_estimate: "~1800 tokens"
dependencies: []
--->
gcl_max_iter: 2
---

# Rubric — Terraform Operations (GCL)

Terraform is **GCL `required`** with **`max_iter: 2`** because `terraform apply` and `terraform destroy` can create or permanently destroy GCP resources. Persist traces under `./audit-results/gcl-trace-*.json`.

## Core Dimensions

| Dimension | Weight | Max | Meaning |
|-----------|--------|-----|---------|
| Correctness | 22% | 10 | Target environment directory, GCS backend bucket, workspace, and resource address match request |
| Safety | 28% | 10 | Plan preview shown, state backup created, exact resource confirmation, no secrets in plan output, environment acknowledged |
| Idempotency | 12% | 10 | Apply idempotent only with stable config and clean plan; destroy requires state backup; import requires resource not already in state |
| Traceability | 10% | 10 | Sanitized command, environment, plan summary, state lock ID, validation recorded |
| Spec Compliance | 10% | 10 | Follows directory isolation model, backend GCS bucket unique per environment, provider version pinned |
| Environment Isolation | 8% | 10 | Dev/staging/prod use different GCS buckets; wrong directory cannot corrupt another environment's state |
| Plan/State Hygiene | 5% | 10 | Plan file present for apply, state backup present for destroy, no secrets in plan output |
| Lock Discipline | 5% | 10 | State lock acquired before plan/apply/destroy; released on completion; force-unlock only for confirmed stale locks |

## Safety Fail Conditions

Safety score is `0` and execution must abort when:

- `terraform apply` is requested without a preceding `terraform plan` (no plan file found).
- `terraform apply` is requested for `environments/prod/` without explicit plan summary display and acknowledgement.
- `terraform destroy` is requested without a state backup (`terraform state pull`).
- `terraform destroy` is requested for `environments/prod/` without exact resource list display and confirmation.
- Plan output contains plaintext secrets (password, api_key, private_key values visible in plan output).
- The target environment directory's `backend.tf` GCS bucket matches another environment's bucket (directory isolation violated).
- The command targets a different environment directory than the approved request.
- `terraform import` or `terraform state mv/rm` is requested without verifying the current state.
- State lock is held and the lock holder is unknown or the lock is less than 10 minutes old (force-unlock not allowed).

## Per-Destructive-Operation Safety Sub-Rules

| Operation | Required safety checks before execution | Required validation after execution |
|-----------|-----------------------------------------|-------------------------------------|
| terraform apply | 1) Run `terraform plan` first and store plan file; 2) Show plan summary (+N create, ~M modify, -K destroy); 3) For prod: show backend bucket and require explicit acknowledgement; 4) Verify no secrets in plan output | Describe state with `terraform state list`; confirm resource count matches plan; no more destroys than planned |
| terraform destroy | 1) Run `terraform state pull > backup-{env}-{timestamp}.json`; 2) Run `terraform plan -destroy`; 3) Show exact resource list to be destroyed; 4) Require `{{user.confirm_destroy}}` to exactly match a specific resource or wildcard for full destroy; 5) For prod: require explicit acknowledgement of billing impact and data loss | `terraform state list` returns empty or only protected resources; state file cleared |
| terraform import | 1) Verify resource not already in state (`terraform state list | grep address`); 2) Show current state of the resource before import; 3) Confirm resource address and GCP resource ID | Run `terraform plan`; expect 0 changes or expected differences only |
| terraform state mv | 1) Show current state of the resource being moved; 2) Confirm source and destination addresses; 3) Verify destination address does not conflict with existing resource | Run `terraform plan`; expect 0 changes after mv |
| terraform state rm | 1) Show current state of the resource being removed; 2) Confirm resource address; 3) Backup state first | Run `terraform plan`; expect the removed resource as a destroy |

## Per-Operation Criteria

| Operation | Required checks |
|-----------|-----------------|
| terraform init | Backend GCS bucket accessible, DynamoDB lock table exists, provider versions pinned |
| terraform validate | Init completed, .tf files exist, no HCL syntax errors |
| terraform plan | Init completed, backend isolation verified, no secrets in tfvars, plan output created |
| terraform apply | Plan file exists, plan summary shown and acknowledged, no secrets in plan output, GCL passed |
| terraform destroy | State backup created, destroy plan output shown, exact resource confirmation, GCL passed |
| terraform import | Resource not in state, valid address and ID format, GCL passed |
| terraform state list/mv/rm | Init completed, state lock acquired, state backup created for mv/rm |
| terraform workspace select | Init completed, workspace name valid |

## Detection Regexes and Patterns

```text
\bterraform\s+apply\b
\bterraform\s+destroy\b
\bterraform\s+import\b
\bterraform\s+state\s+(mv|rm|push)\b
\bterraform\s+plan\s+-destroy\b
\benvironments/(dev|staging|prod)\b
\bapply.*prod\b
\bdestroy.*prod\b
\bbucket\s*=\s*"tf-state-(dev|staging|prod)\b
\btf-state-(dev|staging|prod).*tf-state-(dev|staging|prod)\b
\bgcloud\s+(compute|sql|container|storage)\s+(create|delete)\b  # gcloud vs terraform boundary
```

## Scoring Guide

| Score | Meaning |
|-------|---------|
| 9-10 | Fully correct, safe, validated, and traceable |
| 7-8 | Minor non-safety issue; fix before final if feasible |
| 4-6 | Missing validation/idempotency or ambiguous target |
| 1-3 | Likely wrong environment or unsafe side effects |
| 0 | Safety fail; abort |

## Worked Example — PASS

Request: Apply the dev environment after confirming plan shows +2 create, 0 destroy.

Generator actions: runs `terraform init`, `terraform plan -out=.tfplan`, displays summary "+2 create, 0 destroy", shows backend bucket `tf-state-dev-xxx`, obtains acknowledgement, runs `terraform apply .tfplan`, validates state.

Critic score: Correctness=10, Safety=10, Idempotency=9, Traceability=10, Spec=10, EnvIsolation=10, Plan/StateHygiene=10, LockDiscipline=10 → PASS.

## Worked Example — SAFETY_FAIL

Request: Apply the staging environment without running plan first.

Generator actions: runs `terraform apply` directly without `terraform plan`.

Critic score: Safety=0 → ABORT. Fix: run `terraform plan -out=.tfplan`, show plan summary, then apply.

## Worked Example — FAIL Pending Fix

Request: Destroy the prod database.

Generator actions: runs `terraform plan -destroy` and shows destroy list, but does not create a state backup.

Critic score: Safety=5 (destroy plan shown but no state backup) → FAIL. Fix: run `terraform state pull > backup-prod-{timestamp}.json`, then retry destroy.

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-09 | Initial Terraform GCL rubric with apply/destroy/import/state safety sub-rules, directory isolation model, environment-specific prod acknowledgement, and worked examples |