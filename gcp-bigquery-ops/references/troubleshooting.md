# Troubleshooting — Cloud BigQuery

## Error Codes

| HTTP | gRPC | Meaning | Agent Action |
|------|------|---------|--------------|
| 400 | INVALID_ARGUMENT | Invalid query syntax or parameters | Fix query syntax per SQL reference |
| 403 | PERMISSION_DENIED | Insufficient IAM role | Grant bigquery.dataEditor or bigquery.admin |
| 404 | NOT_FOUND | Dataset/table/job not found | Verify project:dataset.table format |
| 409 | ALREADY_EXISTS | Resource already exists | Verify resource, skip or use --replace |
| 413 | QUERY_TOO_LARGE | Query exceeds 1MB limit | Break into smaller queries |
| 429 | QUOTA_EXCEEDED | Concurrent/query quota exceeded | Implement backoff; request increase |
| 500 | INTERNAL | Server error | Retry with backoff; then escalate |
| 503 | UNAVAILABLE | Service unavailable | Retry with exponential backoff |
| — | BILLING_NOT_ENABLED | Billing not active | Enable in Cloud Console |
| — | JOB_NOT_FOUND | Job ID does not exist | Verify job ID is correct |
| — | QUOTA_EXCEEDED | Daily/bytes quota exceeded | Wait or request increase |
| — | SLOT_UNAVAILABLE | No slots available | Check reservation; optimize query |
| — | NOT_PARTITIONED | Partition required but table not partitioned | Create partitioned table |
| — | INVALID_PARTITION | Invalid partition filter | Check partition column and values |
| — | SCHEMA_MISMATCH | Source/target schema mismatch | Align schemas; use --autodetect |
| — | GCS_ACCESS_DENIED | Cannot read/write GCS source/dest | Grant storage.objectViewer/Admin |
| — | TABLE_NOT_FOUND | Table does not exist | Verify dataset.table format |
| — | DATASET_NOT_FOUND | Dataset does not exist | Verify project:dataset format |
| — | LOCATION_MISMATCH | Resources in different locations | Use same location for all resources |
| — | CMEK_KEY_ERROR | CMEK key inaccessible or revoked | Verify KMS key and permissions |

## Diagnostic Order

1. Check billing enabled: `gcloud beta billing projects describe "{{env.CLOUDSDK_CORE_PROJECT}}"`
2. Check BigQuery API enabled: `gcloud services list --enabled --filter=bigquery.googleapis.com`
3. Check dataset exists: `bq show "{{user.dataset_id}}" --format=json`
4. Check table exists: `bq show "{{user.table_id}}" --format=json`
5. Check permissions: `bq get-iam-policy "{{user.dataset_id}}" --format=json`
6. Check job status: `bq show -j "{{user.job_id}}" --format=json | jq '.status'`
7. Check location mismatch: Verify all resources in same region
8. Check Cloud Logging: `resource.type="bigquery_resource"`
9. Check quotas: BigQuery quotas in Cloud Console
10. Check slot utilization: Cloud Monitoring `bigquery.googleapis.com/slots/allocated`

## Common Issues

### Query Fails or Runs Slowly

**Diagnosis**:
```bash
# Dry-run to check cost estimate
bq query --dry_run --use_legacy_sql=false "{{user.query}}"

# Check job statistics
bq show -j "{{user.job_id}}" --format=json | jq '{statistics.query.totalBytesProcessed, statistics.query.totalSlotMs, status.errorResult}'
```

**Root causes**:
- Full table scan: No partition pruning — add WHERE clause on partition column
- Missing clustering: Filter on non-clustered columns — add clustering fields
- Complex joins: Too many joins or cross joins — optimize query structure
- Large intermediate results: Subqueries producing excessive data — use temporary tables
- No query cache hit: Different query text — use identical query for cache benefit
- Slot contention: All slots in use — check reservation or use batch priority

