# Integration

## Go Runtime Bootstrap

```bash
if ! command -v go &> /dev/null; then
    OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    ARCH=$(uname -m); [ "$ARCH" = "x86_64" ] && ARCH="amd64"; [ "$ARCH" = "aarch64" ] && ARCH="arm64"
    mkdir -p /tmp/go-runtime
    curl -fsSL "https://go.dev/dl/go1.24.0.${OS}-${ARCH}.tar.gz" | tar -xz -C /tmp/go-runtime
    export PATH="/tmp/go-runtime/go/bin:$PATH"
fi
```

## Environment Variables

```ini
GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
CLOUDSDK_CORE_PROJECT=my-gcp-project
CLOUDSDK_STORAGE_REGION=US
```

## Go SDK Script Template

```go
package main

import (
    "context"
    "fmt"
    "log"
    "os"

    "cloud.google.com/go/storage"
    "google.golang.org/api/option"
)

func main() {
    ctx := context.Background()
    project := os.Getenv("CLOUDSDK_CORE_PROJECT")

    client, err := storage.NewClient(ctx,
        option.WithCredentialsFile(os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")))
    if err != nil { log.Fatalf("NewClient: %v", err) }
    defer client.Close()
}
```

## Cross-Skill Delegation

| Resource | Skill |
|----------|-------|
| IAM / Service Accounts | gcp-iam-ops |
| Pub/Sub Topics | (planned) |
| Cloud KMS Keys | (planned) |
| Monitoring | gcp-monitoring-ops |
