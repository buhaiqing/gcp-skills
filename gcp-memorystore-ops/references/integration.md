# Integration — Memorystore for Redis

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
| `REDIS_REGION` | No | `us-central1` | Default Redis region |

## Python SDK Setup

```bash
pip install --quiet --user google-cloud-redis
```

## Go SDK Setup

```bash
go get cloud.google.com/go/redis/apiv1
go get google.golang.org/api/option
```

## Go SDK Script Template

```go
package main

import (
    "context" "fmt" "log" "os"
    redis "cloud.google.com/go/redis/apiv1"
    "cloud.google.com/go/redis/apiv1/redispb"
    "google.golang.org/api/option"
)

func main() {
    ctx := context.Background()
    project := os.Getenv("CLOUDSDK_CORE_PROJECT")
    if project == "" { log.Fatal("CLOUDSDK_CORE_PROJECT not set") }
    client, err := redis.NewCloudRedisClient(ctx,
        option.WithCredentialsFile(os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")))
    if err != nil { log.Fatalf("NewClient: %v", err) }
    defer client.Close()
    // ... operations here
}
```

## Cross-Skill Delegation

| Scenario | Delegate To |
|----------|-------------|
| VPC network creation | `gcp-vpc-ops` |
| Cloud Monitoring alerts | `gcp-monitoring-ops` |
| GCE instance for Redis client | `gcp-gce-ops` |
| Cloud Storage for export/import | `gcp-gcs-ops` |