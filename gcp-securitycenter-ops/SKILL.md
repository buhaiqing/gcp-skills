---
name: gcp-securitycenter-ops
description: >-
  Use when the user needs to manage Google Security Command Center (SCC) —
  enable SCC at organization or project, manage sources, list/describe/update
  findings, create/list/delete mute configs, configure Pub/Sub notification
  configs, set up BigQuery continuous exports, manage Security Health
  Analytics custom modules, configure resource value configs, export findings
  to CSV, or triage security posture. Triggers on Security Command Center,
  SCC, securitycenter.googleapis.com, gcloud scc, finding, vulnerability,
  threat, security posture, Mute Config, Notification Config, BigQuery Export,
  Security Health Analytics, Container Threat Detection, Event Threat
  Detection, SCC Premium, SCC Standard, SCC Enterprise. Not for IAM policy
  administration, Cloud Logging sinks, Cloud Monitoring alert policies, or
  general security incident response that does not involve SCC resources.
license: MIT
compatibility: >-
  Official Google Cloud CLI (`gcloud scc`, Python-based SDK), optional
  Python 3.10+ with google-cloud-securitycenter for SDK fallback, valid
  Google Cloud credentials with Security Center Admin / Editor / Viewer
  / Finding Editor roles, and network access to securitycenter.googleapis.com.
metadata:
  author: gcp-skills
  version: "1.0.0"
  last_updated: "2026-06-09"
  runtime: Harness AI Agent, Claude Code, or compatible Agent runtimes
  go_version_minimum: "1.21"
  gcl_classification: "required"
  gcl_max_iter: 2
  api_profile: "https://securitycenter.googleapis.com/$discovery/rest?version=v1"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    gcloud scc --help exposes settings, sources, findings, mute-configs,
    notifications, and operations modules. Custom modules, effective modules,
    and resource value configs require the SDK or REST API. See
    https://cloud.google.com/sdk/gcloud/reference/scc.
  environment:
    - GOOGLE_APPLICATION_CREDENTIALS
    - CLOUDSDK_CORE_PROJECT
    - CLOUDSDK_AUTH_ACCESS_TOKEN
---

> This skill follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Google Security Command Center Operations Skill

## Overview

Security Command Center (SCC) is Google's centralized vulnerability and threat management platform. It collects security findings from built-in detectors (Security Health Analytics, Event Threat Detection, Container Threat Detection, etc.) and custom sources; lets operators triage, mute, and resolve findings; and exports finding data to Pub/Sub and BigQuery for downstream automation. This skill is an operational runbook for agents to manage SCC resources with explicit scope, credential safety, pre-flight checks, dual-path `gcloud`/SDK guidance, validation, recovery, monitoring, and GCL review for the destructive and posture-impacting operations.

> **UX Compliance:** Follow the [User Experience Specification](../gcp-skill-generator/references/user-experience-spec.md): ask only for missing `{{user.*}}` values, show safe previews before mutations, mask credentials, and report actionable next steps.

### CLI applicability

- **`cli_applicability: dual-path`:** SCC has broad official CLI coverage via `gcloud scc` (settings, sources, findings, mute-configs, notifications, operations). Custom modules, effective modules, and resource value configs are exposed only via the SDK / REST API. Use `gcloud` as the primary path; fall back to the Security Center API or Python SDK for the SDK-only operations.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT triggers distinguish SCC from IAM, Logging, Monitoring, and Security posture response |
| 2 | **Structured I/O** | Variables use `{{env.*}}`, `{{user.*}}`, `{{output.*}}`; JSON paths centralized at [variables-and-conventions.md](references/variables-and-conventions.md) |
| 3 | **Explicit Actionable Steps** | Operations include Pre-flight → Execute → Validate → Recover flows; full details at [execution-flows.md](references/execution-flows.md) |
| 4 | **Complete Failure Strategies** | [troubleshooting.md](references/troubleshooting.md) has ≥15 SCC-specific error rows with HALT/retry guidance |
| 5 | **Absolute Single Responsibility** | One product: SCC findings, sources, mute/notification configs, exports, modules; adjacent services delegated |

