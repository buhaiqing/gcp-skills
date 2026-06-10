<!---
load_condition: "[总是加载 — 变量约定和环境路径]"
token_cost_estimate: "~900 tokens"
dependencies: []
--->

# Variables and API Conventions — Terraform Operations

## Variable Convention

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.GOOGLE_APPLICATION_CREDENTIALS}}` | Path to service account key JSON | NEVER ask; verify file exists without printing content |
| `{{env.CLOUDSDK_CORE_PROJECT}}` | Default project ID | NEVER ask; HALT if unset |
| `{{env.CLOUDSDK_AUTH_ACCESS_TOKEN}}` | Temporary access token | NEVER ask; refresh via gcloud as needed |
| `{{env.TF_LOG}}` | Terraform log level (DEBUG/INFO/WARN/ERROR) | NEVER ask; default off |
| `{{env.TF_IN_AUTOMATION}}` | Reduces verbose output | NEVER ask; default off |
| `{{user.environment}}` | Target environment | Ask once; one of `dev`, `staging`, `prod` |
| `{{user.target_dir}}` | Terraform working directory | Ask once; derived from `{{user.environment}}` → `environments/{{user.environment}}/` |
| `{{user.plan_out_file}}` | Plan output file path | Ask once; default `{{user.target_dir}}/.tfplan` |
| `{{user.confirm_apply}}` | Apply confirmation | Require plan summary display; explicit acknowledgement before apply |
| `{{user.confirm_destroy}}` | Destroy confirmation | Require exact resource list + state backup confirmation |
| `{{user.resource_address}}` | Terraform resource address for import/state operations | Ask once; format: `google_sql_database_instance.prod_db` |
| `{{user.resource_id}}` | GCP resource ID for import | Ask once; format: `projects/{project}/instances/{name}` |
| `{{user.workspace_name}}` | Terraform workspace name | Ask once; defaults to `default` |
| `{{user.state_lock_id}}` | State lock ID (from plan output) | Parse from `terraform plan` output; use in unlock on failure |
| `{{user.backend_bucket}}` | GCS bucket for backend | From `environments/{{user.environment}}/backend.tf`; confirm different across envs |
| `{{user.var_file}}` | Variable file path | Ask once; default `environments/{{user.environment}}/terraform.tfvars` |
| `{{user.import_resource_type}}` | Resource type to import | Ask once; must match Terraform resource type schema |
| `{{user.backup_file}}` | State backup file path | Ask once; format `backup-{{user.environment}}-{timestamp}.json` |
| `{{output.plan_summary}}` | Plan summary | Parse from `terraform plan` stdout: `+N create, -M destroy, ~K modify` |
| `{{output.destroy_count}}` | Resources to be destroyed | Parse from `terraform plan -destroy` output |
| `{{output.state_lock_id}}` | State lock identifier | Parse from plan error or `terraform plan` lock acquisition message |
| `{{output.apply_summary}}` | Apply result | Parse from `terraform apply` stdout: resources added/modified/destroyed |
| `{{output.imported_resource}}` | Imported resource address | Parse from `terraform import` stdout |
| `{{output.output_values}}` | Terraform output values | Parse from `terraform output -json` |

> `{{env.*}}` values are never collected from the user. `{{user.*}}` values are asked once and reused. Never print service account key content, access tokens, or plan output containing sensitive variable values.

## Centralized Environment Paths

| Environment | Directory | GCS Backend Bucket | DynamoDB Lock Table |
|-------------|-----------|-------------------|---------------------|
| `dev` | `environments/dev/` | `gs://tf-state-dev-{project}-terraform` | `terraform-state-lock-dev` |
| `staging` | `environments/staging/` | `gs://tf-state-staging-{project}-terraform` | `terraform-state-lock-staging` |
| `prod` | `environments/prod/` | `gs://tf-state-prod-{project}-terraform` | `terraform-state-lock-prod` |

**Isolation guarantee**: each environment uses a different GCS bucket. If the Agent runs `terraform apply` in the wrong directory, the state is isolated to that environment's bucket — it cannot overwrite another environment's state.

## Terraform Command Output Parsing

| Operation | Output Format | Parse Key |
|-----------|--------------|----------|
| `terraform plan` | Text summary | `+N create, -M destroy, ~K in-place` |
| `terraform plan -destroy` | Text list | `-/+ resource_type.resource_name` |
| `terraform apply` | Text summary | `Apply complete! Resources: N added, M changed, K destroyed.` |
| `terraform state list` | One resource per line | `resource_type.resource_name` |
| `terraform output` | `-json` flag gives structured output | `$.value` |
| `terraform show` | JSON state dump | `$.resources[].type, name, instances` |
| `terraform validate` | Exit code only (0=pass) | return code |
| `terraform import` | `Imported google_xxx resource_name` | resource address confirmation |

## Safety Conventions

- **Plan must precede apply**: always run `terraform plan -out={{user.plan_out_file}}` before `terraform apply`.
- **Destroy requires backup**: always run `terraform state pull > {{user.backup_file}}` before `terraform destroy`.
- **Lock verification**: check state lock before plan/apply; never force-unlock unless lock is confirmed stale.
- **Backend isolation check**: before any mutation, confirm the GCS bucket in `backend.tf` is unique to this environment.