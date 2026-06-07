# Integration — Cloud KMS

## Go Runtime Bootstrap

```bash
if ! command -v go &> /dev/null; then
    OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    ARCH=$(uname -m); [ "$ARCH" = "x86_64" ] && ARCH="amd64"; [ "$ARCH" = "aarch64" ] && ARCH="arm64"
    mkdir -p /tmp/go-runtime
    curl -fsSL "https://go.dev/dl/go1.24.0.${OS}-${ARCH}.tar.gz" | tar -xz -C /tmp/go-runtime 2>/dev/null \
    || curl -fsSL "https://go.dev/dl/go1.24.0.linux-${ARCH}.tar.gz" | tar -xz -C /tmp/go-runtime
    export PATH="/tmp/go-runtime/go/bin:$PATH"
fi
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Yes | — | Path to SA key JSON |
| `CLOUDSDK_CORE_PROJECT` | Yes | — | GCP project ID |
| `CLOUDSDK_AUTH_ACCESS_TOKEN` | No | — | Temporary access token |
| `KMS_LOCATION` | No | `global` | Default KMS location |

## Python SDK Setup

```bash
pip install --quiet --user google-cloud-kms
```

## Go SDK Setup

```bash
go get cloud.google.com/go/kms/apiv1
go get google.golang.org/api/option
```

## Go SDK Script Template

```go
package main

import (
    "context" "fmt" "log" "os"
    kms "cloud.google.com/go/kms/apiv1"
    "cloud.google.com/go/kms/apiv1/kmspb"
    "google.golang.org/api/option"
)

func main() {
    ctx := context.Background()
    project := os.Getenv("CLOUDSDK_CORE_PROJECT")
    if project == "" { log.Fatal("CLOUDSDK_CORE_PROJECT not set") }
    client, err := kms.NewKeyManagementClient(ctx,
        option.WithCredentialsFile(os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")))
    if err != nil { log.Fatalf("NewClient: %v", err) }
    defer client.Close()
    // ... operations here
}
```

## Cross-Skill Delegation

| Scenario | Delegate To |
|----------|-------------|
| IAM policy management | `gcp-iam-ops` |
| Secret storage | `gcp-secretmanager-ops` |
| Monitoring & alerts | `gcp-monitoring-ops` |
| CMEK for Logging | `gcp-logging-ops` |
| KMS audit logs | `gcp-logging-ops` |