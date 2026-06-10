<!---
load_condition: "[失败或报错时加载]"
token_cost_estimate: "~1200 tokens"
dependencies: []
--->

# Troubleshooting — Terraform on Google Cloud

## Diagnostic Flow

1. Identify the failing operation (init, validate, plan, apply, destroy, import, state).
2. Capture the full error message — Terraform errors are structured and informative.
3. Classify using the error taxonomy below.
4. Recommend the smallest safe fix. Do not force-unlock, force-apply, or skip plan unless explicitly approved.

## Error Taxonomy

| Code / Symptom | Likely Cause | Recovery |
|----------------|--------------|----------|
| `Error: Failed to decode cache file` | Corrupted `.terraform.lock.hcl` or provider cache | Delete `.terraform.lock.hcl` and re-run `terraform init` |
| `Error: Failed to save plan` | Disk full or permissions on plan output directory | Verify directory exists and is writable; check disk space |
| `Backend initialization required` | `backend.tf` changed or `init` never run | Run `terraform init` with `-reconfigure` if backend config changed |
| `Error: Missing required provider` | `versions.tf` not initialized, provider not downloaded | Run `terraform init`; verify `required_providers` block in `versions.tf` |
| `Error: Provider version constraint` | Installed provider version conflicts with `versions.tf` constraint | Run `terraform init -upgrade` to update provider; verify version constraint in `versions.tf` |
| `Error: Unsupported block type` | HCL syntax error — unsupported block in context | Fix `.tf` file syntax; check Terraform version matches required_version in `versions.tf` |
| `Error: Missing network tier` | GCP resource-specific attribute missing (e.g., `network_tier` for `google_compute_address`) | Add required attribute to `.tf` file; do not manually edit if module-managed |
| `Error: Invalid resource address` | Wrong resource address format for import/state operations | Use format `google_resource_type.resource_name`; list resources with `terraform state list` |
| `Error: Resource already exists` | Resource was created outside Terraform (e.g., via gcloud) | Use `terraform import` to bring into state; do not recreate |
| `Error: Resource not found` | Resource was deleted outside Terraform but still in state | Run `terraform plan` to detect drift; remove stale state with `terraform state rm` |
| `Error: Provider has no available resource` | GCP API version changed, resource type deprecated | [VERIFY: check hashicorp/google provider changelog]; update provider version or resource type |
| `Error: Concurrent plan/apply` | State lock held by another operation | Wait for the other operation to complete; check DynamoDB lock table |
| `State lock held by another process` | Previous operation failed without releasing lock | Check if other Terraform process is running; if stale (> 10 min), use `terraform force-unlock {lock_id}` |
| `Error: IAM policy` | Terraform service account lacks required GCP IAM role | Grant required role to the Terraform service account via `gcp-iam-ops`; do not use `roles/owner` in prod unless required |
| `Error: Bucket does not exist` | GCS backend bucket not created | Create bucket with `gsutil mb -l {region} gs://tf-state-{env}-{project}-terraform`; verify bucket name in `backend.tf` |
| `Error: Permission denied (storage)` | Terraform service account lacks GCS bucket permissions | Grant `roles/storage.objectAdmin` on the backend bucket to the Terraform service account |
| `Error: Permission denied (GCP API)` | Terraform service account lacks resource-specific role | Grant least-privilege role for the specific resource type; delegate via `gcp-iam-ops` |
| `Error: Module not found` | Terraform Registry module not accessible or version doesn't exist | Verify module source URL and version; check network access to registry.terraform.io |
| `Error: Duplicate resource` | Same resource defined in multiple `.tf` files | Search for duplicate `resource` blocks; consolidate or remove duplicates |
| `Error: Cycle detected` | Module dependency cycle | [VERIFY: check module graph with `terraform graph`]; restructure module dependencies |
| `Error: Invalid function argument` | Wrong argument type or value for HCL function | Check Terraform built-in function documentation; verify argument types |
| `Error: Instance count exceeded` | GCP quota exceeded for the resource type | Check `gcloud compute instances list` for current count; request quota increase or use resource scheduling |
| `Plan shows destroy for resources not in config` | State drift — resource was deleted outside Terraform | Investigate drift source; run `terraform plan` and review destroy list before apply |

## Diagnostic Commands

```bash
# Verify Terraform version
terraform version

# Check which directory Terraform is running in
pwd
ls -la environments/{{user.environment}}/ | grep -E "backend|versions|main|variables"

# Verify backend configuration
grep -A5 'backend "gcs"' environments/{{user.environment}}/backend.tf

# Verify state lock (check DynamoDB)
aws dynamodb get-item \
  --table-name terraform-state-lock-{{user.environment}} \
  --key '{"LockID":{"S":"gs://tf-state-{{user.environment}}-{project}/environments/{{user.environment}}/default.tfstate"}}'

# Verify GCS bucket exists and is accessible
gsutil ls -la gs://tf-state-{{user.environment}}-{project}-terraform/environments/{{user.environment}}/ | head -5

# Check for concurrent Terraform processes
ps aux | grep terraform

# State inspection
cd environments/{{user.environment}}/
terraform state list | head -20
terraform state pull > /tmp/{{user.environment}}-state-backup.json

# Plan with verbose output
TF_LOG=DEBUG terraform plan -out={{user.target_dir}}/.tfplan 2>&1 | tail -50

# Check for secrets in tfvars (diagnostic)
grep -E 'password|secret|api_key|private_key' environments/{{user.environment}}/terraform.tfvars
```

## Recovery Rules

| Situation | Rule |
|-----------|------|
| State lock held | Wait; if stale (> 10 min), `terraform force-unlock {lock_id}` |
| Provider version conflict | `terraform init -upgrade` |
| State drift | Run `terraform plan` first; review destroy list; decide to import or accept drift |
| Wrong resource in state | `terraform state rm google_xxx.wrong_name` then `terraform import` correct resource |
| GCS bucket permission error | Grant Terraform service account `roles/storage.objectAdmin` on bucket |
| Plan shows unexpected destroy | STOP; investigate; do not apply until destroy list is confirmed intentional |
| Corrupted state file | Restore from GCS versioned state: `gsutil cp gs://bucket/path/default.tfstate.backup environments/{{user.environment}}/terraform.tfstate` |
| HCL syntax error | Fix `.tf` file; do not use `terraform apply -auto-approve` to bypass validation |