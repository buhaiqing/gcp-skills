---
name: billing-integration
description: Environment setup, Go bootstrap, env vars, IAM roles, and cross-skill delegation for Cloud Billing

<!---
load_condition: "[集成/环境设置时加载]"
token_cost_estimate: "~800 tokens"
dependencies: []
--->
---

# Integration — Cloud Billing

## Environment Setup

### Primary Path: gcloud CLI

```bash
gcloud version
gcloud auth application-default print-access-token --quiet && echo "✅ Auth OK"
```

### Fallback Path: Python SDK

```bash
pip install --quiet --user google-cloud-billing google-cloud-billing-budgets
```

### Required APIs

```bash
gcloud services enable cloudbilling.googleapis.com --project="{{env.CLOUDSDK_CORE_PROJECT}}"
gcloud services enable billingbudgets.googleapis.com --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

## Required IAM Roles

| Operation | Minimum Role | Scope |
|-----------|-------------|-------|
| List/describe billing accounts | `roles/billing.viewer` | Billing account or organization |
| Link/unlink projects | `roles/billing.accountAdmin` | Billing account |
| Budget CRUD | `roles/billing.budgetAdmin` | Billing account |
| Export CRUD | `roles/billing.costsManager` | Billing account |
| Query pricing/SKUs | `roles/billing.viewer` | Organization |
| BigQuery export data read | `roles/bigquery.dataViewer` | BigQuery dataset |

## Go Runtime Bootstrap (JIT SDK Fallback)

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
    export GOMODCACHE="/tmp/go-modcache"
    export GOPROXY="https://proxy.golang.org,direct"
fi
go version
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Yes | Path to SA key JSON |
| `CLOUDSDK_CORE_PROJECT` | Yes | GCP project ID |
| `CLOUDSDK_AUTH_ACCESS_TOKEN` | Auto | Temporary access token |
| `BILLING_ACCOUNT_ID` | Conditional | Default billing account for operations |

## Cross-Skill Delegation Matrix

| Capability | Delegate To | When |
|------------|-------------|------|
| IAM role management | `gcp-iam-ops` | Granting/revoking billing roles |
| BigQuery dataset/table admin | `gcp-bigquery-ops` | Creating export destination dataset |
| Monitoring alert policies | `gcp-monitoring-ops` | Non-budget alert policies for spend metrics |
| Pub/Sub topic management | `gcp-pubsub-ops` | Creating budget alert Pub/Sub topics |
| FinOps deep-dive | `references/advanced/finops-cost-analysis.md` | Resource-level cost optimization |
| GCL quality gate | `gcp-gcl-runner-ops` | Adversarial review of budget/export mutations |

## JIT Go SDK Workflow

```bash
mkdir -p /tmp/gcp-sdk-workspace
cd /tmp/gcp-sdk-workspace
go mod init sdk-script
go get cloud.google.com/go/billing/apiv1
go get google.golang.org/api/option
go run ./main.go
```

## SDK Package Names

| GCP Product | Go SDK Package |
|-------------|---------------|
| Cloud Billing | `cloud.google.com/go/billing/apiv1` |
| Billing Budgets | `cloud.google.com/go/billing/budgets/apiv1` (or REST API) |

## Security Notes

- Never print `GOOGLE_APPLICATION_CREDENTIALS` path content or access tokens.
- Billing account IDs are not secrets but avoid logging in public channels.
- Budget threshold email recipients should be previewed with partial masking.
- Use `gcloud auth application-default print-access-token` for API calls; never store tokens.
