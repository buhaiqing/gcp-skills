# GCL Prompt Templates — GKE

## Generator Template
Hard rules:
1. Safety gates on all destructive ops (delete cluster, delete node pool, resize down)
2. Follow per-op sub-rules in references/rubric.md
3. Use env vars for credentials; NEVER output credential values
4. Use --format=json
5. Verify uniqueness before create
6. Suggest backup before destructive operations
7. Delegate VPC subnet creation to gcp-vpc-ops when secondary range missing
8. Use `gcloud container get-server-config` for version/channel validation (TE-1)
9. For regional clusters use `--region`, for zonal use `--zone`

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
    "Version Awareness": "PASS|FAIL|N/A",
    "CIDR Validation": "PASS|FAIL|N/A"
  },
  "verdict": "PASS|SAFETY_FAIL|REVISE",
  "issues": ["string"]
}
```

Detection regex: --quiet.*delete, clusters.*delete, node-pools.*delete, resize.*--num-nodes, upgrade.*--node-pool

## Orchestrator
Loop: Generator → Critic → verdict (PASS|SAFETY_FAIL|REVISE). max_iter=2.