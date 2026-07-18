---
name: gcp-billing-ops
description: >-
  Use when the user needs to manage, query, configure, or troubleshoot Google
  Cloud Billing — billing accounts, budgets, budget alerts, cost exports
  (BigQuery), billing project links, and pricing catalog queries. User mentions
  Cloud Billing, billing account, budget, cost management, billing export,
  cost breakdown, or describes billing scenarios (e.g., "set up budget alert",
  "check spending", "export billing data", "link project to billing account",
  "why am I being charged") even without naming the product directly. Not for
  IAM policy management, resource-level cost optimization (FinOps), or BigQuery
  dataset/table administration that have their own ops skills.
license: MIT
compatibility: >-
  Official Google Cloud CLI (`gcloud`, Python-based SDK), Go 1.21+ runtime
  (for JIT SDK fallback), valid service account credentials with Billing Account
  Administrator or Billing Account Viewer roles, network access to Google Cloud
  endpoints (`billingbudgets.googleapis.com`, `billing.googleapis.com`,
  `cloudbilling.googleapis.com`).
metadata:
  author: gcp-skills
  version: "1.0.0"
  last_updated: "2026-06-09"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  go_version_minimum: "1.21"
  go_version_jit: "1.24+"
  gcl_classification: "recommended"
  gcl_max_iter: 3
  api_profile: "https://cloudbilling.googleapis.com/$discovery/rest?version=v1"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    gcloud billing --help confirms subcommands: accounts, budgets, projects.
    gcloud alpha billing budgets exposes budget CRUD. See
    https://cloud.google.com/sdk/gcloud/reference/billing and
    https://cloud.google.com/sdk/gcloud/reference/alpha/billing.
  environment:
    - GOOGLE_APPLICATION_CREDENTIALS
    - CLOUDSDK_CORE_PROJECT
    - CLOUDSDK_AUTH_ACCESS_TOKEN
---

> This skill follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Google Cloud Billing Operations Skill

## Overview

Cloud Billing manages Google Cloud costs — billing accounts, budgets with threshold alerts, cost data exports to BigQuery, and project-to-billing-account linking. This skill is an operational runbook for agents to perform billing actions with explicit scope, credential safety, pre-flight checks, dual-path `gcloud`/SDK guidance, validation, recovery, and GCL review for budget and export mutations.

> **UX Compliance:** Follow the [User Experience Specification](../gcp-skill-generator/references/user-experience-spec.md): ask only for missing `{{user.*}}` values, show safe previews before mutations, mask credentials, and report actionable next steps.
> **Portability note:** This link requires `gcp-skill-generator` as a sibling directory. If this skill is copied standalone, the UX rules are: ask minimal questions, preview mutations, mask credentials, report next steps.

### CLI applicability

- **`cli_applicability: dual-path`:** Cloud Billing has broad CLI coverage via `gcloud billing` and `gcloud alpha billing`. Use `gcloud` as the primary path and the Billing Budgets API/Python SDK as fallback for complex budget rules or automation.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT triggers distinguish billing from IAM, BigQuery admin, and FinOps optimization |
| 2 | **Structured I/O** | Variables use `{{env.*}}`, `{{user.*}}`, `{{output.*}}`; JSON paths centralized at [api-sdk-usage.md](references/api-sdk-usage.md) |
| 3 | **Explicit Actionable Steps** | Operations include Pre-flight → Execute → Validate → Recover flows; full details at [gcloud-usage.md](references/gcloud-usage.md) |
| 4 | **Complete Failure Strategies** | [troubleshooting.md](references/troubleshooting.md) has ≥15 billing-specific error rows with HALT/retry guidance |
| 5 | **Absolute Single Responsibility** | One product: Cloud Billing accounts, budgets, exports, project links; adjacent services delegated |

