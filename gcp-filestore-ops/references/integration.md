# Integration

## Go Runtime Bootstrap

```bash
if ! command -v go &> /dev/null; then
    OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    ARCH=$(uname -m); [ "$ARCH" = "x86_64" ] && ARCH="amd64"
    [ "$ARCH" = "aarch64" ] && ARCH="arm64"
    mkdir -p /tmp/go-runtime
    curl -fsSL "https://go.dev/dl/go1.24.0.${OS}-${ARCH}.tar.gz" | tar -xz -C /tmp/go-runtime 2>/dev/null \
    || curl -fsSL "https://go.dev/dl/go1.24.0.linux-${ARCH}.tar.gz" | tar -xz -C /tmp/go-runtime
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

## Credential Rules

| Variable | Purpose | Source |
|----------|---------|--------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON key | `{{env.*}}` — NEVER ask user |
| `CLOUDSDK_CORE_PROJECT` | GCP project ID | `{{env.*}}` or `gcloud config get-value project` |
| `CLOUDSDK_COMPUTE_ZONE` | Default compute zone | `{{env.*}}` or `gcloud config get-value compute/zone` |
| `CLOUDSDK_COMPUTE_REGION` | Default compute region | `{{env.*}}` or `gcloud config get-value compute/region` |

**Never output credentials**: Replace access tokens and service account keys in logs with `****`. Python SDK reads credentials via `GOOGLE_APPLICATION_CREDENTIALS` env var automatically (safe).

## Go SDK Script Template

```go
// main.go (generated dynamically in /tmp/gcp-sdk-workspace)
package main

import (
    "context"
    "fmt"
    "log"
    "os"

    filestore "cloud.google.com/go/filestore/apiv1"
    "google.golang.org/api/option"
)

func main() {
    ctx := context.Background()
    project := os.Getenv("CLOUDSDK_CORE_PROJECT")
    creds := os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")

    client, err := filestore.NewCloudFilestoreManagerClient(ctx,
        option.WithCredentialsFile(creds))
    if err != nil {
        log.Fatalf("NewClient: %v", err)
    }
    defer client.Close()

    // Example: List instances
    parent := fmt.Sprintf("projects/%s/locations/%s", project, "us-central1-a")
    it := client.ListInstances(ctx, &filestorepb.ListInstancesRequest{
        Parent: parent,
    })
    for {
        resp, err := it.Next()
        if err != nil {
            break
        }
        fmt.Printf("Instance: %s\n", resp.Name)
    }
}
```

> ⚠️ Never output credential values in logs or fmt.Println. Go SDK config structs can leak — prohibit such output.

## Python SDK Setup

```bash
# Install Python SDK
pip install google-cloud-filestore

# Verify installation
python3 -c "from google.cloud import filestore_v1; print('✅ Filestore SDK OK')"
```

## Cross-Skill Delegation

| Resource | Skill |
|----------|-------|
| IAM / Service Accounts | gcp-iam-ops |
| VPC Networks | gcp-vpc-ops |
| Cloud KMS Keys | gcp-kms-ops |
| Monitoring | gcp-monitoring-ops |
| Cloud Logging | gcp-logging-ops |
