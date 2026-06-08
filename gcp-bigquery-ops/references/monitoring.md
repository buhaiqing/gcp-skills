# Monitoring — Cloud BigQuery

## Key Metrics

| Metric | Type | Description | Threshold |
|--------|------|-------------|-----------|
| `bigquery.googleapis.com/query/total_bytes_processed` | Counter | Bytes scanned by queries | Alert if > 80% of monthly budget |
| `bigquery.googleapis.com/query/total_bytes_billed` | Counter | Billed bytes (after free tier) | Track for cost optimization |
| `bigquery.googleapis.com/slots/allocated` | Gauge | Active slot allocation | Alert if consistently at max |
| `bigquery.googleapis.com/slots/utilization` | Gauge | Slot utilization rate (0-1) | Alert if > 0.85 (saturation) |
| `bigquery.googleapis.com/slots/wait_time` | Gauge | Time queries wait for slots | Alert if > 5 minutes |
| `bigquery.googleapis.com/job/total_executed_jobs` | Counter | Total jobs executed | Baseline — sudden drops = issues |
| `bigquery.googleapis.com/job/failed_jobs` | Counter | Failed jobs count | Alert if > 0 |
| `bigquery.googleapis.com/storage/total_bytes` | Gauge | Total storage usage | Track growth rate |
| `bigquery.googleapis.com/storage/active_logical_bytes` | Gauge | Active (not long-term) storage | Cost tracking |
| `bigquery.googleapis.com/storage/long_term_logical_bytes` | Gauge | Long-term storage (>90 days) | Lower cost tier |
| `bigquery.googleapis.com/streaming/insert_errors` | Counter | Streaming insert failures | Alert if > 0 |
| `bigquery.googleapis.com/query/cache_hit_ratio` | Gauge | Query cache effectiveness | Monitor for optimization |

## Alert Policy Examples

### High Bytes Processed (Cost Alert)
```bash
gcloud alpha monitoring policies create \
  --display-name="BigQuery-High-Bytes-Processed" \
  --condition-filter='metric.type="bigquery.googleapis.com/query/total_bytes_processed"' \
  --condition-threshold-value=500000000000 \
  --condition-duration=3600s \
  --notification-channels="{{user.notification_channel_id}}"
```

### Job Failures
```bash
gcloud alpha monitoring policies create \
  --display-name="BigQuery-Job-Failures" \
  --condition-filter='metric.type="bigquery.googleapis.com/job/failed_jobs"' \
  --condition-threshold-value=1 \
  --condition-duration=300s
```

### Slot Saturation
```bash
gcloud alpha monitoring policies create \
  --display-name="BigQuery-Slot-Saturation" \
  --condition-filter='metric.type="bigquery.googleapis.com/slots/utilization"' \
  --condition-threshold-value=0.85 \
  --condition-duration=600s
```

## Dashboard Query (Cloud Monitoring MQL)

### Bytes Processed Over Time
```
fetch bigquery_project
| metric 'bigquery.googleapis.com/query/total_bytes_processed'
| group_by [project_id], sum(value.total_bytes_processed)
| every 1h
```

### Slot Utilization
```
fetch bigquery_project
| metric 'bigquery.googleapis.com/slots/utilization'
| group_by [project_id], mean(value.utilization)
| every 5m
```

### Job Duration Distribution
```
fetch bigquery_project
| metric 'bigquery.googleapis.com/job/total_executed_jobs'
| group_by [project_id], sum(value.job_count)
| every 1h
| value [job_count: sum(value.job_count)]
```

### Storage Growth
```
fetch bigquery_project
| metric 'bigquery.googleapis.com/storage/total_bytes'
| group_by [project_id], max(value.total_bytes)
| every 1d
```

## Anomaly Patterns

| Pattern | Likely Cause | Action |
|---------|--------------|--------|
| Bytes processed spike | Full table scan, missing partition pruning | Optimize queries, enforce partition filters |
| Slot utilization > 0.85 | Insufficient slots, peak workload | Increase reservation, use batch priority |
| Job failures spike | Schema changes, permission issues | Check recent deployments, audit IAM |
| Storage rapid growth | Ingestion rate increase, missing expiration | Set table expiration, review data retention |
| Cache hit ratio drops | Query changes, increased ad-hoc queries | Standardize queries, use materialized views |
| Streaming insert errors | Schema mismatch, quota exceeded | Check schema, reduce insert rate |

## Cost Monitoring

### Monthly Cost Estimation
```sql
-- Query your own billing data (requires BigQuery export)
SELECT
  DATE(usage_start_time) AS date,
  SUM(cost) AS total_cost
FROM `project.dataset.gcp_billing_export`
WHERE service.description = 'BigQuery'
GROUP BY date
ORDER BY date DESC
LIMIT 30
```

### Top Cost Queries (via INFORMATION_SCHEMA)
```sql
SELECT
  job_id,
  user_email,
  total_bytes_processed,
  total_bytes_processed / POWER(1024, 4) * 5 AS estimated_cost_usd,
  creation_time
FROM `region-us`.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE creation_time > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
  AND total_bytes_processed > 100000000000  -- > 100GB
ORDER BY total_bytes_processed DESC
LIMIT 20
```

## Recommended Alerts

| Alert | Metric | Threshold | Severity |
|-------|--------|-----------|----------|
| Bytes > monthly budget | `total_bytes_processed` | > 80% of allocation | Critical |
| Job failure rate | `failed_jobs / total_executed_jobs` | > 5% in 1h | Warning |
| Slot wait time | `slots/wait_time` | > 5 minutes | Warning |
| Storage growth rate | `storage/total_bytes` | > 20% MoM | Info |
| Streaming errors | `streaming/insert_errors` | > 0 in 5 minutes | Warning |
