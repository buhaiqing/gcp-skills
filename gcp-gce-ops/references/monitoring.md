# Monitoring — Compute Engine

## Key Metrics

| Metric | Type | Threshold |
|--------|------|-----------|
| compute.googleapis.com/instance/cpu/utilization | Gauge | > 80% for 5min → alert |
| compute.googleapis.com/instance/disk/read_bytes_count | Counter | Baseline |
| compute.googleapis.com/instance/disk/write_bytes_count | Counter | Baseline |
| compute.googleapis.com/instance/disk/read_ops_count | Counter | Watch IOPS limits |
| compute.googleapis.com/instance/disk/write_ops_count | Counter | Watch IOPS limits |
| compute.googleapis.com/instance/network/sent_bytes_count | Counter | Baseline |
| compute.googleapis.com/instance/network/received_bytes_count | Counter | Baseline |
| agent.googleapis.com/memory/percent_used | Gauge | > 90% → alert |
| agent.googleapis.com/disk/percent_used | Gauge | > 85% → alert |

## Alert Policy Example

```bash
gcloud alpha monitoring policies create \
  --display-name="GCE-High-CPU" \
  --condition-filter='metric.type="compute.googleapis.com/instance/cpu/utilization"' \
  --condition-threshold-value=0.8 \
  --condition-duration=300s
```

## Anomaly Patterns

| Pattern | Likely Cause |
|---------|--------------|
| CPU spike then drop to 0 | Instance terminated / OOM |
| IOPS at limit for >5 min | Need faster disk type |
| Network bytes = 0 | Instance stopped or network issue |
| Memory rising daily | Memory leak in app |
