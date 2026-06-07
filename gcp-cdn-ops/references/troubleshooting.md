# Troubleshooting — Cloud CDN

## Diagnostic Order

1. Describe backend service and verify CDN configuration
2. List CDN-enabled backends to confirm scope
3. Check backend health and load balancer configuration
4. Verify CDN cache mode and TTL settings
5. Check Cloud Monitoring metrics (cache hit ratio, error rates)
6. Review Cloud Logging for CDN-specific log entries
7. Test cache invalidation if stale content suspected

## Common API Error Codes

| Error Code | HTTP | Meaning | Agent Action |
|------------|------|---------|--------------|
| invalid / 400 | 400 | Invalid backend service configuration | Validate cache mode enum, TTL ranges (0-86400) |
| forbidden / 403 | 403 | Insufficient permissions (needs roles/compute.admin) | Verify IAM role; grant compute.backendServices.update |
| notFound / 404 | 404 | Backend service or resource does not exist | Verify backend name and project; list backends to confirm |
| resourceAlreadyExists / 409 | 409 | Backend service already exists | Use update instead of create |
| resourceInUse / 409 | 409 | Resource is currently in use | Wait for concurrent operation; retry after 30s |
| quotaExceeded / 429 | 429 | Compute Engine quota exceeded | Check quotas; request increase via Cloud Console |
| operationError / 500 | 500 | Compute operation failed | Retry with exponential backoff; check operation details |
| zoneResourcePending / 409 | 409 | Resource creation pending in zone | Wait and retry; propagation delay |
| invalidConfiguration / 400 | 400 | CDN configuration invalid | Check cache mode, TTL constraints, backend protocol |
| insufficientPermissions / 403 | 403 | Missing IAM permissions | Verify roles/compute.loadBalancerAdmin or roles/compute.admin |
| rateLimited / 429 | 429 | API rate limit exceeded | Back off; respect Retry-After header |
| serviceNotReady / 503 | 503 | Compute service temporarily unavailable | Retry with exponential backoff |
| cacheInvalidationFailed / 500 | 500 | Cache invalidation operation failed | Verify URL map exists; check path pattern syntax; retry once |

## Diagnostic Commands

### 1. Verify CDN Configuration

```bash
gcloud compute backend-services describe "{{user.backend_name}}" \
  --global \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{
    enableCdn: .enableCdn,
    cacheMode: .cdnPolicy.cacheMode,
    defaultTtl: .cdnPolicy.defaultTtl,
    maxTtl: .cdnPolicy.maxTtl,
    backends: [.backends[] | (.group | split("/")[-1])],
    protocol: .protocol
  }'
```

### 2. Check Backend Health

```bash
gcloud compute backend-services get-health "{{user.backend_name}}" \
  --global \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

### 3. Verify Load Balancer Configuration

```bash
# Check URL maps referencing this backend
gcloud compute url-maps list --global --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json | jq '[.[] | select(.defaultService | contains("{{user.backend_name}}")) | {name: .name, defaultService: .defaultService}]'
```

### 4. Check Cache Invalidation Status

```bash
gcloud compute operations describe "{{output.invalidation_id}}" \
  --global \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{status: .status, progress: .progress, error: .error}'
```

## Common Issues and Fixes

### Cache Miss Rate High

**Symptoms:** Low cache hit ratio (< 80%), high origin load

**Diagnostic Steps:**
1. Check cache mode: `gcloud compute backend-services describe NAME --global --format=json | jq '.cdnPolicy.cacheMode'`
2. Verify origin sends cacheable responses (200, Cache-Control headers)
3. Check for query string bypass: `jq '.cdnPolicy.cacheKeyPolicy.includeQueryString'`
4. Review Cloud Monitoring: `cache.hit_ratio` metric

**Fixes:**
- Switch to `CACHE_ALL_STATIC` or `FORCE_CACHE_ALL` if appropriate
- Adjust `defaultTtl` and `maxTtl` to reasonable values
- Enable negative caching for 404/501 responses
- Use `includeQueryString` to cache different query parameters separately

### Stale Content Not Refreshing

**Symptoms:** Old content served despite origin updates

**Diagnostic Steps:**
1. Check TTL settings: `jq '.cdnPolicy | {defaultTtl, maxTtl, clientTtl}'`
2. Verify content was actually updated on origin
3. Check if invalidation completed: describe operation status

**Fixes:**
- Invalidate cache for specific paths: `gcloud compute url-maps invalidate-cache URL_MAP --host="*" --path="/path/*"`
- Reduce `maxTtl` for frequently updated content
- Use `USE_ORIGIN_HEADERS` mode if origin controls caching

### Signed URL Validation Failures

**Symptoms:** 403 Forbidden for signed URLs

**Diagnostic Steps:**
1. Verify key exists: `jq '.cdnPolicy.signedUrlKeys[] | .keyName'`
2. Check key version matches URL signature
3. Verify URL hasn't expired (check Expires parameter)
4. Check signature algorithm matches backend configuration

**Fixes:**
- Regenerate signed URL with correct key
- Rotate keys if compromised
- Check clock skew between signing server and Google edge

### CDN Not Propagating

**Symptoms:** CDN configuration changes not taking effect

**Diagnostic Steps:**
1. Check operation status: `gcloud compute operations describe OP_ID --global --format=json | jq '.status'`
2. Verify no concurrent operations on backend service
3. Check backend service health

**Fixes:**
- Wait 60-120 seconds for propagation to edge PoPs
- Retry configuration if operation failed
- Check for conflicting concurrent operations

### Origin Connection Errors

**Symptoms:** 502/504 errors from CDN edge

**Diagnostic Steps:**
1. Check backend health: `gcloud compute backend-services get-health NAME --global`
2. Verify backend instances/NEGs are running and healthy
3. Check firewall rules allow traffic from Google health check ranges
4. Verify origin responds within timeout period (default 30s)

**Fixes:**
- Fix backend health issues
- Increase timeout if origin is slow: `gcloud compute backend-services update NAME --timeout=60`
- Check network connectivity between Google edge and origin

## Log Analysis

CDN logs are available in Cloud Logging with the following log names:

- `httprequests` - HTTP(S) load balancer access logs (includes CDN hit/miss)
- `cloudcdn.googleapis.com` - CDN-specific operations

### Query for Cache Miss Analysis

```
resource.type="http_load_balancer"
jsonPayload.statusDetails="backend_response"
```

### Query for CDN Errors

```
resource.type="http_load_balancer"
jsonPayload.statusDetails=~"backend_(timeout|failure|connection_error)"
```

## Recovery Procedures

### Emergency Cache Flush

If content must be immediately removed from all edge caches:

```bash
gcloud compute url-maps invalidate-cache "{{user.url_map}}" \
  --host="*" \
  --path="/*" \
  --global \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

**Warning:** This will cause a spike in origin load as all content is re-fetched.

### CDN Disable and Re-enable

If CDN configuration is corrupted:

```bash
# Disable CDN
gcloud compute backend-services update "{{user.backend_name}}" \
  --no-enable-cdn --global --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Wait 30 seconds
sleep 30

# Re-enable with correct configuration
gcloud compute backend-services update "{{user.backend_name}}" \
  --enable-cdn \
  --cache-mode="CACHE_ALL_STATIC" \
  --default-ttl="3600" \
  --max-ttl="86400" \
  --global \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```
