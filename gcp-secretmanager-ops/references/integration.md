# Integration — Cloud Secret Manager

## Go SDK Bootstrap

### Prerequisites
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
export CLOUDSDK_CORE_PROJECT="my-project"
```

### Minimal Client
```go
package main

import (
    "context"
    "log"
    "os"
    
    secretmanager "cloud.google.com/go/secretmanager/apiv1"
    "google.golang.org/api/option"
)

func main() {
    ctx := context.Background()
    client, err := secretmanager.NewClient(ctx,
        option.WithCredentialsFile(os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")))
    if err != nil {
        log.Fatalf("NewClient: %v", err)
    }
    defer client.Close()
    // Use client...
}
```

### Error Handling
```go
import "google.golang.org/grpc/status"

if err != nil {
    st := status.Convert(err)
    switch st.Code() {
    case codes.NotFound:
        // Handle not found
    case codes.PermissionDenied:
        // Handle permission denied
    default:
        // Handle other errors
    }
}
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Yes | Path to service account JSON key |
| `CLOUDSDK_CORE_PROJECT` | Yes | GCP project ID |
| `CLOUDSDK_AUTH_ACCESS_TOKEN` | No | Temporary access token (alternative to SA key) |

## Credential Rules

### Authentication Priority
1. `GOOGLE_APPLICATION_CREDENTIALS` env var
2. Application Default Credentials (ADC)
3. gcloud CLI credentials

### Service Account Requirements

| Operation | Minimum IAM Role |
|-----------|-----------------|
| Create/Update/Delete secrets | roles/secretmanager.admin |
| Access secret versions | roles/secretmanager.secretAccessor |
| View secret metadata | roles/secretmanager.viewer |

### Security Guidelines

- **NEVER** log or print credential content
- **NEVER** commit service account keys to version control
- Use workload identity for GKE/GCE workloads
- Rotate service account keys regularly

## Python SDK Integration

### Installation
```bash
pip install google-cloud-secret-manager
```

### Client Initialization
```python
from google.cloud import secretmanager_v1 as sm

# Uses ADC automatically
client = sm.SecretManagerServiceClient()

# Or explicit credentials
client = sm.SecretManagerServiceClient.from_service_account_file(
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
)
```

## CI/CD Integration

### Cloud Build
```yaml
steps:
  - name: 'gcr.io/cloud-builders/gcloud'
    entrypoint: 'bash'
    args:
      - '-c'
      - |
        SECRET=$(gcloud secrets versions access latest --secret=my-secret --format="value(payload.data)")
        echo "$SECRET" > /tmp/secret
    secretEnv: ['MY_SECRET']
availableSecrets:
  secretManager:
    - versionName: projects/$PROJECT_ID/secrets/my-secret/versions/latest
      env: 'MY_SECRET'
```

### Terraform
```hcl
data "google_secret_manager_secret_version" "db_password" {
  secret = "db-password"
  project = var.project_id
}

resource "google_sql_user" "default" {
  name     = "app"
  password = data.google_secret_manager_secret_version.db_password.secret_data
}
```
