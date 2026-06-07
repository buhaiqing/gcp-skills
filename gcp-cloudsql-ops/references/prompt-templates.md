# GCL Prompt Templates — Cloud SQL

## Generator Template
Hard rules:
1. Safety gates on all destructive ops (delete instance, delete database, restore backup, promote replica, import)
2. Follow per-op sub-rules in references/rubric.md
3. Use env vars for credentials; NEVER output credential values
4. Use --format=json
5. Verify uniqueness before create
6. Suggest backup before destructive operations
7. Passwords: NEVER use `-p` flag for local DB client; use `MYSQL_PWD`/`PGPASSWORD` env vars
8. Delegate VPC ops to gcp-vpc-ops, GCS ops to gcp-gcs-ops

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
    "Password Handling": "PASS|FAIL|N/A",
    "Quota Awareness": "PASS|FAIL|N/A",
    "Connectivity Validation": "PASS|FAIL|N/A"
  },
  "verdict": "PASS|SAFETY_FAIL|REVISE",
  "issues": ["string"]
}
```

Detection regex: --quiet.*delete, sql.*instances.*delete, sql.*databases.*delete, sql.*backups.*restore, promote-replica, -p[PASSWORD]

## Orchestrator
Loop: Generator → Critic → verdict (PASS|SAFETY_FAIL|REVISE). max_iter=2.