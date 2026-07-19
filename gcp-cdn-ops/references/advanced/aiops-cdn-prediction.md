# AIOps Prediction — Google Cloud CDN Capacity & Traffic

> Provides CDN operators with a guide to capacity and traffic prediction for Cloud CDN — forecast egress volume, plan edge capacity, and pre-warm cache before traffic spikes. Aligns with `gcp-cdn-ops` SKILL.md (cache modes, TTL, origins).

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Traffic Signals](#traffic-signals)
4. [Capacity Prediction](#capacity-prediction)
5. [Cache Pre-Warming](#cache-pre-warming)
6. [Forecast-Driven TTL Tuning](#forecast-driven-ttl-tuning)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)
9. [See Also](#see-also)

## Overview

AIOps prediction uses historical CDN telemetry to forecast traffic and capacity needs, enabling proactive cache pre-warming and TTL tuning before demand spikes (campaigns, product launches, viral events). Goals:

- Forecast egress bandwidth and request volume (capacity planning)
- Pre-warm edge cache to avoid origin overload at spike onset
- Tune TTLs ahead of predictable traffic patterns
- Reduce cache miss storms during sudden load

### Prediction Capabilities

| Prediction Type | Input | Output | Lead Time |
|-----------------|-------|--------|-----------|
| Egress volume | 30-day hourly egress | 24-72h forecast | 1-3 days |
| Request rate | Request count time series | Peak QPS estimate | 1-3 days |
| Cache miss risk | Hit ratio trend + forecast | Pre-warm target list | Same day |
| Cost projection | Egress forecast × pricing | Daily $ estimate | 1-3 days |

## Prerequisites

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Monitoring enabled | `gcloud services list --enabled --filter="name:monitoring.googleapis.com"` | Enabled | `gcloud services enable monitoring.googleapis.com` |
| BigQuery enabled | `gcloud services list --enabled --filter="name:bigquery.googleapis.com"` | Enabled | `gcloud services enable bigquery.googleapis.com` |
| CDN backend exists | `gcloud compute backend-services describe {{user.backend_name}} --global --quiet` | Exit 0 | HALT — create backend via `gcp-lb-ops` first |

> **Credential Masking (§0.1):** Verify SA existence only — never print key content.

## Traffic Signals

### Collect Historical Egress

```bash
# Export 30-day hourly egress to BigQuery via log sink, then query baseline
gcloud monitoring time-series list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --filter='metric.type="loadbalancing.googleapis.com/https/response_count" AND resource.type="https_lb_rule"' \
  --interval=2592000s \
  --format="json" | jq '[.timeSeries[] | {backend: .resource.labels.backend_service_name}]'
```

### Peak QPS Estimate

```sql
-- BigQuery: Peak requests per minute over last 30 days
SELECT
  resource.labels.backend_service_name AS backend,
  TIMESTAMP_TRUNC(timestamp, MINUTE) AS minute,
  COUNT(*) AS requests
FROM `{{env.CLOUDSDK_CORE_PROJECT}}.{{user.dataset}}.cdn_requests`
WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY backend, minute
ORDER BY requests DESC
LIMIT 100
```

## Capacity Prediction

### Forecast Model

```sql
-- ARIMA_PLUS forecast of request volume
CREATE OR REPLACE MODEL `{{env.CLOUDSDK_CORE_PROJECT}}.{{user.dataset}}.cdn_traffic_forecast`
OPTIONS(
  model_type='ARIMA_PLUS',
  time_series_timestamp_col='timestamp',
  time_series_data_col='requests'
) AS
SELECT
  TIMESTAMP_TRUNC(timestamp, HOUR) AS timestamp,
  COUNT(*) AS requests
FROM `{{env.CLOUDSDK_CORE_PROJECT}}.{{user.dataset}}.cdn_requests`
WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY timestamp;
```

```sql
-- 72h forecast with confidence bands
SELECT
  forecast_timestamp,
  forecast_value,
  prediction_interval_lower_bound,
  prediction_interval_upper_bound
FROM ML.FORECAST(
  MODEL `{{env.CLOUDSDK_CORE_PROJECT}}.{{user.dataset}}.cdn_traffic_forecast`,
  STRUCT(72 AS horizon, 0.9 AS confidence_level)
)
ORDER BY forecast_timestamp
```

### Capacity Decision

| Forecast Peak QPS | Action |
|-------------------|--------|
| < 1.2x baseline | No action |
| 1.2x – 2x baseline | Pre-warm cache (see below) |
| > 2x baseline | Pre-warm + notify on-call + verify origin autoscaling |

## Cache Pre-Warming

Pre-warming fills edge caches with predicted-hot objects before traffic arrives, reducing origin load at spike onset.

### Dry-Run Pre-Warm (list targets only)

```bash
# Identify top-N hot paths from historical logs — no requests sent
gcloud logging read \
  'resource.type="https_lb_rule" AND jsonPayload.cacheHit=true' \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --freshness=7d \
  --format=json | jq -r '.[].httpRequest.requestUrl' | sort | uniq -c | sort -rn | head -50
```

> **Idempotent:** Pre-warm requests are read-only GETs; repeating them only refreshes cache, no state change.

### Execute Pre-Warm

```bash
# Warm cache by requesting hot paths through the LB (origin offload)
for url in $(cat /tmp/hot_paths.txt); do
  curl -s -o /dev/null -w "%{http_code} $url\n" "$url"
done
```

> **Gate:** Only run after dry-run confirms target list. Pre-warm traffic counts as egress — budget accordingly (see `finops-cdn-cost-analysis.md`).

## Forecast-Driven TTL Tuning

When a traffic spike is predicted, raise TTLs to maximize cache hits during the window:

```bash
# Preview current TTL before change (dry-run inspect)
gcloud compute backend-services describe "{{user.backend_name}}" \
  --global --format="json" | jq '.cdnPolicy.defaultTtl'
```

> **Safety:** TTL changes affect cache behavior within ~60s. Apply only during predicted low-traffic windows; revert after spike. See `aiops-cdn-auto-remediation.md` for guarded execution.

## Best Practices

### Forecast Cadence

| Signal | Retrain | Horizon |
|--------|---------|---------|
| Traffic volume | Daily | 72h |
| Egress cost | Daily | 7d |
| Cache miss risk | Hourly (event-driven) | Same day |

### Pre-Warm Strategy

| Scenario | Pre-warm lead | Scope |
|----------|---------------|-------|
| Known campaign | 2h before | Top 100 paths |
| Unexpected viral | Immediate | Top 50 paths |
| Recurring peak | Weekly | Full asset set |

## Troubleshooting

### Issue: Forecast accuracy low

**Diagnosis:** Check training window coverage and outliers.
**Solution:** Extend window to 60 days; exclude known anomaly periods.

### Issue: Pre-warm incomplete

**Diagnosis:** Verify LB endpoint reachable and paths valid.
**Solution:** Re-run dry-run list; check for 4xx in warm responses.

### Error Taxonomy

| Error | Cause | Resolution |
|-------|-------|------------|
| `Model training fails` | Insufficient history | Extend window |
| `Pre-warm 4xx` | Wrong path | Fix URL list |
| `Forecast stale` | No retrain | Schedule daily retrain |

## See Also

- [CDN Anomaly Detection](./aiops-cdn-anomaly-detection.md)
- [CDN Auto-Remediation](./aiops-cdn-auto-remediation.md)
- [CDN Cost Analysis](./finops-cdn-cost-analysis.md)
- [Error Taxonomy](../../docs/error-taxonomy.md)
- [Cross-Skill Blast Radius](../../docs/cross-skill-blast-radius.md)
