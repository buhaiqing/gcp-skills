---
name: gcp-monitoring-ops
description: >-
  Use when the user needs to query, configure, troubleshoot, or manage Google
  Cloud Monitoring — metrics, dashboards, alert policies, notification channels,
  uptime checks, and time-series data. User mentions Cloud Monitoring, Stackdriver,
  alert policies, metric queries, dashboard management, uptime checks, or describes
  monitoring scenarios (e.g., "set up alerts", "check metrics", "create dashboard",
  "notification not working") even without naming the product directly. Not for
  Cloud Logging, billing cost analysis, or IAM roles that have their own ops skills.
license: MIT
compatibility: >-
  Official Google Cloud CLI (`gcloud`, Python-based SDK), Go 1.21+ runtime
  (for JIT SDK fallback), valid service account credentials, network access to
  Google Cloud Monitoring endpoints (`monitoring.googleapis.com`).
metadata:
  author: gcp-skills
  version: "1.0.0"
  last_updated: "2026-06-07"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  go_version_minimum: "1.21"
  go_version_jit: "1.24+"
  api_profile: "https://monitoring.googleapis.com/$discovery/rest?version=v3"
  cli_applicability: "dual-path"
  cli_support_evidence: "gcloud monitoring --help confirms subcommands: dashboards, alert-policies, notification-channels, metrics, uptime. See https://cloud.google.com/sdk/gcloud/reference/monitoring"
  environment:
    - GOOGLE_APPLICATION_CREDENTIALS
    - CLOUDSDK_CORE_PROJECT
    - CLOUDSDK_AUTH_ACCESS_TOKEN
---

> This skill follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Google Cloud Monitoring Operations Skill

## Overview

Cloud Monitoring on Google Cloud provides observability for applications and infrastructure — metrics, dashboards, alerting, uptime checks, and time-series analysis. This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **dual-path execution** (official **SDK/API** and **`gcloud`** CLI), response validation, and failure recovery.

> **UX Compliance:** This skill follows the [User Experience Specification](../gcp-skill-generator/references/user-experience-spec.md). All operations include onboarding guidance, minimal prompts, smart defaults, clear feedback, and user-friendly error handling.

### CLI applicability (repository policy)

- **`cli_applicability: dual-path`:** Official `gcloud` supports monitoring. Full CLI commands + SDK scripts at [references/gcloud-usage.md](references/gcloud-usage.md). SDK details at [references/api-sdk-usage.md](references/api-sdk-usage.md).

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use conditions with precise triggers and delegation rules |
| 2 | **Structured I/O** | Placeholder conventions (`{{env.*}}`, `{{user.*}}`, `{{output.*}}`) with type and source documented |
| 3 | **Explicit Actionable Steps** | Every operation: Pre-flight → Execute → Validate → Recover (see [gcloud-usage.md](references/gcloud-usage.md)) |
| 4 | **Complete Failure Strategies** | Error taxonomy table with ≥ 10 product-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | One product (Cloud Monitoring) with clear cross-product delegation (Logging, GCE, GKE, etc.) |

### Google Cloud Architecture Framework Integration

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **Security** | IAM permissions, credential masking, VPC SC, data encryption | [well-architected-assessment.md](references/well-architected-assessment.md) §2.1 |
| **Stability** | Alert redundancy, uptime check multi-region, failure-oriented design | [well-architected-assessment.md](references/well-architected-assessment.md) §2.2 |
| **Cost** | Metrics retention pricing, custom metrics costs, waste detection | [well-architected-assessment.md](references/well-architected-assessment.md) §2.3 |
| **Efficiency** | Batch operations, CI/CD integration, automation patterns | [well-architected-assessment.md](references/well-architected-assessment.md) §2.4 |
| **Performance** | Monitoring latency, alert freshness, query performance | [well-architected-assessment.md](references/well-architected-assessment.md) §2.5 |

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "Cloud Monitoring", "Stackdriver", "metrics", "alert policies", "dashboards", "notification channels", or "uptime checks"
- Task involves querying time-series metrics (CPU, memory, disk, network, custom metrics)
- Task involves CRUD on alert policies, notification channels, dashboards, uptime check configs
- Task keywords: monitor, alert, metric, dashboard, notification, uptime, incident, silen[ce], SLO
- User asks to set up, configure, troubleshoot, or investigate GCP observability

