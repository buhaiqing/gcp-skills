# Integration

## Environment Setup

**Primary path:** `gcloud` CLI (Google Cloud SDK, Python-based)

**Fallback path:** JIT Go SDK (dynamic script generation + `go run`)

### Go Runtime Bootstrap

```bash
if ! command -v go &> /dev/null; then
    OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    ARCH=$(uname -m); [ "$ARCH" = "x86_64" ] && ARCH="amd64"; [ "$ARCH" = "aarch64" ] && ARCH="arm64"
    mkdir -p /tmp/go-runtime
    curl -fsSL "https://go.dev/dl/go1.24.0.${OS}-${ARCH}.tar.gz" | tar -xz -C /tmp/go-runtime
    export PATH="/tmp/go-runtime/go/bin:$PATH"
    export GOPATH="/tmp/go-workspace"
    export GOCACHE="/tmp/go-cache"
fi
```

> **Go version strategy:** JIT download Go 1.24+; script compatibility Go 1.21+

### JIT Go SDK Workflow

```bash
mkdir -p /tmp/gcp-sdk-workspace
cd /tmp/gcp-sdk-workspace
go mod init sdk-script
export GOPROXY="https://proxy.golang.org,direct"
go get cloud.google.com/go/compute/apiv1
go get google.golang.org/api/option
# Generate and run script
go run ./main.go
```

### SDK Package Naming

| Resource | Go SDK Package |
|----------|---------------|
| Forwarding Rules | `cloud.google.com/go/compute/apiv1` (ForwardingRulesClient) |
| Backend Services | `cloud.google.com/go/compute/apiv1` (BackendServicesClient) |
| URL Maps | `cloud.google.com/go/compute/apiv1` (UrlMapsClient) |
| Health Checks | `cloud.google.com/go/compute/apiv1` (HealthChecksClient) |
| Target Proxies | `cloud.google.com/go/compute/apiv1` (TargetHttpProxiesClient / TargetHttpsProxiesClient) |
| SSL Certificates | `cloud.google.com/go/compute/apiv1` (SslCertificatesClient) |
| NEGs | `cloud.google.com/go/compute/apiv1` (NetworkEndpointGroupsClient) |

### Environment Variables

```ini
# .env file
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
CLOUDSDK_CORE_PROJECT=my-gcp-project
CLOUDSDK_COMPUTE_REGION=us-central1
CLOUDSDK_COMPUTE_ZONE=us-central1-a
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
    compute "cloud.google.com/go/compute/apiv1"
    "cloud.google.com/go/compute/apiv1/computepb"
    "google.golang.org/api/option"
)

func main() {
    ctx := context.Background()
    project := os.Getenv("CLOUDSDK_CORE_PROJECT")

    client, err := compute.NewForwardingRulesRESTClient(ctx,
        option.WithCredentialsFile(os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")))
    if err != nil {
        log.Fatalf("NewClient: %v", err)
    }
    defer client.Close()

    // Operation-specific code below — see SKILL.md Execution Flows
}
```

### Cross-Skill Delegation Matrix

| Resource | Skill | Integration Point |
|----------|-------|-------------------|
| VM Instances / MIGs | `gcp-gce-ops` | Create instance groups as LB backends |
| VPC / Subnets | `gcp-vpc-ops` | Internal LB subnet creation; firewall rules for health checks |
| DNS Records | `gcp-dns-ops` | A/AAAA DNS record pointing at LB IP |
| IAM | `gcp-iam-ops` | Service accounts and IAM roles for LB operations |
| Monitoring | `gcp-monitoring-ops` | Dashboards and alerts for LB health |

> **Security:** All credentials use `{{env.*}}` placeholders. Never hardcode secrets.
> Prohibit `log.Printf("%+v", ...)` on client config or `fmt.Println(config)` — these can leak credential values.