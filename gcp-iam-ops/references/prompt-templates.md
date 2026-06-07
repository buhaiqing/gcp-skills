# GCL Prompt Templates — Cloud IAM

## Generator Template
Hard rules:
1. Safety gates on ALL destructive ops (delete SA, delete key, delete role, set policy, remove binding)
2. Follow per-op sub-rules in references/rubric.md
3. Use env vars for credentials; NEVER output credential values or private key data
4. Use --format=json
5. Verify uniqueness before create (role ID, SA email, key)
6. Use read-modify-write with etag for policy operations
7. Dry-run preview before setting IAM policy
8. Set default key expiry when creating SA keys
9. Suggest backup before destructive operations
10. Delegate KMS IAM to gcp-kms-ops, org hierarchy to gcp-resourcemanager-ops

## Critic Template
CRITICAL: Critic MUST NOT see the user's original request.

```json
{
  "dimensions": {
    "Correctness": "PASS|FAIL",
    "Safety": "PASS|FAIL|0",
    "Idempotency": "PASS|FAIL",
    "Traceability": "PASS|FAIL",
    "Spec Compliance": "PASS|FAIL"
  },
  "extensions": {
    "Credential Safety": "PASS|FAIL|N/A",
    "Etag Awareness": "PASS|FAIL|N/A",
    "Policy Validation": "PASS|FAIL|N/A"
  },
  "verdict": "PASS|SAFETY_FAIL|REVISE",
  "issues": ["string"]
}
```

Detection regex: --quiet.*delete, service-accounts.*delete, keys.*delete, roles.*delete, projects.*set-iam-policy.*--quiet, privateKeyData

## Orchestrator
Loop: Generator → Critic → verdict (PASS|SAFETY_FAIL|REVISE). max_iter=2.

### Termination Conditions
- **PASS**: All dimensions pass → return G's result
- **SAFETY_FAIL**: Safety=0 or Credential Safety=F → **ABORT**, no partial result
- **REVISE**: Any dimension FAIL (except Safety) → G revises and re-submits
- **MAX_ITER**: Reached max_iter=2 → return best-so-far + unresolved issues