### SHOULD NOT Use This Skill When

- Task is purely Cloud Logging (log queries, log buckets, log-based metrics) → delegate to: `gcp-logging-ops`
- Task is IAM / permission model only → delegate to: `gcp-iam-ops`
- Task is about Compute Engine instance state (start/stop/ssh) → delegate to: `gcp-gce-ops`
- Task is about GKE cluster metrics (use kubectl top / gke-ops) → delegate to: `gcp-gke-ops`
- Task is about billing cost analysis → delegate to: `gcp-billing-ops`

### Delegation Rules

| Resource | Delegated Skill | Flow |
|----------|----------------|------|
| VM CPU/Memory investigation | `gcp-gce-ops` | Monitoring detects anomaly → delegate describe/patch to GCE |
| K8s cluster metrics | `gcp-gke-ops` | GKE metrics → GKE skill describes cluster/node |
| Log-based alert policies | `gcp-logging-ops` | Log-based metrics query → Logging skill for log filter |
| Database query performance | `gcp-cloudsql-ops` | Monitoring detects slow query → Cloud SQL skill investigates |

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.GOOGLE_APPLICATION_CREDENTIALS}}` | Path to SA key JSON | NEVER ask the user; fail if unset |
| `{{env.CLOUDSDK_CORE_PROJECT}}` | GCP project ID | NEVER ask the user; fail if unset |
| `{{env.CLOUDSDK_AUTH_ACCESS_TOKEN}}` | Temporary access token | NEVER ask the user; fail if needs refresh |
| `{{user.project}}` | User-supplied project (override) | Ask once; reuse |
| `{{user.alert_policy_id}}` | Alert policy name/ID | Ask once; reuse |
| `{{user.channel_id}}` | Notification channel ID | Ask once; reuse |
| `{{user.dashboard_id}}` | Dashboard ID | Ask once; reuse |
| `{{user.metric_type}}` | Metric type (e.g., compute.googleapis.com/instance/cpu/utilization) | Ask once; reuse |
| `{{user.uptime_check_id}}` | Uptime check config ID | Ask once; reuse |
| `{{user.filter}}` | Monitoring filter expression | Ask once; reuse |
| `{{output.resource_name}}` | From last API or `gcloud` JSON response | Parse per operation |
| `{{output.alert_policy_name}}` | Created/modified alert policy name | Parse per API response |
| `{{output.channel_name}}` | Created notification channel name | Parse per API response |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.
>
> **Security Warning (Credential Masking — MANDATORY):** NEVER log, print, or expose service account key content, `GOOGLE_APPLICATION_CREDENTIALS` path content, or any credential field value. Verification MUST check existence only: `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA key file exists"`.

## API and Response Conventions

- **REST API is canonical:** `https://monitoring.googleapis.com/v3/`
- **Time format:** RFC 3339 (e.g., `2026-06-07T10:00:00Z`)
- **Pagination:** `pageToken` in request, `nextPageToken` in response; page size defaults to 100
- **Metric types:** `{service}.googleapis.com/{namespace}/{metric}`

### Common JSON Paths (TE-4)

```
$.timeSeries[].metric.type          → metric type string
$.timeSeries[].resource.type        → monitored resource type
$.timeSeries[].points[].value       → metric values
$.timeSeries[].points[].interval    → time range
$.name               → "projects/{project}/alertPolicies/{policy_id}"
$.displayName        → human-readable name
$.combiner           → OR / AND / AND_WITH_MATCHING_RESOURCE
$.conditions[]       → list of alert conditions
$.notificationChannels[] → linked notification channels
$.enabled            → { "value": true/false }
$.type               → "email" | "sms" | "pagerduty" | "slack" | "webhook"
$.labels             → channel-specific config
$.gridLayout.widgets[] → widget definitions
$.etag               → for optimistic concurrency control
$.period             → check frequency (e.g., "60s")
$.timeout            → check timeout (e.g., "10s")
$.checkType          → HTTP | HTTPS | TCP
```

### Expected State Transitions

