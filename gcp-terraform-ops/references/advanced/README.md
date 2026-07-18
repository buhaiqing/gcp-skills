# Advanced Terraform Operations — References

Advanced operational runbooks extending the core Terraform lifecycle management.

## Contents

| File | Description |
|------|-------------|
| [finops-cost-from-plan.md](./finops-cost-from-plan.md) | Parse `terraform show -json plan` to estimate costs using Infracost or GCP Pricing API; integrate into CI/CD with pre-apply cost gates |
| [validation-scripts-ci-cd.md](./validation-scripts-ci-cd.md) | Standalone validation scripts for CI/CD: `terraform fmt -check`, `terraform validate`, Checkov security scanning, Terratest unit testing |
| [terraform-import-resources.md](./terraform-import-resources.md) | `terraform import` for Cloud SQL, GKE, GCS, BigQuery with examples, state file management, and bulk import patterns |
| [workspace-team-collaboration.md](./workspace-team-collaboration.md) | Terraform workspace-based team collaboration: workspace isolation, state locking with GCS/DynamoDB, team IAM policies, CI/CD integration |
| [provider-version-upgrade.md](./provider-version-upgrade.md) | Provider version upgrade runbook: `terraform init -upgrade`, state migration, breaking change detection, rollback procedures |

## Usage

These runbooks are loaded **on-demand** when the referenced operation is needed:

| Operation | Load Condition |
|-----------|----------------|
| FinOps cost estimation | User asks about cost implications before apply |
| Validation scripts | CI/CD pipeline or pre-apply checks |
| Resource import | `terraform import` or adopting existing resources |
| Workspace management | Multi-environment or team collaboration |
| Provider upgrade | Upgrading Terraform GCP provider version |

## Related References

- [execution-flows.md](../execution-flows.md) — Core Pre-flight → Execute → Validate → Recover flows
- [core-concepts.md](../core-concepts.md) — Terraform state model, backend, workspace concepts
- [well-architected-assessment.md](../well-architected-assessment.md) — Well-Architected Framework alignment (Security/Stability/Cost/Efficiency/Performance)
- [troubleshooting.md](../troubleshooting.md) — Error diagnosis and recovery procedures

## Token Efficiency

Per AGENTS.md §9 (TE-7): Advanced content requiring deep operational knowledge (FinOps, CI/CD, multi-team) is layered into `references/advanced/` to keep SKILL.md lean. Reference depth is capped at 2 layers (SKILL.md → references/advanced/).
