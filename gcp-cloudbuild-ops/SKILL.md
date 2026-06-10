---
name: gcp-cloudbuild-ops
description: >-
  Use when the user needs to submit, inspect, cancel, retry, troubleshoot, or
  monitor Google Cloud Build builds; manage Cloud Build triggers; run triggers;
  manage private worker pools; diagnose build logs, artifacts, substitutions,
  source connections, service account/IAM issues, or CI/CD pipeline failures.
  Triggers on Cloud Build, cloudbuild.googleapis.com, gcloud builds, build
  trigger, private worker pool, build config, cloudbuild.yaml, or CI/CD build
  failure. Not for Cloud Deploy release orchestration, Cloud Run service config,
  Artifact Registry repository administration, or generic IAM beyond Cloud Build
  access required by these operations.
license: MIT
compatibility: >-
  Official Google Cloud CLI (`gcloud`, Python-based SDK), optional Python 3.10+
  with google-cloud-build for SDK fallback, valid Google Cloud credentials with
  Cloud Build Viewer/Editor/Admin or Cloud Build WorkerPool Owner as required,
  and network access to Google Cloud endpoints.
metadata:
  author: gcp-skills
  version: "1.0.0"
  last_updated: "2026-06-09"
  runtime: Harness AI Agent, Claude Code, or compatible Agent runtimes
  go_version_minimum: "1.21"
  gcl_classification: "required"
  gcl_max_iter: 2
  api_profile: "https://cloudbuild.googleapis.com/$discovery/rest?version=v1"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    gcloud builds --help, gcloud builds triggers --help, and gcloud builds
    worker-pools --help expose build submission/inspection/cancel/retry,
    trigger CRUD/run, and private worker pool list/describe/create/update/delete
    commands. See https://cloud.google.com/sdk/gcloud/reference/builds.
  environment:
    - GOOGLE_APPLICATION_CREDENTIALS
    - CLOUDSDK_CORE_PROJECT
    - CLOUDSDK_AUTH_ACCESS_TOKEN
---

> This skill follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Google Cloud Build Operations Skill

## Overview

Cloud Build executes builds from source archives, repositories, and build configs; connects CI/CD triggers to source events; and supports private worker pools for isolated builds. This skill is an operational runbook for agents to perform Cloud Build actions with explicit scope, credential safety, pre-flight checks, dual-path `gcloud`/SDK guidance, validation, recovery, monitoring, and GCL review for CI/CD mutation risk.

> **UX Compliance:** Follow the [User Experience Specification](../gcp-skill-generator/references/user-experience-spec.md): ask only for missing `{{user.*}}` values, show safe previews before mutations, mask credentials, and report actionable next steps.

### CLI applicability

- **`cli_applicability: dual-path`:** Cloud Build has broad official CLI coverage via `gcloud builds`, `gcloud builds triggers`, and `gcloud builds worker-pools`. Use `gcloud` as the primary path and the Cloud Build API/Python SDK as fallback or for structured automation.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT triggers distinguish Cloud Build from Cloud Deploy, Cloud Run, IAM, Logging, and Artifact Registry |
| 2 | **Structured I/O** | Variables use `{{env.*}}`, `{{user.*}}`, `{{output.*}}`; JSON paths centralized at [variables-and-conventions.md](references/variables-and-conventions.md) |
| 3 | **Explicit Actionable Steps** | Operations include Pre-flight → Execute → Validate → Recover flows; full details at [execution-flows.md](references/execution-flows.md) |
| 4 | **Complete Failure Strategies** | [troubleshooting.md](references/troubleshooting.md) has ≥15 Cloud Build-specific error rows with HALT/retry guidance |
| 5 | **Absolute Single Responsibility** | One product: Cloud Build builds, triggers, worker pools, build diagnostics; adjacent services delegated |

