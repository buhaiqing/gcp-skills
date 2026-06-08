# Monitoring — Cloud Functions

## Cloud Monitoring Metrics

### Invocation Metrics

| Metric | Type | Unit | Description |
|--------|------|------|-------------|
| `cloudfunctions.googleapis.com/function/active_instances` | Gauge | count | Number of active function instances |
| `cloudfunctions.googleapis.com/function/execution_count` | Delta | count | Number of function executions |
| `cloudfunctions.googleapis.com/function/execution_times` | Delta | ms | Function execution time (latency) |
| `cloudfunctions.googleapis.com/function/user_memory_bytes` | Gauge | bytes | Memory used by function |
| `cloudfunctions.googleapis.com/function/network_egress` | Delta | bytes | Network bytes sent from function |

### Instance Metrics

| Metric | Type | Unit | Description |
|--------|------|------|-------------|
| `cloudfunctions.googleapis.com/function/container/cpu/utilizations` | Delta | ratio | CPU utilization (0.0–1.0) |
| `cloudfunctions.googleapis.com/function/container/startup_latency` | Delta | ms | Container startup time (cold start) |
| `cloudfunctions.googleapis.com/function/instance_count` | Gauge | count | Total instances (running + starting) |

### Error Metrics

| Metric | Type | Unit | Description |
|--------|------|------|-------------|
| `cloudfunctions.googleapis.com/function/execution_errors` | Delta | count | Number of execution errors |
| `cloudfunctions.googleapis.com/function/5xx_count` | Delta | count | HTTP 5xx responses |

### Billing Metrics

| Metric | Type | Unit | Description |
|--------|------|------|-------------|
| `cloudfunctions.googleapis.com/function/billed_execution_times` | Delta | ms | Billable execution time |

## Recommended Dashboards

### Function Health Dashboard

```
Dashboard: "Cloud Functions - Function Health"
├── Panel 1: Execution Count (last 1h, 6h, 24h)
│   metric: execution_count
│   group_by: function_name
│   alert: > 0 (function is being called)
├── Panel 2: Error Rate (%)
│   metric: execution_errors / execution_count * 100
│   alert: > 5% (high error rate)
├── Panel 3: P95 Latency
│   metric: execution_times (95th percentile)
│   alert: > timeout_seconds * 0.8 (approaching timeout)
├── Panel 4: Active Instances
│   metric: active_instances
│   alert: > max_instance_count * 0.9 (near limit)
└── Panel 5: Memory Usage
    metric: user_memory_bytes / available_memory * 100
    alert: > 90% (near OOM)
```

### Cost Monitoring Dashboard

```
Dashboard: "Cloud Functions - Cost"
├── Panel 1: Billed Execution Time (GB-seconds)
│   metric: billed_execution_times * available_memory / 1e9
│   alert: > 80% of free tier (400,000 GB-s/month)
├── Panel 2: Invocation Count
│   metric: execution_count
│   alert: > 2M/month (free tier limit)
├── Panel 3: Network Egress
│   metric: network_egress
│   alert: > expected threshold
└── Panel 4: Instance Hours
    metric: active_instances (sum over time)
    alert: > budget threshold
```

## Alert Policies

### Critical Alerts

| Alert | Condition | Severity | Action |
|-------|-----------|----------|--------|
| Function Error Rate > 10% | `execution_errors / execution_count > 0.1` (5 min window) | P0 | Page on-call; check logs |
| Function Down | `active_instances == 0` AND `state != ACTIVE` (2 min) | P0 | Page on-call; redeploy |
| P99 Latency > Timeout | `execution_times.p99 > timeout * 0.9` (5 min) | P1 | Investigate; increase timeout |
| Memory > 95% | `user_memory_bytes / available_memory > 0.95` (5 min) | P1 | Increase memory; optimize code |
| Instances at Max | `active_instances / max_instance_count > 0.9` (5 min) | P2 | Increase max-instances |
| Cold Start > 5s | `container/startup_latency > 5000` (1 min) | P2 | Set min-instances > 0 |

### Warning Alerts

| Alert | Condition | Severity | Action |
|-------|-----------|----------|--------|
| Error Rate > 5% | `execution_errors / execution_count > 0.05` (15 min) | P2 | Check logs; investigate |
| Latency Degradation | `execution_times.p50 > 2x baseline` (15 min) | P2 | Investigate; check dependencies |
| Execution Count Drop | `execution_count < 50% of baseline` (1h) | P3 | Check trigger/source health |
| Quota Warning | Quota utilization > 80% | P2 | Request quota increase |

## Log-Based Metrics

Create custom metrics from Cloud Functions logs:

### Error Count by Type

```bash
# Create log-based metric for function errors
gcloud logging metrics create "cloudfunctions/error-by-type" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --description="Cloud Functions errors by type" \
  --log-filter='resource.type="cloud_function" AND severity="ERROR"'
```

### Cold Start Count

```bash
# Create log-based metric for cold starts
gcloud logging metrics create "cloudfunctions/cold-starts" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --description="Cloud Functions cold start events" \
  --log-filter='resource.type="cloud_function" AND textPayload:"cold start"'
```

### Custom Business Logic Metric

```bash
# Create log-based metric for custom events (e.g., payment failures)
gcloud logging metrics create "cloudfunctions/payment-failures" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --description="Payment processing failures" \
  --log-filter='resource.type="cloud_function" AND textPayload:"payment_failed"'
```

## SLO Recommendations

| SLO | Target | Measurement |
|-----|--------|-------------|
| Availability | 99.95% (monthly) | `execution_count - execution_errors / execution_count` |
| Latency (P95) | < 1000ms | `execution_times.p95` |
| Latency (P99) | < 3000ms | `execution_times.p99` |
| Cold Start | < 2s (50th percentile) | `container/startup_latency.p50` |
| Error Rate | < 0.1% | `execution_errors / execution_count` |

## Cloud Logging Queries

### Recent Errors

```
resource.type="cloud_function"
resource.labels.function_name="{{user.function_name}}"
severity="ERROR"
```

### All Function Logs

```
resource.type="cloud_function"
resource.labels.function_name="{{user.function_name}}"
```

### Slow Executions

```
resource.type="cloud_function"
resource.labels.function_name="{{user.function_name}}"
textPayload:"execution took"
```

### Cold Starts

```
resource.type="cloud_function"
resource.labels.function_name="{{user.function_name}}"
textPayload:"cold start"
```

### Specific Time Range

```
resource.type="cloud_function"
resource.labels.function_name="{{user.function_name}}"
timestamp >= "2026-06-08T00:00:00Z"
timestamp <= "2026-06-08T23:59:59Z"
```

## Cloud Trace Integration

Cloud Functions automatically integrates with Cloud Trace. Each invocation generates a trace span with:

- **Function invocation**: Main span with execution time
- **HTTP client calls**: Child spans for outgoing requests
- **Cloud SDK calls**: Child spans for GCP API calls

View traces:
```bash
# View traces for a function
gcloud trace list --filter="cloud_function_name={{user.function_name}}" --limit=10
```

> **Delegation**: For advanced trace analysis, dashboards, and alerting, delegate to `gcp-monitoring-ops`.
