# Well-Architected Assessment — Cloud CDN

## Overview

This assessment maps Cloud CDN operations to the Google Cloud Architecture Framework five pillars. Each pillar includes design principles, implementation guidance, and risk mitigation strategies.

## 2.1 Security

### Principles
- Minimize origin exposure
- Enforce access controls at the edge
- Protect private content delivery

### Implementation

| Control | Method | Notes |
|---------|--------|-------|
| Signed URLs | `cdnPolicy.signedUrlKeys` | Time-limited, cryptographically-signed access |
| Cloud Armor | Security policies on backend service | DDoS protection, WAF rules, IP allow/deny lists |
| VPC Service Controls | Perimeter around CDN backend | Prevent data exfiltration |
| HTTPS origin | Backend protocol = HTTPS | Encrypt CDN-to-origin traffic |
| HTTPS to client | Load balancer SSL certificate | TLS termination at edge |
| IAM | roles/compute.loadBalancerAdmin | Least privilege for CDN management |
| Key rotation | 90-day schedule | Delete old keys, create new ones |

### Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Origin IP exposure | Use Cloud Armor; restrict origin to Google IP ranges |
| Hotlinking | Signed URLs; Referer-based restrictions via Cloud Armor |
| Key compromise | Rotate keys; limit key versions to 3 |
| Cache poisoning | Validate origin responses; use cache key policies |

## 2.2 Stability

### Principles
- Design for cache miss scenarios
- Implement graceful degradation
- Plan for origin failover

### Implementation

| Control | Method | Notes |
|---------|--------|-------|
| Cache invalidation | URL map invalidate-cache | Targeted path patterns, not wildcards |
| Multi-region CDN | Global edge PoPs (90+) | Automatic geographic distribution |
| Origin failover | Multiple backends in backend service | Configure failover ratio |
| TTL management | Appropriate defaultTtl/maxTtl | Balance freshness vs. origin load |
| Negative caching | `negativeCaching: true` | Cache 4xx/5xx to reduce origin load |
| Health checks | HTTP/HTTPS health checks | Detect origin failures early |

### Disaster Recovery Runbook

1. **Cache flush needed**: Invalidate specific paths; wait 60-120s for propagation
2. **Origin failure**: CDN serves cached content until TTL expires; monitor cache hit ratio
3. **CDN configuration error**: Disable CDN, wait 30s, re-enable with correct config
4. **Signed key compromised**: Delete key immediately; generate new key; redistribute URLs

## 2.3 Cost

### Principles
- Optimize cache hit ratio to minimize origin egress
- Right-size TTL for content type
- Monitor CDN costs vs. origin costs

### Cost Analysis

| Cost Component | Description | Optimization |
|---------------|-------------|-------------|
| CDN egress | Data served from edge caches | Increase cache hit ratio; use CACHE_ALL_STATIC |
| Origin egress | Data fetched from origin (cache misses) | Reduce cache misses; enable negative caching |
| Cloud Storage origin | Storage + egress from GCS | Use GCS as origin (cheaper than Compute Engine) |
| Cloud Armor | Security policy charges | Use basic rules first; premium for advanced WAF |
| Cache invalidation | Operations (300 per 10 min limit) | Batch invalidations; use targeted patterns |

### Cost Optimization Strategies

1. **Increase cache hit ratio**: Aim for > 80%; each 10% improvement reduces origin cost by ~10%
2. **Use Cloud Storage as origin**: GCS egress to CDN is free; Compute Engine egress is charged
3. **Enable negative caching**: Reduces origin load from bad requests
4. **Set appropriate TTLs**: Longer TTLs for static content, shorter for dynamic
5. **Monitor costs**: Use Cloud Billing reports with CDN labels

## 2.4 Efficiency

### Principles
- Automate CDN configuration
- Use appropriate cache modes
- Optimize cache key policies

### Implementation

| Control | Method | Notes |
|---------|--------|-------|
| Cache mode selection | CACHE_ALL_STATIC / USE_ORIGIN_HEADERS / FORCE_CACHE_ALL | Match mode to content type |
| Cache key policy | Customize what goes into cache key | Include/exclude query strings, headers, cookies |
| Request coalescing | `requestCoalescing: true` | Merge concurrent requests for same object |
| Automation | gcloud CLI / SDK | CI/CD integration for CDN config changes |
| Monitoring | Cloud Monitoring metrics | Track hit ratio, fill rate, error rates |

### Automation Patterns

```bash
# CI/CD pipeline: update CDN config
gcloud compute backend-services update "$BACKEND" \
  --enable-cdn \
  --cache-mode="$CACHE_MODE" \
  --default-ttl="$DEFAULT_TTL" \
  --max-ttl="$MAX_TTL" \
  --global \
  --project="$PROJECT"

# Automated cache invalidation on deploy
gcloud compute url-maps invalidate-cache "$URL_MAP" \
  --host="*" \
  --path="/static/*" \
  --global \
  --project="$PROJECT"
```

## 2.5 Performance

### Principles
- Minimize latency through edge caching
- Optimize cache fill patterns
- Monitor CDN performance metrics

### Performance Metrics

| Metric | Target | Notes |
|--------|--------|-------|
| Cache hit ratio | > 80% | Higher ratio = lower latency, lower origin load |
| Cache fill latency | < 500ms | Time to fetch from origin on cache miss |
| Edge response latency | < 50ms | Time to serve from edge cache |
| Invalidation propagation | < 120s | Time for cache invalidation to take effect globally |

### Performance Optimization

1. **Pre-warm cache**: After deploy, request critical paths to populate edge caches
2. **Use CDN logging**: Analyze cache hit/miss patterns; identify optimization opportunities
3. **Optimize origin responses**: Compress content; set appropriate Cache-Control headers
4. **Configure cache key policy**: Include only necessary fields; avoid over-segmentation
5. **Enable request coalescing**: Reduces duplicate origin requests for popular content

### Edge PoP Distribution

Google Cloud CDN has 90+ edge PoPs globally. Performance varies by region:

| Region | Approximate Edge Latency | PoP Count |
|--------|-------------------------|-----------|
| North America | 10-30ms | 25+ |
| Europe | 10-40ms | 20+ |
| Asia Pacific | 15-50ms | 25+ |
| South America | 20-60ms | 10+ |
| Africa/Middle East | 30-80ms | 5+ |
