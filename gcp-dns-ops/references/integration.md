# Integration — Cloud DNS

## Environment Setup

**Primary path:** `gcloud` CLI (Google Cloud SDK, Python-based)

**Fallback path:** JIT Python SDK or Go SDK (dynamic script generation + `python3`/`go run`)

### Go Runtime Bootstrap

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

### Python SDK Setup

```bash
pip install --quiet --user google-cloud-dns
python3 -c "from google.cloud import dns_v1; print('DNS SDK OK')"
```

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
   go get google.golang.org/api/dns/v1
   go get google.golang.org/api/option
   ```

3. **Generate script** (Agent dynamically creates operation-specific .go file)

4. **Execute:**
   ```bash
   go run ./main.go
   ```

### SDK Package Reference

| GCP Product | Go SDK Package | Python SDK Package |
|-------------|---------------|-------------------|
| Cloud DNS | `google.golang.org/api/dns/v1` | `google-cloud-dns` (`google.cloud.dns_v1`) |

## Environment Variable Loading

Credentials are sourced from environment variables:

```
Shell env (highest) > .env file > gcloud config (lowest)
```

### .env File Format

```ini
# Google Cloud credentials
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
CLOUDSDK_CORE_PROJECT=my-gcp-project
```

- **Security**: `.env` MUST be in `.gitignore` — never commit credentials

### Credential Verification (Safe)

```bash
# Verify file exists (never echo the path content)
test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "SA key file exists" || echo "SA key file missing"
test -n "$CLOUDSDK_CORE_PROJECT" && echo "Project set" || echo "Project not set"
```

### Go SDK Script Template

```go
// main.go
package main

import (
    "context"
    "fmt"
    "log"
    "os"

    "google.golang.org/api/option"
    dns "google.golang.org/api/dns/v1"
)

func main() {
    ctx := context.Background()
    svc, err := dns.NewService(ctx,
        option.WithCredentialsFile(os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")))
    if err != nil {
        log.Fatalf("Failed to create DNS service: %v", err)
    }

    project := os.Getenv("CLOUDSDK_CORE_PROJECT")
    zones, err := svc.ManagedZones.List(project).Do()
    if err != nil {
        log.Fatalf("Failed to list zones: %v", err)
    }

    for _, z := range zones.ManagedZones {
        fmt.Printf("Zone: %s, DNS: %s, Visibility: %s\n", z.Name, z.DnsName, z.Visibility)
    }
}
```

> Use `os.Getenv("KEY")` for all credentials. Never hardcode secrets in scripts.
