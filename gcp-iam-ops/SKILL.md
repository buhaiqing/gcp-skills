---
name: gcp-iam-ops
description: >-
  Use when the user needs to manage Google Cloud IAM resources — roles
  (predefined and custom), policies (get, set, bind, condition), service
  accounts (create, delete, keys, disable/enable), Workload Identity
  Federation, IAM Deny policies, TestIamPermissions, and Policy Analyzer.
  User mentions IAM, role, permission, policy, service account, SA, workload
  identity, deny policy, or describes access control scenarios even without
  naming the product directly. Not for KMS key-specific IAM
  (delegate to gcp-kms-ops), organization-level folder/project hierarchy
  (delegate to gcp-resourcemanager-ops), or monitoring/metrics
  (delegate to gcp-monitoring-ops).
license: MIT
compatibility: >-
  Official Google Cloud CLI (`gcloud`, Python-based SDK), Go 1.21+ runtime
  (for JIT SDK fallback), valid service account credentials with Security
  Admin, IAM Admin, or Service Account Admin IAM role, network access to
  Google Cloud endpoints.
metadata:
  author: gcp-skills
  version: "1.0.0"
  last_updated: "2026-06-07"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  go_version_minimum: "1.21"
  go_version_jit: "1.24+"
  api_profile: >-
    https://iam.googleapis.com/$discovery/rest?version=v1,
    https://cloudresourcemanager.googleapis.com/$discovery/rest?version=v3
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    gcloud iam --help confirms subcommands: roles, service-accounts,
    workload-identity-pools, deny-policies, policy-analyzer. See
    https://cloud.google.com/sdk/gcloud/reference/iam
  environment:
    - GOOGLE_APPLICATION_CREDENTIALS
    - CLOUDSDK_CORE_PROJECT
    - CLOUDSDK_AUTH_ACCESS_TOKEN
---
> This skill follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Google Cloud IAM Operations Skill

## Overview

Google Cloud IAM provides unified access control for all GCP resources — roles (predefined and custom), policies with conditions, service accounts, Workload Identity Federation, IAM Deny policies, permission testing, and policy analysis. **Dual-path execution** (SDK/API + `gcloud` CLI).

> **UX Compliance:** Follows the [User Experience Specification](../gcp-skill-generator/references/user-experience-spec.md).

### Five Core Standards

| # | Standard | Fulfillment |
|---|----------|-------------|
| 1 | Clear Boundaries | SHOULD/SHOULD NOT with delegation rules |
| 2 | Structured I/O | `{{env.*}}`, `{{user.*}}`, `{{output.*}}` conventions |
| 3 | Explicit Steps | Pre-flight → Execute → Validate → Recover |
| 4 | Failure Strategies | Error taxonomy ≥10 codes with HALT/retry logic |
| 5 | Single Responsibility | One product (IAM); delegate KMS, RM, Monitoring |

