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
```

## Go SDK Script Template

```go
package main

import (
    "context"
    "fmt"
    "log"
    "os"

    "cloud.google.com/go/pubsub"
)

func main() {
    ctx := context.Background()
    project := os.Getenv("CLOUDSDK_CORE_PROJECT")

    client, err := pubsub.NewClient(ctx, project)
    if err != nil { log.Fatalf("NewClient: %v", err) }
    defer client.Close()
}
```

> ⚠️ Never output credential values in logs or fmt.Println. Go SDK config structs can leak — prohibit such output.

## IAM Role Requirements

| Role | Permissions | Use Case |
|------|-------------|----------|
| roles/pubsub.admin | Full Pub/Sub access | Admin operations |
| roles/pubsub.editor | Create/manage topics & subscriptions | Development, configuration |
| roles/pubsub.viewer | Read-only access | Auditing, monitoring |
| roles/pubsub.publisher | Publish to topics | Producer applications |
| roles/pubsub.subscriber | Pull from subscriptions | Consumer applications |

## Cross-Skill Delegation

| Resource | Skill |
|----------|-------|
| IAM / Service Accounts | gcp-iam-ops |
| Cloud KMS Keys | gcp-kms-ops |
| Monitoring / Alerts | gcp-monitoring-ops |
| Logging | gcp-logging-ops |
