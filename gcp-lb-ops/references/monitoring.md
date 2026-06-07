# Monitoring — Cloud Load Balancing

## Key Cloud Monitoring Metrics

| Metric | Type | Description | Recommended Threshold |
|--------|------|-------------|----------------------|
| `loadbalancing.googleapis.com/https/request_count` | Counter | Number of requests per LB | Alert if 0 for 5 min |
| `loadbalancing.googleapis.com/https/request_bytes` | Counter | Total request bytes | Baseline for traffic |
| `loadbalancing.googleapis.com/https/response_bytes` | Counter | Total response bytes | Baseline for traffic |
| `loadbalancing.googleapis.com/https/backend_latencies` | Distribution | Backend response time in ms | P99 > 5s → alert |
| `loadbalancing.googleapis.com/https/backend_request_bytes` | Counter | Bytes sent to backends | Alert if 0 |
| `loadbalancing.googleapis.com/https/total_latencies` | Distribution | End-to-end latency in ms | P99 > 10s → alert |
| `loadbalancing.googleapis.com/https/backend_serving_errors` | Counter | Backend 5xx errors | Alert if > 1% |
| `loadbalancing.googleapis.com/https/frontend_serving_errors` | Counter | LB-generated errors (502) | Alert if > 0 |
| `loadbalancing.googleapis.com/https/egress_latencies` | Distribution | Egress latency | Baseline |
| `loadbalancing.googleapis.com/https/grpc_*` | Various | gRPC metrics | Per gRPC code |

## Key Metrics for Passthrough / Proxy Network LB

| Metric | Type | Description |
|--------|------|-------------|
| `compute.googleapis.com/loadbalancing/passthrough/forwarding_rule/backend_healthy_count` | Gauge | Number of healthy backends |
| `compute.googleapis.com/loadbalancing/passthrough/forwarding_rule/backend_unhealthy_count` | Gauge | Number of unhealthy backends |
| `compute.googleapis.com/loadbalancing/passthrough/forwarding_rule/packets` | Counter | Packet count |
| `compute.googleapis.com/loadbalancing/passthrough/forwarding_rule/bytes` | Counter | Byte count |
| `compute.googleapis.com/loadbalancing/proxy/active_connections` | Gauge | Active connections |
| `compute.googleapis.com/loadbalancing/proxy/new_connections` | Counter | New connections / sec |

## Cloud Monitoring Setup

### Dashboards

Create a dedicated dashboard for each LB:

```bash
gcloud monitoring dashboards create \
  --config-from-file=lb-dashboard.yaml \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

**Recommended dashboard widgets:**
- Request count timeseries (1h, 6h, 24h)
- P50/P95/P99 latency timeseries
- Backend 5xx error rate (percentage)
- Frontend error count (502/503)
- Healthy backend count
- Request distribution by backend (top-N)

### Alert Policies

**Zero healthy backends (critical):**
```bash
gcloud alpha monitoring policies create \
  --display-name="LB-Zero-Healthy-Backends" \
  --condition-filter='metric.type="loadbalancing.googleapis.com/https/backend_latencies"' \
  --condition-threshold-value=0 \
  --condition-duration=300s \
  --notification-channels="{{user.notification_channel}}"
```

**High backend latency (P99 > 5s):**
- Metric: `loadbalancing.googleapis.com/https/backend_latencies`
- Condition: P99 > 5000ms for 5 minutes
- Severity: Warning

**High error rate (> 1% 5xx):**
- Metric: `loadbalancing.googleapis.com/https/backend_serving_errors`
- Condition: rate > 0.01 for 5 minutes
- Severity: Critical

## Anomaly Patterns

| Pattern | Indicator | Likely Cause |
|---------|-----------|--------------|
| Sudden request drop to 0 | request_count = 0 | DNS change, forwarding rule deleted, client routing change |
| Spiky P99 latency | backend_latencies P99 > 10x baseline | Backend overload, autoscaling lag |
| Gradual error increase | backend_serving_errors trending up | Backend degradation (memory leak, DB slow) |
| All backends unhealthy | healthy_backend_count = 0 | Health check misconfig, firewall blocking probes |
| SSL cert failures | frontend_serving_errors 502/526 | Managed cert failed to provision, cert expired |