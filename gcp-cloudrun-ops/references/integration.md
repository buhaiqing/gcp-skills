# Integration — Cloud Run

## Environment Setup

**Primary path:** `gcloud` CLI (Google Cloud SDK, Python-based)

**Fallback path:** JIT Go SDK (dynamic script generation + `go run`)

### Go Runtime Bootstrap

If Agent Runtime lacks Go, JIT download from official source:

```bash
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

### JIT Go SDK Workflow

1. **Initialize workspace:**
   ```bash
   mkdir -p /tmp/gcp-sdk-workspace && cd /tmp/gcp-sdk-workspace
   go mod init sdk-script
   ```

2. **Get dependencies:**
   ```bash
   export GOPROXY="https://proxy.golang.org,direct"
   go get cloud.google.com/go/run/apiv2
   ```

3. **Generate script** (Agent creates operation-specific .go file)

4. **Execute:**
   ```bash
   go run ./main.go
   ```

### SDK Package Mapping

| GCP Product | Go SDK Package | Python SDK Package |
|-------------|---------------|-------------------|
| Cloud Run | `cloud.google.com/go/run/apiv2` | `google.cloud.run_v2` |

## Go SDK Script Template

```go
package main

import (
    "context"
    "fmt"
    "log"
    "os"
    "google.golang.org/api/option"
    run "cloud.google.com/go/run/apiv2"
    runpb "cloud.google.com/go/run/apiv2/runpb"
)

func main() {
    ctx := context.Background()
    client, err := run.NewServicesClient(ctx,
        option.WithCredentialsFile(os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")))
    if err != nil {
        log.Fatalf("Failed to create client: %v", err)
    }
    defer client.Close()

    parent := fmt.Sprintf("projects/%s/locations/%s",
        os.Getenv("CLOUDSDK_CORE_PROJECT"), os.Getenv("CLOUDSDK_RUN_LOCATION", "us-central1"))

    req := &runpb.ListServicesRequest{Parent: parent}
    it := client.ListServices(ctx, req)
    for {
        svc, err := it.Next()
        if err != nil {
            break
        }
        fmt.Printf("Service: %s URL: %s\n", svc.Name, svc.Uri)
    }
}
```

> Use `os.Getenv("KEY")` for all credentials. Never hardcode secrets. Go SDK's `fmt.Printf("%+v", ...)` can leak credentials — prohibit such output.

## Environment Variable Loading

```
Shell env (highest) > `.env` file > gcloud config (lowest)
```

### `.env` File Format

```ini
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
CLOUDSDK_CORE_PROJECT=my-gcp-project
CLOUDSDK_RUN_LOCATION=us-central1
```

- **Security**: `.env` MUST be in `.gitignore`

## IAM Roles

| Role | Permissions | Use Case |
|------|------------|----------|
| `roles/run.admin` | Full Cloud Run admin | Service lifecycle management |
| `roles/run.viewer` | Read-only Cloud Run | Audit, monitoring |
| `roles/run.invoker` | Invoke services | Service consumers |
| `roles/run.developer` | Deploy/update services | CI/CD pipelines |

## Credential Rules

| Variable | Purpose | Source |
|----------|---------|--------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to SA key JSON | `{{env.*}}` — NEVER ask user |
| `CLOUDSDK_CORE_PROJECT` | GCP project ID | `{{env.*}}` or `gcloud config` |
| `CLOUDSDK_AUTH_ACCESS_TOKEN` | Temporary access token | `gcloud auth print-access-token` |

**Never output credentials**: Replace access tokens and SA key content in logs with `****`.
