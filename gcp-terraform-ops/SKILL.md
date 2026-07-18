---
name: gcp-terraform-ops
description: >-
  Use when the user needs to manage Google Cloud infrastructure via Terraform —
  initialize working directories, validate HCL configuration, plan and apply
  infrastructure changes, destroy resources, manage Terraform state, import
  existing GCP resources into Terraform state, manage workspaces, or read
  infrastructure output values. Triggers on terraform, tf, HCL, infrastructure
  as code, IaC, .tf file, terraform plan, terraform apply, terraform destroy,
  terraform init, terraform validate, terraform state, terraform workspace,
  terraform import, environments/dev, environments/staging, environments/prod,
  backend GCS, Terraform workspace. Not for manual gcloud commands that manage
  GCP resources directly (delegate to gcp-gce-ops, gcp-gke-ops, etc.), or for
  Terraform module development (this skill manages plan/apply/validate/state,
  not HCL configuration authoring).
license: MIT
compatibility: >-
  HashiCorp Terraform CLI (1.6+), Google Cloud Platform provider (hashicorp/google
  ~> 5.0), valid Google Cloud credentials with Terraform service account roles
  (roles/owner or equivalent for target resources), GCS bucket for state backend,
  DynamoDB table for state locking, and network access to storage.googleapis.com.
metadata:
  author: gcp-skills
  version: "1.0.0"
  last_updated: "2026-06-09"
  runtime: Harness AI Agent, Claude Code, or compatible Agent runtimes
  go_version_minimum: "1.21"
  gcl_classification: "required"
  gcl_max_iter: 2
  api_profile: "https://developer.hashicorp.com/terraform/cli/commands"
  cli_applicability: "cli-only"  # Terraform is its own CLI, not gcloud
  cli_support_evidence: >-
    terraform --version, terraform init, terraform validate, terraform plan,
    terraform apply, terraform destroy, terraform import, terraform state,
    terraform workspace, terraform output, terraform show. All subcommands are
    documented at https://developer.hashicorp.com/terraform/cli/commands.
  environment:
    - GOOGLE_APPLICATION_CREDENTIALS
    - CLOUDSDK_CORE_PROJECT
    - CLOUDSDK_AUTH_ACCESS_TOKEN
    - TF_LOG (optional, for debug output)
    - TF_IN_AUTOMATION (optional, for reduced output formatting)
---

> This skill follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Google Cloud Terraform Operations Skill

## Overview

Terraform on GCP uses HashiCorp Terraform to manage infrastructure as code. State files track the mapping between HCL configuration and real GCP resources. This skill is an operational runbook for agents to perform Terraform lifecycle operations — init, validate, plan, apply, destroy, state management, workspace management, and resource import — with explicit scope, credential safety, pre-flight checks, environment isolation, dual safety gates (plan preview + GCL review) for all mutations, validation, recovery, monitoring, and GCL adversarial review for apply/destroy.

> **UX Compliance:** Follow the [User Experience Specification](../gcp-skill-generator/references/user-experience-spec.md): always confirm the target environment directory before mutation, show plan output before apply, and mask sensitive values from plan output.

### Directory Structure (Environment Isolation)

```
gcp-terraform-ops/
└── environments/
    ├── dev/          ← GCS bucket: gs://tf-state-dev-{project}/terraform/
    │   ├── backend.tf
    │   ├── versions.tf
    │   ├── main.tf
    │   ├── variables.tf
    │   ├── terraform.tfvars
    │   └── outputs.tf
    ├── staging/      ← GCS bucket: gs://tf-state-staging-{project}/terraform/
    │   └── ...
    └── prod/         ← GCS bucket: gs://tf-state-prod-{project}/terraform/
        └── ...

```

Each environment has its own GCS bucket — directory isolation guarantees that `environments/dev/` state never collides with `environments/prod/` state, even if Agent navigates to the wrong directory.

### CLI applicability

- **`cli_applicability: cli-only`:** Terraform is its own CLI (`terraform`). Do not use `gcloud` commands to manage resources that Terraform manages. Delegate `gcloud`-only operations to the appropriate GCP skill (gcp-gce-ops, gcp-gke-ops, etc.).
- The Terraform CLI covers all operations in this skill. No SDK fallback is needed.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT triggers distinguish Terraform lifecycle management from gcloud SDK operations and from HCL authoring |
| 2 | **Structured I/O** | Variables use `{{env.*}}`, `{{user.*}}`, `{{output.*}}`; environment paths centralized at [variables-and-conventions.md](references/variables-and-conventions.md) |
| 3 | **Explicit Actionable Steps** | Operations include Pre-flight → Execute → Validate → Recover; plan must precede all apply/destroy; full details at [execution-flows.md](references/execution-flows.md) |
| 4 | **Complete Failure Strategies** | [troubleshooting.md](references/troubleshooting.md) has ≥15 Terraform-specific error rows with HALT/retry guidance |
| 5 | **Absolute Single Responsibility** | One tool: Terraform CLI; adjacent GCP resource lifecycle delegated to Terraform module consumers |

