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
CLOUDSDK_AUTH_ACCESS_TOKEN=<token>
SQL_INSTANCE_NAME=my-instance
SQL_REGION=us-central1
SQL_DATABASE_VERSION=MYSQL_8_0
SQL_TIER=db-n1-standard-2
SQL_USER_PASSWORD=my-secure-password
```

## Go SDK Script Template

```go
package main

import (
    "context" "fmt" "log" "os"
    sql "cloud.google.com/go/sql/apiv1"
    "cloud.google.com/go/sql/apiv1/sqlpb"
    "google.golang.org/api/option"
)

func main() {
    ctx := context.Background()
    project := os.Getenv("CLOUDSDK_CORE_PROJECT")

    client, err := sql.NewSqlInstancesRESTClient(ctx,
        option.WithCredentialsFile(os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")))
    if err != nil { log.Fatalf("NewClient: %v", err) }
    defer client.Close()

    req := &sqlpb.SqlInstancesGetRequest{
        Project: project,
        Instance: os.Getenv("SQL_INSTANCE_NAME"),
    }
    resp, err := client.Get(ctx, req)
    if err != nil { log.Fatalf("Get: %v", err) }
    fmt.Printf("Instance: %s, State: %s\n", resp.Name, resp.State)
}
```

## Cloud SQL Auth Proxy Setup

Cloud SQL Auth Proxy provides secure access to Cloud SQL instances without authorized networks or SSL configuration.

```bash
# Download
curl -o /tmp/cloud-sql-proxy \
  "https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.13.0/cloud-sql-proxy.linux.amd64"
chmod +x /tmp/cloud-sql-proxy

# Run for a specific instance
/tmp/cloud-sql-proxy --auto-iam-authn \
  "{{env.CLOUDSDK_CORE_PROJECT}}:{{user.region}}:{{user.instance_name}}"

# Connect via local port
MYSQL_PWD="{{user.password}}" mysql -u "{{user.user_name}}" -h 127.0.0.1 -P 3306 -D "{{user.database_name}}"
PGPASSWORD="{{user.password}}" psql -U "{{user.user_name}}" -h 127.0.0.1 -p 5432 -d "{{user.database_name}}"
```

> **Security**: Passwords are passed via `MYSQL_PWD`/`PGPASSWORD` environment variables, NOT via CLI `-p` flags. This prevents password exposure in `ps aux` output or shell history.

## IAM Database Authentication (PostgreSQL)

PostgreSQL supports IAM database authentication, eliminating the need for passwords:

```bash
# 1. Enable IAM DB auth
gcloud sql instances patch {{user.instance_name}} \
  --database-flags=cloudsql.iam_authentication=on

# 2. Create a user with IAM format
gcloud sql users create "{{user.user_email}}@{{env.CLOUDSDK_CORE_PROJECT}}.iam" \
  --instance="{{user.instance_name}}" \
  --type=cloud_iam_service_account

# 3. Connect using Cloud SQL Auth Proxy with IAM auth
/tmp/cloud-sql-proxy --auto-iam-authn \
  "{{env.CLOUDSDK_CORE_PROJECT}}:{{user.region}}:{{user.instance_name}}"
psql -U "{{user.user_email}}@{{env.CLOUDSDK_CORE_PROJECT}}.iam" \
  -h 127.0.0.1 -d "{{user.database_name}}"
```

## Cross-Skill Delegation

| Resource | Skill |
|----------|-------|
| VPC / Subnet (private IP) | gcp-vpc-ops |
| Cloud Storage (import/export) | gcp-gcs-ops |
| IAM / Service Accounts | gcp-iam-ops |
| Monitoring & Alerts | gcp-monitoring-ops |
| Cloud KMS (CMEK) | gcp-kms-ops |
| Secret Manager | gcp-secretmanager-ops |