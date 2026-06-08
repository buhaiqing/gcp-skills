# GCL Prompt Templates — Cloud BigQuery

## Generator Template
Hard rules:
1. Safety gates on all destructive ops (delete dataset, delete table)
2. Cost safety: dry-run before any query, display bytes processed and estimated cost
3. Follow per-op sub-rules in references/rubric.md
4. Use env vars for credentials; NEVER output credential values
5. Use standard SQL (not legacy SQL) for all queries
6. Verify resource existence before create/delete operations
7. Use --format=prettyjson for structured output
8. Suggest backup before destructive operations
9. Delegate IAM ops to gcp-iam-ops, GCS to gcp-gcs-ops, KMS to (planned)
10. Validate dataset:table ID format (project:dataset.table)
11. Use partition pruning where applicable

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
    "Dataset/Table ID Format": "PASS|FAIL|N/A",
    "Cost Guard (Dry-Run)": "PASS|FAIL|N/A",
    "Partition Pruning": "PASS|FAIL|N/A",
    "Location Consistency": "PASS|FAIL|N/A"
  },
  "verdict": "PASS|SAFETY_FAIL|REVISE",
  "issues": ["string"]
}
```

Detection regex: rm.*-f.*dataset, rm.*-f.*table, query.*--dry_run, query.*--destination_table, load.*--source_format, extract.*--destination_format

## Orchestrator
Loop: Generator → Critic → verdict (PASS|SAFETY_FAIL|REVISE). max_iter=2.