| Operation | Initial State | Target State | Poll Interval | Max Wait |
|-----------|---------------|--------------|---------------|----------|
| Create Alert Policy | — | exists (no async) | — | 30s |
| Create Notification Channel | — | exists (no async) | — | 30s |
| Create Dashboard | — | exists (no async) | — | 30s |
| Create Uptime Check | — | exists (no async) | — | 30s |
| Delete (any) | exists | deleted | — | 30s |

## Quick Start

### Prerequisites
- [ ] `gcloud` CLI installed (or Go runtime for JIT fallback)
- [ ] Service account key configured: `GOOGLE_APPLICATION_CREDENTIALS`
- [ ] Project set: `gcloud config set project <project-id>` or `CLOUDSDK_CORE_PROJECT`

### Verify Setup
```bash
gcloud config get-value project
gcloud auth application-default print-access-token --quiet &>/dev/null && echo "✅ Auth OK"
```

### Your First Command
```bash
gcloud monitoring metrics list --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" | jq '[.[] | {name, type, unit}]'
```

### Next Steps
- [Core Concepts](references/core-concepts.md) — Understand Cloud Monitoring architecture
- [Common Operations](references/gcloud-usage.md) — Manage alerts, dashboards, channels
- [Troubleshooting](references/troubleshooting.md) — Fix common issues

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| Query Time Series | Query metric time-series data | Medium | None |
| List Metric Descriptors | List all metric types available | Low | None |
| List/Create/Modify/Delete Alert Policies | Manage alert rules | Medium | **Medium** |
| List/Create/Describe/Delete Notification Channels | Configure alert routing | Low | **Low** |
| List/Create/Describe/Delete Dashboards | Visual metric dashboards | Medium | Low |
| Create/Describe/Delete Uptime Checks | External endpoint monitoring | Medium | Low |
| Silence/Unsilence Alerts | Temporarily mute alerts | Low | **Low** |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-07 | Initial Cloud Monitoring skill with time-series, alerts, channels, dashboards, uptime checks |

## Execution Flows

Every operation: **Pre-flight → Execute (gcloud + SDK) → Validate → Recover**.

### Pre-flight Checks (Common)

| Check | Command | Action |
|-------|---------|--------|
| gcloud CLI | `gcloud version` | Install if exit ≠0 |
| Credentials | `gcloud auth print-access-token --quiet` | HALT if empty; re-authenticate |
| Project | `gcloud config get-value project` | HALT if unset; set `CLOUDSDK_CORE_PROJECT` |
| Monitoring API | `gcloud services list --enabled --filter="config:monitoring.googleapis.com"` | HALT if disabled; enable with `gcloud services enable monitoring.googleapis.com` |

### Operations Summary

For full gcloud commands, Python SDK scripts, Go SDK fallbacks, pre-flight checks, validation, and recovery for each operation, see [references/gcloud-usage.md](references/gcloud-usage.md).

| Operation | Risk | Reference |
|-----------|------|-----------|
| Query Time-Series Metrics | None | [gcloud-usage.md](references/gcloud-usage.md) §Time-Series |
| Alert Policies CRUD | **Medium** | [gcloud-usage.md](references/gcloud-usage.md) §Alert-Policies |
| Notification Channels CRUD | Low | [gcloud-usage.md](references/gcloud-usage.md) §Notification-Channels |
| Dashboards CRUD | Low | [gcloud-usage.md](references/gcloud-usage.md) §Dashboards |
| Uptime Checks CRUD | Low | [gcloud-usage.md](references/gcloud-usage.md) §Uptime-Checks |

> **Safety Gates:** Delete operations for alert policies, notification channels, and dashboards require explicit user confirmation (type exact resource ID).

## Prerequisites

1. **Install gcloud CLI:** `curl https://sdk.cloud.google.com | bash && exec -l $SHELL && gcloud init`
2. **Bootstrap Go runtime** (JIT fallback): See [integration.md](references/integration.md)
3. **Configure Credentials:** `export GOOGLE_APPLICATION_CREDENTIALS=... && export CLOUDSDK_CORE_PROJECT=...`
4. **Enable Monitoring API:** `gcloud services enable monitoring.googleapis.com`

## Reference Directory

