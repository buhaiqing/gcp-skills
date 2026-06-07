# Integration

## Environment Setup

**Primary path:** `gcloud` CLI (Google Cloud SDK, Python-based)

**Fallback path:** JIT Go SDK (dynamic script generation + `go run`)

### Go Runtime Bootstrap

If Agent Runtime lacks Go, JIT download from official source:

```bash
# Check Go runtime
if ! command -v go &> /dev/null; then
    OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    ARCH=$(uname -m)
    [ "$ARCH" = "x86_64" ] && ARCH="amd64"
    [ "$ARCH" = "aarch64" ] && ARCH="arm64"
    
    mkdir -p /tmp/go-runtime
    curl -fsSL "https://go.dev/dl/go1.24.0.${OS}-${ARCH}.tar.gz" | tar -xz -C /tmp/go-runtime
    export PATH="/tmp/go-runtime/go/bin:$PATH"
    export GOPATH="/tmp/go-workspace"
    export GOCACHE="/tmp/go-cache"
fi

go version
```

> **Go version strategy:**
> - **JIT download:** Go 1.24+ (latest stable)
> - **Script compatibility:** Go 1.21+ (minimum)

### JIT Go SDK Workflow

1. **Initialize workspace:**
   ```bash
   mkdir -p /tmp/gcp-sdk-workspace
   cd /tmp/gcp-sdk-workspace
   go mod init sdk-script
   ```

2. **Get dependencies:**
   ```bash
   export GOPROXY="https://proxy.golang.org,direct"
   go get cloud.google.com/go/compute/apiv1
   ```

3. **Generate script** (Agent dynamically creates operation-specific .go file)

4. **Execute:**
   ```bash
   go run ./main.go
   ```

### SDK Package Naming

| GCP Product | Go SDK Package |
|-------------|---------------|
| Compute Engine | `cloud.google.com/go/compute/apiv1` |
| Cloud SQL | `cloud.google.com/go/sql/apiv1` |
| Cloud Storage | `cloud.google.com/go/storage` |
| Cloud Run | `cloud.google.com/go/run/apiv2` |
| GKE | `cloud.google.com/go/container/apiv1` |

> Find package names at: https://pkg.go.dev/cloud.google.com/go

## Environment Variable Loading

Credentials can be sourced from multiple locations:

```
Shell env (highest) > `.env` file > gcloud config (lowest)
```

### `.env` File Format

```ini
# Google Cloud credentials
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
CLOUDSDK_CORE_PROJECT=my-gcp-project
```

- **Security**: `.env` MUST be in `.gitignore` — never commit credentials

## Go SDK Script Template (CDN-specific)

```go
package main

import (
    "context"
    "fmt"
    "log"
    "os"
    
    "google.golang.org/api/option"
    compute "cloud.google.com/go/compute/apiv1"
    computepb "cloud.google.com/go/compute/apiv1/computepb"
)

func main() {
    ctx := context.Background()
    project := os.Getenv("CLOUDSDK_CORE_PROJECT")
    backendName := os.Getenv("BACKEND_NAME")
    
    client, err := compute.NewBackendServicesRESTClient(ctx,
        option.WithCredentialsFile(os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")))
    if err != nil {
        log.Fatalf("Failed to create client: %v", err)
    }
    defer client.Close()
    
    // Get existing backend
    backend, err := client.Get(ctx, &computepb.GetBackendServiceRequest{
        Project:        project,
        BackendService: backendName,
    })
    if err != nil {
        log.Fatalf("Failed to get backend: %v", err)
    }
    
    // Enable CDN and configure policy
    backend.EnableCdn = true
    backend.CdnPolicy = &computepb.CdnPolicy{
        CacheMode:  computepb.CdnPolicy_CACHE_ALL_STATIC,
        DefaultTtl: 3600,
        MaxTtl:     86400,
        ClientTtl:  3600,
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

> Use `os.Getenv("KEY")` for all credentials. Never hardcode secrets in scripts.
