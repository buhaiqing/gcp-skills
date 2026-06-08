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
CLOUDSDK_AUTH_ACCESS_TOKEN=
BQ_DATASET_ID=my_dataset
BQ_TABLE_ID=my_dataset.my_table
BQ_LOCATION=US
```

## Go SDK Script Template

```go
package main

import (
    "context"
    "fmt"
    "log"
    "os"

    "cloud.google.com/go/bigquery"
    "google.golang.org/api/option"
)

func main() {
    ctx := context.Background()
    project := os.Getenv("CLOUDSDK_CORE_PROJECT")

    client, err := bigquery.NewClient(ctx, project,
        option.WithCredentialsFile(os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")))
    if err != nil { log.Fatalf("NewClient: %v", err) }
    defer client.Close()
}
```

## IAM Role Requirements

| Operation | Minimum IAM Role |
|-----------|------------------|
| List datasets | `roles/bigquery.user` |
| Create dataset | `roles/bigquery.dataOwner` or `roles/bigquery.admin` |
| Create table | `roles/bigquery.dataEditor` or higher |
| Run query | `roles/bigquery.jobUser` + table read access |
| Load data | `roles/bigquery.dataEditor` + `roles/storage.objectViewer` |
| Export data | `roles/bigquery.dataViewer` + `roles/storage.objectAdmin` |
| Delete dataset/table | `roles/bigquery.dataOwner` or `roles/bigquery.admin` |
| Set IAM policy | `roles/bigquery.admin` |
| Create routine | `roles/bigquery.dataEditor` or higher |

## Credential Rules

| Variable | Purpose | Source |
|----------|---------|--------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to SA key JSON | `{{env.*}}` — NEVER ask user |
| `CLOUDSDK_CORE_PROJECT` | GCP project ID | `{{env.*}}` or `gcloud config get-value project` |
| `CLOUDSDK_AUTH_ACCESS_TOKEN` | Temporary access token | `gcloud auth print-access-token` |

**Never output credentials**: Replace access tokens and service account keys in logs with `****`.

## Cross-Skill Delegation

| Resource | Skill |
|----------|-------|
| IAM / Service Accounts | gcp-iam-ops |
| GCS (load/export source/dest) | gcp-gcs-ops |
| Cloud KMS Keys | (planned) |
| Monitoring / Alerts | gcp-monitoring-ops |
| VPC Service Controls | gcp-vpc-ops |
