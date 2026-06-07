# Monitoring & Alerts — Cloud Logging

## Key Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `logging.googleapis.com/byte_count` | counter | Log volume in bytes |
| `logging.googleapis.com/log_entry_count` | counter | Number of log entries ingested |
| `logging.googleapis.com/request_count` | counter | API request count |
| `logging.googleapis.com/exclusion_count` | counter | Entries excluded by exclusions |
| `logging.googleapis.com/ingestion_rate` | gauge | Log ingestion rate (bytes/sec) |

## Alert Policy Example

### High Log Volume Alert

```yaml
# high_log_volume.yaml
combiner: OR
conditions:
- conditionThreshold:
    filter: metric.type="logging.googleapis.com/log_entry_count"
    duration: 300s
    comparison: COMPARISON_GT
    thresholdValue: 100000
    aggregations:
    - perSeriesAligner: ALIGN_RATE
displayName: "High log entry count"
documentation:
  content: |-
    Log ingestion rate exceeded 100K entries/min.
    Check for application errors or misconfigured logging.
notificationChannels:
- "projects/{{env.CLOUDSDK_CORE_PROJECT}}/notificationChannels/NOTIFY_ID"
```

## Anomaly Patterns

| Pattern | Possible Cause | Recommended Action |
|---------|---------------|-------------------|
| Sudden log drop | Sink/exclusion misconfigured | Check exclusions and sink filters |
| Log volume spike | Application error or attack | Investigate application logs |
| Quota approaching limit | Sustained high volume | Create exclusion rules, request quota increase |
| Sink delivery errors | Destination IAM changed | Verify writer identity and destination access |

## Dashboards

Create a logging dashboard in Cloud Monitoring:

```bash
gcloud monitoring dashboards create \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --config-from-file=logging-dashboard.yaml
```