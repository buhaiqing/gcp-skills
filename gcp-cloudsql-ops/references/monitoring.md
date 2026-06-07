# Monitoring — Cloud SQL

## Key Metrics

| Metric | Type | Threshold |
|--------|------|-----------|
| cloudsql.googleapis.com/database/cpu/utilization | Gauge | > 80% for 5min → alert |
| cloudsql.googleapis.com/database/memory/utilization | Gauge | > 90% → alert |
| cloudsql.googleapis.com/database/disk/utilization | Gauge | > 85% → alert |
| cloudsql.googleapis.com/database/disk/bytes_used | Gauge | Watch for storage full |
| cloudsql.googleapis.com/database/network/connections | Gauge | Connection saturation |
| cloudsql.googleapis.com/database/postgresql/num_backends | Gauge | Active connections (PG) |
| cloudsql.googleapis.com/database/mysql/threads_running | Gauge | Active threads (MySQL) |
| cloudsql.googleapis.com/database/replication/replica_lag | Gauge | > 30s → alert (replicas) |
| cloudsql.googleapis.com/database/disk/read_ops_count | Counter | IOPS monitoring |
| cloudsql.googleapis.com/database/disk/write_ops_count | Counter | IOPS monitoring |
| cloudsql.googleapis.com/database/state | State | Not RUNNABLE → alert |
| cloudsql.googleapis.com/database/up | Bool | 0 → critical alert |

## Query Insights Metrics

| Metric | Description |
|--------|-------------|
| cloudsql.googleapis.com/database/query_stats/execution_count | Query execution count |
| cloudsql.googleapis.com/database/query_stats/latency_avg | Average latency per query |
| cloudsql.googleapis.com/database/query_stats/rows_scanned_avg | Average rows scanned |
| cloudsql.googleapis.com/database/query_stats/cpu_time_avg | Average CPU time |

## Alert Policy Example

```bash
# High CPU utilization alert
gcloud alpha monitoring policies create \
  --display-name="CloudSQL-High-CPU" \
  --condition-filter='metric.type="cloudsql.googleapis.com/database/cpu/utilization"' \
  --condition-threshold-value=0.8 \
  --condition-duration=300s

# High storage utilization alert
gcloud alpha monitoring policies create \
  --display-name="CloudSQL-Storage-Full" \
  --condition-filter='metric.type="cloudsql.googleapis.com/database/disk/utilization"' \
  --condition-threshold-value=0.9 \
  --condition-duration=60s

# Replica lag alert
gcloud alpha monitoring policies create \
  --display-name="CloudSQL-ReplicaLag" \
  --condition-filter='metric.type="cloudsql.googleapis.com/database/replication/replica_lag"' \
  --condition-threshold-value=30 \
  --condition-duration=120s
```

## Anomaly Patterns

| Pattern | Likely Cause |
|---------|--------------|
| CPU spike, then 0 | Instance terminated / OOM |
| Connection count flatlines | Instance stopped / network down |
| Disk IOPS at limit for >5min | Need larger storage or SSD |
| Replica lag growing | Heavy write load on primary | 
| Memory rising daily | Memory leak / missing connection pool |
| Disk filling fast | Missing data retention policy |
| Query latency spike | Missing index / query plan change |

## Dashboard Example

Create a dashboard for Cloud SQL monitoring in Cloud Console using `gcloud alpha monitoring dashboards create` with the following widgets:

1. **CPU Utilization** — time series (last 6h)
2. **Memory Utilization** — time series (last 6h)
3. **Disk Utilization** — time series (last 6h)
4. **Connection Count** — time series (last 6h)
5. **Replica Lag** — time series (last 6h, if replicas exist)
6. **Top 5 Slow Queries** — from Query Insights