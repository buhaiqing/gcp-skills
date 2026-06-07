# GCL Prompt Templates — Cloud Storage

## Generator Template
Hard rules:
1. Safety gates on all destructive ops (delete bucket, delete object, lock retention, signurl)
2. Follow per-op sub-rules in references/rubric.md
3. Use env vars for credentials; NEVER output credential values
4. Use --format=json for gcloud storage; use gsutil for object operations
5. Verify bucket name globally unique before create
6. Verify bucket empty before delete
7. Suggest backup before destructive operations
8. EXTREME safety gate for retention lock: user must type "LOCK" keyword + exact bucket name
9. Delegate IAM ops to gcp-iam-ops, KMS to (planned), Pub/Sub to (planned)

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
    "Bucket Uniqueness": "PASS|FAIL|N/A",
    "Object Path Validation": "PASS|FAIL|N/A",
    "Encryption Consistency": "PASS|FAIL|N/A"
  },
  "verdict": "PASS|SAFETY_FAIL|REVISE",
  "issues": ["string"]
}
```

Detection regex: --quiet.*delete, buckets.*delete, objects.*delete, rm -r, lock.*retention, signurl

## Orchestrator
Loop: Generator → Critic → verdict (PASS|SAFETY_FAIL|REVISE). max_iter=2.