Full definitions at [meta-skill](../gcp-skill-generator/SKILL.md#five-core-standards-quality-gates).

### Google Cloud Architecture Framework

| Pillar | Integration |
|--------|-------------|
| Security | IAM roles, key rotation, conditional bindings, Workload Identity, IAM Deny, least-privilege. See [well-architected-assessment.md](references/well-architected-assessment.md) |
| Stability | SA recovery, policy versioning, audit logging |
| Cost | Key lifecycle optimization, unused SA detection |
| Efficiency | Bulk policy operations, Policy Analyzer |
| Performance | Workload Identity credential caching, policy size limits |

## Trigger & Scope

### SHOULD Use When
- User mentions IAM, Identity and Access Management, permissions, role, policy, service account, SA
- Task: roles (list, create/update/delete custom), IAM policies (get, set, add/remove binding, conditional), service accounts (create, list, delete, disable, enable, keys), Workload Identity Pools/Providers, IAM Deny policies, TestIamPermissions, Policy Analyzer
- Keywords: role, permission, binding, condition, SA, key, workload identity, deny policy, testIamPermissions, policy analyzer, who has access, access review

### SHOULD NOT Use When
- KMS key management → gcp-kms-ops (planned) • Project/folder/organization hierarchy → gcp-resourcemanager-ops (planned)
- Monitoring/metrics/dashboards → gcp-monitoring-ops • VPC firewall rules → gcp-vpc-ops
- User insists on console-only flows → state limitation; do not invent undocumented gcloud steps

### Delegation Rules
- **KMS/Security Keys**: For IAM on crypto keys, delegate to gcp-kms-ops (planned).
- **Resource Manager**: For org-level policy constraints or project hierarchy, delegate to gcp-resourcemanager-ops (planned).

## Variable Convention

| Placeholder | Meaning | Source |
|-------------|---------|--------|
| `{{env.GOOGLE_APPLICATION_CREDENTIALS}}` | Path to SA key JSON | NEVER ask user; HALT if unset |
| `{{env.CLOUDSDK_CORE_PROJECT}}` | GCP project ID | NEVER ask user; HALT if unset |
| `{{user.project}}` | User-supplied project override | Ask once; reuse |
| `{{user.organization}}` | Organization ID | Ask once; reuse |
| `{{user.folder}}` | Folder ID | Ask once; reuse |
| `{{user.role_id}}` | Custom role ID (e.g., `myCustomRole`) | Ask once; reuse |
| `{{user.role_name}}` | Predefined role name (e.g., `roles/compute.admin`) | Ask once; reuse |
| `{{user.service_account_email}}` | SA email (e.g., `sa@project.iam.gserviceaccount.com`) | Ask once; reuse |
| `{{user.member}}` | Member identifier (e.g., `user:foo@bar.com`) | Ask once; reuse |
| `{{user.condition}}` / `{{user.condition_title}}` | CEL condition expression / title | Ask once; reuse |
| `{{user.key_id}}` | Service account key ID | Ask once; reuse |
| `{{user.pool_id}}` / `{{user.provider_id}}` | Workload Identity Pool / Provider ID | Ask once; reuse |
| `{{user.deny_policy_id}}` | IAM Deny policy ID | Ask once; reuse |
| `{{user.permissions}}` | Comma-separated permission list | Ask once; reuse |
| `{{user.resource}}` | GCP resource name (e.g., `//cloudresourcemanager.googleapis.com/projects/PROJECT_ID`) | Ask once; reuse |
| `{{output.role_name}}` / `{{output.role_etag}}` | From role create/describe | Parse from JSON path |
| `{{output.policy_etag}}` | From policy get | Parse from `$.etag` |
| `{{output.key_name}}` / `{{output.sa_email}}` / `{{output.pool_name}}` | From create operations | Parse from API response |

> **Security — Credential Masking (MANDATORY):** NEVER log SA key content, `GOOGLE_APPLICATION_CREDENTIALS` path content, or any credential value. Python SDK auto-reads from env var (safe). Go SDK scripts: prohibit `fmt.Printf("Config: %+v", config)` and `log.Printf("%+v", ...)` — can leak credentials.

## API and Response Conventions

**Canonical APIs**: IAM v1 (`iam.googleapis.com`), Cloud Resource Manager v3 (`cloudresourcemanager.googleapis.com`). Errors per [troubleshooting.md](references/troubleshooting.md). Timestamps: RFC 3339. Idempotency: SetIamPolicy with same etag.

### Key JSON Paths

| Operation | JSON Path | Description |
|-----------|-----------|-------------|
| Get IAM Policy | `$.{bindings,etag,version}` | Policy bindings with etag |
| Set IAM Policy | `$.{bindings,etag}` | Updated policy |
| Create Role | `$.{name,title,etag}` | Custom role metadata |
| List Roles | `$.roles[].{name,title,stage}` | Role listing |
| Create SA | `$.{name,email,uniqueId}` | Service account metadata |
| List SAs | `$.accounts[].{name,email,displayName}` | SA listing |
| Create SA Key | `$.{name,privateKeyData,keyAlgorithm,keyOrigin,keyType}` | Key metadata + private key (single response) |
| List SA Keys | `$.keys[].{name,validAfterTime,validBeforeTime,keyAlgorithm}` | Key metadata (no private key) |
| Test Permissions | `$.{permissions[].{name,state}}` | Permission test results |
| Policy Analyze | `$.{mainAccesses[],accessStates,analysisResult}` | Access analysis results |

## Quick Start

```bash
# Verify setup
gcloud config get-value project
gcloud auth application-default print-access-token --quiet &>/dev/null && echo "Auth OK"
gcloud iam service-accounts list --limit=1 --format="json" &>/dev/null && echo "IAM API OK"

# First command
gcloud iam service-accounts list --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"
```

- [Core Concepts](references/core-concepts.md) — IAM architecture, role types, policy structure, prerequisites
- [API & SDK Usage](references/api-sdk-usage.md) — Python SDK snippets, operation map
- [gcloud Usage](references/gcloud-usage.md) — Full gcloud command map, validation patterns
- [Troubleshooting](references/troubleshooting.md) — Error codes, diagnostics, recovery

## Capabilities at a Glance

| Operation | Complexity | Risk |
|-----------|------------|------|
| Get IAM Policy | Low | None |
| Set IAM Policy (dry-run) | Low | None |
| Add/Remove IAM Binding | Medium | Medium |
| Create/Update Custom Role | Medium | Low/Medium |
| Delete Custom Role | Low | **High** |
| Create/List Service Accounts | Low | Low/None |
| Add/Delete SA Key | Medium | **High** |
| Disable/Enable SA | Low | Medium |
| Delete Service Account | Low | **High** |
| Test IAM Permissions | Low | None |
| Analyze Policy | Medium | None |
| Workload Identity Pool | Medium | Medium |
| IAM Deny Policy | Medium | **High** |

## Execution Flows

Every operation: **Pre-flight → Execute (gcloud) → Validate → Recover**. SDK snippets at [api-sdk-usage.md](references/api-sdk-usage.md). Common recovery at [troubleshooting.md](references/troubleshooting.md).

### Get IAM Policy

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Credentials | `gcloud auth print-access-token` | Token returned | HALT |
| Resource exists | `gcloud projects describe {{user.project}} --quiet` | Exit 0 | HALT |

```bash
# Project-level
gcloud projects get-iam-policy "{{user.project}}" --format="json"
# Organization-level
gcloud organizations get-iam-policy "{{user.organization}}" --format="json"
# Folder-level
gcloud resource-manager folders get-iam-policy "{{user.folder}}" --format="json"
```
**Validate**: `gcloud projects get-iam-policy "{{user.project}}" --format="json" | jq '.bindings | length'`
**Recover**: See [troubleshooting.md](references/troubleshooting.md) for 403/404 errors.

### Set IAM Policy (with Dry-Run)

**Safety Gate:** MUST use dry-run preview. MUST obtain explicit user confirmation. MUST use etag for read-modify-write.

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Etag present | Get current policy | Non-null | HALT |
| User confirm | Ask: `Preview and confirm? (yes/no)` | yes | HALT |

```bash
# Export, edit, preview, apply
gcloud projects get-iam-policy "{{user.project}}" --format=json > /tmp/iam-policy.json
# Edit policy with jq, e.g. add binding:
cat /tmp/iam-policy.json | jq '.bindings[.bindings | length] |= . + {"role":"roles/compute.admin","members":["user:admin@example.com"]}' > /tmp/iam-policy-new.json
gcloud projects set-iam-policy "{{user.project}}" /tmp/iam-policy-new.json --dry-run --format=json
gcloud projects set-iam-policy "{{user.project}}" /tmp/iam-policy-new.json --format=json
```
**Validate**: Verify new binding appears in policy output.
**Recover**: `CONDITION_NOT_SUPPORTED` (policy version <3), `POLICY_SIZE_EXCEEDED` (>250KB), etag conflicts (re-fetch). See [troubleshooting.md](references/troubleshooting.md).

### Add IAM Binding (with optional Condition)

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Role exists | `gcloud iam roles describe {{user.role_name}} --format=json` | Exit 0 | HALT |
| Member format | Validate prefix | `user:|group:|serviceAccount:|domain:` | HALT |

```bash
# Without condition
gcloud projects add-iam-policy-binding "{{user.project}}" --member="{{user.member}}" --role="{{user.role_name}}" --format=json
# With condition
gcloud projects add-iam-policy-binding "{{user.project}}" --member="{{user.member}}" --role="{{user.role_name}}" --condition="expression={{user.condition}},title={{user.condition_title}}" --format=json
# Organization-level
gcloud organizations add-iam-policy-binding "{{user.organization}}" --member="{{user.member}}" --role="{{user.role_name}}" --format=json
```
**Validate**: `gcloud projects get-iam-policy "{{user.project}}" --format=json | jq '.bindings[] | select(.role == "{{user.role_name}}")'`

### Remove IAM Binding

**Safety Gate:** Obtain user confirmation showing current binding before removal. Warn if removing last owner/admin.

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Binding exists | Get policy | Role + member exists | HALT |
| User confirm | Ask: `Remove <member> from <role>? (yes/no)` | yes | HALT |

```bash
gcloud projects remove-iam-policy-binding "{{user.project}}" --member="{{user.member}}" --role="{{user.role_name}}" --format=json
# With condition (must match exactly)
gcloud projects remove-iam-policy-binding "{{user.project}}" --member="{{user.member}}" --role="{{user.role_name}}" --condition="expression={{user.condition}},title={{user.condition_title}}" --format=json
```
**Validate**: Confirm binding no longer in policy output.

### Create Custom Role

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Role ID unique | `gcloud iam roles describe {{user.role_id}} --project={{user.project}} --quiet 2>/dev/null` | Exit != 0 | HALT |
| Permissions valid | `gcloud iam list-testable-permissions ...` | Exist | HALT |

```bash
# Project-level
gcloud iam roles create "{{user.role_id}}" --project="{{user.project}}" --title="{{user.role_title}}" --description="{{user.role_description}}" --permissions="{{user.permissions}}" --stage="GA" --format="json"
# Organization-level
gcloud iam roles create "{{user.role_id}}" --organization="{{user.organization}}" --title="{{user.role_title}}" --permissions="{{user.permissions}}" --stage="GA" --format="json"
```
**Validate**: `gcloud iam roles describe "{{user.role_id}}" --project="{{user.project}}" --format="json" | jq '{name, title, stage}'`

### Update Custom Role

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Role exists | Describe | Exit 0 | HALT |
| Etag | Describe response | Non-null | HALT |

```bash
# Full update
gcloud iam roles update "{{user.role_id}}" --project="{{user.project}}" --title="{{user.new_title}}" --permissions="{{user.permissions}}" --stage="{{user.stage}}" --format="json"
# Add permissions
gcloud iam roles update "{{user.role_id}}" --project="{{user.project}}" --add-permissions="{{user.permissions}}" --format="json"
# Remove permissions
gcloud iam roles update "{{user.role_id}}" --project="{{user.project}}" --remove-permissions="{{user.permissions}}" --format="json"
```
**Validate**: `gcloud iam roles describe "{{user.role_id}}" --project="{{user.project}}" --format="json" | jq '.includedPermissions'`

### Delete Custom Role

**Safety Gate (CRITICAL):** User must type exact role ID to confirm. Warn: role DISABLED — no new bindings. Check if role is in use. Suggest backup before deletion.

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Role usage | `gcloud projects get-iam-policy {{user.project}} --format=json | jq '.bindings[] | select(.role | contains("{{user.role_id}}"))'` | No bindings | Warn: role in use |
| User confirm | Ask: `Type role ID <{{user.role_id}}> to confirm` | Exact match | HALT |
| Backup | Suggest `describe > /tmp/role-backup.json` | User accepts | Continue |

```bash
gcloud iam roles delete "{{user.role_id}}" --project="{{user.project}}" --format="json"
```
**Never use `--quiet`** to bypass safety gate. Restore via `gcloud iam roles undelete`.
**Validate**: `gcloud iam roles describe "{{user.role_id}}" --project="{{user.project}}" --quiet 2>&1 || echo "Role confirmed deleted"`

### Create Service Account

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| SA email unique | `gcloud iam service-accounts describe {{user.service_account_email}} --quiet 2>/dev/null` | Exit != 0 | HALT |

```bash
gcloud iam service-accounts create "{{user.sa_name}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --display-name="{{user.sa_display_name}}" --description="{{user.sa_description}}" --format="json"
```
**Validate**: `gcloud iam service-accounts describe "{{user.service_account_email}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" | jq '{name, email, displayName, uniqueId, disabled}'`

### List Service Accounts

```bash
gcloud iam service-accounts list --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"
# Filter by display name
gcloud iam service-accounts list --project="{{env.CLOUDSDK_CORE_PROJECT}}" --filter="displayName:{{user.sa_display_name}}" --format="json"
```
**Validate**: `gcloud iam service-accounts list --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" | jq '.accounts | length'`

### Add Key to Service Account

**Safety Gate (CRITICAL):** Warn: key generation is security-sensitive. Recommend setting expiry. Mask private key data in all logs.

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| SA exists | Describe | Exit 0 | HALT |
| SA disabled? | `.disabled` field | `false` | HALT — enable SA first |

```bash
gcloud iam service-accounts keys create "/tmp/{{user.sa_name}}-key.json" --iam-account="{{user.service_account_email}}" --key-file-type="json" --format="json"
# With expiry
gcloud iam service-accounts keys create "/tmp/{{user.sa_name}}-key.json" --iam-account="{{user.service_account_email}}" --valid-until="{{user.key_expiry_date}}" --key-file-type="json" --format="json"
```
> **Security:** Private key data returned only on creation. Store securely. NEVER log contents.
**Validate**: `gcloud iam service-accounts keys list --iam-account="{{user.service_account_email}}" --managed-by="user" --format="json"`

### List Keys for Service Account

```bash
gcloud iam service-accounts keys list --iam-account="{{user.service_account_email}}" --managed-by="user" --format="json"
# Include system-managed keys
gcloud iam service-accounts keys list --iam-account="{{user.service_account_email}}" --managed-by="any" --format="json"
```
> **Security:** This operation NEVER returns private key data. Output is safe to log.

### Delete Key from Service Account

**Safety Gate (CRITICAL):** Warn: deleting in-use key causes auth failures. User must confirm key_id + SA email. Suggest verifying workloads using this key.

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Key exists | List keys | Key in list | HALT |
| User confirm | Ask: `Delete key <key_id> from SA <email>? (type key_id)` | Exact match | HALT |

```bash
gcloud iam service-accounts keys delete "{{user.key_id}}" --iam-account="{{user.service_account_email}}" --format="json"
```
**Never use `--quiet`** to bypass safety gate.
**Validate**: `gcloud iam service-accounts keys list --iam-account="{{user.service_account_email}}" --managed-by="user" --format="json" | jq -r '.keys[] | .name' | grep "{{user.key_id}}" || echo "Key confirmed deleted"`

### Disable / Enable Service Account

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Current state | `.disabled` field | Opposite of target | HALT |

```bash
# Disable
gcloud iam service-accounts disable "{{user.service_account_email}}" --format="json"
# Enable
gcloud iam service-accounts enable "{{user.service_account_email}}" --format="json"
```
**Validate**: `gcloud iam service-accounts describe "{{user.service_account_email}}" --format="json" | jq -r '.disabled'`

### Delete Service Account

**Safety Gate (CRITICAL):** User must type exact SA email. Warn: irreversible — all resources using this SA lose access. Check active keys and IAM bindings.

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Active keys | `gcloud iam service-accounts keys list --iam-account={{user.service_account_email}} --managed-by=user --format=json | jq '.keys | length'` | Warn if > 0 | Warn: delete keys first |
| IAM bindings | `gcloud iam service-accounts get-iam-policy {{user.service_account_email}} --format=json` | Check for bindings | Warn |
| User confirm | Ask: `Permanently delete SA <email>? Type exact email to confirm` | Exact match | HALT |

```bash
gcloud iam service-accounts delete "{{user.service_account_email}}" --format="json"
```
**Never use `--quiet`** to bypass safety gate.
**Validate**: `gcloud iam service-accounts describe "{{user.service_account_email}}" --quiet 2>&1 || echo "SA confirmed deleted"`

### Test IAM Permissions

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Permissions specified | User provides list | Non-empty | HALT |

```bash
gcloud iam test-iam-permissions "{{user.resource}}" --permissions="{{user.permissions}}" --format="json"
```
**Validate**: `gcloud iam test-iam-permissions "{{user.resource}}" --permissions="{{user.permissions}}" --format="json" | jq -r '.permissions[]'`

### Analyze Policy (Policy Analyzer)

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Cloud Asset API | `gcloud services list --enabled | grep cloudasset.googleapis.com` | Enabled | HALT |

```bash
# Analyze for principal
gcloud asset analyze-iam-policy --scope="projects/{{user.project}}" --principal="user:{{user.member}}" --format="json"
# Analyze for permissions
gcloud asset analyze-iam-policy --scope="projects/{{user.project}}" --permissions="{{user.permissions}}" --format="json"
# Analyze for resource
gcloud asset analyze-iam-policy --scope="projects/{{user.project}}" --resource="{{user.resource}}" --format="json"
```
**Validate**: Check `mainAccesses[].accessState` in response.

### Workload Identity Pool Management

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Pool ID valid | Alphanumeric + hyphens | Valid | HALT |

```bash
# Create pool
gcloud iam workload-identity-pools create "{{user.pool_id}}" --location="global" --display-name="{{user.pool_display_name}}" --format="json"
# Create OIDC provider
gcloud iam workload-identity-pools providers create-oidc "{{user.provider_id}}" --location="global" --workload-identity-pool="{{user.pool_id}}" --issuer-uri="{{user.issuer_uri}}" --attribute-mapping="{{user.attribute_mapping}}" --format="json"
# List pools
gcloud iam workload-identity-pools list --location="global" --format="json"
```
**Validate**: `gcloud iam workload-identity-pools describe "{{user.pool_id}}" --location="global" --format="json"`

### IAM Deny Policy Management

**Safety Gate (CRITICAL) — Delete:** Deleting a deny policy removes access protection. MUST show policy rules before deletion. User must type exact policy ID to confirm.

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Deny API enabled | `gcloud services list --enabled | grep iam.googleapis.com` | Enabled | HALT |
| Policy ID valid | Alphanumeric + hyphens | Valid | HALT |

```bash
# Create deny policy from YAML
cat > /tmp/deny-policy.yaml << 'EOF'
denyRules:
- deniedPrincipals:
  - principalSet://goog/public:all
  deniedPermissions:
  - iam.serviceAccounts.delete
  exceptionPrincipals: []
  title: "Deny SA deletion"
EOF
gcloud iam deny-policies create "{{user.deny_policy_id}}" --policy-file="/tmp/deny-policy.yaml" --format="json"

# List deny policies
gcloud iam deny-policies list --format="json"

# Describe deny policy
gcloud iam deny-policies describe "{{user.deny_policy_id}}" --format="json"
```

**Delete — Safety Gate:** Warn: deleting a deny policy removes protection against denied actions. Show current policy rules. User must type exact policy ID to confirm.

```bash
# Show policy rules before deletion
echo "Current deny policy rules:"
gcloud iam deny-policies describe "{{user.deny_policy_id}}" --format="json"

# Delete (only after explicit confirmation)
gcloud iam deny-policies delete "{{user.deny_policy_id}}" --format="json"
```
**Never use `--quiet`** to bypass this safety gate.
**Validate**: `gcloud iam deny-policies list --format="json" | jq '.denyPolicies[] | select(.name | contains("{{user.deny_policy_id}}"))' || echo "Deny policy confirmed deleted"`

## Reference Directory

- [Core Concepts](references/core-concepts.md) / [API & SDK](references/api-sdk-usage.md) / [gcloud CLI](references/gcloud-usage.md)
- [Troubleshooting](references/troubleshooting.md) / [Monitoring](references/monitoring.md) / [Integration](references/integration.md)
- [Idempotency Checklist](references/idempotency-checklist.md) / [Well-Architected Assessment](references/well-architected-assessment.md)
- [Rubric](references/rubric.md) / [Prompt Templates](references/prompt-templates.md)

## Operational Best Practices

- **Least privilege** — Grant minimum permissions; use predefined roles. **Key rotation** — Set expiry; prefer Workload Identity Federation.
- **Conditions** — Use CEL for time-bound/resource-scoped access. **Audit** — Enable Cloud Audit Logs for IAM changes.
- **Backup** — Export roles/policies before deletion. **Security** — Prefer Workload Identity Federation over SA keys.

## Quality Gate (GCL)

| Property | Value |
|----------|-------|
| Classification | **required** |
| max_iter | 2 |
| Most-scrutinized | Delete SA, Delete Key, Delete Custom Role, Set IAM Policy |

Rubric: [references/rubric.md](references/rubric.md) | Templates: [references/prompt-templates.md](references/prompt-templates.md)

## Token Efficiency Guidelines

- **TE-1/2**: Use `gcloud` for live data; inline `#` comments only (no docstrings)
- **TE-3/4**: Error tables ≤3 cols (see [troubleshooting.md](references/troubleshooting.md)); centralized JSON paths above
- **TE-5/6/7**: YAML anchors in `assets/example-config.yaml`; no cross-file duplication; AIOps in `advanced/`

## See Also

- **Meta-Skill**: [gcp-skill-generator](../gcp-skill-generator/SKILL.md)
- **KMS**: gcp-kms-ops (planned)
- **Resource Manager**: gcp-resourcemanager-ops (planned)
- **Monitoring**: [gcp-monitoring-ops](../gcp-monitoring-ops/SKILL.md)
- **GCL Runner**: [gcp-gcl-runner-ops](../gcp-gcl-runner-ops/SKILL.md)