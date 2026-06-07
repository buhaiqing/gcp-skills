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
CLOUDSDK_COMPUTE_ZONE=us-central1-a
CLOUDSDK_COMPUTE_REGION=us-central1
```

## Go SDK Script Template

```go
package main

import (
    "context" "fmt" "log" "os"
    compute "cloud.google.com/go/compute/apiv1"
    "cloud.google.com/go/compute/apiv1/computepb"
    "google.golang.org/api/option"
)

func main() {
    ctx := context.Background()
    project := os.Getenv("CLOUDSDK_CORE_PROJECT")
    zone := os.Getenv("CLOUDSDK_COMPUTE_ZONE")

    client, err := compute.NewInstancesRESTClient(ctx,
        option.WithCredentialsFile(os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")))
    if err != nil { log.Fatalf("NewClient: %v", err) }
    defer client.Close()
}
```

## Cross-Skill Delegation

| Resource | Skill |
|----------|-------|
| VPC / Subnet | gcp-vpc-ops |
| Firewall Rules | gcp-vpc-ops |
| Load Balancing | gcp-lb-ops |
| Monitoring | gcp-monitoring-ops |
| DNS | gcp-dns-ops |
