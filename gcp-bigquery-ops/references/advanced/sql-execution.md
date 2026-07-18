# SQL Execution (Security-Sensitive) — Google Cloud BigQuery

> Provides data engineers and security administrators with a guide to executing SQL queries in BigQuery with security controls — dry-run validation, cost estimation, query analysis, parameterized queries, result validation, and audit trail verification.

## Table of Contents

1. [Overview](#overview)
2. [Security Model](#security-model)
3. [Pre-Execution Validation](#pre-execution-validation)
4. [Query Execution Methods](#query-execution-methods)
5. [Parameterized Queries](#parameterized-queries)
6. [Result Handling](#result-handling)
7. [Audit & Compliance](#audit--compliance)
8. [Error Handling](#error-handling)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)
11. [See Also](#see-also)

## Overview

Security-sensitive SQL execution in BigQuery requires:
- **Cost control**: Prevent runaway queries from accumulating charges
- **Data classification**: Ensure query results match data sensitivity levels
- **Audit trail**: Log all queries for compliance and forensics
- **Injection prevention**: Use parameterized queries to prevent SQL injection
- **Least privilege**: Run queries with minimum required IAM permissions

### Security Considerations

| Concern | Mitigation | Severity |
|---------|------------|----------|
| Cost explosion | Dry-run + bytes limit | Critical |
| Data exfiltration | Column/row-level security, VPC-SC | Critical |
| SQL injection | Parameterized queries only | Critical |
| Permission escalation | Least-privilege IAM roles | High |
| Audit compliance | Cloud Audit Logs integration | High |
| Sensitive data exposure | CMEK + column-level security | High |

## Security Model

```
┌────────────────────────────────────────────────────────────────────────┐
│                     Security-Sensitive SQL Execution                     │
│                                                                          │
│  User Request                                                            │
│  ┌──────────────┐    ┌──────────────────┐    ┌─────────────────────┐ │
│  │ Input        │───►│ Dry-Run          │───►│ Cost Estimation    │ │
│  │ Validation   │    │ (bytes processed)│    │ ($5/TB baseline)   │ │
│  └──────────────┘    └──────────────────┘    └─────────────────────┘ │
│                            │                          │                  │
│                            ▼                          ▼                  │
│  ┌──────────────┐    ┌──────────────────┐    ┌─────────────────────┐ │
│  │ IAM Check    │◄───│ Parameterized     │◄───│ Threshold          │ │
│  │ (roles)      │    │ Query Builder    │    │ Validation          │ │
│  └──────────────┘    └──────────────────┘    └─────────────────────┘ │
│                            │                                             │
│                            ▼                                             │
│  ┌──────────────┐    ┌──────────────────┐    ┌─────────────────────┐ │
│  │ Execute      │───►│ Result           │───►│ Audit Log           │ │
│  │ (limited)    │    │ Validation       │    │ (Cloud Logging)     │ │
│  └──────────────┘    └──────────────────┘    └─────────────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
```

## Pre-Execution Validation

### 1. Cost Estimation (Dry-Run)

Always run dry-run before executing security-sensitive queries:

```bash
# Dry-run to estimate cost
bq query \
  --dry_run \
  --use_legacy_sql=false \
  --format=json \
  "{{user.query}}"
```

**Extract bytes processed**:
```bash
DRY_RUN_RESULT=$(bq query \
  --dry_run \
  --use_legacy_sql=false \
  --format=json \
  "{{user.query}}")

ESTIMATED_BYTES=$(echo "$DRY_RUN_RESULT" | jq -r '.[0].totalBytesProcessed // "0"')
ESTIMATED_COST_TB=$(echo "scale=4; $ESTIMATED_BYTES / 1099511627776" | bc)
ESTIMATED_COST_USD=$(echo "scale=2; $ESTIMATED_COST_TB * 5" | bc)

echo "Estimated: $ESTIMATED_BYTES bytes ($ESTIMATED_COST_TB TB = \$$ESTIMATED_COST_USD on-demand)"
```

### 2. Cost Threshold Check

| Threshold | Action |
|-----------|--------|
| < 1 GB | Proceed |
| 1-10 GB | Warn user, require confirmation |
| > 10 GB | HALT — optimize query |

```bash
# Cost threshold check
MAX_COST_USD=10
if (( $(echo "$ESTIMATED_COST_USD > $MAX_COST_USD" | bc -l) )); then
  echo "ERROR: Estimated cost \$$ESTIMATED_COST_USD exceeds threshold \$$MAX_COST_USD"
  echo "HALT: Optimize query or request quota increase"
  exit 1
fi
```

### 3. Syntax Validation

```bash
# Validate query syntax without execution
bq query \
  --dry_run \
  --use_legacy_sql=false \
  "{{user.query}}" 2>&1 | grep -q "Syntax error" && {
  echo "ERROR: Query syntax invalid"
  exit 1
}
```

### 4. IAM Permission Check

```bash
# Verify user has required roles
gcloud projects get-iam-policy "$CLOUDSDK_CORE_PROJECT" \
  --format=json | jq -r '
    .bindings[] |
    select(.members[] | contains("user:{{user.email}}")) |
    .role' | grep -qE "bigquery\.(dataEditor|dataViewer|jobUser|admin)" && {
  echo "✅ User has BigQuery permissions"
} || {
  echo "ERROR: User lacks BigQuery permissions"
  exit 1
}
```

## Query Execution Methods

### Interactive Query (Small Results)

```bash
# Interactive query with row limit
bq query \
  --use_legacy_sql=false \
  --format=prettyjson \
  --max_rows=100 \
  "{{user.query}}"
```

**Security flags**:
- `--max_rows=100`: Prevent accidental large result sets
- `--dry_run`: Always validate first

### Batch Query (Large Results)

```bash
# Batch query to destination table
bq query \
  --use_legacy_sql=false \
  --priority=batch \
  --destination_table="{{user.dataset_id}}.{{user.table_id}}" \
  --write_disposition=WRITE_TRUNCATE \
  "{{user.query}}"
```

### Dry-Run Query

```bash
# Dry-run only (no execution)
bq query \
  --dry_run \
  --use_legacy_sql=false \
  "{{user.query}}"
```

### Query with Bytes Limit

```bash
# Limit billed bytes to prevent cost explosion
bq query \
  --use_legacy_sql=false \
  --maximum_bytes_billed=1073741824 \
  "{{user.query}}"
```

> **Note**: `maximum_bytes_billed` caps cost at 1 GB = $0.005 on-demand

## Parameterized Queries

### Python SDK (Secure)

```python
from google.cloud import bigquery

client = bigquery.Client()

query = """
  SELECT * FROM `{{user.dataset_id}}.{{user.table_id}}`
  WHERE date >= @start_date
    AND date <= @end_date
    AND status = @status
"""
job_config = bigquery.QueryJobConfig(
    query_parameters=[
        bigquery.ScalarQueryParameter("start_date", "STRING", "{{user.start_date}}"),
        bigquery.ScalarQueryParameter("end_date", "STRING", "{{user.end_date}}"),
        bigquery.ScalarQueryParameter("status", "STRING", "{{user.status}}"),
    ]
)
results = client.query(query, job_config=job_config)
```

### CLI (Parameterized)

```bash
# Use bq query with parameters (requires standard SQL)
bq query \
  --use_legacy_sql=false \
  --parameter="start_date:{{user.start_date}}:STRING" \
  --parameter="end_date:{{user.end_date}}:STRING" \
  --parameter="status:{{user.status}}:STRING" \
  "SELECT * FROM \`{{user.dataset_id}}.{{user.table_id}}\`
   WHERE date >= @start_date AND date <= @end_date AND status = @status"
```

### Go SDK (Secure)

```go
import (
    "cloud.google.com/go/bigquery"
    "context"
)

func runSecureQuery(ctx context.Context, client *bigquery.Client, startDate, endDate, status string) error {
    query := client.Query(`
        SELECT * FROM @dataset_id.@table_id
        WHERE date >= @start_date
          AND date <= @end_date
          AND status = @status
    `)
    query.Parameters = []bigquery.QueryParameter{
        {Name: "dataset_id", Value: "{{user.dataset_id}}"},
        {Name: "table_id", Value: "{{user.table_id}}"},
        {Name: "start_date", Value: startDate},
        {Name: "end_date", Value: endDate},
        {Name: "status", Value: status},
    }
    job, err := query.Run(ctx)
    // ...
}
```

## Result Handling

### Validate Result Size

```bash
# After query execution, validate result size
JOB_ID="{{output.job_id}}"
RESULT_BYTES=$(bq show -j "$JOB_ID" --format=json | jq '.statistics.query.totalBytesProcessed')
RESULT_ROWS=$(bq show -j "$JOB_ID" --format=json | jq '.statistics.query.numOutputRows')

echo "Result: $RESULT_BYTES bytes, $RESULT_ROWS rows"

if [ "$RESULT_BYTES" -gt 10737418240 ]; then
  echo "WARN: Large result set — verify data classification before downstream use"
fi
```

### Export to GCS (Secured)

```bash
# Export with CMEK and restricted access
bq extract \
  --destination_format=CSV \
  --compression=GZIP \
  --kms_key="{{user.kms_key}}" \
  "{{user.table_id}}" \
  "gs://{{user.bucket}}/exports/{{user.filename}}-$(date +%Y%m%d-%H%M%S).csv"

# Verify export
gsutil ls -l "gs://{{user.bucket}}/exports/" | head -5
```

## Audit & Compliance

### Enable Cloud Audit Logs

```bash
# Verify BigQuery Data Access logging is enabled
gcloud projects get-iam-policy "$CLOUDSDK_CORE_PROJECT" \
  --format=json | jq '.auditConfigs[] | select(.service=="bigquery.googleapis.com")'
```

### Query Audit Log

```bash
# Query recent SQL executions from audit logs
gcloud logging read \
  'resource.type="bigquery_dataset"
   logName="bigquery.googleapis.com/sql_activity"
   protoPayload.methodName="query"' \
  --project="$CLOUDSDK_CORE_PROJECT" \
  --format=json \
  --order-by="timestamp desc" \
  --limit=50 | jq '.[] | {
      timestamp: .timestamp,
      query: .protoPayload.serviceData.jobConfiguration.query.query,
      user: .protoPayload.authenticationInfo.principalEmail,
      bytes: .protoPayload.serviceData.jobStatistics.totalBytesProcessed
    }'
```

### Export Audit Trail

```bash
# Export audit logs to GCS for compliance
gcloud logging export "gs://{{user.audit_bucket}}/audit-logs/bq-$(date +%Y%m%d).json" \
  --log-name="bigquery.googleapis.com/sql_activity" \
  --project="$CLOUDSDK_CORE_PROJECT"
```

## Error Handling

### Error Code Reference

| Error | Cause | Resolution |
|-------|-------|------------|
| `dryRunOnly` | Query contains DML/DDL | Use appropriate job type |
| `accessDenied` | Insufficient IAM | Request `bigquery.dataViewer` role |
| `quotaExceeded` | Bytes limit exceeded | Add `--maximum_bytes_billed` or increase quota |
| `invalidQuery` | Syntax error | Fix query syntax |
| `resourceExceeded` | Query too complex | Simplify query or partition |

### Error Recovery

```bash
# Handle quota exceeded
if echo "$ERROR" | grep -q "quotaExceeded"; then
  echo "RETRY: Adding bytes limit and retrying..."
  bq query \
    --use_legacy_sql=false \
    --maximum_bytes_billed=1073741824 \
    "{{user.query}}"
fi

# Handle access denied
if echo "$ERROR" | grep -q "accessDenied"; then
  echo "HALT: Insufficient permissions"
  echo "FIX: gcloud projects add-iam-policy-binding $CLOUDSDK_CORE_PROJECT \
    --member=user:{{user.email}} --role=roles/bigquery.dataViewer"
  exit 1
fi
```

## Best Practices

1. **Always dry-run first**: Estimate cost before execution
2. **Use parameterized queries**: Prevent SQL injection
3. **Set bytes limit**: `--maximum_bytes_billed` to cap costs
4. **Enable audit logging**: Cloud Audit Logs for compliance
5. **Use CMEK**: Encrypt sensitive data at rest
6. **Least privilege**: Use minimum required IAM role
7. **Validate results**: Check result size and data classification
8. **Partition pruning**: Use partitioned tables to reduce scanned data
9. **Avoid SELECT ***: Specify columns to reduce data exposure
10. **Use dry-run + confirmation**: For queries > $10 estimated cost

## Troubleshooting

### Query Hangs

```bash
# Check if query is running
bq ls -j --project_id="$CLOUDSDK_CORE_PROJECT" | grep -E "PENDING|RUNNING"

# Cancel hung query
bq cancel "{{user.job_id}}"
```

### Cost Unexpectedly High

```bash
# Analyze query execution details
bq show -j "{{user.job_id}}" --format=json | jq '{
    bytesProcessed: .statistics.query.totalBytesProcessed,
    bytesBilled: .statistics.query.totalBytesBilled,
    slotMs: .statistics.query.totalSlotMs,
    cacheHit: .statistics.query.cacheHit
  }'
```

### Permission Denied

```bash
# Debug IAM
gcloud projects get-iam-policy "$CLOUDSDK_CORE_PROJECT" \
  --format=json | jq '.bindings[] | select(.role | contains("bigquery"))'
```

## See Also

- [BigQuery Core Concepts](../core-concepts.md)
- [BigQuery Monitoring](../monitoring.md)
- [BigQuery Troubleshooting](../troubleshooting.md)
- [IAM for BigQuery](https://cloud.google.com/bigquery/docs/access-control)
- [BigQuery SQL Reference](https://cloud.google.com/bigquery/docs/reference/standard-sql)
