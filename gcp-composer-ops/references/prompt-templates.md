# GCL Prompt Templates — Cloud Composer

## Generator Template
Hard rules:
1. Safety gates on all destructive/prod-impacting ops (update env, import DAG, delete env)
2. Follow per-op sub-rules in references/rubric.md
3. Preview env config diff before apply; human review for prod-impacting changes
4. Validate DAG with `python -m py_compile` / `airflow dags list-import-errors` before import
5. Use env vars for credentials; NEVER output credential values
6. Use --format=json for gcloud composer; track long ops via `composer operations`
7. Scaling down node count risks running DAGs → confirm explicitly
8. Suggest backup (DAGs, variables, connections) before delete env
9. Delegate IAM ops to gcp-iam-ops, GCS to gcp-gcs-ops, VPC to gcp-vpc-ops

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
    "Env Config Preview": "PASS|FAIL|N/A",
    "DAG Parse Validation": "PASS|FAIL|N/A",
    "Pipeline Impact": "PASS|FAIL|N/A"
  },
  "verdict": "PASS|SAFETY_FAIL|REVISE",
  "issues": ["string"]
}
```

Detection regex: composer environments update, composer environments delete, storage dags import, composer operations

## Orchestrator
Loop: Generator → Critic → verdict (PASS|SAFETY_FAIL|REVISE). max_iter=2.
