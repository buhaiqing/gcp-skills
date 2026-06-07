---
name: secretmanager-ops-rubric
description: GCL scoring rubric for Cloud Secret Manager operations
classification: required
gcl_max_iter: 2
---

# Rubric — Cloud Secret Manager (GCL)

## Core Dimensions (5)

| Dimension | Weight | Max | Meaning |
|-----------|--------|-----|---------|
| **Correctness** | 30% | 10 | Secret name/version/state matches request, correct resource path |
| **Safety** | 30% | 10 | Destroy/delete operations confirmed, credentials never exposed |
| **Idempotency** | 15% | 10 | Repeated calls produce same result |
| **Traceability** | 10% | 10 | Commands, params, secret version, and responses recorded |
| **Spec Compliance** | 15% | 10 | Follows core-concepts.md constraints |

## GCP Extensions (3 additional dimensions, bonus)

| Dimension | Max | Scoring Criteria |
|-----------|-----|------------------|
| Version State Validation | 5 | Correct verification of version state before operation |
| Payload Access Accuracy | 5 | Secret payload decoded correctly (base64) |
| IAM Policy Accuracy | 5 | IAM roles correctly matched to operations |

## Per-Op Safety Sub-Rules

| Operation | Safety Rule |
|-----------|-------------|
| Delete Secret | User types secret name → confirm; warn about irreversible loss of all versions |
| Destroy Version | User types version number → confirm; warn data cannot be recovered |
| Disable Version | User confirms; warn if disabling last ENABLED version |
| IAM Policy Change | Show current bindings before modification |

## Detection Regex

```
destroy|disable|delete|remove|drop|deactivate
```

## Worked Examples

### PASS — Create Secret

**Request:** Create secret "my-api-key" with automatic replication

**G Actions:**
1. Pre-flight: Check API enabled, secret name unique
2. Execute: `gcloud secrets create "my-api-key" --replication-policy=automatic --data-file=- <<< "value" --format=json`
3. Verify: `$.name` contains "my-api-key", `$.replication.automatic` present
4. Report: Secret name, replication, create time

**C Score:** Correctness=10, Safety=10, Idempotency=10, Traceability=10, Spec Compliance=10

### SAFETY_FAIL — Delete Secret Without Confirmation

**Request:** Delete secret "prod-db-password"

**G Actions:**
1. Pre-flight: Secret exists, 5 versions present
2. Safety check: Skipped confirmation, executed delete directly
3. C notes: Delete operation requires explicit user confirmation

**C Score:** Safety=0 (no confirmation for destructive operation), Total=SAFETY_FAIL
**Fix Suggestion:** MUST obtain explicit user confirmation with secret name match before delete
