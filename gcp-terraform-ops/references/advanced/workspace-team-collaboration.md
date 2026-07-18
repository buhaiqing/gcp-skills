# Terraform Workspace Team Collaboration

> Terraform workspace-based team collaboration: workspace isolation, state locking with DynamoDB/S3, team IAM policies, and remote state backend configuration.

## Table of Contents

1. [Overview](#overview)
2. [Workspace Architecture](#workspace-architecture)
3. [Remote Backend Configuration](#remote-backend-configuration)
4. [State Locking](#state-locking)
5. [Team IAM Policies](#team-iam-policies)
6. [Workspace Lifecycle](#workspace-lifecycle)
7. [CI/CD Integration](#cicd-integration)
8. [Best Practices](#best-practices)
9. [See Also](#see-also)

## Overview

Terraform workspaces enable teams to manage multiple environments (dev, staging, prod) from a single configuration while maintaining isolated state files. This runbook covers the operational patterns for team-based Terraform workspace management on GCP.

### Workspace Isolation Model

| Workspace | State Backend | GCS Bucket | DynamoDB Table | Purpose |
|-----------|---------------|-----------|----------------|---------|
| `dev` | gcs | `gs://tf-state-dev-{project}` | `tf-lock-dev` | Development |
| `staging` | gcs | `gs://tf-state-staging-{project}` | `tf-lock-staging` | Pre-production |
| `prod` | gcs | `gs://tf-state-prod-{project}` | `tf-lock-prod` | Production |

## Workspace Architecture

### Directory Structure

```
terraform/
├── environments/
│   ├── dev/
│   │   ├── backend.tf
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── terraform.tfvars
│   ├── staging/
│   │   └── ...
│   └── prod/
│       └── ...
├── modules/
│   ├── networking/
│   ├── compute/
│   └── database/
└── shared/
    └── versions.tf
```

### Environment-Specific Backend

```hcl
# environments/dev/backend.tf
terraform {
  backend "gcs" {
    bucket = "tf-state-dev-${var.project_id}"
    prefix = "dev/terraform.tfstate"
  }
}
```

## Remote Backend Configuration

### GCS Backend with State Locking

```hcl
# environments/shared/backend.tf
terraform {
  backend "gcs" {
    bucket                 = "tf-state-${var.environment}-${var.project_id}"
    prefix                 = "terraform/state"
    encryption_key_alias    = "terraform-state-key"  # CSEK or CMEK
  }
}
```

### Backend Variables

```hcl
# environments/dev/variables.tf
variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}
```

### Initialize with Backend

```bash
cd environments/dev/

# Initialize with specific workspace
terraform init

# Or initialize with backend config
terraform init -backend-config="bucket=tf-state-dev-myproject"
```

## State Locking

### DynamoDB Table for State Locking

```bash
# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name tf-state-lock-dev \
  --attribute-yes \
  --attribute-name LockID \
  --attribute-type S \
  --billing-mode PAY_PER_REQUEST \
  --key-schema AttributeName=LockID,KeyType=HASH

# Or via gcloud (if using Google Cloud Storage for state only)
# Note: Terraform GCS backend uses GCS for locking by default
# For DynamoDB, use terraform-aws-backend module or AWS provider
```

### Verify State Locking

```bash
# Run plan - this will acquire and release lock automatically
terraform plan

# If locked, you see:
# Error: Error acquiring the state lock
# Lock Info:
#   ID:        abc-123-xyz
#   Who:       user@example.com
#   Operation: OperationTypePlan
#   Created:   2024-01-15 10:30:00.000 +0000 UTC

# Check who holds the lock
terraform state pull | jq '.metadata'

# Force unlock (USE WITH CAUTION - only if lock is stale)
# terraform force-unlock <lock-id>
```

### Lock Timeout Configuration

```hcl
# environments/dev/backend.tf
terraform {
  backend "gcs" {
    bucket = "tf-state-dev-${var.project_id}"
    prefix = "terraform/state"

    # GCS bucket versioning for state history
    # Enable versioning on bucket separately via gsutil
  }
}
```

## Team IAM Policies

### Service Account for Terraform

```bash
# Create Terraform service account
gcloud iam service-accounts create terraform-runner \
  --display-name="Terraform CI/CD Runner"

# Grant project-level roles (adjust to least-privilege)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:terraform-runner@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/owner"  # Or more specific roles

# Download key (for CI/CD - prefer workload identity)
gcloud iam service-accounts keys create terraform-sa-key.json \
  --iam-account=terraform-runner@$PROJECT_ID.iam.gserviceaccount.com
```

### GCS Bucket IAM

```bash
# Set bucket-level permissions
gsutil iam ch serviceAccount:terraform-runner@$PROJECT_ID.iam.gserviceaccount.com:storage.admin \
  gs://tf-state-dev-$PROJECT_ID/

# Bucket-only policy for state bucket
gsutil mb -p $PROJECT_ID -l us-central1 gs://tf-state-dev-$PROJECT_ID
gsutil uniformbucketlevelaccess set on gs://tf-state-dev-$PROJECT_ID

# Encryption with CMEK
gsutil kms encryption -k projects/$PROJECT_ID/locations/us-central1/keyRings/tf-keyring/cryptoKeys/tf-state-key \
  gs://tf-state-dev-$PROJECT_ID/
```

### Workspace-Specific Policies

```bash
# Dev workspace - broader access
gcloud projects add-iam-policy-binding $DEV_PROJECT_ID \
  --member="group:dev-team@company.com" \
  --role="roles/editor"

# Prod workspace - restricted access
gcloud projects add-iam-policy-binding $PROD_PROJECT_ID \
  --member="group:platform-team@company.com" \
  --role="roles/editor"

# Break-glass access for emergencies
gcloud projects add-iam-policy-binding $PROD_PROJECT_ID \
  --member="user:emergency-access@company.com" \
  --role="roles/owner"
```

## Workspace Lifecycle

### Create New Workspace

```bash
# Create workspace (implicit via terraform init with backend)
cd environments/new-environment/
terraform init

# Or select existing
terraform workspace new staging
terraform workspace select staging
```

### Workspace Commands

```bash
# List all workspaces
terraform workspace list

# Show current workspace
terraform workspace show

# Select workspace
terraform workspace select dev

# Create workspace
terraform workspace new feature-x

# Delete workspace (MUST be empty)
terraform workspace delete feature-x
```

### Workspace-Specific Configuration

```hcl
# environments/shared/workspace-vars.tf
locals {
  # Workspace-specific values
  instance_count = terraform.workspace == "prod" ? 3 :
                   terraform.workspace == "staging" ? 2 : 1

  machine_type = terraform.workspace == "prod" ? "n2-standard-4" :
                 terraform.workspace == "staging" ? "n2-standard-2" :
                 "n2-standard-2"

  environment_labels = {
    environment = terraform.workspace
    managed_by  = "terraform"
  }
}
```

### Workspace State Operations

```bash
# Pull current state
terraform state pull > state.json

# Push state (rarely needed)
terraform state push state.json

# List resources in current workspace state
terraform state list

# Move resource between states
terraform state mv \
  google_compute_instance.old \
  google_compute_instance.new
```

## CI/CD Integration

### GitHub Actions with Workspace Selection

```yaml
# .github/workflows/terraform.yml
name: Terraform

on:
  push:
    branches: [main]
  pull_request:

jobs:
  terraform:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        environment: [dev, staging, prod]

    steps:
      - uses: actions/checkout@v4

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: 1.6.0
          terraform_wrapper: true

      - name: Configure GCP Credentials
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Init Terraform
        run: |
          terraform init -backend=true
        env:
          TF_VAR_environment: ${{ matrix.environment }}
          TF_VAR_project_id: ${{ vars.GCP_PROJECT_ID }}
        working-directory: environments/${{ matrix.environment }}

      - name: Select Workspace
        run: terraform workspace select ${{ matrix.environment }}

      - name: Validate
        run: terraform validate

      - name: Plan
        run: terraform plan -out=tfplan

      - name: Apply (on push to main)
        if: github.ref == 'refs/heads/main' && github.event_name == 'push'
        run: terraform apply -auto-approve tfplan
```

### Protected Production Access

```yaml
# .github/workflows/terraform-prod.yml
name: Terraform Prod

on:
  push:
    branches: [main]
    paths:
      - 'environments/prod/**'

jobs:
  terraform-prod:
    runs-on: ubuntu-latest
    environment: production  # Requires GitHub Environment approval
    steps:
      - uses: actions/checkout@v4

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: 1.6.0

      - name: Authenticate
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_PROD_SA_KEY }}

      - name: Init
        run: terraform init
        working-directory: environments/prod

      - name: Plan
        run: terraform plan

      - name: Apply
        if: github.event_name == 'push'
        run: terraform apply -auto-approve
```

## Best Practices

### Workspace Naming Conventions

```bash
# Use descriptive names
terraform workspace new feature/add-gpu-nodes
terraform workspace new bugfix/sql-memory-issue

# Avoid numbers in workspace names (conflicts with terraform)
terraform workspace new staging-2  # Avoid
terraform workspace new staging2    # OK
```

### State Isolation

```bash
# NEVER share state between environments
# Each workspace must have its own GCS bucket

# Wrong
terraform {
  backend "gcs" {
    bucket = "tf-state-shared"  # BAD - shared state
  }
}

# Correct
terraform {
  backend "gcs" {
    bucket = "tf-state-${var.environment}-${var.project_id}"
  }
}
```

### Lock Timeout and Retries

```bash
# Set environment variable for longer lock timeout
export TF_LOCK_TIMEOUT=10m

# Retry on lock contention
terraform plan -lock-timeout=5m
```

### State Backup

```bash
# Enable GCS bucket versioning (manual step)
gsutil versioning set on gs://tf-state-dev-$PROJECT_ID

# List state versions
gsutil ls -a gs://tf-state-dev-$PROJECT_ID/terraform/

# Restore old version
gsutil cp gs://tf-state-dev-$PROJECT_ID/terraform/terraform.tfstate#older-version ./restore.tfstate
```

## See Also

- [Terraform Workspaces](https://developer.hashicorp.com/terraform/cli/workspaces)
- [GCS Backend](https://developer.hashicorp.com/terraform/language/settings/backends/gcs)
- [DynamoDB State Locking](https://developer.hashicorp.com/terraform/language/state/locking)
- [Well-Architected Assessment - Efficiency](../well-architected-assessment.md#efficiency)
