<!---
load_condition: "[总是加载 — 架构和状态模型]"
token_cost_estimate: "~1500 tokens"
dependencies: []
--->

# Core Concepts — Terraform on Google Cloud

## Resource Model

| Concept | Description |
|---------|-------------|
| **Configuration** | `.tf` files (HCL) describing desired GCP resources; authored by the user |
| **State** | `terraform.tfstate` — JSON mapping configuration to real GCP resources; stored in GCS |
| **Plan** | `terraform.tfplan` — diff between configuration and state; must precede all mutations |
| **Backend** | GCS bucket + DynamoDB lock table; remote state prevents concurrent mutations |
| **Provider** | `hashicorp/google ~> 5.0`; manages GCP API interaction |
| **Workspace** | Named state isolation within a backend; `default` workspace is standard |

## Directory Isolation Model

```
gcp-terraform-ops/environments/
├── dev/        → GCS bucket: gs://tf-state-dev-{project}/terraform/
│   ├── backend.tf    ← bucket: tf-state-dev-{project}
│   ├── versions.tf  ← provider version pinned
│   └── main.tf       ← dev-scale resources
├── staging/    → GCS bucket: gs://tf-state-staging-{project}/terraform/
│   └── ...
└── prod/       → GCS bucket: gs://tf-state-prod-{project}/terraform/
    └── ...
```

**Critical invariant**: each environment uses a **different GCS bucket**. This guarantees that even if the Agent navigates to the wrong directory or runs the wrong workspace, the state files for different environments cannot collide.

## Terraform Lifecycle

```
terraform init
  → Download providers, modules
  → Connect to GCS backend
  → Verify state lock table exists

terraform validate
  → Syntax check all .tf files
  → Reference check (variables, resources, data sources)
  → No API calls, no state read

terraform plan
  → Read current state from GCS
  → Compare configuration to state
  → Generate diff (.tfplan file)
  → Show create/destroy counts (NO mutations)

terraform apply
  → Require valid plan output from terraform plan
  → Apply changes to GCP API
  → Update state in GCS
  → Release state lock

terraform destroy
  → Require plan -destroy output
  → Require state backup (terraform state pull)
  → Require explicit resource list confirmation
  → Destroy all managed resources
  → Clear state (optional)
```

## Backend (GCS + DynamoDB Lock)

```hcl
terraform {
  backend "gcs" {
    bucket = "tf-state-{env}-{project}-terraform"
    prefix = "environments/{env}"
    # DynamoDB table: terraform-state-lock-{env}
    # Must exist before terraform init
  }
}
```

State lock uses DynamoDB with:
- Table name: `terraform-state-lock-{env}`
- Partition key: `LockID` (value: `gs://{bucket}/{prefix}/default.tfstate`)
- TTL: not used

## IAM Requirements (Terraform Service Account)

| Role | Scope | Purpose |
|------|-------|---------|
| `roles/owner` | Project (dev only) | Full resource management in dev |
| `roles/editor` | Project (staging) | Resource management without billing |
| Least-privilege | Per-resource (prod) | `roles/compute.admin`, `roles/cloudsql.admin`, etc. |

The Terraform service account (set via `GOOGLE_APPLICATION_CREDENTIALS` or ADC) needs permissions on:
1. **GCS bucket** — `storage.objectAdmin` (write state, read plan)
2. **DynamoDB lock table** — `dynamodb:GetItem`, `dynamodb:PutItem`, `dynamodb:DeleteItem`
3. **Target GCP resources** — varies by resource type

## State Lock Mechanism

When Terraform acquires the state lock:
- Lock ID written to DynamoDB with holder identity and timestamp
- All subsequent Terraform operations (plan/apply/destroy) check lock
- Lock automatically released on successful operation
- On failure, lock may be held — use `terraform force-unlock` only if lock is confirmed stale

```
# Check lock before planning
gcloud alpha storage ls gs://tf-state-dev-{project}/terraform/environments/dev/
# Check DynamoDB lock table
aws dynamodb get-item --table-name terraform-state-lock-dev --key '{"LockID":{"S":"gs://..."}}'
```

## Provider Version Pinning

All environments must use identical `required_providers` constraints. Pin to `~> 5.0` (allows 5.x.y, blocks 6.0.0+):

```hcl
required_providers {
  google = {
    source  = "hashicorp/google"
    version = "~> 5.0"  # Pinned — prevents provider upgrade drift
  }
}
```

## Terraform Import

Import brings an existing GCP resource into Terraform state without changing the resource:

```
terraform import {resource_address} {resource_id}
# Example: terraform import google_sql_database_instance.prod_db projects/{project}/instances/prod-postgres-xxx
```

- Import modifies state only — does not create or change the real resource
- After import, run `terraform plan` to verify state matches configuration
- If configuration does not match imported state, `terraform plan` will show differences

## Credential and Secret Handling

- **Never** place secrets in `.tfvars` files. Use:
  - Environment variables (`TF_VAR_*`)
  - GCP Secret Manager (`google_secret_manager_secret` data source)
  - GCS object (sensitive file in a private bucket)
- **Plan output redaction**: Terraform plan may expose variable values. Set `TF_IN_AUTOMATION=1` to reduce verbose output, but always inspect plan for sensitive values before sharing.
- **State file**: contains all resource attributes including potentially sensitive values. GCS bucket must have versioning enabled and lifecycle policy (90-day retention).