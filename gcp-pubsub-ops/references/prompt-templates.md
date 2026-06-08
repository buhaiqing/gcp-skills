# GCL Prompt Templates — Cloud Pub/Sub

## Generator Template
Hard rules:
1. Safety gates on all destructive ops (delete topic, delete subscription)
2. Follow per-op sub-rules in references/rubric.md
3. Use env vars for credentials; NEVER output credential values
4. Use --format=json for gcloud pubsub
5. Verify topic exists before creating subscription
6. Verify DLQ topic exists and grant permissions before DLQ config
7. Check snapshot validity (exists, not expired) before seek
8. Warn about irreversible message loss on subscription delete
9. Delegate IAM ops to gcp-iam-ops when cross-resource

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
    "Topic Existence Check": "PASS|FAIL|N/A",
    "DLQ Topic Permissions": "PASS|FAIL|N/A",
    "Snapshot Validity": "PASS|FAIL|N/A",
    "Push Endpoint Format": "PASS|FAIL|N/A"
  },
  "verdict": "PASS|SAFETY_FAIL|REVISE",
  "issues": ["string"]
}
```

Detection regex: --quiet.*delete, topics.*delete, subscriptions.*delete, dead-letter-topic, seek.*snapshot, publish.*--message

## Orchestrator
Loop: Generator → Critic → verdict (PASS|SAFETY_FAIL|REVISE). max_iter=2.