### Google Cloud Architecture Framework / Well-Architected Framework Integration

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **Security** | Billing IAM roles, credential masking, export data access control, budget alert sensitivity | [well-architected-assessment.md](references/well-architected-assessment.md#1-security) |
| **Stability** | Budget alert reliability, export pipeline resilience, multi-channel notification redundancy | [well-architected-assessment.md](references/well-architected-assessment.md#2-stability) |
| **Cost** | Budget thresholds, actual vs forecast tracking, export-driven cost analysis, pricing queries | [well-architected-assessment.md](references/well-architected-assessment.md#3-cost) |
| **Efficiency** | Idempotent budget/export management, bulk project linking, automated alert rules | [well-architected-assessment.md](references/well-architected-assessment.md#4-efficiency) |
| **Performance** | Budget evaluation latency, export freshness, alert notification delivery | [well-architected-assessment.md](references/well-architected-assessment.md#5-performance) |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions Cloud Billing, billing account, budget, cost management, billing export, or pricing.
- User asks to list/describe billing accounts or check which billing account a project uses.
- User asks to create/list/describe/update/delete a budget with spending thresholds and alert rules.
- User asks to link/unlink a project to/from a billing account.
- User asks to create/list/describe/update/delete a BigQuery billing export (standard/detailed).
- User asks to query GCP pricing or SKU information for cost estimation.
- User asks to check current spend, forecast, or budget status.
- User asks to troubleshoot billing access, budget alert delivery, or export pipeline issues.

### SHOULD NOT Use This Skill When

- Task is purely IAM policy management for billing roles → delegate to `gcp-iam-ops`.
- Task is BigQuery dataset/table administration for the export destination → delegate to `gcp-bigquery-ops`.
- Task is FinOps deep-dive cost optimization or resource right-sizing → delegate to `gcp-billing-ops/references/advanced/finops-cost-analysis.md` when available (planned).
- Task is managing Cloud Monitoring alert policies for billing metrics → delegate to `gcp-monitoring-ops`.
- User requests console-only instructions with no API/CLI execution → provide high-level limitation; do not invent unverified console paths.

### Delegation Rules

- Use this skill for billing-specific IAM diagnosis (e.g., missing `billing.accounts.get`); delegate broad IAM policy design to `gcp-iam-ops`.
- Use this skill to configure billing export destination; delegate BigQuery dataset/table lifecycle to `gcp-bigquery-ops`.
- Use this skill to create budget threshold rules; delegate notification channel management to `gcp-monitoring-ops`.
- Apply GCL using [references/rubric.md](references/rubric.md) and [references/prompt-templates.md](references/prompt-templates.md) for budget and export mutations.

## Quality Gate (GCL)

> [总是加载 — budget/export 变更前必须加载 rubric 和 prompt templates]

Cloud Billing is classified as **GCL `recommended`** with **`max_iter: 3`** because this skill includes destructive operations: **Delete Budget** and **Delete Billing Export**. Use [references/rubric.md](references/rubric.md) and [references/prompt-templates.md](references/prompt-templates.md) before executing budget/export deletes and budget threshold mutations that affect alert delivery. Persist every GCL trace under `./audit-results/gcl-trace-*.json` with commands, sanitized parameters, responses, validation evidence, and reviewer decision. Delete operations must satisfy the per-operation safety sub-rules in the rubric.

## Variable Convention

> [总是加载 — 变量约定]

Full variable table and JSON paths at [references/api-sdk-usage.md](references/api-sdk-usage.md). Key conventions:

- `{{env.*}}` — NEVER ask user; HALT if unset. Includes `GOOGLE_APPLICATION_CREDENTIALS`, `CLOUDSDK_CORE_PROJECT`, `CLOUDSDK_AUTH_ACCESS_TOKEN`.
- `{{user.*}}` — Ask once, reuse. Covers `billing_account_id`, `budget_id`, `budget_display_name`, `budget_amount`, `threshold_rules`, `export_dataset`, `export_prefix`, `confirm_delete`.
- `{{output.*}}` — Parse from API responses. Key paths: `$.name`, `$.displayName`, `$.amount.specifiedAmount.units`, `$.thresholdRules`, `$.datasetSpec.datasetId`.
- Never print access tokens, service account key content, or billing account sensitive metadata.

## Quick Start

### Prerequisites

- [ ] `gcloud` CLI installed.
- [ ] Billing Budgets API enabled for `{{env.CLOUDSDK_CORE_PROJECT}}`.
- [ ] Credentials available via `gcloud auth` or ADC; do not print credential files.
- [ ] IAM roles: `roles/billing.viewer` (read), `roles/billing.accountAdmin` (link/unlink), `roles/billing.budgetAdmin` (budget CRUD), `roles/billing.costsManager` (export CRUD).

### Verify Setup (no mutation)

```bash
gcloud version
gcloud config get-value project
gcloud services list --enabled --filter='config.name=billingbudgets.googleapis.com' --format='value(config.name)'
gcloud billing accounts list --format=json
```

### Common Command Preview

List billing accounts. Full command syntax at [gcloud-usage.md](references/gcloud-usage.md#operation-list-billing-accounts). For SDK fallback, see [api-sdk-usage.md](references/api-sdk-usage.md).

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| List/Describe Billing Accounts | View accessible billing accounts and metadata | Low | Read-only |
| List/Describe Project Billing Info | Check which billing account a project uses | Low | Read-only |
| Link/Unlink Project | Associate or disassociate project with billing account | Medium | High — unlink stops billable services |
| Create Budget | Set spending limit with threshold alert rules | Medium | Medium — alert delivery impact |
| List/Describe Budgets | View existing budgets and current spend status | Low | Read-only |
| Update Budget | Modify budget amount, thresholds, or notifications | Medium | Medium — alert delivery impact |
| Delete Budget | Remove budget and its alert rules | Low | Medium — requires confirmation |
| Create Billing Export | Set up BigQuery export for cost data | Medium | Medium — data pipeline creation |
| List/Describe/Update/Delete Export | Manage existing billing exports | Low-Medium | Medium — delete removes cost data pipeline |
| Query Pricing/SKUs | Look up service pricing and SKU details | Low | Read-only |

## Execution Flows

> [总是加载 — 所有操作的核心执行流程]

Every operation follows **Pre-flight → Execute → Validate → Recover**. Full pre-flight tables, execution steps, validation checks, and failure recovery for each operation are at [references/gcloud-usage.md](references/gcloud-usage.md). Key pointers:

| Operation | Execution Reference | Command Reference |
|-----------|-------------------|-------------------|
| List/Describe Billing Accounts | [gcloud-usage.md](references/gcloud-usage.md#operation-list-billing-accounts) | [gcloud-usage.md](references/gcloud-usage.md#operation-list-billing-accounts) |
| List/Describe Project Billing | [gcloud-usage.md](references/gcloud-usage.md#operation-listdescribe-project-billing-info) | [gcloud-usage.md](references/gcloud-usage.md#operation-listdescribe-project-billing-info) |
| Link/Unlink Project | [gcloud-usage.md](references/gcloud-usage.md#operation-link-project-to-billing-account) | [gcloud-usage.md](references/gcloud-usage.md#operation-link-project-to-billing-account) |
| Budget CRUD | [gcloud-usage.md](references/gcloud-usage.md#operation-create-budget) | [gcloud-usage.md](references/gcloud-usage.md#operation-create-budget) |
| Billing Export CRUD | [gcloud-usage.md](references/gcloud-usage.md#operation-create-billing-export) | [gcloud-usage.md](references/gcloud-usage.md#operation-create-billing-export) |
| Query Pricing/SKUs | [gcloud-usage.md](references/gcloud-usage.md#operation-query-pricing-and-skus) | [gcloud-usage.md](references/gcloud-usage.md#operation-query-pricing-and-skus) |

## Security and Safety Requirements

- Never print credential file contents, access tokens, or billing account sensitive metadata.
- Unlink project from billing account is destructive — requires explicit confirmation with project ID and billing account ID.
- Delete budget removes alert rules — require exact budget ID confirmation.
- Delete billing export stops cost data pipeline — require exact export ID confirmation.
- Budget threshold rules may trigger email/pubsub notifications — preview recipients before create/update.
- Record command, sanitized parameters, response IDs, and validation result for traceability.

## Reference Index

> [按需加载 — 根据操作类型选择对应 reference 文件]

| Reference | Load Condition | Description |
|-----------|---------------|-------------|
| [core-concepts.md](references/core-concepts.md) | 总是加载 | Architecture, resource model, IAM, quotas, safety constraints |
| [api-sdk-usage.md](references/api-sdk-usage.md) | SDK 操作时加载 | REST API map, Python/Go SDK, JSON paths |
| [gcloud-usage.md](references/gcloud-usage.md) | CLI 操作时加载 | Full gcloud command map, execution flows, validation |
| [troubleshooting.md](references/troubleshooting.md) | 报错或诊断时加载 | Error taxonomy (≥15), diagnostics, recovery |
| [monitoring.md](references/monitoring.md) | 监控/告警操作时加载 | Billing metrics, budget alerts, export monitoring |
| [integration.md](references/integration.md) | 集成/环境设置时加载 | Go bootstrap, env vars, cross-skill delegation |
| [well-architected-assessment.md](references/well-architected-assessment.md) | 架构评估时加载 | Five-pillar assessment |
| [idempotency-checklist.md](references/idempotency-checklist.md) | 自动化/重试时加载 | Idempotent patterns for budget/export operations |
| [rubric.md](references/rubric.md) | GCL 变更前加载 | GCL scoring rubric for billing mutations |
| [prompt-templates.md](references/prompt-templates.md) | GCL 变更前加载 | Generator + Critic prompt templates |

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

**Non-compressible**: Agent-executable commands (params, JSON paths), error recovery logic, safety gates, credential rules, cross-skill orchestration chains.

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-09 | Initial release: billing accounts, budgets, exports, project links, pricing queries |
