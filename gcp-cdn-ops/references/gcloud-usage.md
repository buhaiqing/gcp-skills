# gcloud — Cloud CDN CLI

## Install and config

- Install: see [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
- **CRITICAL Credentials:** Set `GOOGLE_APPLICATION_CREDENTIALS` or run `gcloud auth login`
- CDN commands are under `gcloud compute backend-services` and `gcloud compute url-maps`

## Conventions (agent execution)

- Always use `--format=json` for machine-parseable output
- Use `jq` for field extraction from JSON output
- CDN operations on backend services use `--global` flag (CDN is global)
- Cache invalidation operates on URL maps

## CDN Command Map

| Goal | Example `gcloud` invocation | Notes |
|------|--------------------------|-------|
| Enable CDN | `gcloud compute backend-services update NAME --global --enable-cdn --cache-mode=CACHE_ALL_STATIC --project=PROJECT --format=json` | Sync operation |
| Update CDN policy | `gcloud compute backend-services update NAME --global --enable-cdn --cache-mode=MODE --default-ttl=SEC --max-ttl=SEC --project=PROJECT --format=json` | Sync operation |
| Disable CDN | `gcloud compute backend-services update NAME --global --no-enable-cdn --project=PROJECT --format=json` | Sync operation |
| Describe CDN config | `gcloud compute backend-services describe NAME --global --project=PROJECT --format=json \| jq '.cdnPolicy'` | Read-only |
| List CDN backends | `gcloud compute backend-services list --global --filter="enableCdn=true" --project=PROJECT --format=json` | Read-only |
| Add signed URL key | `gcloud compute backend-services add-signed-url-key NAME --key-name=KEY_NAME --global --project=PROJECT --format=json` | Key value in response |
| Delete signed URL key | `gcloud compute backend-services delete-signed-url-key NAME --key-name=KEY_NAME --global --project=PROJECT --format=json` | Immediate revocation |
| Invalidate cache | `gcloud compute url-maps invalidate-cache URL_MAP --host=HOST --path=PATH --global --project=PROJECT --format=json` | Async operation |
| Describe operation | `gcloud compute operations describe OPERATION_ID --global --project=PROJECT --format=json` | Poll for completion |

## Cache Mode Options

| Flag Value | Description |
|------------|-------------|
| `--cache-mode=CACHE_ALL_STATIC` | Cache static content (default) |
| `--cache-mode=USE_ORIGIN_HEADERS` | Respect origin Cache-Control headers |
| `--cache-mode=FORCE_CACHE_ALL` | Cache all content regardless of headers |
| `--cache-mode=CACHE_ALL_STATIC_WITH_PRIVATE` | Cache static, respect private directive |

## TTL Flags

| Flag | Type | Description |
|------|------|-------------|
| `--default-ttl=SECONDS` | int | Default TTL if origin doesn't specify (0–86400) |
| `--max-ttl=SECONDS` | int | Maximum TTL cap (0–86400) |
| `--client-ttl=SECONDS` | int | TTL sent to client (0–86400) |

## Negative Caching Flags

| Flag | Description |
|------|-------------|
| `--negative-caching` | Enable negative response caching |
| `--no-negative-caching` | Disable negative response caching |
| `--negative-caching-policy=CODE=TTL,...` | Per-response-code TTLs (e.g., `404=30,501=10`) |

## CLI vs API coverage gap

| Operation | Available via `gcloud`? | Notes |
|-----------|---------------------|-------|
| Enable/Disable CDN | yes | Via --enable-cdn / --no-enable-cdn |
| Update CDN policy | yes | Via --cache-mode, --default-ttl, etc. |
| Add/Delete signed URL key | yes | Via add-signed-url-key / delete-signed-url-key |
| Invalidate cache | yes | Via url-maps invalidate-cache |
| Custom cache key policy | yes | Via --cache-key-include-host, etc. |
| Bypass cache on headers | yes | Via --bypass-cache-on-request-headers |
| Request coalescing | yes | Via --request-coalescing |
| CDN logging | yes | Via --enable-cdn-logging / --no-enable-cdn-logging |
| Describe backend with CDN | yes | Via backend-services describe |
| List CDN backends | yes | Via backend-services list with filter |

All CDN operations are covered by `gcloud` CLI.

## Useful Filters

```bash
# List all CDN-enabled backend services
gcloud compute backend-services list --global --filter="enableCdn=true" --format=json

# List backends with specific cache mode
gcloud compute backend-services list --global --filter="enableCdn=true AND cdnPolicy.cacheMode=CACHE_ALL_STATIC" --format=json

# List backend services using a specific backend group
gcloud compute backend-services list --global --filter="backends.group ~ INSTANCE_GROUP_NAME" --format=json
```

## jq Extraction Patterns

```bash
# Extract CDN policy
gcloud compute backend-services describe NAME --global --format=json | jq '.cdnPolicy'

# Check if CDN is enabled
gcloud compute backend-services describe NAME --global --format=json | jq -r '.enableCdn'

# Extract signed URL key names
gcloud compute backend-services describe NAME --global --format=json | jq -r '.cdnPolicy.signedUrlKeys[]?.keyName'

# Extract cache hit metrics (if available in response)
gcloud compute backend-services describe NAME --global --format=json | jq '.cdnPolicy | {cacheMode, defaultTtl, maxTtl}'

# Get operation status
gcloud compute operations describe OP_ID --global --format=json | jq '{status: .status, progress: .progress, error: .error}'
```
