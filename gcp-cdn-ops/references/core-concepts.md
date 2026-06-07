# Core Concepts — Cloud CDN

## Architecture

Google Cloud CDN caches content at Google's globally distributed edge points of presence (PoPs). When a client requests content, the request is routed to the nearest edge PoP. If the content is cached (cache hit), it is served directly from the edge. If not cached (cache miss), the request is forwarded to the origin (backend service), the response is cached at the edge, and served to the client.

### Request Flow

```
Client → Google Edge PoP → (cache hit?) → Serve from cache
                           → (cache miss) → Forward to origin → Cache response → Serve to client
```

### Key Components

- **Backend Service**: The origin resource that CDN is enabled on. Must be part of an HTTP(S) load balancer.
- **CDN Policy**: Configuration object attached to backend service defining cache mode, TTLs, negative caching, and signed URL settings.
- **Edge Cache**: Google's globally distributed cache infrastructure (~90+ PoPs).
- **URL Map**: Routes requests to backend services; cache invalidation operates at the URL map level.

## Cache Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| `CACHE_ALL_STATIC` | Caches static content (images, CSS, JS) based on file extension. Dynamic content bypasses cache. | Most web applications (default) |
| `USE_ORIGIN_HEADERS` | Caches only if origin sends valid `Cache-Control` and `Expires` headers. No header = no cache. | Origin-controlled caching |
| `FORCE_CACHE_ALL` | Caches ALL content regardless of origin headers, including dynamic responses. | Static asset delivery, API responses with fixed TTL |
| `CACHE_ALL_STATIC_WITH_PRIVATE` | Like CACHE_ALL_STATIC but respects the `private` Cache-Control directive (excludes from shared cache). | Multi-tenant apps with some private static content |

### Cacheability Rules

Content is cacheable when:
- Response status is 200, 203, 206, 300, 301, 302, 307, 308, 404, 405, 410, 414, 501
- Response size ≤ 10 MB (default limit)
- Request method is GET or HEAD
- URL does not contain query parameters (unless `bypassOnQuery` is configured)

Content is NOT cacheable when:
- Response has `Set-Cookie` header
- Response has `Cache-Control: private, no-store, no-cache`
- Request has `Authorization` header (unless configured otherwise)
- Response size exceeds max-cacheable-size

## TTL Configuration

| Parameter | Range | Default | Description |
|-----------|-------|---------|-------------|
| `defaultTtl` | 0–86400s | 3600s (1h) | TTL when origin doesn't specify `Cache-Control: max-age` |
| `maxTtl` | 0–86400s | 86400s (24h) | Maximum TTL regardless of origin headers |
| `clientTtl` | 0–86400s | 3600s (1h) | TTL sent to client in `Cache-Control: public, max-age=` |

### TTL Precedence

1. If origin sends `Cache-Control: max-age` or `Expires`, use origin value (capped by `maxTtl`)
2. If origin doesn't specify TTL, use `defaultTtl`
3. `maxTtl` always caps the effective TTL
4. `clientTtl` overrides the TTL sent to the client

## Negative Caching

Negative caching stores error responses at the edge to reduce origin load from repeated bad requests.

| Response Code | Default TTL | Recommended TTL |
|---------------|-------------|-----------------|
| 300 | 60s | 60s |
| 301 | 120s | 120s |
| 302 | 120s | 120s |
| 404 | 120s | 30s |
| 405 | 60s | 60s |
| 410 | 120s | 120s |
| 421 | 60s | 60s |
| 451 | 120s | 120s |
| 501 | 60s | 30s |

Enable with `--negative-caching` flag and optionally set per-code TTLs via `--negative-caching-policy`.

## Signed URLs

Signed URLs provide time-limited, cryptographically-signed access to private content served through CDN.

### How It Works

1. Generate a signed URL on the server using a secret key
2. Client receives the signed URL (with `?GoogleAccessId=...&Signature=...&Expires=...`)
3. Edge PoP validates the signature and expiration before serving content
4. Invalid signature or expired URL → 403 Forbidden

### Key Management

- Maximum 3 signed URL keys per backend service (`signedUrlKeyMaxVersion`)
- Key names are visible in API responses; key values are only returned on creation
- Rotate keys regularly (90 days recommended)
- Deleting a key immediately invalidates all URLs signed with it

### URL Signing Algorithm

- Algorithm: RSA-SHA256 or HMAC-SHA256
- Signed fields: URL path, expiration timestamp, optional custom fields
- Signature is Base64-URL encoded

## Limits and Quotas

| Limit | Value | Notes |
|-------|-------|-------|
| Max cacheable response size | 10 MB | Default; configurable up to ~37 MB with Cloud Storage backend |
| Max backend services with CDN | Per project Compute API quota | Check with `gcloud compute project-info describe` |
| Max signed URL keys per backend | 3 | Hard limit |
| Max cache invalidation operations | 300 per 10 minutes | Per project |
| Edge PoP count | 90+ | Global coverage, varies by region |

## Dependencies

- CDN requires an HTTP(S) load balancer with a backend service
- Backend service must have at least one backend (instance group, NEG, or Cloud Storage bucket)
- Cache invalidation requires the URL map associated with the load balancer
- Signed URLs require the backend service protocol to be HTTP, HTTPS, or HTTP2

## Regional Availability

Cloud CDN is a **global** service — edge cache is available at all Google Cloud PoPs worldwide. The backend service must be global (not regional) for CDN to function.
