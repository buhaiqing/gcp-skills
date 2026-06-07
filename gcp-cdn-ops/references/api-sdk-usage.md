# API & SDK Usage — Cloud CDN

## REST API

- **Discovery document**: `https://compute.googleapis.com/$discovery/rest?version=v1`
- **Base URL**: `https://compute.googleapis.com/compute/v1/`
- **Resource**: `projects/{project}/global/backendServices/{backendService}`

CDN is a property of backend services — there is no standalone CDN API.

## SDK Operations Map

| Goal | REST Method & Path | Python SDK Method | Go SDK Method |
|------|-------------------|-------------------|---------------|
| Enable/Update CDN | `PATCH /v1/projects/{project}/global/backendServices/{backend}` | `BackendServicesClient.patch()` | `BackendServicesClient.Patch()` |
| Describe CDN config | `GET /v1/projects/{project}/global/backendServices/{backend}` | `BackendServicesClient.get()` | `BackendServicesClient.Get()` |
| List CDN backends | `GET /v1/projects/{project}/global/backendServices` | `BackendServicesClient.list()` | `BackendServicesClient.List()` |
| Invalidate cache | `POST /v1/projects/{project}/global/urlMaps/{urlMap}/invalidateCache` | `UrlMapsClient.invalidate_cache()` | `UrlMapsClient.InvalidateCache()` |
| Add signed URL key | `PATCH /v1/projects/{project}/global/backendServices/{backend}` (add to cdnPolicy.signedUrlKeys) | `BackendServicesClient.patch()` | `BackendServicesClient.Patch()` |
| Delete signed URL key | `PATCH /v1/projects/{project}/global/backendServices/{backend}` (remove from cdnPolicy.signedUrlKeys) | `BackendServicesClient.patch()` | `BackendServicesClient.Patch()` |
| Describe operation | `GET /v1/projects/{project}/global/operations/{operation}` | `GlobalOperationsClient.get()` | `GlobalOperationsClient.Get()` |

## Request / Response Notes

### CDN Policy (CdnPolicy message)

| Field | Type | Notes |
|-------|------|-------|
| `cacheMode` | enum | CACHE_ALL_STATIC, USE_ORIGIN_HEADERS, FORCE_CACHE_ALL, CACHE_ALL_STATIC_WITH_PRIVATE |
| `defaultTtl` | int32 | 0–86400 seconds |
| `maxTtl` | int32 | 0–86400 seconds |
| `clientTtl` | int32 | 0–86400 seconds |
| `negativeCaching` | bool | Enable negative response caching |
| `negativeCachingPolicy` | list | List of {code: int, ttl: int} pairs |
| `signedUrlKeyMaxVersion` | int32 | Max 3 |
| `signedUrlKeys` | list | List of {keyName: string, keyValue: bytes, keyVersion: int} |
| `bypassCacheOnRequestHeaders` | list | Headers that bypass cache |
| `requestCoalescing` | bool | Merge concurrent requests for same object |
| `cacheKeyPolicy` | object | Custom cache key configuration |

### Cache Key Policy

| Field | Type | Notes |
|-------|------|-------|
| `includeHost` | bool | Include host in cache key |
| `includeProtocol` | bool | Include protocol (http/https) in cache key |
| `includeQueryString` | bool | Include query string in cache key |
| `queryStringBlacklist` | list | Query params to exclude from cache key |
| `queryStringWhitelist` | list | Query params to include (exclusive with blacklist) |
| `includeNamedCookies` | list | Cookie names to include in cache key |
| `includeHttpHeaders` | list | Header names to include in cache key |

## Python SDK Example

```python
import os
from google.cloud import compute_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
backend_name = "my-backend"

client = compute_v1.BackendServicesClient()

# Get backend service
backend = client.get(project=project, backend_service=backend_name)

# Configure CDN policy
policy = compute_v1.CdnPolicy()
policy.cache_mode = compute_v1.CdnPolicy.CacheMode.CACHE_ALL_STATIC
policy.default_ttl = 3600
policy.max_ttl = 86400
policy.client_ttl = 3600
policy.negative_caching = True

backend.enable_cdn = True
backend.cdn_policy = policy

# Apply changes
operation = client.patch(
    project=project,
    backend_service=backend_name,
    backend_service_resource=backend,
)
print(f"Operation: {operation.name}")
```

## Go SDK Example

```go
package main

import (
    "context"
    "fmt"
    "log"
    "os"

    compute "cloud.google.com/go/compute/apiv1"
    computepb "cloud.google.com/go/compute/apiv1/computepb"
    "google.golang.org/api/option"
)

func main() {
    ctx := context.Background()
    project := os.Getenv("CLOUDSDK_CORE_PROJECT")
    backendName := "my-backend"

    client, err := compute.NewBackendServicesRESTClient(ctx,
        option.WithCredentialsFile(os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")))
    if err != nil {
        log.Fatalf("Failed to create client: %v", err)
    }
    defer client.Close()

    // Get existing backend
    backend, err := client.Get(ctx, &computepb.GetBackendServiceRequest{
        Project:         project,
        BackendService:  backendName,
    })
    if err != nil {
        log.Fatalf("Failed to get backend: %v", err)
    }

    // Enable CDN
    backend.EnableCdn = true
    backend.CdnPolicy = &computepb.CdnPolicy{
        CacheMode:   computepb.CdnPolicy_CACHE_ALL_STATIC,
        DefaultTtl:  3600,
        MaxTtl:      86400,
        ClientTtl:   3600,
    }

    // Apply changes
    op, err := client.Patch(ctx, &computepb.PatchBackendServiceRequest{
        Project:            project,
        BackendService:     backendName,
        BackendServiceResource: backend,
    })
    if err != nil {
        log.Fatalf("Failed to patch backend: %v", err)
    }
    if err := op.Wait(ctx); err != nil {
        log.Fatalf("Operation failed: %v", err)
    }
    fmt.Printf("CDN enabled on %s\n", backendName)
}
```

## Pagination

- `list` operations return paginated results
- Use `page_size` parameter to control page size (default 500, max 500)
- Use `page_token` from previous response to fetch next page
- Python SDK handles pagination automatically with iterator
- Go SDK requires manual `page_token` handling

## Error Handling

| Error | gRPC Code | Action |
|-------|-----------|--------|
| Backend not found | NOT_FOUND (5) | Verify backend name and project |
| Invalid CDN config | INVALID_ARGUMENT (3) | Check cache mode enum and TTL ranges |
| Permission denied | PERMISSION_DENIED (7) | Verify IAM roles |
| Quota exceeded | RESOURCE_EXHAUSTED (8) | Check project quotas |
| Conflict | ABORTED (10) | Retry with backoff |
| Internal error | INTERNAL (13) | Retry with exponential backoff |
