# GCL Prompt Templates — Compute Engine

## Generator Template
Hard rules:
1. Safety gates on all destructive ops (delete instance, disk, resize, stop)
2. Follow per-op sub-rules in references/rubric.md
3. Use env vars for credentials; NEVER output credential values
4. Use --format=json
5. Verify uniqueness before create
6. Suggest backup before destructive operations
7. Delegate VPC ops to gcp-vpc-ops

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
    "Quota Awareness": "PASS|FAIL|N/A",
    "SSH Accessibility": "PASS|FAIL|N/A",
    "Disk Validation": "PASS|FAIL|N/A"
  },
  "verdict": "PASS|SAFETY_FAIL|REVISE",
  "issues": ["string"]
}
```

Detection regex: --quiet.*delete, instances.*delete, disks.*delete, resize.*--size, snapshots.*delete

## Orchestrator
Loop: Generator → Critic → verdict (PASS|SAFETY_FAIL|REVISE). max_iter=2.