### Google Cloud Architecture Framework / Well-Architected Framework Integration

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **Security** | Least-privilege Cloud Build service accounts, trigger confirmation, secret masking, worker pool network controls | [well-architected-assessment.md](references/well-architected-assessment.md#security) |
| **Stability** | Build retries/cancel behavior, queue diagnostics, trigger validation, worker pool capacity checks | [well-architected-assessment.md](references/well-architected-assessment.md#stability) |
| **Cost** | Machine type, timeout, private pool sizing, log retention, artifact cleanup | [well-architected-assessment.md](references/well-architected-assessment.md#cost) |
| **Efficiency** | Idempotent trigger/worker pool management, substitutions, reusable configs | [well-architected-assessment.md](references/well-architected-assessment.md#efficiency) |
| **Performance** | Build step parallelism, cache/artifact strategy, regional worker placement | [well-architected-assessment.md](references/well-architected-assessment.md#performance) |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions Cloud Build, `cloudbuild.googleapis.com`, `gcloud builds`, `cloudbuild.yaml`, build config, CI build, build logs, or build failure.
- User asks to submit a build, list/describe builds, cancel a running build, retry a failed build, or diagnose a failed/queued build.
- User asks to create/list/describe/update/delete/run Cloud Build triggers.
- User asks to list/describe/create/update/delete Cloud Build private worker pools.
- User asks to troubleshoot Cloud Build IAM, logs, source fetch, substitution, Docker build, Artifact Registry push, timeout, quota, or worker pool failures.

### SHOULD NOT Use This Skill When

- Task is Cloud Deploy release/pipeline orchestration → delegate to a Cloud Deploy skill when available.
- Task is deploying or configuring a Cloud Run service outside a Cloud Build step → delegate to `gcp-cloudrun-ops`.
- Task is creating Artifact Registry repositories or changing repository IAM independent of build troubleshooting → delegate to artifact/registry or IAM skill when available.
- Task is generic Logging sinks/buckets/metrics unrelated to Cloud Build build logs → delegate to `gcp-logging-ops`.
- Task is broad IAM/service account administration not needed to run Cloud Build → delegate to `gcp-iam-ops`.
- User requests console-only instructions with no API/CLI execution → provide high-level limitation; do not invent unverified console paths.

### Delegation Rules

- Use this skill for Cloud Build-specific IAM diagnosis (e.g., build service account lacks `artifactregistry.writer`); delegate broad IAM policy design to `gcp-iam-ops`.
- Use this skill to inspect build logs; delegate log sink/exclusion/metric management to `gcp-logging-ops`.
- Use this skill to troubleshoot artifact upload/push from builds; delegate repository lifecycle to Artifact Registry skill when available.
- Apply GCL using [references/rubric.md](references/rubric.md) and [references/prompt-templates.md](references/prompt-templates.md) for trigger and worker-pool mutations.

## Quality Gate (GCL)

> [总是加载 — 触发/worker-pool 变更前必须加载 rubric 和 prompt templates]

Cloud Build is classified as **GCL `required`** with **`max_iter: 2`** because this skill includes destructive operations: **Delete Trigger** and **Delete Worker Pool**. Use [references/rubric.md](references/rubric.md) and [references/prompt-templates.md](references/prompt-templates.md) before executing trigger/worker-pool deletes and production-impacting trigger/build mutations. Persist every GCL trace under `./audit-results/gcl-trace-*.json` with commands, sanitized parameters, responses, validation evidence, and reviewer decision. Delete operations must satisfy the per-operation safety sub-rules in the rubric; non-destructive trigger/worker-pool mutations are GCL `recommended` unless production-impacting, then treat them as `required`.

## Variable Convention and API Conventions

> [总是加载 — 变量约定和 JSON paths]

Full variable table and centralized JSON paths at [references/variables-and-conventions.md](references/variables-and-conventions.md). Key conventions:

- `{{env.*}}` — NEVER ask user; HALT if unset. Includes `GOOGLE_APPLICATION_CREDENTIALS`, `CLOUDSDK_CORE_PROJECT`, `CLOUDSDK_AUTH_ACCESS_TOKEN`.
- `{{user.*}}` — Ask once, reuse. Covers project, region, build/trigger/worker-pool IDs, config paths, substitutions, and `confirm_delete`.
- `{{output.*}}` — Parse from API responses. Key paths: `$.id`, `$.status`, `$.logUrl`, `$.name`, `$.state`.
- Never print access tokens, service account key content, secret substitutions, or credential-bearing build logs.

## Quick Start

### Prerequisites

- [ ] `gcloud` CLI installed.
- [ ] Cloud Build API enabled for `{{env.CLOUDSDK_CORE_PROJECT}}`.
- [ ] Credentials available via `gcloud auth` or ADC; do not print credential files.
- [ ] IAM roles appropriate to the operation: `roles/cloudbuild.builds.viewer`, `roles/cloudbuild.builds.editor`, `roles/cloudbuild.builds.builder`, `roles/cloudbuild.workerPoolOwner`, plus downstream roles for artifacts/deployments.

### Verify Setup (no mutation)

```bash
gcloud version
gcloud config get-value project
gcloud services list --enabled --filter='config.name=cloudbuild.googleapis.com' --format='value(config.name)'
gcloud builds list --limit=1 --format=json
```

### Common Command Preview

Submit a build from local source with a build config. Full command syntax at [gcloud-usage.md#submit-build](references/gcloud-usage.md#submit-build). For SDK fallback, see [api-sdk-usage.md#submit-build](references/api-sdk-usage.md#submit-build).

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| Submit Build | Run a build from local/source config | Medium | Medium — may deploy/push artifacts |
| List/Describe Builds | Inspect historical/running builds | Low | Read-only |
| Cancel Build | Stop a running/queued build | Low | Medium — interrupts CI/CD |
| Retry Build | Re-run a build | Low | Medium — can redeploy/re-push |
| Create/Update Trigger | Mutate source-event pipeline | Medium | High |
| Delete Trigger | Remove CI/CD automation | Low | High — requires confirmation |
| Run Trigger | Manually invoke trigger | Low | Medium/High depending build steps |
| List/Describe Worker Pools | Inspect private pools | Low | Read-only |
| Create/Update Worker Pool | Change private build execution capacity/network | Medium | High |
| Delete Worker Pool | Remove private execution capacity | Low | High — requires confirmation |
| Diagnose Failure | Analyze status, logs, IAM, source, artifact errors | Medium | Read-only unless fix requested |

## Execution Flows

> [总是加载 — 所有操作的核心执行流程]

Every operation follows **Pre-flight → Execute → Validate → Recover**. Full pre-flight tables, execution steps, validation checks, and failure recovery for each operation are at [references/execution-flows.md](references/execution-flows.md). Key pointers:

| Operation | Execution Reference | Command Reference |
|-----------|-------------------|-------------------|
| Submit Build | [execution-flows.md#submit-build](references/execution-flows.md#operation-submit-build) | [gcloud-usage.md#submit-build](references/gcloud-usage.md#submit-build) |
| List/Describe Builds | [execution-flows.md#list-describe](references/execution-flows.md#operation-list-or-describe-builds) | [gcloud-usage.md#list-and-describe-builds](references/gcloud-usage.md#list-and-describe-builds) |
| Cancel/Retry Build | [execution-flows.md#cancel-retry](references/execution-flows.md#operation-cancel-or-retry-build) | [gcloud-usage.md#cancel-and-retry-builds](references/gcloud-usage.md#cancel-and-retry-builds) |
| Trigger CRUD/Run | [execution-flows.md#trigger](references/execution-flows.md#operation-create-update-list-describe-run-or-delete-trigger) | [gcloud-usage.md#triggers](references/gcloud-usage.md#triggers) |
| Worker Pools | [execution-flows.md#worker-pools](references/execution-flows.md#operation-manage-private-worker-pools) | [gcloud-usage.md#private-worker-pools](references/gcloud-usage.md#private-worker-pools) |
| Diagnose Failure | [execution-flows.md#diagnose](references/execution-flows.md#operation-diagnose-build-failure) | [troubleshooting.md#diagnostic-flow](references/troubleshooting.md#diagnostic-flow) |

## Security and Safety Requirements

- Never print credential file contents, access tokens, Git provider OAuth tokens, webhook secrets, or secret substitutions.
- Use Secret Manager references or Cloud Build available secrets; do not pass passwords in substitutions or command lines.
- Delete operations for triggers and worker pools require exact resource-name confirmation.
- Treat trigger and worker-pool **delete** operations as GCL `required`; treat non-destructive trigger/worker-pool mutations as GCL `recommended` unless production-impacting, then treat them as `required`.
- Record command, sanitized parameters, response IDs, and validation result for traceability.

## Reference Index

> [按需加载 — 根据操作类型选择对应 reference 文件]

| Topic | File | Load Condition |
|-------|------|----------------|
| Architecture, limits, permissions | [core-concepts.md](references/core-concepts.md) | 总是加载 |
| Variables and JSON paths | [variables-and-conventions.md](references/variables-and-conventions.md) | 总是加载 |
| Execution flows (Pre-flight/Validate/Recover) | [execution-flows.md](references/execution-flows.md) | 总是加载 |
| gcloud command map | [gcloud-usage.md](references/gcloud-usage.md) | 执行 CLI 操作时加载 |
| API and SDK examples | [api-sdk-usage.md](references/api-sdk-usage.md) | SDK/API fallback 时加载 |
| Error diagnosis and recovery | [troubleshooting.md](references/troubleshooting.md) | 构建失败或报错时加载 |
| Monitoring and alerts | [monitoring.md](references/monitoring.md) | 用户询问监控/告警时加载 |
| Integration/bootstrap | [integration.md](references/integration.md) | 首次使用或环境配置时加载 |
| Idempotency | [idempotency-checklist.md](references/idempotency-checklist.md) | 执行重试/幂等操作时加载 |
| Well-Architected | [well-architected-assessment.md](references/well-architected-assessment.md) | 架构评审时加载 |
| GCL rubric | [rubric.md](references/rubric.md) | trigger/worker-pool 变更前加载 |
| GCL prompt templates | [prompt-templates.md](references/prompt-templates.md) | trigger/worker-pool 变更前加载 |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-09 | Initial Cloud Build operations skill: builds, triggers, private worker pools, diagnostics, monitoring, GCL artifacts |
