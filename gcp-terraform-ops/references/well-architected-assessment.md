<!---
load_condition: "[架构评审时加载]"
token_cost_estimate: "~700 tokens"
dependencies: []
--->

# Well-Architected Assessment — Terraform Operations

## Pillar Summary

| Pillar | Controls | Evidence |
|--------|----------|----------|
| Security | GCS backend with versioning, DynamoDB lock, no secrets in tfvars, plan output redaction, IAM least-privilege, GCL required for apply/destroy | backend.tf, state lock, tfvars check, GCL trace |
| Stability | State lock prevents concurrent mutations, plan preview before all mutations, state backup before destroy, idempotent init/validate/plan | execution-flows.md, state backup, lock check |
| Cost | Plan shows resource changes, no unexpected recreate, state file size monitoring | plan output, monitoring.md |
| Efficiency | Remote state, lock table, module caching, workspace isolation for team collaboration | backend.tf, workspace commands |
| Performance | Backend GCS + DynamoDB lock; large state handling via modules; parallel plan where applicable | backend config, module structure |

## Security

| Check | Method | Target |
|-------|--------|--------|
| Backend GCS bucket versioning | `gsutil versioning get gs://tf-state-{env}-{project}-terraform` | Versioning enabled |
| No secrets in tfvars | `grep -E 'password|secret|api_key' environments/*/terraform.tfvars` | No matches |
| DynamoDB lock table exists | `aws dynamodb describe-table --table-name terraform-state-lock-{env}` | Table present |
| Terraform service account least-privilege | Describe service account IAM | No `roles/owner` in prod unless required |
| State file not world-readable | `gsutil iam get gs://tf-state-{env}-{project}-terraform/environments/{env}/default.tfstate` | No `allUsers`/`allAuthenticatedUsers` |
| GCL trace persisted | Check `./audit-results/gcl-trace-*.json` exists | Trace for apply/destroy |
| Plan output redaction | Inspect plan output before sharing | No plaintext secrets |

## Stability

- `terraform plan` must precede every `terraform apply` and `terraform destroy`.
- State lock must be acquirable before any mutation; if lock is held, investigate before force-unlock.
- State backup must be created before every `terraform destroy` via `terraform state pull > backup-{env}-{timestamp}.json`.
- `terraform apply` partial failure: inspect state with `terraform show` and decide next action; do not re-apply blindly.
- `terraform destroy` partial failure: fix GCP API errors, re-plan destroy, do not re-apply without review.

## Cost

- Plan output shows resource creation/destruction count. Review before apply to catch unexpected large resource creates.
- State file size > 10 MB indicates large state; consider module splitting to reduce plan time and state lock duration.
- GCS bucket egress costs: Terraform state is accessed on every plan/apply. Consider using a regional GCS bucket in the same region as the Terraform runtime.
- [VERIFY: exact GCS storage costs for state files across environments — check current GCP pricing]

## Efficiency

- Workspace isolation allows team members to work on different features without conflicting on state.
- Remote state (GCS) enables collaboration without file-sharing.
- Module caching via `.terraform/modules/` reduces provider download time.
- Plan file (`-out=.tfplan`) allows exact replay of the planned changes without re-running the plan.

## Performance

- State file size directly affects plan/apply latency. Large state (> 50 MB) may cause timeouts.
- DynamoDB lock table on-demand billing is cost-efficient; provisioned capacity is only needed for high-frequency plan/apply.
- Provider plugin download: run `terraform init` once per environment; cached in `.terraform/`.
- Workspace switching (`terraform workspace select`) is instant — no state download required.