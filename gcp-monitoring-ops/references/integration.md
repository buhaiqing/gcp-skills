# Integration — Cloud Monitoring

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

## Python SDK Setup

```bash
pip install --quiet --user google-cloud-monitoring
```

## Go SDK Setup

```bash
go get cloud.google.com/go/monitoring/apiv3
go get cloud.google.com/go/monitoring/apiv3/v2/monitoringpb
go get google.golang.org/api/option
go get google.golang.org/protobuf/types/known/timestamppb
go get google.golang.org/protobuf/types/known/durationpb
```

## Go SDK Script Template

```go
package main

import (
    "context"
    "fmt"
    "log"
    "os"
    monitoring "cloud.google.com/go/monitoring/apiv3"
    "cloud.google.com/go/monitoring/apiv3/v2/monitoringpb"
    "google.golang.org/api/option"
)

func main() {
    ctx := context.Background()
    project := os.Getenv("CLOUDSDK_CORE_PROJECT")
    if project == "" { log.Fatal("CLOUDSDK_CORE_PROJECT not set") }
    client, err := monitoring.NewMetricClient(ctx,
        option.WithCredentialsFile(os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")))
    if err != nil { log.Fatalf("NewClient: %v", err) }
    defer client.Close()

    alertClient, err := monitoring.NewAlertPolicyClient(ctx,
        option.WithCredentialsFile(os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")))
    if err != nil { log.Fatalf("NewAlertClient: %v", err) }
    defer alertClient.Close()
    // ... operations here
}
```

## IAM Roles

| Role | Permissions | Use Case |
|------|-------------|----------|
| `roles/monitoring.viewer` | `monitoring.timeSeries.list`, `monitoring.alertPolicies.get`, `monitoring.dashboards.get` | Read-only dashboards and metrics |
| `roles/monitoring.editor` | All viewer + `monitoring.alertPolicies.create/update/delete`, `monitoring.notificationChannels.*`, `monitoring.dashboards.*` | Manage alerts, channels, dashboards |
| `roles/monitoring.admin` | All editor + `monitoring.monitoredResourceDescriptors.*`, `monitoring.metricDescriptors.*` | Full Monitoring management |
| `roles/monitoring.notificationChannelEditor` | `monitoring.notificationChannels.*` | Manage notification channels only |

## Credential Rules

| Variable | Purpose | Source |
|----------|---------|--------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to SA key JSON | `{{env.*}}` — NEVER ask user |
| `CLOUDSDK_CORE_PROJECT` | GCP project ID | `{{env.*}}` or `gcloud config get-value project` |
| `CLOUDSDK_AUTH_ACCESS_TOKEN` | Temporary access token | `gcloud auth print-access-token` |

**Never output credentials**: Replace tokens and key paths in logs with `****`. Python SDK reads credentials via env var automatically.

## Cross-Skill Delegation

| Scenario | Delegate To |
|----------|-------------|
| VM instance investigation (CPU, disk, SSH) | `gcp-gce-ops` |
| GKE cluster/node metrics | `gcp-gke-ops` |
| Log queries and log-based metrics source | `gcp-logging-ops` |
| Cloud SQL performance metrics source | `gcp-cloudsql-ops` |
| IAM role management for Monitoring | `gcp-iam-ops` |
| Billing and cost analysis for Monitoring | `gcp-billing-ops` |
