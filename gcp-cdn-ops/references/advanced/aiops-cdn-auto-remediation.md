# AIOps Auto-Remediation — Google Cloud CDN

> Provides CDN operators with guarded, idempotent automated remediation runbooks for Cloud CDN anomalies — origin failover, TTL adjustment, and cache purge. Every mutating action includes a **dry-run** and a **human-review gate**. Aligns with `gcp-cdn-ops` SKILL.md (origins, cache policies, signed URLs).

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Remediation Catalog](#remediation-catalog)
4. [Origin Failover](#origin-failover)
5. [TTL Adjustment](#ttl-adjustment)
6. [Cache Purge (Invalidation)](#cache-purge-invalidation)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)
9. [See Also](#see-also)

## Overview

Auto-remediation responds to anomalies detected by `aiops-cdn-anomaly-detection.md`. All mutating actions follow the same safety contract:

- **Dry-run first**: Print the exact command and target, make no changes.
- **Human-review gate**: Destructive or traffic-impacting actions require `--confirm` or explicit operator approval.
- **Idempotent**: Re-running the same action yields the same end state.
- **Credential masking (§0.1)**: Never print SA key content.

### Remediation Catalog

| Action | Trigger | Risk | Gate |
|--------|---------|------|------|
| Origin failover | Origin 5xx > 5% | **High** | HALT + `--confirm` |
| TTL adjustment | Hit ratio < 80% | Medium | `--confirm` |
| Cache purge | Stale content / bad deploy | Medium | `--confirm` |

## Prerequisites

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| gcloud CLI | `gcloud version` | Exit 0 | HALT — install gcloud |
| Credentials | `gcloud auth print-access-token --quiet` | Token valid | HALT — authenticate |
| CDN backend exists | `gcloud compute backend-services describe {{user.backend_name}} --global --quiet` | Exit 0 | HALT — create via `gcp-lb-ops` |

## Origin Failover

Switch traffic away from a failing origin backend group to a healthy standby.

### Step 1 — Dry-Run (inspect current backends)

```bash
gcloud compute backend-services describe "{{user.backend_name}}" \
  --global --format="json" | jq '.backends[] | {group: .group, capacityScaler: .capacityScaler}'
```

### Step 2 — Validate standby health

```bash
# Confirm standby group is healthy before failing over
gcloud compute backend-services describe "{{user.standby_backend}}" \
  --global --format="json" | jq '{enableCdn: .enableCdn, backends: [.backends[] | .group]}'
```

### Step 3 — Execute (HALT — requires explicit confirmation)

```bash
# DRAIN failing origin: set capacityScaler=0 (non-destructive, reversible)
gcloud compute backend-services update "{{user.backend_name}}" \
  --global \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" \
  --backend='{"group":"{{user.failing_group}}","capacityScaler":0}'
```

> **HALT:** Origin failover changes production traffic routing. MUST confirm: `Proceed with draining {{user.failing_group}} on {{user.backend_name}}? Type the backend name to confirm:`. Do NOT use `--quiet`.

### Step 4 — Validate

```bash
gcloud compute backend-services describe "{{user.backend_name}}" \
  --global --format="json" | jq '.backends[] | select(.group=="{{user.failing_group}}") | .capacityScaler'
```

Verify `capacityScaler` is `0`. **Idempotent**: re-applying `capacityScaler=0` is a no-op.

## TTL Adjustment

Raise TTLs to recover cache hit ratio during a predicted or active miss storm.

### Step 1 — Dry-Run (preview current policy)

```bash
gcloud compute backend-services describe "{{user.backend_name}}" \
  --global --format="json" | jq '.cdnPolicy | {cacheMode, defaultTtl, maxTtl, clientTtl}'
```

### Step 2 — Execute (requires confirmation)

```bash
gcloud compute backend-services update "{{user.backend_name}}" \
  --enable-cdn \
  --cache-mode="{{user.cache_mode:-CACHE_ALL_STATIC}}" \
  --default-ttl="{{user.default_ttl:-86400}}" \
  --max-ttl="{{user.max_ttl:-86400}}" \
  --client-ttl="{{user.client_ttl:-86400}}" \
  --global \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

> **Gate:** MUST warn "Changing CDN policy affects cache behavior within ~60s" and confirm before applying. TTL values must satisfy `0 < default_ttl ≤ max_ttl ≤ 86400`.

### Step 3 — Validate

```bash
gcloud compute backend-services describe "{{user.backend_name}}" \
  --global --format="json" | jq '.cdnPolicy.defaultTtl'
```

Verify `defaultTtl` matches request. **Idempotent**: same values → no behavioral change.

## Cache Purge (Invalidation)

Purge stale or bad-deploy content by host/path pattern.

### Step 1 — Dry-Run (list what would be purged)

```bash
# Preview target without invalidating
echo "Would invalidate: host=*{{user.host_rule}} path={{user.path_pattern}} on {{user.url_map}}"
gcloud compute url-maps describe "{{user.url_map}}" --global --format="json" | jq '.name'
```

### Step 2 — Execute (requires confirmation)

```bash
gcloud compute url-maps invalidate-cache "{{user.url_map}}" \
  --host="*{{user.host_rule}}" \
  --path="{{user.path_pattern}}" \
  --global \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

> **Gate:** MUST confirm: `Proceed with cache purge on {{user.url_map}} (host=*{{user.host_rule}}, path={{user.path_pattern}})? Type the URL map name to confirm:`. Prefer targeted path patterns over wildcards to minimize origin load spike.

### Step 3 — Validate

```bash
OPERATION_ID=$(gcloud compute url-maps invalidate-cache "{{user.url_map}}" \
  --host="*{{user.host_rule}}" --path="{{user.path_pattern}}" \
  --global --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" | jq -r '.name')
gcloud compute operations describe "$OPERATION_ID" --global --format="json" | jq '.status'
```

Verify status is `DONE`. **Idempotent**: re-invalidating same path is safe (cache already cleared).

## Best Practices

### Gate Summary

| Action | Dry-run | Human gate | Idempotent |
|--------|---------|-----------|------------|
| Origin failover | Yes (inspect) | HALT + `--confirm` | Yes |
| TTL adjustment | Yes (preview) | `--confirm` | Yes |
| Cache purge | Yes (list) | `--confirm` | Yes |

### Rollback

- Origin failover: set `capacityScaler` back to `1`.
- TTL adjustment: re-apply previous TTL values.
- Cache purge: no rollback needed (content re-cached on next request).

## Troubleshooting

### Issue: Failover not taking effect

**Diagnosis:** Check `capacityScaler` and health check status.
**Solution:** Verify standby group health; ensure `capacityScaler=0` applied.

### Issue: TTL change ignored

**Diagnosis:** Cache mode may override TTL (e.g. `USE_ORIGIN_HEADERS`).
**Solution:** Switch to `CACHE_ALL_STATIC` or align origin `Cache-Control`.

### Error Taxonomy

| Error | Cause | Resolution |
|-------|-------|------------|
| `PERMISSION_DENIED` | SA lacks update role | HALT — grant `roles/compute.loadBalancerAdmin` |
| `NOT_FOUND` | Backend/URL map missing | HALT — verify name |
| `resourceInUse` | Concurrent op | Retry after 30s |

## See Also

- [CDN Anomaly Detection](./aiops-cdn-anomaly-detection.md)
- [CDN Prediction](./aiops-cdn-prediction.md)
- [CDN Cost Analysis](./finops-cdn-cost-analysis.md)
- [Error Taxonomy](../../../docs/error-taxonomy.md)
- [Cross-Skill Blast Radius](../../../docs/cross-skill-blast-radius.md)
