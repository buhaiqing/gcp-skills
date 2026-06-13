# JIT Python SDK (Primary) & Go SDK (Secondary) Setup

> **Purpose:** Just-In-Time (JIT) SDK setup for Python and Go. Use when `gcloud` CLI cannot cover the required operation.
> **SDK Preference:** Python SDK (primary) > Go SDK (secondary).

---

## Python SDK (Primary)

### Install Python SDK

```bash
# Install Python SDK (example: Compute Engine)
pip install google-cloud-compute  # ~5-15MB per product

# Verify
python3 -c "from google.cloud import compute_v1; print('OK')"
```

### Python SDK Example

```python
from google.cloud import compute_v1
from google.oauth2 import service_account

# Client reads GOOGLE_APPLICATION_CREDENTIALS automatically
client = compute_v1.InstancesClient()

# List instances
project = "my-project"
zone = "us-central1-a"

response = client.list(project=project, zone=zone)
for instance in response:
    print(f"Instance: {instance.name} (status: {instance.status})")
```

### Python SDK Decision Table

| Scenario | Action |
|----------|--------|
| `gcloud` covers operation | Use `gcloud` (preferred) |
| `gcloud` missing field | Use Python SDK (`google-cloud-*`) |
| Complex data processing | Use Python SDK |
| No `gcloud` access | Use Python SDK |

---

## Go SDK (Secondary)

### Step 1: Detect or Install Go Runtime

```bash
# Check existing Go
if command -v go &>/dev/null; then
    GO_VERSION=$(go version | awk '{print $3}' | sed 's/go//')
    GO_MAJOR=$(echo "$GO_VERSION" | cut -d. -f1)
    GO_MINOR=$(echo "$GO_VERSION" | cut -d. -f2)

    if [ "$GO_MAJOR" -ge 1 ] && [ "$GO_MINOR" -ge 21 ]; then
        echo "Compatible Go runtime: $GO_VERSION"
    fi
fi

# JIT install Go (if missing)
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)
[ "$ARCH" = "x86_64" ] && ARCH="amd64"
[ "$ARCH" = "aarch64" ] && ARCH="arm64"
mkdir -p /tmp/go-runtime
curl -fsSL "https://go.dev/dl/go1.24.0.${OS}-${ARCH}.tar.gz" | tar -xz -C /tmp/go-runtime
export PATH="/tmp/go-runtime/go/bin:$PATH"
export GOPATH="/tmp/go-workspace"
export GOCACHE="/tmp/go-cache"
export GOMODCACHE="/tmp/go-modcache"
export GOPROXY="https://proxy.golang.org,direct"
```

### Step 2: Generate and Run Go SDK Script

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
    client, err := compute.NewInstancesRESTClient(ctx,
        option.WithCredentialsFile(os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")))
    if err != nil {
        log.Fatalf("Failed to create client: %v", err)
    }
    defer client.Close()

    project := os.Getenv("CLOUDSDK_CORE_PROJECT")
    zone := os.Getenv("CLOUDSDK_COMPUTE_ZONE")

    req := &computepb.ListInstancesRequest{
        Project: project,
        Zone:    zone,
    }

    resp, err := client.List(ctx, req)
    if err != nil {
        log.Fatalf("Failed to list instances: %v", err)
    }

    for _, instance := range resp.Items {
        fmt.Printf("Instance: %s (status: %s)\n", instance.GetName(), instance.GetStatus())
    }
}
```

Execute:
```bash
cd /tmp/gcp-sdk-workspace
go mod init gcp-operation
go get cloud.google.com/go/compute/apiv1
go run ./main.go
```

### Go SDK Execution Time Estimate

| Step | First Run | Subsequent Runs |
|------|-----------|-----------------|
| Download Go runtime | ~30s | 0s (cached) |
| `go get` dependencies | ~15s | ~3s (cached) |
| `go run` | ~5s | ~3s |
| **Total** | **~50s** | **~6s** |

---

## SDK Decision Matrix

| Python 3.8+ | Go | Recommended | Rationale |
|:-----------:|:--:|:-----------:|-----------|
| ✅ | — | **Python SDK** | Zero extra runtime, fastest path |
| ❌ | ✅ | **Go SDK** | Only option if Python unavailable |
| ❌ | ❌ | Docker gcloud | No SDK options → use CLI via Docker |
| ✅ | ✅ | **Python SDK** | Faster cold start, simpler code |

---

## Token Efficiency Note

This file is **lazy-loaded** — agents only read it when:
- `gcloud` CLI cannot cover the operation
- Need to generate Python/Go SDK code snippets
- JIT SDK setup required

For most operations, agents should use `gcloud` CLI (see [execution-environment.md](execution-environment.md)).
