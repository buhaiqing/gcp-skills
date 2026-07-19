# Monitoring & Alerts — Cloud CDN

## Key Metrics

Cloud CDN metrics are available in the `loadbalancing.googleapis.com` namespace.

### Cache Metrics

| Metric | Type | Description | Unit |
|--------|------|-------------|------|
| `cache.hit_ratio` | GAUGE | Ratio of cache hits to total requests | Fraction (0-1) |
| `cache.hit_bytes_count` | DELTA | Bytes served from cache | bytes |
| `cache.hit_count` | DELTA | Number of cache hits | count |
| `cache.lookup_count` | DELTA | Number of cache lookups | count |
| `cache.fill_bytes_count` | DELTA | Bytes filled into cache from origin | bytes |
| `cache.fill_count` | DELTA | Number of cache fills from origin | count |

### Request Metrics

| Metric | Type | Description | Unit |
|--------|------|-------------|------|
| `https/request_bytes_count` | DELTA | Total request bytes received | bytes |
| `https/response_bytes_count` | DELTA | Total response bytes sent | bytes |
| `https/total_latencies` | DELTA | Total latency distribution | milliseconds |
| `https/frontend_request_count` | DELTA | Total number of requests | count |

### Origin Metrics

| Metric | Type | Description | Unit |
|--------|------|-------------|------|
| `https/backend_request_count` | DELTA | Requests sent to backend | count |
| `https/backend_response_bytes_count` | DELTA | Response bytes from backend | bytes |
| `https/backend_latencies` | DELTA | Backend latency distribution | milliseconds |

### Error Metrics

| Metric | Type | Description | Unit |
|--------|------|-------------|------|
| `https/response_bytes_count` (with code filter) | DELTA | Responses by status code | count |
| `https/total_latencies` (with code filter) | DELTA | Latency by status code | milliseconds |

## Cloud Monitoring Setup

### Dashboard: CDN Overview

Create a dashboard with the following widgets:

1. **Cache Hit Ratio** (Time series)
   - Metric: `loadbalancing.googleapis.com/loadbalancing.googleapis.com/https/request_bytes_count`
   - Filter: `resource.label.backend_target_name="{{user.backend_name}}"`
   - Aggregation: Ratio of cache hits to total requests

2. **Cache Fill Rate** (Time series)
   - Metric: `fill_count`
   - Aggregation: Rate per second

3. **Request Latency** (Time series)
   - Metric: `https/total_latencies`
   - Aggregation: p50, p95, p99 percentiles

4. **Error Rate** (Time series)
   - Metric: Response count filtered by status code >= 500
   - Aggregation: Rate per second

### Alert Policies

#### Alert 1: Cache Hit Ratio Drop

| Property | Value |
|----------|-------|
| Metric | `cache.hit_ratio` |
| Condition | Value < 0.8 for 5 minutes |
| Severity | Warning |
| Notification | Email, PagerDuty |
| Runbook | Check cache mode, TTL settings, origin headers |

#### Alert 2: High Error Rate

| Property | Value |
|----------|-------|
| Metric | Response count with status >= 500 |
| Condition | Rate > 1 per second for 2 minutes |
| Severity | Critical |
| Notification | PagerDuty, SMS |
| Runbook | Check backend health, origin availability |

#### Alert 3: Backend Latency Spike

| Property | Value |
|----------|-------|
| Metric | `https/backend_latencies` (p99) |
| Condition | Value > 5000ms for 5 minutes |
| Severity | Warning |
| Notification | Email |
| Runbook | Check origin performance, network connectivity |

## gcloud Commands for Monitoring

```bash
# Read time series data for cache hit ratio
gcloud monitoring time-series list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --filter='metric.type="loadbalancing.googleapis.com/loadbalancing/cache.hit_ratio" AND resource.type="http_load_balancer"' \
  --interval-start-time=$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --interval-end-time=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --format="json"

# List all CDN-related metrics for a backend service
gcloud monitoring time-series list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --filter='metric.type=~"loadbalancing.googleapis.com/.*" AND resource.label.backend_target_name="{{user.backend_name}}"' \
  --interval-start-time=$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --interval-end-time=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --format="json"
```

## Log-Based Metrics

Create log-based metrics from Cloud Logging for custom CDN analysis:

### Cache Miss Rate by Path

```
resource.type="http_load_balancer"
jsonPayload.statusDetails="backend_response"
```

### Signed URL Validation Failures

```
resource.type="http_load_balancer"
jsonPayload.statusDetails="denied_by_security_policy"
```

## Integration with gcp-monitoring-ops

For comprehensive monitoring setup, dashboards, and alert management, delegate to [gcp-monitoring-ops](../../gcp-monitoring-ops/SKILL.md).
