# Monitoring — Cloud Storage

## Key Metrics

| Metric | Type | Threshold |
|--------|------|-----------|
| storage.googleapis.com/storage/object_count | Gauge | Baseline — watch rapid increases |
| storage.googleapis.com/storage/total_bytes | Gauge | Baseline — monitor storage cost growth |
| storage.googleapis.com/api/request_count | Counter | Sudden spikes = potential abuse |
| storage.googleapis.com/api/request_bytes | Counter | Baseline — sudden drops = access issues |
| storage.googleapis.com/network/sent_bytes_count | Counter | Egress cost tracking |
| storage.googleapis.com/network/received_bytes_count | Counter | Ingress cost tracking |
| storage.googleapis.com/throttling/request_count | Gauge | > 0 = rate limited, needs backoff |

## Alert Policy Example

```bash
gcloud alpha monitoring policies create \
  --display-name="GCS-Bucket-Object-Count" \
  --condition-filter='metric.type="storage.googleapis.com/storage/object_count"' \
  --condition-threshold-value=1000000 \
  --condition-duration=600s
```

## Anomaly Patterns

| Pattern | Likely Cause |
|---------|--------------|
| Object count spike | Bulk upload / data migration / abuse |
| Throttling > 0 | Rate limit exceeded — back off |
| Network bytes spike to 0 | Access disabled / IAM revoked |
| Total bytes rapid growth | App writing excessive data / missing lifecycle rules |

## Dashboard Query (Cloud Monitoring MQL)

```
fetch gcs_bucket
| metric 'storage.googleapis.com/storage/object_count'
| group_by [resource.bucket_name], sum()
| every 1h
```