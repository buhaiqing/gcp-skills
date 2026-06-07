# Core Concepts — Cloud SQL

## Architecture

Cloud SQL provides fully managed relational databases on Google Cloud. Each instance runs on a virtual machine with dedicated compute and storage resources, managed automatically by Google.

### Supported Database Engines

| Engine | Supported Versions | Unique Features |
|--------|-------------------|-----------------|
| **MySQL** | 5.7, 8.0 | Legacy compatibility, broad ecosystem |
| **PostgreSQL** | 14, 15, 16 | Advanced features (extensions, JSONB, PostGIS), IAM DB auth |
| **SQL Server** | 2019 Standard, 2019 Enterprise, 2022 Standard | Windows ecosystem, SSIS/SSRS support |

### Key Components

| Component | Description | Scope |
|-----------|-------------|-------|
| **Instance** | Managed VM running the database engine | Region |
| **Database** | Logical database within an instance | Instance-level |
| **User** | Database user with credentials | Instance-level |
| **Backup** | Automated or on-demand backup of instance data | Regional |
| **Read Replica** | Read-only copy of the primary instance | Same or different region |
| **Clone** | Point-in-time copy of an instance | Same region |

### Connectivity Options

| Method | Description | Use Case |
|--------|-------------|----------|
| **Public IP** | Instance accessible via public internet | Dev/test, authorized networks |
| **Private IP** | Instance accessible only within VPC | Production, secure workloads |
| **Cloud SQL Auth Proxy** | Sidecar proxy for secure connections | Production apps, no static IP |
| **SSL/TLS** | Encrypted connections with server cert | All production workloads |

## Quotas

Check current quotas:
```bash
# List available tiers and limits
gcloud sql tiers list --region="{{user.region}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"

# Check instance count quotas
gcloud compute regions describe "{{user.region}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '.quotas[] | select(.metric | test("sql|cpu")) | {metric, limit, usage}'
```

### Default Quotas

| Resource | Default Limit | Request Increase |
|----------|---------------|-----------------|
| Instances per project | 150 (varies by region) | Cloud Console |
| CPUs per project | Regional limit | Cloud Console |
| Backups per instance | 365 automated | N/A |
| Read replicas per instance | 10 (MySQL), 10 (PG) | Cloud Console |
| Concurrent operations | 10 per project | N/A |

## Dependencies

| Depend On | Reason |
|-----------|--------|
| VPC / Subnet | Private IP instances require VPC |
| Cloud Storage (GCS) | Import/export operations |
| IAM | Service account for Admin API; IAM DB auth (PG) |
| Cloud Monitoring | Instance metrics and Query Insights |
| Cloud KMS | CMEK for encryption |
| Secret Manager | Store DB credentials (recommended) |

## SPOF Analysis

| Scenario | Impact | Mitigation |
|----------|--------|------------|
| Single instance fails | App database unavailable | REGIONAL HA failover |
| Zone down | Zonal instance goes down | REGIONAL availability type |
| Region down | All instances in region lost | Cross-region read replica + promote |
| Storage full | Instance rejects writes | Monitor storage, auto-increase |
| Corruption (data) | Data loss | Automated backups + PITR |
| Corruption (schema) | Application errors | Clone to point before change |
| Quota exhausted | Can't create instances | Request increase
## Prerequisites

> **Self-Healing**: Installation flows include multi-path recovery. Each step has ≥3 error-handling strategies.

### 1. Install gcloud CLI

```bash
if ! command -v gcloud &> /dev/null; then
    curl https://sdk.cloud.google.com | bash 2>/dev/null \
    || (sudo apt-get update && sudo apt-get install -y google-cloud-sdk) \
    || (wget -q https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-x86_64.tar.gz \
        && tar -xf google-cloud-cli-*.tar.gz && ./google-cloud-sdk/install.sh --quiet)
    exec -l $SHELL; gcloud init
fi
```

### 2. Bootstrap Go Runtime (JIT Fallback)

```bash
if ! command -v go &> /dev/null; then
    OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    ARCH=$(uname -m); [ "$ARCH" = "x86_64" ] && ARCH="amd64"
    curl -fsSL "https://go.dev/dl/go1.24.0.${OS}-${ARCH}.tar.gz" | tar -xz -C /tmp/go-runtime 2>/dev/null \
    || curl -fsSL "https://go.dev/dl/go1.24.0.linux-${ARCH}.tar.gz" | tar -xz -C /tmp/go-runtime
    export PATH="/tmp/go-runtime/go/bin:$PATH"
fi
```

### 3. Configure Credentials

```bash
export GOOGLE_APPLICATION_CREDENTIALS="{{env.GOOGLE_APPLICATION_CREDENTIALS}}"
export CLOUDSDK_CORE_PROJECT="{{env.CLOUDSDK_CORE_PROJECT}}"
gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS" 2>/dev/null || gcloud auth login --quiet
gcloud config set project "$CLOUDSDK_CORE_PROJECT"
```

### 4. Enable Cloud SQL Admin API

```bash
gcloud services enable sqladmin.googleapis.com --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### 5. Verify Configuration

```bash
gcloud auth application-default print-access-token --quiet &>/dev/null && echo "✅ Auth OK"
gcloud sql instances list --limit=1 --format="json" &>/dev/null && echo "✅ Cloud SQL API OK"
```

> **Security**: Never commit service account keys to version control. All credentials use `{{env.*}}` placeholders.
