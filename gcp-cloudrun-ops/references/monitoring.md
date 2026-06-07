# Monitoring — Cloud Run

## Cloud Monitoring Metrics

### Primary Namespace: `run.googleapis.com`

| Metric | Type | Unit | Description |
|--------|------|------|-------------|
| `request_count` | DELTA | 1 | Total HTTP requests |
| `request_latencies` | DELTA | ms | Request latency distribution |
| `billing_billable_instance_time` | DELTA | seconds | Billable instance time |
| `billing_instance_count` | GAUGE | 1 | Current instance count |
| `container/cpu/utilizations` | GAUGE | 1 | CPU utilization ratio |
| `container/memory/bytes_used` | GAUGE | bytes | Memory usage |
| `container/start_count` | DELTA | 1 | Container start events (cold starts) |
| `container/instance_count` | GAUGE | 1 | Active container instances |
| `container/max_instance_concurrency/utilization` | GAUGE | 1 | Concurrency utilization |

### Query Examples

```bash
# Request count (last 1 hour)
gcloud monitoring metrics read "run.googleapis.com/request_count" \
  --aggregation="alignmentPeriod=60s,crossSeriesReducer=REDUCE_SUM" \
  --interval="PT1H" \
  --format=json

# Average latency (last 1 hour)
gcloud monitoring metrics read "run.googleapis.com/request_latencies" \
  --aggregation="alignmentPeriod=60s,crossSeriesReducer=REDUCE_MEAN,perSeriesAligner=ALIGN_MEAN" \
  --interval="PT1H" \
  --format=json

# Instance count over time
gcloud monitoring metrics read "run.googleapis.com/billing_instance_count" \
  --aggregation="alignmentPeriod=60s,crossSeriesReducer=REDUCE_MEAN" \
  --interval="PT1H" \
  --format=json

# Cold start count (container starts)
gcloud monitoring metrics read "run.googleapis.com/container/start_count" \
  --aggregation="alignmentPeriod=300s,crossSeriesReducer=REDUCE_SUM" \
  --interval="PT1H" \
  --format=json
```

## Cloud Monitoring Dashboards

### Recommended Dashboard Layout

| Widget | Metric | Aggregation | Threshold |
|--------|--------|-------------|-----------|
| Request Rate | `run.googleapis.com/request_count` | REDUCE_SUM (1m) | — |
| P99 Latency | `run.googleapis.com/request_latencies` | DELTA_PERCENTILE(99) | > 2000ms |
| Error Rate | `run.googleapis.com/request_count` (filter: response_code>=500) | REDUCE_SUM (1m) | > 1% |
| Active Instances | `run.googleapis.com/billing_instance_count` | REDUCE_MEAN | — |
| Cold Starts | `run.googleapis.com/container/start_count` | REDUCE_SUM (5m) | > 10/min |
| Memory Usage | `run.googleapis.com/container/memory/bytes_used` | REDUCE_MEAN | > 80% limit |
| CPU Usage | `run.googleapis.com/container/cpu/utilizations` | REDUCE_MEAN | > 80% limit |

## Alert Policies

### Recommended Alerts

| Alert | Metric | Condition | Notification |
|-------|--------|-----------|--------------|
| High Error Rate | `run.googleapis.com/request_count` | 5xx > 5% over 5m | PagerDuty / Email |
| High Latency | `run.googleapis.com/request_latencies` | P99 > 5s over 5m | PagerDuty / Email |
| No Instances | `run.googleapis.com/billing_instance_count` | == 0 for 5m (if min-instances > 0) | PagerDuty |
| Quota Near Limit | `run.googleapis.com/billing_instance_count` | > 90% of max-instances | Email |
| Cold Start Spike | `run.googleapis.com/container/start_count` | > 50/min over 5m | Email |

### Create Alert Policy via gcloud

```bash
gcloud alpha monitoring policies create --policy-from-file="alert-policy.yaml"
```

## Cloud Logging

### Log Filter for Cloud Run

```
resource.type="cloud_run_revision"
resource.labels.service_name="SERVICE_NAME"
resource.labels.revision_name="REVISION_NAME"
```

### Common Log Queries

```bash
# All logs for a service (last 1 hour)
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="NAME"' --limit=100

# Error logs only
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="NAME" AND severity>=ERROR' --limit=50

# Request logs (access log)
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="NAME" AND httpRequest.requestUrl!=""' --limit=20

# Container stdout/stderr
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="NAME" AND severity=INFO' --limit=50
```

## Log-Based Metrics

Create custom metrics from logs:

```bash
gcloud logging metrics create cloud-run-errors \
  --description="Cloud Run 5xx error count" \
  --log-filter='resource.type="cloud_run_revision" AND severity>=ERROR'
```
