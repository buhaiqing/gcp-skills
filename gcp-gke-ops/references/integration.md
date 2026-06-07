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
CLOUDSDK_CONTAINER_CLUSTER=my-cluster
CLOUDSDK_COMPUTE_ZONE=us-central1-a
CLOUDSDK_COMPUTE_REGION=us-central1
```

## Go SDK Script Template

```go
package main

import (
    "context" "fmt" "log" "os"
    container "cloud.google.com/go/container/apiv1"
    "cloud.google.com/go/container/apiv1/containerpb"
    "google.golang.org/api/option"
)

func main() {
    ctx := context.Background()
    project := os.Getenv("CLOUDSDK_CORE_PROJECT")
    location := os.Getenv("CLOUDSDK_CONTAINER_CLUSTER")
    if location == "" { location = "us-central1" }

    client, err := container.NewClusterManagerClient(ctx,
        option.WithCredentialsFile(os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")))
    if err != nil { log.Fatalf("NewClusterManagerClient: %v", err) }
    defer client.Close()

    req := &containerpb.CreateClusterRequest{
        ProjectId: project,
        Zone:      location,
        Cluster: &containerpb.Cluster{
            Name:             "my-cluster",
            InitialNodeCount: 3,
            NodeConfig: &containerpb.NodeConfig{
                MachineType: "e2-medium",
                DiskSizeGb:  100,
                DiskType:    "pd-balanced",
            },
        },
    }
    op, err := client.CreateCluster(ctx, req)
    if err != nil { log.Fatalf("CreateCluster: %v", err) }
    if err := op.Wait(ctx); err != nil { log.Fatalf("Wait: %v", err) }
    fmt.Println("Created cluster: my-cluster")
}
```

Execute:
```bash
cd /tmp/gcp-sdk-workspace && go mod init sdk-script && go mod tidy && go run ./main.go
```

## Cross-Skill Delegation

| Resource | Skill |
|----------|-------|
| VPC / Subnet / Secondary Ranges | gcp-vpc-ops |
| Firewall Rules | gcp-vpc-ops |
| Load Balancing | gcp-lb-ops |
| IAM / Service Accounts | gcp-iam-ops |
| Monitoring | gcp-monitoring-ops |
| DNS | gcp-dns-ops |
| Backup / Disaster Recovery | Manual (gcloud container backup-restore) |
| Container Images | Artifact Registry (indirect)