### Google Cloud Architecture Framework / Well-Architected Framework Integration

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **Security** | GCS backend with DynamoDB lock, state encryption, no secrets in tfvars, plan output redaction, GCL required for apply/destroy | [well-architected-assessment.md](references/well-architected-assessment.md#security) |
| **Stability** | State lock prevents concurrent mutations, plan preview before all mutations, idempotent init/validate/plan, state backup before destroy | [well-architected-assessment.md](references/well-architected-assessment.md#stability) |
| **Cost** | Plan shows resource count and estimated cost implications; drift detection avoids unnecessary recreate | [well-architected-assessment.md](references/well-architected-assessment.md#cost) |
| **Efficiency** | Remote state, lock table, parallel plan/apply, workspace isolation for team collaboration | [well-architected-assessment.md](references/well-architected-assessment.md#efficiency) |
| **Performance** | Backend GCS + DynamoDB lock; large state file handling; module caching | [well-architected-assessment.md](references/well-architected-assessment.md#performance) |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions `terraform`, `.tf` file, HCL, infrastructure as code, IaC, or Terraform lifecycle.
- User asks to `terraform init`, `terraform validate`, `terraform plan`, `terraform apply`, or `terraform destroy` in an environment directory.
- User asks to manage Terraform state — `terraform state list`, `terraform state mv`, `terraform state rm`, `terraform state pull`.
- User asks to manage Terraform workspaces — `terraform workspace list/select/new/delete`.
- User asks to import existing GCP resources into Terraform state — `terraform import`.
- User asks to read infrastructure output values — `terraform output`, `terraform show`.
- User asks to configure or verify Terraform backend (GCS + DynamoDB lock).
- User asks to check Terraform or provider version compatibility.
- User mentions `environments/dev`, `environments/staging`, `environments/prod` in context of infrastructure management.

### SHOULD NOT Use This Skill When

- User requests direct `gcloud` commands to manage GCP resources → delegate to the appropriate GCP skill (gcp-gce-ops, gcp-gke-ops, gcp-cloudsql-ops, etc.).
- User asks to author or modify HCL configuration files (`.tf` files, `.tfvars` files) → the user manages configuration; this skill manages plan/apply/validate/state lifecycle.
- User asks about Terraform Cloud / Terraform Enterprise SaaS features → this skill covers local Terraform CLI only.
- User asks about Pulumi, Ansible, or other IaC tools → these are outside scope.
- User requests console-only instructions with no Terraform CLI → state limitation; do not invent undocumented terraform commands.

### Delegation Rules

- Terraform configuration files (`.tf`, `.tfvars`) are authored by the user. Do not modify them.
- When Terraform configuration references a GCP resource that has its own skill (IAM, VPC, Cloud SQL, GKE), the user manages the module definition; this skill manages the `terraform plan/apply/destroy` execution.
- Terraform state is the source of truth. If a resource was created by Terraform but the state is lost, use `terraform import` to restore — do not recreate via gcloud.

## Quality Gate (GCL)

> [总是加载 — apply/destroy 操作前必须加载 rubric 和 prompt templates]

Terraform is **GCL `required`** with **`max_iter: 2`** because `terraform apply` and `terraform destroy` are the most dangerous operations in cloud infrastructure management — they can create or permanently destroy production resources. Use [references/rubric.md](references/rubric.md) and [references/prompt-templates.md](references/prompt-templates.md) before executing `apply` and `destroy`. Persist every GCL trace under `./audit-results/gcl-trace-*.json`.

| Operation | GCL Level | Rationale |
|-----------|:---------:|-----------|
| `terraform apply` | **required** (max_iter=2) | Creates or modifies real GCP resources; plan preview is mandatory |
| `terraform destroy` | **required** (max_iter=2) | Permanently destroys GCP resources; exact resource confirmation + state backup mandatory |
| `terraform import` | **required** (max_iter=2) | Modifies Terraform state; incorrect import can corrupt state |
| `terraform init` | recommended | Downloads providers/modules; can trigger provider version conflicts |
| `terraform validate` | recommended | Syntax and reference check; non-destructive |
| `terraform plan` | optional | Read-only preview; always safe to run |
| `terraform state mv/rm` | required | Directly modifies state; wrong target can corrupt state |
| `terraform workspace select/new/delete` | recommended | Affects which state file is used; wrong workspace can apply to wrong env |
| `terraform output` / `terraform show` | optional | Read-only |

## Variable Convention and API Conventions

> [总是加载 — 变量约定和环境路径]

Full variable table and environment path conventions at [variables-and-conventions.md](references/variables-and-conventions.md). Key conventions:

- `{{env.*}}` — NEVER ask user; HALT if unset. Includes `GOOGLE_APPLICATION_CREDENTIALS`, `CLOUDSDK_CORE_PROJECT`, `TF_LOG`, `TF_IN_AUTOMATION`.
- `{{user.environment}}` — Ask once; one of `dev`, `staging`, `prod`.
- `{{user.target_dir}}` — Ask once; defaults to `environments/{{user.environment}}/`.
- `{{user.plan_out_file}}` — Ask once for apply; defaults to `{{user.target_dir}}/.tfplan`.
- `{{user.confirm_apply}}` — Required before `terraform apply`; must show plan summary.
- `{{user.confirm_destroy}}` — Required before `terraform destroy`; must show exact resource list and state backup confirmation.
- `{{output.plan_summary}}` — Parse from `terraform plan` output; resource create/destroy counts.
- `{{output.state_lock_id}}` — Parse from `terraform plan` output; lock ID for unlock on failure.
- `{{output.destroy_resources}}` — Parse from `terraform plan -destroy` output; list of resources to be destroyed.

## Quick Start

### Prerequisites

- [ ] Terraform CLI installed (`terraform version`, minimum 1.6.0).
- [ ] Google Cloud credentials via `gcloud auth application-default login` or `GOOGLE_APPLICATION_CREDENTIALS`.
- [ ] GCS buckets created for each environment's backend (dev, staging, prod must use **different buckets**).
- [ ] DynamoDB table for state locking (`terraform-state-lock-{env}`) in each environment.
- [ ] Terraform service account has roles for target resources (typically `roles/owner` for development, least-privilege for production).
- [ ] `environments/{dev,staging,prod}/` directories exist with `backend.tf` and `versions.tf`.

### Verify Setup (no mutation)

```bash
terraform version
terraform init -backend=false  # dry-run init without backend
terraform validate environments/dev/
terraform plan -out=/tmp/dev-plan.tfplan  # preview, no apply
```

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| Init | Initialize working directory (download providers/modules) | Low | Low — download only |
| Validate | Syntax and reference validation | Low | Read-only |
| Plan | Preview infrastructure changes | Low | Read-only — always safe |
| Apply | Execute planned changes to GCP | High | **High — creates/modifies resources** |
| Destroy | Tear down all managed resources | Very High | **Critical — destroys resources** |
| Import | Bring existing GCP resources into Terraform state | Medium | **High — corrupts state if wrong** |
| State List/MV/RM | Manage Terraform state | Medium | **High — state corruption risk** |
| Workspace | Switch/create/delete workspaces | Medium | Medium — affects state file selection |
| Output | Read infrastructure output values | Low | Read-only |
| Show | Display current state snapshot | Low | Read-only |

## Execution Flows

> [总是加载 — 所有操作的核心执行流程]

Every operation follows **Pre-flight → Execute → Validate → Recover**. Full pre-flight tables, execution steps, validation checks, and failure recovery for each operation are at [execution-flows.md](references/execution-flows.md). Key pointers:

| Operation | Execution Reference | Command Reference |
|-----------|-------------------|-------------------|
| Init | [execution-flows.md#init](references/execution-flows.md#operation-terraform-init) | [core-concepts.md#terraform-init](references/core-concepts.md#terraform-init) |
| Validate | [execution-flows.md#validate](references/execution-flows.md#operation-terraform-validate) | [core-concepts.md#terraform-validate](references/core-concepts.md#terraform-validate) |
| Plan | [execution-flows.md#plan](references/execution-flows.md#operation-terraform-plan) | [core-concepts.md#terraform-plan](references/core-concepts.md#terraform-plan) |
| Apply | [execution-flows.md#apply](references/execution-flows.md#operation-terraform-apply) | [core-concepts.md#terraform-apply](references/core-concepts.md#terraform-apply) |
| Destroy | [execution-flows.md#destroy](references/execution-flows.md#operation-terraform-destroy) | [core-concepts.md#terraform-destroy](references/core-concepts.md#terraform-destroy) |
| Import | [execution-flows.md#import](references/execution-flows.md#operation-terraform-import) | [core-concepts.md#terraform-import](references/core-concepts.md#terraform-import) |
| State Management | [execution-flows.md#state](references/execution-flows.md#operation-terraform-state) | [core-concepts.md#terraform-state](references/core-concepts.md#terraform-state) |
| Workspace | [execution-flows.md#workspace](references/execution-flows.md#operation-terraform-workspace) | [core-concepts.md#terraform-workspace](references/core-concepts.md#terraform-workspace) |
| Output/Show | [execution-flows.md#output-show](references/execution-flows.md#operation-terraform-output-and-show) | [core-concepts.md#terraform-output](references/core-concepts.md#terraform-output) |

## Security and Safety Requirements

- **Never print credential files, access tokens, or service account key content.**
- **Never place secrets in `.tfvars` files** — use GCP Secret Manager references or environment variables instead. Check tfvars with the pattern `password = "..."` before running.
- **All `terraform apply` and `terraform destroy` require a preceding `terraform plan`** — never apply without a plan preview.
- **For `terraform destroy`**: always run `terraform state pull > backup-{env}-{timestamp}.json` before destruction.
- **For `terraform apply` in prod**: show the plan summary (create/destroy counts) and require explicit acknowledgement.
- **State lock**: if `terraform plan` fails with "state lock" error, do not force-unlock unless the lock is known stale.
- **Backend isolation**: verify the target environment's `backend.tf` points to a different GCS bucket before any mutation.
- Record command, sanitized parameters, plan summary, and validation result for traceability.

## Reference Index

> [按需加载 — 根据操作类型选择对应 reference 文件]

| Topic | File | Load Condition |
|-------|------|----------------|
| Architecture, state model, backend | [core-concepts.md](references/core-concepts.md) | 总是加载 |
| Variables and environment paths | [variables-and-conventions.md](references/variables-and-conventions.md) | 总是加载 |
| Execution flows (Pre-flight/Validate/Recover) | [execution-flows.md](references/execution-flows.md) | 总是加载 |
| Error diagnosis and recovery | [troubleshooting.md](references/troubleshooting.md) | 失败或报错时加载 |
| Monitoring and cost tracking | [monitoring.md](references/monitoring.md) | 用户询问监控/成本时加载 |
| Integration/bootstrap | [integration.md](references/integration.md) | 首次使用或环境配置时加载 |
| Idempotency | [idempotency-checklist.md](references/idempotency-checklist.md) | 执行重试/幂等操作时加载 |
| Well-Architected | [well-architected-assessment.md](references/well-architected-assessment.md) | 架构评审时加载 |
| GCL rubric | [rubric.md](references/rubric.md) | apply/destroy/import/state 操作前加载 |
| GCL prompt templates | [prompt-templates.md](references/prompt-templates.md) | apply/destroy/import/state 操作前加载 |

## Token Efficiency Guidelines (P0 — 强制)

Every `gcp-*-ops` SKILL.md MUST include this section. Rules TE-1 to TE-7 sourced from `gcp-skill-generator/references/gcp-skill-template.md` §Token Efficiency Guidelines; full definitions at `gcp-skill-generator/SKILL.md` §Token Efficiency Requirements.

| Rule | Key Point | Application |
|------|-----------|-------------|
| **TE-1** API query > static table | Use `gcloud` to fetch versions/quotas, no hardcoding | Replace hardcoded machine-type/version tables with live queries |
| **TE-2** Omit unnecessary docstrings | Inline comments only, no function-level docstring | Python/Go SDK snippets use `#`/`//` inline comments |
| **TE-3** Compact error tables | 1 error code per row, ≤3 columns | Error taxonomy tables in `references/troubleshooting.md` stay compact |
| **TE-4** Centralized JSON paths | Declare at file top, don't repeat | Resource JSON paths declared once in `variables-and-conventions.md` |
| **TE-5** YAML anchors | `example-config.yaml` use `&anchor` | Reusable config blocks use anchors to eliminate duplication |
| **TE-6** Eliminate cross-file duplication | SKILL.md has full flow, references/ don't repeat | Execution flows live in SKILL.md; references/ link, don't re-narrate |
| **TE-7** Layer professional content | AIOps/FinOps in `references/advanced/`; destructive ops marked Security-Sensitive | Advanced content split out; confirmations gated explicitly |
| **TE-8** Reference depth ≤ 2 layers | `references/` nested max 2 levels; no `references/advanced/deep/` chains | ~100-500/file |

**Non-compressible**: Agent-executable commands (params, JSON paths), error recovery logic, safety gates, credential rules, cross-skill orchestration chains.

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-09 | Initial Terraform operations skill: directory isolation, full lifecycle (init/validate/plan/apply/destroy/import/state/workspace/output), GCL required for apply/destroy/import/state, environment examples (dev/staging/prod), test suite |