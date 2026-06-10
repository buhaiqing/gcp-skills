<!---
load_condition: "[首次使用或环境配置时加载]"
token_cost_estimate: "~700 tokens"
dependencies: []
--->

# Integration — Terraform Operations

## Environment Variables

| Variable | Purpose | Rule |
|----------|---------|------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Terraform service account key path | Verify existence; never print file content |
| `CLOUDSDK_CORE_PROJECT` | Default GCP project | Use for `gcloud` fallback commands; Terraform uses `var.project_id` |
| `TF_LOG` | Log verbosity (DEBUG/INFO/WARN/ERROR) | Default off; enable only for diagnostics |
| `TF_IN_AUTOMATION` | Reduces plan output verbosity | Default off; set to `1` in automated scripts |

## Terraform Installation

```bash
# Check installed version
terraform version

# Install (if missing) — use tfenv or official installer
brew install tfenv && tfenv install 1.8.0

# Verify provider requirements
terraform init -backend=false  # dry-run init without backend
terraform version  # minimum 1.6.0 required
```

## Backend Setup (GCS + DynamoDB Lock)

### Step 1: Create GCS Buckets (one per environment)

```bash
# Dev bucket
gsutil mb -l us-central1 gs://tf-state-dev-{project}-terraform

# Staging bucket
gsutil mb -l us-central1 gs://tf-state-staging-{project}-terraform

# Prod bucket — use separate project for stricter isolation
gsutil mb -l us-central1 gs://tf-state-prod-{project}-terraform

# Enable versioning for state backup
gsutil versioning set on gs://tf-state-dev-{project}-terraform
gsutil versioning set on gs://tf-state-staging-{project}-terraform
gsutil versioning set on gs://tf-state-prod-{project}-terraform
```

### Step 2: Create DynamoDB Lock Tables (one per environment)

```bash
# Create DynamoDB table with on-demand billing
aws dynamodb create-table \
  --table-name terraform-state-lock-dev \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

aws dynamodb create-table \
  --table-name terraform-state-lock-staging \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

aws dynamodb create-table \
  --table-name terraform-state-lock-prod \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

### Step 3: Grant Terraform Service Account Permissions

```bash
# Terraform service account (from GOOGLE_APPLICATION_CREDENTIALS)
TERRAFORM_SA=$(gcloud iam service-accounts list \
  --filter="email ~ terraform@" \
  --format="value(email)" | head -1)

# GCS bucket permissions (per environment)
for env in dev staging prod; do
  gsutil iam ch serviceAccount:${TERRAFORM_SA}:roles/storage.objectAdmin \
    gs://tf-state-${env}-{project}-terraform
  gsutil iam ch serviceAccount:${TERRAFORM_SA}:roles/storage.objectViewer \
    gs://tf-state-${env}-{project}-terraform/environments/${env}
done

# DynamoDB lock table permissions
for env in dev staging prod; do
  aws dynamodb grant-table-permissions \
    --table-name terraform-state-lock-${env} \
    --permissions GetItem PutItem DeleteItem \
    --aws-principal-arn ${TERRAFORM_SA}
done
```

## Required GCP Roles by Resource Type (Least-Privilege for Prod)

| Resource Type | Minimal Roles |
|--------------|-------------|
| Compute (VM, network, firewall) | `roles/compute.admin` |
| Cloud SQL | `roles/cloudsql.admin` |
| GKE | `roles/container.admin` |
| Cloud Storage | `roles/storage.admin` |
| VPC | `roles/compute.networkAdmin` |
| IAM | `roles/resourcemanager.projectIamAdmin` (or narrower) |
| Secret Manager | `roles/secretmanager.admin` |
| BigQuery | `roles/bigquery.admin` |

## Cross-Skill Integration

- **State file backup**: after `terraform state pull`, store backup in GCS bucket under `backups/` prefix
- **GCL trace**: persist `terraform plan` output and `terraform apply` result to `./audit-results/gcl-trace-*.json`
- **GCS bucket lifecycle**: use `gsutil lifecycle set` to auto-delete non-current state versions after 90 days
- **Terraform workspace**: use `terraform workspace select {env}` (not directory switching) for team collaboration

## Safe Output Contract

Reports should include:
- Environment directory and GCS bucket (sanitized)
- Plan summary: create/destroy/modify counts per resource type
- State lock ID (if acquired)
- Validation result (apply succeeded / destroy completed)
- Next steps (state file updated, resources managed)

Reports must not include:
- Service account key content
- Access tokens
- Secrets from `.tfvars` or state file
- Full Terraform state dump (use `terraform state list` instead)