**Fix**:
```sql
-- Add partition filter
SELECT * FROM `project.dataset.table`
WHERE _PARTITIONDATE = '2026-06-08'  -- partition pruning

-- Use clustering columns in WHERE
SELECT * FROM `project.dataset.table`
WHERE cluster_col1 = 'value1' AND cluster_col2 = 'value2'
```

### Quota Exceeded

**Types**:
- Concurrent queries (100 default): Queue requests, use batch priority
- Queries/day (10,000 default): Spread across time, request increase
- Response size (1GB API): Use destination table instead
- Table creation rate: Batch table operations

**Fix**:
```bash
# Use batch priority for non-urgent queries
bq query --use_legacy_sql=false --priority=batch "{{user.query}}"

# Write results to table instead of returning
bq query --use_legacy_sql=false \
  --destination_table="{{user.destination_table_id}}" \
  --replace=true \
  "{{user.query}}"
```

### Billing Errors

**Symptoms**: BILLING_NOT_ENABLED, charges not tracking

**Diagnosis**:
```bash
gcloud beta billing projects describe "{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{billingEnabled, billingAccountName}'
```

**Fix**: Link billing account in Cloud Console or:
```bash
gcloud beta billing projects link "{{env.CLOUDSDK_CORE_PROJECT}}" \
  --billing-account="{{user.billing_account_id}}"
```

### Partition Pruning Failures

**Symptoms**: Query scans entire table despite partition column

**Causes**:
- Filter on non-partition column
- Functions on partition column (e.g., `DATE(partition_col)`)
- OR conditions without AND partition filter
- Cross-join eliminating partition filter

**Fix**:
```sql
-- WRONG: no pruning
SELECT * FROM table WHERE DATE(date_col) = '2026-06-08'

-- RIGHT: pruning applied
SELECT * FROM table WHERE date_col = '2026-06-08'
```

### Job Failures

**LOAD job failure**:
```bash
bq show -j "{{user.job_id}}" --format=json | jq '.status.errorResult'
```

**Common load errors**:
- Schema mismatch: Source data doesn't match table schema → use `--autodetect` or fix schema
- Bad records: Data format issues → `--max_bad_records=N` (use sparingly)
- GCS access denied: SA lacks `storage.objects.get` → grant IAM role
- File not found: Invalid GCS URI → verify URI format

**QUERY job failure**:
- Insufficient permissions: Grant `bigquery.jobs.create` and table access
- Invalid SQL: Check syntax, table existence
- Resource exceeded: Split query, use destination table

### Table Not Found

**Causes**:
- Wrong project ID: Check `project:dataset.table` format
- Wrong dataset: List tables to verify: `bq ls "{{user.dataset_id}}"`
- Location mismatch: Table in different region than query
- Table was deleted: Check Cloud Logging audit trail

### Cross-Project Access Issues

**Setup**:
```bash
# Grant dataset access to external project SA
bq add-iam-policy-binding "project:dataset" \
  --member="serviceAccount:sa@other-project.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataViewer"

# Grant job user role for query execution
bq add-iam-policy-binding "other-project" \
  --member="serviceAccount:sa@other-project.iam.gserviceaccount.com" \
  --role="roles/bigquery.jobUser"
```

### Cost Spike / Budget Exceeded

**Investigation**:
```bash
# Check recent large jobs
bq ls -j --all --max_results=50 | sort -k4 -rn | head -10

# Check bytes processed per job
bq show -j "{{user.job_id}}" --format=json | jq '{jobReference.jobId, statistics.query.totalBytesProcessed}'
```

**Prevention**:
- Set billing alerts in Cloud Console
- Use `--max_bytes_billed` flag on queries
- Enable partition pruning
- Set dataset/table expiration policies
- Use materialized views for repeated aggregations

### Schema Evolution Issues

**Adding columns** (allowed):
```bash
bq update --schema="schema_with_new_columns.json" "{{user.table_id}}"
```

**Removing columns** (not directly supported):
- Create new table with desired schema
- Copy data with query: `INSERT new_table SELECT col1, col2 FROM old_table`
- Swap names or update application references

**Type changes** (not allowed):
- Must recreate table with new schema
