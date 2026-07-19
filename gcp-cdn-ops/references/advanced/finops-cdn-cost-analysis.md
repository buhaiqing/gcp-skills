# FinOps Cost Analysis — Google Cloud CDN

> Provides FinOps practitioners with a guide to Cloud CDN bandwidth cost analysis and optimization — egress breakdown, cache efficiency vs cost, and optimization levers. Aligns with `gcp-cdn-ops` SKILL.md (origins, cache policies, signed URLs).

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Cost Model](#cost-model)
4. [Egress Analysis](#egress-analysis)
5. [Cache Efficiency vs Cost](#cache-efficiency-vs-cost)
6. [Optimization Levers](#optimization-levers)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)
9. [See Also](#see-also)

## Overview

Cloud CDN reduces egress cost by serving content from edge caches instead of origin. FinOps analysis quantifies savings and identifies waste:

- Break down egress by backend, region, and content type
- Measure cache hit ratio impact on origin egress cost
- Identify optimization levers (TTL, cache mode, negative caching)
- Project monthly spend from traffic forecasts (see `aiops-cdn-prediction.md`)

### Cost Drivers

| Driver | Impact | Lever |
|--------|--------|-------|
| Edge egress | Lower rate than origin | Maximize cache hit |
| Origin egress (miss) | Full internet egress rate | Improve hit ratio |
| Cache invalidation | Minimal, per operation | Targeted purges only |
| Log storage | Secondary | Sampling + retention |

## Prerequisites

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Billing enabled | `gcloud billing accounts list` | Account linked | HALT — link billing |
| BigQuery enabled | `gcloud services list --enabled --filter="name:bigquery.googleapis.com"` | Enabled | `gcloud services enable bigquery.googleapis.com` |
| CDN backend exists | `gcloud compute backend-services describe {{user.backend_name}} --global --quiet` | Exit 0 | HALT — create via `gcp-lb-ops` |

> **Credential Masking (§0.1):** Never print SA key content. Use `gcloud billing` read-only commands.

## Cost Model

Cloud CDN egress is billed at the CDN edge rate (lower than standard internet egress). Origin egress for cache misses is billed at the full rate.

```
monthly_cost ≈ (edge_egress_gb × edge_rate) + (origin_miss_gb × origin_rate)
```

| Component | Typical Rate (illustrative) | Notes |
|-----------|------------------------------|-------|
| CDN edge egress | ~$0.04–0.08 / GB | Varies by region tier |
| Origin internet egress | ~$0.12 / GB | Full rate |
| Cache invalidation | ~$0.005 / op | Minimal |

> Rates are illustrative; query live pricing via `gcp-billing-ops`.

## Egress Analysis

### Egress by Backend

```sql
-- BigQuery: Monthly egress per backend
SELECT
  resource.labels.backend_service_name AS backend,
  SUM(CAST(jsonPayload.egressBytes AS INT64)) / 1073741824 AS egress_gb
FROM `{{env.CLOUDSDK_CORE_PROJECT}}.{{user.dataset}}.cdn_requests`
WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY backend
ORDER BY egress_gb DESC
```

### Egress by Content Type

```sql
-- BigQuery: Egress by response content type
SELECT
  jsonPayload.responseContentType AS content_type,
  SUM(CAST(jsonPayload.egressBytes AS INT64)) / 1073741824 AS egress_gb
FROM `{{env.CLOUDSDK_CORE_PROJECT}}.{{user.dataset}}.cdn_requests`
WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY content_type
ORDER BY egress_gb DESC
LIMIT 20
```

## Cache Efficiency vs Cost

Higher cache hit ratio directly reduces origin egress cost.

```sql
-- BigQuery: Hit ratio and implied origin egress
SELECT
  resource.labels.backend_service_name AS backend,
  COUNT(*) AS total,
  COUNTIF(jsonPayload.cacheHit = true) AS hits,
  SAFE_DIVIDE(COUNTIF(jsonPayload.cacheHit = true), COUNT(*)) AS hit_ratio,
  SUM(CASE WHEN jsonPayload.cacheHit = false THEN CAST(jsonPayload.egressBytes AS INT64) ELSE 0 END) / 1073741824 AS origin_miss_gb
FROM `{{env.CLOUDSDK_CORE_PROJECT}}.{{user.dataset}}.cdn_requests`
WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY backend
ORDER BY origin_miss_gb DESC
```

### Savings Quantification

| Hit Ratio | Origin Miss % | Relative Origin Cost |
|-----------|--------------|----------------------|
| 95% | 5% | 1.0x (baseline) |
| 80% | 20% | 4.0x |
| 60% | 40% | 8.0x |

> Every 10-point hit-ratio gain can cut origin egress cost by ~2x. See `aiops-cdn-auto-remediation.md` for TTL tuning.

## Optimization Levers

| Lever | Savings | Implementation |
|-------|---------|----------------|
| Raise `default_ttl` | 20-40% | `gcloud compute backend-services update --default-ttl` |
| `FORCE_CACHE_ALL` for static | 30-50% | Set cache mode for asset backends |
| Negative caching (5xx) | 10-20% | `--negative-caching` short TTL |
| Targeted purge only | 5-10% | Avoid wildcard invalidation |
| Cloud Storage origin | 20-30% | Lower origin egress vs compute |

### Example Optimization

```
Scenario: 1 backend, 100 TB/month egress, 80% hit ratio
Before:
  Edge egress: 80 TB × $0.06 = $4,800
  Origin miss: 20 TB × $0.12 = $2,400
  Total: $7,200/month

After (raise hit ratio to 95%):
  Edge egress: 95 TB × $0.06 = $5,700
  Origin miss: 5 TB × $0.12 = $600
  Total: $6,300/month
  Savings: $900/month (12.5%)
```

## Best Practices

### Cost Review Cadence

| Review | Cadence | Focus |
|--------|---------|-------|
| Egress trend | Weekly | Spike detection |
| Hit ratio | Daily | Efficiency drift |
| Lever audit | Monthly | TTL/cache mode tuning |

### Guardrails

- Never lower TTL below content-update frequency (staleness risk)
- Prefer `CACHE_ALL_STATIC` over `FORCE_CACHE_ALL` for mixed content
- Budget pre-warm egress (see `aiops-cdn-prediction.md`)

## Troubleshooting

### Issue: Egress higher than expected

**Diagnosis:** Check hit ratio and miss-heavy content types.
**Solution:** Raise TTL for static assets; enable negative caching.

### Issue: Cost not decreasing after TTL raise

**Diagnosis:** Cache mode may be `USE_ORIGIN_HEADERS` (origin controls TTL).
**Solution:** Switch to `CACHE_ALL_STATIC` or fix origin `Cache-Control`.

### Error Taxonomy

| Error | Cause | Resolution |
|-------|-------|------------|
| `No egress data` | Logs not exported | Verify log sink |
| `Hit ratio stuck low` | Cache mode mismatch | Align cache mode |
| `Billing query denied` | IAM missing | Grant billing viewer |

## See Also

- [CDN Anomaly Detection](./aiops-cdn-anomaly-detection.md)
- [CDN Prediction](./aiops-cdn-prediction.md)
- [CDN Auto-Remediation](./aiops-cdn-auto-remediation.md)
- [Billing Operations](../../../gcp-billing-ops/SKILL.md)
- [Error Taxonomy](../../../docs/error-taxonomy.md)
- [Cross-Skill Blast Radius](../../../docs/cross-skill-blast-radius.md)
