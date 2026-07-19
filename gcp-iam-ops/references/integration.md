# Integration

### Go Runtime Bootstrap (JIT SDK fallback)
> See AGENTS.md §0.2 — Go JIT bootstrap is defined once at repo level, not duplicated here.

## Environment Variables

```ini
GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
CLOUDSDK_CORE_PROJECT=my-gcp-project
SA_EMAIL=my-sa@my-project.iam.gserviceaccount.com
```

## Python SDK Setup

```bash
# Install required packages
pip install --quiet --user google-cloud-iam google-cloud-resourcemanager google-cloud-asset
```

## Go SDK Script Template (IAM Roles)

```go
package main

import (
    "context" "fmt" "log" "os"
    iam "cloud.google.com/go/iam/admin/apiv1"
    "cloud.google.com/go/iam/admin/apiv1/adminpb"
    "google.golang.org/api/option"
)

func main() {
    ctx := context.Background()
    project := os.Getenv("CLOUDSDK_CORE_PROJECT")

    client, err := iam.NewIamClient(ctx,
        option.WithCredentialsFile(os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")))
    if err != nil { log.Fatalf("NewClient: %v", err) }
    defer client.Close()

    // Example: list service accounts
    req := &adminpb.ListServiceAccountsRequest{
        Name: "projects/" + project,
    }
    it := client.ListServiceAccounts(ctx, req)
    for {
        sa, err := it.Next()
        if err != nil { break }
        fmt.Printf("SA: %s (%s)\n", sa.Email, sa.DisplayName)
    }
}
```

## Go SDK Script Template (IAM Policies via Resource Manager)

```go
package main

import (
    "context" "fmt" "log" "os"
    resourcemanager "cloud.google.com/go/resourcemanager/apiv3"
    "google.golang.org/api/option"
)

func main() {
    ctx := context.Background()
    project := os.Getenv("CLOUDSDK_CORE_PROJECT")

    client, err := resourcemanager.NewProjectsClient(ctx,
        option.WithCredentialsFile(os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")))
    if err != nil { log.Fatalf("NewClient: %v", err) }
    defer client.Close()

    // Example: get IAM policy
    policy, err := client.GetIamPolicy(ctx, &iampb.GetIamPolicyRequest{
        Resource: "projects/" + project,
    })
    if err != nil { log.Fatalf("GetIamPolicy: %v", err) }
    fmt.Printf("Policy etag: %s\n", policy.Etag)
}
```

## Credential Rules

| Variable | Purpose | Source | Safe Pattern |
|----------|---------|--------|--------------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to SA key JSON | `{{env.*}}` | `test -f "$GOOGLE_APPLICATION_CREDENTIALS"` — existence check only |
| `CLOUDSDK_CORE_PROJECT` | GCP project ID | `{{env.*}}` or `gcloud config` | Read from env; never expose value if sensitive |
| `SA_EMAIL` | Service account email | `{{user.*}}` or `{{output.*}}` | Safe to log |
| Private Key Data | SA private key content | Single response on key create | **NEVER log, output, or expose** |

> **CRITICAL:** Go SDK scripts with `config` structs, `fmt.Println(config)`, or `log.Printf("%+v", ...)` can leak credentials — prohibit such output. Python SDK auto-reads from env var — safe.

## Cross-Skill Delegation

| Resource | Skill |
|----------|-------|
| KMS CryptoKey IAM | gcp-kms-ops (planned) |
| Project / Folder / Org hierarchy | gcp-resourcemanager-ops (planned) |
| Monitoring & Alerting | gcp-monitoring-ops |
| Compute Engine SA association | gcp-gce-ops |
| GKE Workload Identity | gcp-gke-ops |