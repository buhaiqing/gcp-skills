# Integration

## Environment Setup

**Primary path:** `gcloud` CLI (via `gcloud compute` subcommands)

**Fallback path:** JIT Go SDK (dynamic script generation + `go run`)

### Go Runtime Bootstrap

> See AGENTS.md §0.2 — embedded Go JIT bootstrap (do not duplicate here).

### JIT Go SDK Workflow

1. Initialize workspace:
   ```bash
   mkdir -p /tmp/gcp-sdk-workspace
   cd /tmp/gcp-sdk-workspace
   go mod init sdk-script
   ```

2. Get dependencies:
   ```bash
   export GOPROXY="https://proxy.golang.org,direct"
   go get cloud.google.com/go/compute/apiv1
   go get google.golang.org/api/option
   go get google.golang.org/protobuf/proto
   ```

3. Generate script → `go run ./main.go`

### SDK Package Reference

| Product | Go SDK | Python SDK |
|---------|--------|------------|
| Compute (VPC) | `cloud.google.com/go/compute/apiv1` | `google-cloud-compute` |
| Compute (operations) | `cloud.google.com/go/compute/apiv1` | `google-cloud-compute` |

## Environment Variable Loading

```bash
export GOOGLE_APPLICATION_CREDENTIALS="{{env.GOOGLE_APPLICATION_CREDENTIALS}}"
export CLOUDSDK_CORE_PROJECT="{{env.CLOUDSDK_CORE_PROJECT}}"
```

## Go SDK Script Template

```go
package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"time"

	compute "cloud.google.com/go/compute/apiv1"
	"cloud.google.com/go/compute/apiv1/computepb"
	"google.golang.org/api/option"
	"google.golang.org/protobuf/proto"
)

func main() {
	ctx := context.Background()

	client, err := compute.NewNetworksRESTClient(ctx,
		option.WithCredentialsFile(os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")))
	if err != nil {
		log.Fatalf("Failed to create client: %v", err)
	}
	defer client.Close()

	project := os.Getenv("CLOUDSDK_CORE_PROJECT")

	// Replace with operation-specific request
	req := &computepb.ListNetworksRequest{Project: project}
	it := client.List(ctx, req)

	for {
		network, err := it.Next()
		if err != nil {
			break
		}
		fmt.Printf("Network: %s (subnetMode: %s)\n",
			network.GetName(), network.GetAutoCreateSubnetworks())
	}
}
```

> Use `os.Getenv("KEY")` for all credentials. Never hardcode secrets in scripts.