### Google Cloud Architecture Framework / Well-Architected Framework Integration

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **Security** | Least-privilege SCC roles, org/folder hierarchy scoping, VPC-SC integration, audit log review, finding state transitions | [well-architected-assessment.md](references/well-architected-assessment.md#security) |
| **Stability** | Notification configs as DR (Pub/Sub to multiple regions), BigQuery export as cold backup, idempotent mute configs | [well-architected-assessment.md](references/well-architected-assessment.md#stability) |
| **Cost** | Tier-aware pricing, finding cardinality, BigQuery export storage cost, container/anomaly detector selection | [well-architected-assessment.md](references/well-architected-assessment.md#cost) |
| **Efficiency** | Filtered list with `--filter`, pagination, batch finding updates, project/folder scoping | [well-architected-assessment.md](references/well-architected-assessment.md#efficiency) |
| **Performance** | Indexing by `event_time`, state=ACTIVE prefilter, parent resource scoping, dataset partition pruning for exports | [well-architected-assessment.md](references/well-architected-assessment.md#performance) |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions Security Command Center, `securitycenter.googleapis.com`, `gcloud scc`, finding, vulnerability, threat, security posture, mute config, notification config, or BigQuery export.
- User asks to enable SCC at organization or project, list/describe findings, mark a finding as ACTIVE/INACTIVE/MUTED/UNMUTED, or triage findings.
- User asks to create/list/describe/delete mute configs.
- User asks to create/list/describe/update/delete notification configs (Pub/Sub).
- User asks to create/list/describe/update/delete BigQuery exports (continuous export of findings to BigQuery).
- User asks to list/describe/enable/disable Security Health Analytics custom or effective modules.
- User asks to create/list/describe/update/delete resource value configs.
- User asks to export findings to CSV.
- User asks to get or update organization settings (enable/disable SCC).

### SHOULD NOT Use This Skill When

- Task is generic IAM policy design or service account administration → delegate to `gcp-iam-ops`.
- Task is Cloud Logging sinks/exclusions/metrics unrelated to SCC audit logs → delegate to `gcp-logging-ops`.
- Task is Cloud Monitoring alert policies unrelated to SCC metrics → delegate to `gcp-monitoring-ops`.
- Task is general incident response / SOAR playbooks that do not touch SCC resources → keep at the agent's general-purpose tool layer.
- Task is creating Pub/Sub topics or BigQuery datasets required for SCC exports → delegate topic/dataset lifecycle, then return.
- User requests console-only instructions with no API/CLI execution → provide high-level limitation; do not invent unverified console paths.

### Delegation Rules

- Use this skill to read SCC findings, mute configs, notification configs, and exports; delegate the underlying Pub/Sub topic, BigQuery dataset, and IAM policy management to `gcp-pubsub-ops`, `gcp-bigquery-ops`, and `gcp-iam-ops` respectively.
- Use this skill to manage SCC custom modules; delegate module-template definitions and module editor IAM to `gcp-iam-ops`.
- Apply GCL using [references/rubric.md](references/rubric.md) and [references/prompt-templates.md](references/prompt-templates.md) before destructive or posture-impacting operations (delete mute config, delete notification config, delete BigQuery export, update finding state, enable SCC at org level).

## Quality Gate (GCL)

> [总是加载 — 破坏性或姿态影响操作前必须加载 rubric 和 prompt templates]

SCC is classified as **GCL `required`** with **`max_iter: 2`** because this skill includes destructive and posture-impacting operations: **Delete Mute Config**, **Delete Notification Config**, **Delete BigQuery Export**, **Update Finding State** (silent mute/resolve), and **Enable SCC at organization level**. Use [references/rubric.md](references/rubric.md) and [references/prompt-templates.md](references/prompt-templates.md) before executing destructive operations. Persist every GCL trace under `./audit-results/gcl-trace-*.json` with commands, sanitized parameters, responses, validation evidence, and reviewer decision. State-changing operations (mute, resolve, set state to MUTED/INACTIVE) are GCL `required`; read-only operations (list, describe, get) are GCL `optional`.

## Variable Convention and API Conventions

> [总是加载 — 变量约定和 JSON paths]

Full variable table and centralized JSON paths at [references/variables-and-conventions.md](references/variables-and-conventions.md). Key conventions:

- `{{env.*}}` — NEVER ask user; HALT if unset. Includes `GOOGLE_APPLICATION_CREDENTIALS`, `CLOUDSDK_CORE_PROJECT`, `CLOUDSDK_AUTH_ACCESS_TOKEN`.
- `{{user.*}}` — Ask once, reuse. Covers parent (org/folder/project), source ID, finding ID, mute/notification/BQ-export ID, filter, severity, state, and `confirm_delete`.
- `{{output.*}}` — Parse from API responses. Key paths: `$.name`, `$.parent`, `$.state`, `$.severity`, `$.category`, `$.resourceName`, `$.eventTime`, `$.muteConfig`, `$.notificationConfigName`.
- Never print access tokens, service account key content, or credential material in findings.

## Quick Start

### Prerequisites

- [ ] `gcloud` CLI installed.
- [ ] SCC API enabled for `{{env.CLOUDSDK_CORE_PROJECT}}` (`securitycenter.googleapis.com`).
- [ ] Credentials available via `gcloud auth` or ADC; do not print credential files.
- [ ] IAM roles appropriate to the operation: `roles/securitycenter.admin`, `roles/securitycenter.adminViewer`, `roles/securitycenter.findingsEditor`, `roles/securitycenter.findingsViewer`, `roles/securitycenter.muteConfigsEditor`, `roles/securitycenter.notificationConfigsEditor`, `roles/securitycenter.bigQueryExportsEditor`, `roles/securitycenter.customModulesEditor`, `roles/securitycenter.resourceValueConfigsEditor`.
- [ ] For organization-level operations, the agent identity must be at the org level (or be impersonated via a Security Center Admin on the org node).

### Verify Setup (no mutation)

```bash
gcloud version
gcloud config get-value project
gcloud services list --enabled --filter='config.name=securitycenter.googleapis.com' --format='value(config.name)'
gcloud scc settings get --organization="{{user.org_id}}" --format=json
gcloud scc findings list --organization="{{user.org_id}}" --limit=1 --format=json
```

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| Enable SCC at Org/Project | Turn on SCC at the given parent resource | Low | High — billing impact, broad posture scope |
| List/Describe Sources | Discover built-in or custom security sources | Low | Read-only |
| List/Describe Findings | Inspect active and historical findings | Low | Read-only |
| Update Finding State | Mark finding as ACTIVE/INACTIVE/MUTED/UNMUTED | Low | High — affects alerting and posture dashboards |
| Mute Configs | Create/list/describe/delete mute rules | Medium | High — can silently suppress findings |
| Notification Configs | Create/list/describe/update/delete Pub/Sub notification rules | Medium | High — can break alerting if deleted |
| BigQuery Exports | Create/list/describe/update/delete continuous exports | Medium | High — cost and data loss on delete |
| Custom Modules | List/describe/enable/disable Security Health Analytics custom detectors | Medium | Medium — affects detection coverage |
| Effective Modules | List/describe/enable/disable per-folder/project module enablement | Medium | Medium |
| Resource Value Configs | Create/list/describe/update/delete per-resource severity overrides | Medium | High — can downplay or amplify risk scores |
| Organization Settings | Get/update SCC enablement and asset discovery | Low | High — org-wide impact |
| Export Findings to CSV | One-shot CSV export of findings | Low | Low — read-only |

## Execution Flows

> [总是加载 — 所有操作的核心执行流程]

Every operation follows **Pre-flight → Execute → Validate → Recover**. Full pre-flight tables, execution steps, validation checks, and failure recovery for each operation are at [references/execution-flows.md](references/execution-flows.md). Key pointers:

| Operation | Execution Reference | Command Reference |
|-----------|-------------------|-------------------|
| Enable SCC | [execution-flows.md#enable-scc](references/execution-flows.md#operation-enable-scc) | [gcloud-usage.md#settings](references/gcloud-usage.md#settings) |
| List/Describe Sources | [execution-flows.md#sources](references/execution-flows.md#operation-list-describe-or-update-sources) | [gcloud-usage.md#sources](references/gcloud-usage.md#sources) |
| List/Describe Findings | [execution-flows.md#findings](references/execution-flows.md#operation-list-describe-findings) | [gcloud-usage.md#findings](references/gcloud-usage.md#findings) |
| Update Finding State | [execution-flows.md#update-finding](references/execution-flows.md#operation-update-finding-state) | [gcloud-usage.md#findings](references/gcloud-usage.md#findings) |
| Mute Configs | [execution-flows.md#mute-configs](references/execution-flows.md#operation-manage-mute-configs) | [gcloud-usage.md#mute-configs](references/gcloud-usage.md#mute-configs) |
| Notification Configs | [execution-flows.md#notifications](references/execution-flows.md#operation-manage-notification-configs) | [gcloud-usage.md#notifications](references/gcloud-usage.md#notifications) |
| BigQuery Exports | [execution-flows.md#bigquery-exports](references/execution-flows.md#operation-manage-bigquery-exports) | [gcloud-usage.md#bigquery-exports](references/gcloud-usage.md#bigquery-exports) |
| Custom Modules | [execution-flows.md#custom-modules](references/execution-flows.md#operation-manage-custom-modules) | [api-sdk-usage.md#custom-modules](references/api-sdk-usage.md#custom-modules) |
| Effective Modules | [execution-flows.md#effective-modules](references/execution-flows.md#operation-manage-effective-modules) | [api-sdk-usage.md#effective-modules](references/api-sdk-usage.md#effective-modules) |
| Resource Value Configs | [execution-flows.md#resource-value-configs](references/execution-flows.md#operation-manage-resource-value-configs) | [api-sdk-usage.md#resource-value-configs](references/api-sdk-usage.md#resource-value-configs) |
| Org Settings | [execution-flows.md#org-settings](references/execution-flows.md#operation-organization-settings) | [gcloud-usage.md#settings](references/gcloud-usage.md#settings) |
| Export Findings (CSV) | [execution-flows.md#export-csv](references/execution-flows.md#operation-export-findings-csv) | [gcloud-usage.md#findings](references/gcloud-usage.md#findings) |

## Security and Safety Requirements

- Never print credential file contents, access tokens, or service account key material. Redact `Authorization` headers, `access_token`, and `private_key` patterns from any SCC findings or audit-log traces.
- Operations that change finding state (especially `MUTED` / `INACTIVE`) and operations that delete mute configs, notification configs, or BigQuery exports require exact target confirmation.
- Enabling SCC at the organization level has billing and posture-scope impact; require explicit acknowledgement.
- Resource value configs can amplify or downplay severity; preview the resource and severity delta before apply.
- Record command, sanitized parameters, response IDs, and validation result for traceability.

## Reference Index

> [按需加载 — 根据操作类型选择对应 reference 文件]

| Topic | File | Load Condition |
|-------|------|----------------|
| Architecture, limits, permissions | [core-concepts.md](references/core-concepts.md) | 总是加载 |
| Variables and JSON paths | [variables-and-conventions.md](references/variables-and-conventions.md) | 总是加载 |
| Execution flows (Pre-flight/Validate/Recover) | [execution-flows.md](references/execution-flows.md) | 总是加载 |
| gcloud command map | [gcloud-usage.md](references/gcloud-usage.md) | 执行 CLI 操作时加载 |
| API and SDK examples | [api-sdk-usage.md](references/api-sdk-usage.md) | SDK/API fallback 或 custom modules / resource value configs 时加载 |
| Error diagnosis and recovery | [troubleshooting.md](references/troubleshooting.md) | 失败或报错时加载 |
| Monitoring and alerts | [monitoring.md](references/monitoring.md) | 用户询问监控/告警时加载 |
| Integration/bootstrap | [integration.md](references/integration.md) | 首次使用或环境配置时加载 |
| Idempotency | [idempotency-checklist.md](references/idempotency-checklist.md) | 执行重试/幂等操作时加载 |
| Well-Architected | [well-architected-assessment.md](references/well-architected-assessment.md) | 架构评审时加载 |
| GCL rubric | [rubric.md](references/rubric.md) | 破坏性或姿态影响操作前加载 |
| GCL prompt templates | [prompt-templates.md](references/prompt-templates.md) | 破坏性或姿态影响操作前加载 |

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
| 1.0.0 | 2026-06-09 | Initial Security Command Center operations skill: enablement, sources, findings, mute/notification/BQ exports, custom modules, resource value configs, monitoring, GCL artifacts |
