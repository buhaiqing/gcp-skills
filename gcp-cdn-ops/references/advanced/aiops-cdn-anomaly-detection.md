# AIOps Anomaly Detection — Google Cloud CDN

> Provides CDN operators with a guide to implementing AIOps-driven anomaly detection for Cloud CDN — origin failure rate, cache hit ratio drops, and 5xx spikes. Aligns with `gcp-cdn-ops` SKILL.md (origins, cache policies, signed URLs).

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Detection Capabilities](#detection-capabilities)
4. [Metric-Based Detection](#metric-based-detection)
5. [Log-Based Detection](#log-based-detection)
6. [BigQuery ML Baseline](#bigquery-ml-baseline)
7. [Real-Time Alerting](#real-time-alerting)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)
10. [See Also](#see-also)

## Overview

AIOps (Artificial Intelligence for IT Operations) uses machine learning and statistical baselines to detect anomalies in Cloud CDN behavior. With Cloud Monitoring CDN metrics and Cloud Logging request logs, you can:

- Detect origin fetch failure rate spikes (origin health degradation)
- Identify cache hit ratio drops (cache policy misconfiguration or purge storms)
- Spot 5xx error rate surges (origin overload or backend misconfiguration)
- Track unusual egress volume (cost anomalies)
- Trigger automated remediation (see `aiops-cdn-auto-remediation.md`)

### Detection Capabilities

| Anomaly Type | Detection Method | Severity |
|--------------|-----------------|----------|
| Origin failure rate spike | `cdn.origin_requests` with 5xx / total > baseline | High |
| Cache hit ratio drop | `cdn.cache_hit_ratio` < 80% baseline | Medium |
| 5xx surge | `cdn.requests` with response_code_class=500 | High |
| Latency increase | `cdn.total_latencies` p95 shift | Low |
| Egress volume anomaly | `cdn.egress_bytes` > 2x baseline | Medium |

## Prerequisites

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Compute API enabled | `gcloud services list --enabled --filter="name:compute.googleapis.com"` | Enabled | `gcloud services enable compute.googleapis.com` |
| Monitoring enabled | `gcloud services list --enabled --filter="name:monitoring.googleapis.com"` | Enabled | `gcloud services enable monitoring.googleapis.com` |
| Logging enabled | `gcloud services list --enabled --filter="name:logging.googleapis.com"` | Enabled | `gcloud services enable logging.googleapis.com` |
| CDN backend exists | `gcloud compute backend-services describe {{user.backend_name}} --global --quiet` | Exit 0 | HALT — create backend via `gcp-lb-ops` first |

> **Credential Masking (§0.1):** Never print `GOOGLE_APPLICATION_CREDENTIALS` content. Verify existence only: `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA exists"`.

## Metric-Based Detection

### Origin Failure Rate Spike

```bash
# List CDN backends and capture origin error ratio over last 1h
gcloud monitoring time-series list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --filter='metric.type="loadbalancing.googleapis.com/https/backend_request_count" AND resource.type="https_lb_rule" AND metric.response_code_class="500"' \
  --interval=3600s \
  --format="json" | jq '[.timeSeries[] | {backend: .resource.labels.backend_service_name, points: [.points[].value.int64Value]}]'
```

### Cache Hit Ratio Drop

```bash
# Cache hit ratio (served from cache / total)
gcloud monitoring time-series list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --filter='metric.type="loadbalancing.googleapis.com/https/request_count" AND resource.type="https_lb_rule"' \
  --interval=3600s \
  --format="json" | jq '[.timeSeries[] | {backend: .resource.labels.backend_service_name, points: [.points[].value.int64Value]}]'
```

> Cache hit ratio is derived from `https/request_count` (cache hit vs miss). Alert when hit ratio drops below 80% (see SKILL.md Operational Best Practices).

### 5xx Surge

```bash
# 5xx response class count per backend
gcloud monitoring time-series list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --filter='metric.type="loadbalancing.googleapis.com/https/backend_request_count" AND metric.response_code_class="500"' \
  --interval=900s \
  --format="json" | jq '[.timeSeries[] | {backend: .resource.labels.backend_service_name, points: [.points[].value.int64Value]}]'
```

## Log-Based Detection

### Query for Origin Failures

```sql
-- BigQuery: Detect origin fetch failures (>5% of requests in window)
SELECT
  resource.labels.backend_service_name AS backend,
  COUNT(*) AS total_requests,
  COUNTIF(jsonPayload.responseCodeClass = '5xx') AS origin_5xx,
  SAFE_DIVIDE(
    COUNTIF(jsonPayload.responseCodeClass = '5xx'),
    COUNT(*)
  ) AS failure_ratio
FROM `{{env.CLOUDSDK_CORE_PROJECT}}.{{user.dataset}}.cdn_requests`
WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
GROUP BY backend
HAVING failure_ratio > 0.05
ORDER BY failure_ratio DESC
```

### Query for Cache Miss Storm

```sql
-- BigQuery: Detect cache hit ratio drop (miss rate > 20%)
SELECT
  resource.labels.backend_service_name AS backend,
  COUNT(*) AS total_requests,
  COUNTIF(jsonPayload.cacheHit = false) AS cache_misses,
  SAFE_DIVIDE(COUNTIF(jsonPayload.cacheHit = false), COUNT(*)) AS miss_ratio
FROM `{{env.CLOUDSDK_CORE_PROJECT}}.{{user.dataset}}.cdn_requests`
WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
GROUP BY backend
HAVING miss_ratio > 0.20
ORDER BY miss_ratio DESC
```

### Query for 5xx Spike

```sql
-- BigQuery: Detect 5xx surge per URL path
SELECT
  httpRequest.requestUrl AS url,
  COUNT(*) AS total,
  COUNTIF(httpRequest.status = 500 OR httpRequest.status = 502 OR httpRequest.status = 503) AS errors_5xx
FROM `{{env.CLOUDSDK_CORE_PROJECT}}.{{user.dataset}}.cdn_requests`
WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 15 MINUTE)
GROUP BY url
HAVING errors_5xx > 50
ORDER BY errors_5xx DESC
```

## BigQuery ML Baseline

### Create Baseline Model

```sql
-- Create ARIMA_PLUS model for daily egress baseline
CREATE OR REPLACE MODEL `{{env.CLOUDSDK_CORE_PROJECT}}.{{user.dataset}}.cdn_egress_baseline`
OPTIONS(
  model_type='ARIMA_PLUS',
  time_series_timestamp_col='timestamp',
  time_series_data_col='egress_bytes'
) AS
SELECT
  TIMESTAMP_TRUNC(timestamp, HOUR) AS timestamp,
  SUM(CAST(jsonPayload.egressBytes AS INT64)) AS egress_bytes
FROM `{{env.CLOUDSDK_CORE_PROJECT}}.{{user.dataset}}.cdn_requests`
WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY timestamp;
```

### Detect Anomalies

```sql
-- Flag egress outside prediction interval
SELECT
  timestamp,
  egress_bytes,
  prediction_interval_lower_bound,
  prediction_interval_upper_bound,
  CASE
    WHEN egress_bytes > prediction_interval_upper_bound THEN 'ANOMALY_HIGH'
    ELSE 'NORMAL'
  END AS anomaly_type
FROM ML.FORECAST(
  MODEL `{{env.CLOUDSDK_CORE_PROJECT}}.{{user.dataset}}.cdn_egress_baseline`,
  STRUCT(24 AS horizon, 0.95 AS confidence_level)
)
ORDER BY timestamp DESC
```

## Real-Time Alerting

### Create Alert Policy for Cache Hit Ratio

```bash
gcloud alpha monitoring policies create \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --policy='{
    "displayName": "CDN Cache Hit Ratio Drop",
    "conditions": [{
      "displayName": "Hit ratio below 80%",
      "conditionThreshold": {
        "filter": "metric.type=\"loadbalancing.googleapis.com/https/request_count\" AND resource.type=\"https_lb_rule\"",
        "comparison": "COMPARISON_LT",
        "thresholdValue": 0.8,
        "duration": "300s",
        "trigger": {"count": 1}
      }
    }],
    "notificationChannels": ["projects/{{env.CLOUDSDK_CORE_PROJECT}}/notificationChannels/{{user.channel_id}}"]
  }'
```

### Log Sink to Pub/Sub

```bash
gcloud logging sinks create "cdn-anomaly-sink" \
  pubsub.googleapis.com/projects/{{env.CLOUDSDK_CORE_PROJECT}}/topics/cdn-anomaly-alerts \
  --log-filter='resource.type="https_lb_rule" AND jsonPayload.responseCodeClass="5xx"' \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

## Best Practices

### Alert Thresholds

| Anomaly Type | Threshold | Severity |
|--------------|-----------|----------|
| Origin failure rate | >5% over 5 min | P1 |
| Cache hit ratio | <80% over 5 min | P2 |
| 5xx surge | >50 req/15min per path | P1 |
| Egress volume | >2x baseline | P2 |
| Latency p95 | >200ms shift | P3 |

### Sampling Strategy

| Signal | Cadence | Notes |
|--------|---------|-------|
| Monitoring metrics | 60s alignment | Native CDN metrics |
| Request logs | Sample 100% for critical backends | Use log sampling for cost control |
| ML baseline | Daily retrain | 30-day window |

## Troubleshooting

### Issue: Metrics not appearing

**Diagnosis:**
```bash
gcloud monitoring time-series list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --filter='metric.type="loadbalancing.googleapis.com/https/request_count"' \
  --interval=300s --format="json" | jq 'length'
```

**Solution:** Verify CDN is enabled on the backend (`gcloud compute backend-services describe {{user.backend_name}} --global --format='json' | jq '.enableCdn'`).

### Issue: False positives

**Solution:** Tune thresholds against 14-day historical baseline; prefer ML baseline over static thresholds.

### Error Taxonomy

| Error | Cause | Resolution |
|-------|-------|------------|
| `Metrics not appearing` | CDN not enabled | Enable CDN via `gcp-cdn-ops` |
| `High false positive` | Threshold too sensitive | Use ML baseline |
| `Log export delay` | Sink misconfigured | Verify log sink exists |
| `Pub/Sub message loss` | No subscription | Create subscription for topic |

## See Also

- [CDN Anomaly Auto-Remediation](./aiops-cdn-auto-remediation.md)
- [CDN Cost Analysis](./finops-cdn-cost-analysis.md)
- [CDN Monitoring Reference](../monitoring.md)
- [Error Taxonomy](../../docs/error-taxonomy.md)
- [Cross-Skill Blast Radius](../../docs/cross-skill-blast-radius.md)
