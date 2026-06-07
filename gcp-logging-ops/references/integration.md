# Integration — Cloud Logging

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
| `LOGGING_LOCATION` | No | `global` | Default log bucket location |

## Python SDK Setup

```bash
pip install --quiet --user google-cloud-logging
```

## Go SDK Setup

```bash
go get cloud.google.com/go/logging/apiv2
go get google.golang.org/api/option
```

## Go SDK Script Template

```go
package main

import (
    "context" "fmt" "log" "os"
    "google.golang.org/api/option"
    logging "cloud.google.com/go/logging/apiv2"
    loggingpb "cloud.google.com/go/logging/apiv2/loggingpb"
)

func main() {
    ctx := context.Background()
    project := os.Getenv("CLOUDSDK_CORE_PROJECT")
    if project == "" { log.Fatal("CLOUDSDK_CORE_PROJECT not set") }
    client, err := logging.NewClient(ctx,
        option.WithCredentialsFile(os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")))
    if err != nil { log.Fatalf("NewClient: %v", err) }
    defer client.Close()
    // ... operations here
}
```

## Cross-Skill Delegation

| Scenario | Delegate To |
|----------|-------------|
| Cloud Monitoring alerts | `gcp-monitoring-ops` |
| BigQuery destination | `gcp-bigquery-ops` |
| Cloud Storage destination | `gcp-gcs-ops` |
| Pub/Sub topic destination | `gcp-pubsub-ops` |
| CMEK key management | `gcp-kms-ops` |
| IAM permissions | `gcp-iam-ops` |