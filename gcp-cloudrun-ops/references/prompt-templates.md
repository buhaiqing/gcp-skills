# GCL Prompt Templates — Cloud Run

## Generator Template
Hard rules:
1. Safety gates on all destructive ops (delete service)
2. Follow per-op sub-rules in references/rubric.md
3. Use env vars for credentials; NEVER output credential values
4. Use --format=json
5. Verify uniqueness before create
6. Verify image accessibility before deploy
7. Validate traffic percentages sum to 100 before update-traffic
8. Delegate VPC ops to gcp-vpc-ops, Secret Manager ops to gcp-secretmanager-ops

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
    "Credential Handling": "PASS|FAIL|N/A",
    "Quota Awareness": "PASS|FAIL|N/A",
    "Traffic Validation": "PASS|FAIL|N/A",
    "Image Accessibility": "PASS|FAIL|N/A"
  },
  "verdict": "PASS|SAFETY_FAIL|REVISE",
  "issues": ["string"]
}
```

Detection regex: --quiet.*delete, run.*services.*delete, run.*services.*update-traffic, --to-revisions=, --set-secrets=, --vpc-connector=, permissionDenied, imagePullError

## Orchestrator
Loop: Generator → Critic → verdict (PASS|SAFETY_FAIL|REVISE). max_iter=3.
