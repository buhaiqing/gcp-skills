# Idempotency Checklist — Cloud BigQuery

## Create

| Resource | Key | Retry Behavior |
|----------|-----|----------------|
| Dataset | dataset_id (project-scoped) | ALREADY_EXISTS / 409 — skip or use update |
| Table | table_id (dataset-scoped) | ALREADY_EXISTS / 409 — skip or use `--replace` |
| Materialized View | table_id | ALREADY_EXISTS / 409 — skip |
| Routine | dataset.routine_name | ALREADY_EXISTS / 409 — skip or drop then recreate |

## Update

| Operation | Idempotent? |
|-----------|-------------|
| Update dataset labels | Yes (same key:value = no-op) |
| Update dataset description | Yes (same value = no-op) |
| Update default table expiration | Yes (same value = no-op) |
| Update table schema (additive) | Yes (new fields only) |
| Update table description | Yes (same value = no-op) |
| Update table labels | Yes (same key:value = no-op) |
| Update table clustering | Yes (same fields = no-op) |
| Update table partitioning | Yes (same config = no-op) |
| Update IAM binding (add) | Yes (same member+role = no-op) |
| Update IAM binding (remove) | Yes (same member+role = no-op) |
| Cancel job | Yes (already cancelled = no-op) |

## Delete

| Resource | Retry Safe? |
|----------|-------------|
| Dataset | Safe — NOT_FOUND on second attempt |
| Table | Safe — NOT_FOUND on second attempt |
| Job | Safe — job still exists but cancelled |

## Query Idempotency

| Scenario | Safe Retry? | Notes |
|----------|-------------|-------|
| SELECT query | Yes | Read-only, no side effects |
| INSERT query | No | Duplicates rows on retry |
| INSERT with DEDUP | Yes | If table has deduplication logic |
| UPDATE query | No | May double-apply updates |
| DELETE query | No | May fail on second run (rows already gone) |
| CREATE TABLE AS SELECT | No | ALREADY_EXISTS on retry |
| CREATE TABLE IF NOT EXISTS AS | Yes | No-op if table exists |

## Safe Retry Patterns

### Create Dataset (Idempotent)
```bash
if ! bq show "{{user.dataset_id}}" --quiet 2>/dev/null; then
    bq mk --dataset --location=US "{{user.dataset_id}}"
else
    echo "Already exists — no action needed"
fi
```

### Create Table (Idempotent)
```bash
if ! bq show "{{user.table_id}}" --quiet 2>/dev/null; then
    bq mk --table --schema="{{user.schema}}" "{{user.table_id}}"
else
    echo "Already exists — no action needed"
fi
```

### Replace Table (Safe Overwrite)
```bash
# Using query with --replace flag
bq query --use_legacy_sql=false \
  --destination_table="{{user.table_id}}" \
  --replace=true \
  "{{user.query}}"
```

### Load Data (Safe Overwrite)
```bash
# Using WRITE_TRUNCATE to replace all data
bq load --source_format=CSV \
  --write_disposition=WRITE_TRUNCATE \
  --autodetect \
  "{{user.table_id}}" "gs://bucket/data.csv"
```

### Label De-Duplication
```bash
bq update --set_label=deployment-id=deploy-20260608-001,created-by=automation \
  "{{user.table_id}}"
```

### Query with Cost Guard
```bash
# Always dry-run first for cost estimation
bq query --dry_run --use_legacy_sql=false "{{user.query}}" 2>&1 | grep "totalBytesProcessed"
# Then execute with max_bytes_billed guard
bq query --use_legacy_sql=false \
  --max_bytes_billed=500000000000 \
  "{{user.query}}"
```
