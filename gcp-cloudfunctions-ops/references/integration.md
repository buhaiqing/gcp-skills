# Integration — Cloud Functions

## Environment Setup

**Primary path:** `gcloud` CLI (Google Cloud SDK, Python-based)

**Fallback path:** JIT Go SDK (dynamic script generation + `go run`)

### Go Runtime Bootstrap

If Agent Runtime lacks Go, JIT download from official source:

```bash
if ! command -v go &> /dev/null; then
    OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    ARCH=$(uname -m)
    [ "$ARCH" = "x86_64" ] && ARCH="amd64"
    [ "$ARCH" = "aarch64" ] && ARCH="arm64"
    
    mkdir -p /tmp/go-runtime
    curl -fsSL "https://go.dev/dl/go1.24.0.${OS}-${ARCH}.tar.gz" | tar -xz -C /tmp/go-runtime
    export PATH="/tmp/go-runtime/go/bin:$PATH"
    export GOPATH="/tmp/go-workspace"
    export GOCACHE="/tmp/go-cache"
fi

go version
```

> **Go version strategy:** JIT download Go 1.24+ (latest stable), script compatibility Go 1.21+ (minimum).

### JIT Go SDK Workflow

1. **Initialize workspace:**
   ```bash
   mkdir -p /tmp/gcp-sdk-workspace && cd /tmp/gcp-sdk-workspace
   go mod init sdk-script
   ```

2. **Get dependencies:**
   ```bash
   export GOPROXY="https://proxy.golang.org,direct"
   go get cloud.google.com/go/functions/v2
   ```

3. **Generate script** (Agent dynamically creates operation-specific `.go` file)

4. **Execute:**
   ```bash
   go run ./main.go
   ```

### SDK Package Naming

| GCP Product | Go SDK Package |
|-------------|---------------|
| Cloud Functions | `cloud.google.com/go/functions/v2` |
| Cloud Run | `cloud.google.com/go/run/apiv2` |
| Cloud Storage | `cloud.google.com/go/storage` |
| Pub/Sub | `cloud.google.com/go/pubsub` |
| Cloud Build | `cloud.google.com/go/cloudbuild/apiv1/v2` |
| IAM | `cloud.google.com/go/iam/admin/apiv1` |

> Find package names at: https://pkg.go.dev/cloud.google.com/go

## Go SDK Script Template

```go
package main

import (
    "context"
    "fmt"
    "log"
    "os"

    functions "cloud.google.com/go/functions/v2"
    functionspb "cloud.google.com/go/functions/v2/apiv2/functionspb"
)

func main() {
    ctx := context.Background()
    client, err := functions.NewClient(ctx)
    if err != nil {
        log.Fatalf("Failed to create client: %v", err)
    }
    defer client.Close()

    project := os.Getenv("CLOUDSDK_CORE_PROJECT")
    location := os.Getenv("CLOUDSDK_COMPUTE_REGION", "us-central1")

    // Operation-specific code (generated per REST API)
    name := fmt.Sprintf("projects/%s/locations/%s/functions/my-function", project, location)
    function, err := client.GetFunction(ctx, &functionspb.GetFunctionRequest{Name: name})
    if err != nil {
        log.Fatalf("Failed to get function: %v", err)
    }

    fmt.Printf("Function: %s (state: %s)\n", function.Name, function.State)
}
```

> Use `os.Getenv("KEY")` for all credentials. Never hardcode secrets in scripts. Never `fmt.Printf("%+v", config)` as it may leak credential values.

## Credential Rules

| Variable | Purpose | Source |
|----------|---------|--------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON key | `{{env.*}}` — NEVER ask user |
| `CLOUDSDK_CORE_PROJECT` | GCP project ID | `{{env.*}}` or `gcloud config get-value project` |
| `CLOUDSDK_AUTH_ACCESS_TOKEN` | Temporary access token | `gcloud auth print-access-token` |

**Never output credentials**: Replace access tokens and service account keys in logs with `****`. Python SDK reads credentials via `GOOGLE_APPLICATION_CREDENTIALS` env var automatically (safe). Go SDK scripts' `config` structs, `fmt.Println(config)`, and `log.Printf("%+v", ...)` can all leak credentials — prohibit such output.

**Credential verification MUST check existence only**, never echo the value:
- Bash: `test -n "$GOOGLE_APPLICATION_CREDENTIALS"` ✅ | `cat $GOOGLE_APPLICATION_CREDENTIALS` ❌
- Go: `if os.Getenv("GOOGLE_APPLICATION_CREDENTIALS") == ""` ✅ | `fmt.Println(os.Getenv("GOOGLE_APPLICATION_CREDENTIALS"))` ❌

## Environment Variable Loading

Credentials sourced in priority order:
```
Shell env (highest) > `.env` file > gcloud config (lowest)
```

### `.env` File Format

```ini
# Google Cloud credentials
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
CLOUDSDK_CORE_PROJECT=my-gcp-project
```

- **Security**: `.env` MUST be in `.gitignore` — never commit credentials

## Cross-Skill Integration Patterns

| Dependency | Skill | When to Delegate |
|------------|-------|-----------------|
| VPC Connector setup | `gcp-vpc-ops` | Function needs VPC access and connector doesn't exist |
| Secret Manager setup | `gcp-secretmanager-ops` | Secret doesn't exist or needs IAM configuration |
| Eventarc triggers | `gcp-eventarc-ops` | Custom event routing beyond built-in triggers |
| Cloud Build CI/CD | `gcp-cloudbuild-ops` | Automated deployment pipelines |
| Monitoring/Alerts | `gcp-monitoring-ops` | Dashboards, alert policies, log-based metrics |
| IAM roles/policies | `gcp-iam-ops` | Complex IAM beyond function-level bindings |
| Cloud Run migration | `gcp-cloudrun-ops` | Gen2 functions backed by Cloud Run infrastructure |
| Artifact Registry | `gcp-artifactregistry-ops` | Container image management for packaged functions |
| Cloud Scheduler | `gcp-scheduler-ops` | Cron-triggered function invocations |
| BigQuery | `gcp-bigquery-ops` | Function writes to BigQuery |
| Cloud Storage | `gcp-gcs-ops` | Function reads/writes to Cloud Storage |

### Inline Delegation Pattern

When a Cloud Functions operation depends on another skill's resource, inline the necessary commands:

```markdown
# Execution — Deploy function with VPC connector
# 1. Verify VPC connector exists (delegate to gcp-vpc-ops if creation needed)
gcloud compute networks vpc-access connectors describe my-connector --region=us-central1 --format=json || {
    echo "VPC connector not found. Delegate to gcp-vpc-ops to create."
    exit 1
}

# 2. Deploy function with VPC connector
gcloud functions deploy my-function --gen2 --vpc-connector=my-connector ...
```
