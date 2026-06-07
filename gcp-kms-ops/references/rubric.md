---
name: kms-ops-rubric
description: GCL scoring rubric for Cloud KMS operations
classification: required
gcl_max_iter: 2
---

# Rubric — Cloud KMS (GCL)

## Core Dimensions (5)

| Dimension | Weight | Max | Meaning |
|-----------|--------|-----|---------|
| **Correctness** | 30% | 10 | Key name/version/state matches request, correct key in resource path |
| **Safety** | 30% | 10 | Destroy operations confirmed, 24h restore window respected, encryption keys not used for signing |
| **Idempotency** | 15% | 10 | Repeated calls produce same result |
| **Traceability** | 10% | 10 | Commands, params, key version, and responses recorded |
| **Spec Compliance** | 15% | 10 | Follows core-concepts.md constraints |

## GCP Extensions (3 additional dimensions, bonus)

| Dimension | Max | Scoring Criteria |
|-----------|-----|------------------|
| Key State Validation | 5 | Correct verification of version state before operation |
| Encryption Round-trip | 5 | Decrypt of encrypted data returns original plaintext |
| IAM Policy Accuracy | 5 | IAM roles correctly matched to operations |

## Per-Op Safety Sub-Rules

| Operation | Safety Rule |
|-----------|-------------|
| Destroy Key Version | User types version name → confirm; warn about 24h window and encrypt/decrypt impact |
| Disable Key Version | User confirms; warn if version is primary |
| Delete IAM Binding | User confirms; show current bindings first |

## Detection Regex

```
destroy|disable|delete|remove|drop|deactivate
```

## Worked Examples

### PASS — Create Crypto Key

**Request:** Create encryption key "my-app-key" for app data encryption

**G Actions:**
1. Pre-flight: Check key ring exists, key name unique
2. Execute: `gcloud kms keys create "my-app-key" --keyring="my-keyring" --location=global --purpose=encryption --protection-level=software --format=json`
3. Verify: `.state == "ENABLED"`, `.primary` is set
4. Report: Key name, primary version, state, purpose

**C Score:** Correctness=10, Safety=10, Idempotency=10, Traceability=9, Spec Compliance=10

### SAFETY_FAIL — Destroy Primary Key Version

**Request:** Destroy key version 1 of primary key

**G Actions:**
1. Pre-flight: Version 1 is primary for "my-app-key"
2. Safety check: Warn user — destroying primary version breaks all encrypt/decrypt
3. User confirms anyway → execute destroy
4. C notes: Version 1 was primary, safety check insufficient (should also suggest designating new primary)

**C Score:** Safety=5 (insufficient guidance, should have suggested `gcloud kms keys update --primary-version=V2` before destroy), Total=FAIL
**Fix Suggestion:** Before destroy, designate a different primary version or warn user must re-encrypt data with new key