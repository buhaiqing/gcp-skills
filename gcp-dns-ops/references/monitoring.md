# Monitoring — Cloud DNS

## Cloud Monitoring Metrics

Cloud DNS publishes metrics to Cloud Monitoring under the `dns.googleapis.com` namespace.

### Key Metrics

| Metric | Type | Description | Unit |
|--------|------|-------------|------|
| `dns.googleapis.com/query/response_count` | Delta | Number of DNS query responses | Count |
| `dns.googleapis.com/query/response_latencies` | Delta | DNS query response latency distribution | Milliseconds |
| `dns.googleapis.com/query/size` | Delta | Size of DNS query responses | Bytes |
| `dns.googleapis.com/managed_zone/query/response_count` | Delta | Per-zone query response count | Count |

### Query Metrics via gcloud

```bash
# List recent DNS query counts
gcloud monitoring metrics list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --filter='metric.type="dns.googleapis.com/query/response_count"' \
  --interval="PT1H"

# Get query latency percentiles
gcloud monitoring metrics list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --filter='metric.type="dns.googleapis.com/query/response_latencies"' \
  --interval="PT1H"
```

## Alert Policies

Recommended alert policies for Cloud DNS:

| Alert | Condition | Threshold | Notification |
|-------|-----------|-----------|--------------|
| **High query latency** | p99 latency exceeds threshold | > 500ms | PagerDuty / Email |
| **Query volume spike** | Query count exceeds baseline | > 3x normal | Slack / Email |
| **Zone operation failure** | Failed zone operations detected | > 0 in 5min | PagerDuty |
| **DNSSEC validation failure** | DNSSEC validation errors | > 0 | Email |

## Log-Based Metrics

Cloud DNS logs to Cloud Logging. Create log-based metrics for custom alerting:

```bash
# Query DNS API logs
gcloud logging read "resource.type=dns_query AND log_name=projects/{{env.CLOUDSDK_CORE_PROJECT}}/logs/dns.googleapis.com%2Fdns_queries" \
  --limit=10 --format=json

# Create log-based metric for DNS errors
gcloud logging metrics create dns_error_count \
  --description="Count of DNS API errors" \
  --log-filter='resource.type="dns_query" severity>=ERROR' \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

## Dashboard Configuration

Example dashboard panels for Cloud DNS:

1. **Query Volume**: `dns.googleapis.com/query/response_count` over time
2. **Response Latency**: `dns.googleapis.com/query/response_latencies` p50/p95/p99
3. **Zone Operations**: Count of zone create/delete/update operations
4. **Error Rate**: DNS API error responses over time

## DNS Health Checks

```bash
# Verify name server responsiveness
for ns in $(gcloud dns managed-zones describe "{{user.zone_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="value(nameServers)"); do
  echo "Testing $ns..."
  dig @"$ns" "{{user.dns_name}}" SOA +short
done

# Check DNS resolution from GCE instance
gcloud compute ssh instance-name --zone=us-central1-a \
  --command="dig {{user.record_name}} {{user.record_type}} +short"
```

## Monitoring Delegation

For advanced DNS monitoring setup, alerting policies, and dashboard creation, delegate to `gcp-monitoring-ops`.