- [Core Concepts](references/core-concepts.md) — Architecture, metric types, monitored resources, quotas
- [API & SDK Usage](references/api-sdk-usage.md) — REST API, Python/Go SDK operation maps, pagination
- [gcloud Usage](references/gcloud-usage.md) — Full CLI commands, jq patterns, detailed execution flows
- [Troubleshooting Guide](references/troubleshooting.md) — 12 error codes, 6 diagnostic scenarios
- [Monitoring & Alerts](references/monitoring.md) — Self-monitoring metrics, dashboard templates
- [Integration](references/integration.md) — Go JIT bootstrap, SDK setup, credential rules
- [Well-Architected Assessment](references/well-architected-assessment.md) — Five-pillar assessment
- [Idempotency Checklist](references/idempotency-checklist.md) — Alert/channel/dashboard/uptime idempotency
- [User Experience Specification](../gcp-skill-generator/references/user-experience-spec.md)
- [Execution Environment Setup](../gcp-skill-generator/references/execution-environment.md)

## Operational Best Practices

- **Least privilege:** `roles/monitoring.viewer` (read-only), `roles/monitoring.editor` (alerts/dashboards), `roles/monitoring.admin` (full)
- **Alert hygiene:** Avoid alert fatigue with proper condition thresholds and durations
- **Dashboard structure:** Use `gridLayout` for organized widgets; label by team/service/environment
- **Metrics retention:** Standard 6 weeks for most metrics; custom metrics follow billing plan
- **Uptime check regions:** Use ≥ 3 regions for reliable health checking

## Quality Gate (GCL)

This skill uses the **Generator-Critic-Loop (GCL)** adversarial quality gate.

| Dimension | Classification | Default `max_iter` | Most-scrutinized ops |
|-----------|---------------|:------------------:|----------------------|
| Cloud Monitoring | `recommended` | 3 | Delete Alert Policy, Modify Alert, Delete Notification Channel |

**Rubric:** See [references/rubric.md](references/rubric.md)
**Prompt templates:** See [references/prompt-templates.md](references/prompt-templates.md)

## Token Efficiency Guidelines (P0 — 强制)

### TE-1: API Query > Static Tables
Use `gcloud monitoring metrics list` to fetch metric descriptors instead of hardcoding.

### TE-2: No docstrings in code
Inline `#` comments only. No function-level docstrings.

### TE-3: Compact error tables
See [troubleshooting.md](references/troubleshooting.md) for compact error table format.

### TE-4: Centralized JSON paths
JSON paths declared at file top under [Common JSON Paths](#common-json-paths).

### TE-5: YAML anchors in example-config.yaml
See [assets/example-config.yaml](assets/example-config.yaml) for YAML anchor patterns.

### TE-6: Eliminate cross-file duplicate flows
Detailed execution flows are in [references/gcloud-usage.md](references/gcloud-usage.md); SKILL.md only contains operation summary table with links.

### TE-7: Advanced content in references/advanced/
Advanced topics (custom metrics, SLO-based alerting, multi-project monitoring) are in [references/advanced/](references/advanced/). Core operations remain in the main references/ files.

### TE-8: Reference depth ≤ 2 layers
All references use ≤2 path segments (e.g., `references/gcloud-usage.md`). Avoid referencing `references/advanced/some-file.md` directly from SKILL.md — intermediate index in references/ is preferred.

## AIOps 自愈 (Self-Healing)

Cloud Monitoring 是自愈的天然触发器。当检测到**告警风暴**（同策略短时间大量 firing）或**策略抖动**（flapping）时，本 skill 提供带 **dry-run + 幂等 + 人工复核门禁** 的静默/抑制自愈能力；破坏性动作（删除策略、改阈值、批量静默）一律标 **HALT**。监控只静默自身告警面，底层资源修复委托给对应 skill 的 AIOps runbook。

- 完整 runbook：[references/advanced/aiops-alert-anomaly.md](references/advanced/aiops-alert-anomaly.md)
- 跨 skill 触发与爆炸半径：[docs/cross-skill-blast-radius.md](docs/cross-skill-blast-radius.md)
- 错误分类（仓库级）：[docs/error-taxonomy.md](docs/error-taxonomy.md)
