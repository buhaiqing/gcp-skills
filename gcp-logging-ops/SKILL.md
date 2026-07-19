---
name: gcp-logging-ops
description: >-
  Use when the user needs to manage, configure, troubleshoot, or monitor Google
  Cloud Logging resources — log buckets, log views, log sinks, log-based metrics,
  log entries, and log exclusions. User mentions Cloud Logging, Logging, log
  sink, log bucket, log metric, log entry, excludes, exports, or describes
  logging scenarios (e.g., "can't see logs", "forward logs to BigQuery", "create
  log-based metric", "log export stopped working") even without naming the
  product directly. Not for Cloud Monitoring (metrics, alerts), Error Reporting,
  or Cloud Audit Logs IAM policies that have their own ops skills.
license: MIT
compatibility: >-
  Official Google Cloud CLI (`gcloud`, Python-based SDK), Go 1.21+ runtime
  (for JIT SDK fallback), valid service account credentials with Logs Admin or
  Logs Viewer IAM role, network access to Google Cloud endpoints.
metadata:
  author: gcp-skills
  version: "1.0.0"
  last_updated: "2026-06-07"
  runtime: Harness AI Agent, Claude Code, or compatible Agent runtimes
  go_version_minimum: "1.21"
  go_version_jit: "1.24+"
  api_profile: "https://logging.googleapis.com/$discovery/rest?version=v2"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    gcloud logging --help confirms subcommands: buckets, views, sinks, metrics,
    logs, operations, locations. See
    https://cloud.google.com/sdk/gcloud/reference/logging
  environment:
    - GOOGLE_APPLICATION_CREDENTIALS
    - CLOUDSDK_CORE_PROJECT
    - CLOUDSDK_AUTH_ACCESS_TOKEN
---

> This skill follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Google Cloud Logging Operations Skill

## Overview

Google Cloud Logging provides real-time log management and analysis with log buckets, views, sinks, metrics, and exclusions. This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **dual-path execution** (official **SDK/API** and **`gcloud`** CLI), response validation, and failure recovery.

> **UX Compliance:** This skill follows the Agent Skill OpenSpec UX conventions. All operations include onboarding guidance, minimal prompts, smart defaults, clear feedback, and user-friendly error handling.

### CLI applicability (repository policy)

- **`cli_applicability: dual-path`:** Official `gcloud` fully supports Cloud Logging via `gcloud logging buckets`, `gcloud logging views`, `gcloud logging sinks`, `gcloud logging metrics`, etc. You MUST ship both **`references/gcloud-usage.md`** and, in each execution flow below, document **both** the SDK step **and** the `gcloud` step for every operation. Coverage gaps (SDK-only operations) are listed in `references/gcloud-usage.md`.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use conditions with precise triggers and delegation rules |
| 2 | **Structured I/O** | Placeholder conventions (`{{env.*}}`, `{{user.*}}`, `{{output.*}}`) with type and source documented |
| 3 | **Explicit Actionable Steps** | Every operation: Pre-flight → Execute → Validate → Recover, with numbered imperative steps |
| 4 | **Complete Failure Strategies** | Error taxonomy table with ≥ 12 product-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | One product (Cloud Logging) with clear delegation to related skills (Monitoring, BigQuery, Pub/Sub, Storage) |

Refer to the Five Core Standards table above for the summary of each quality gate.

### Google Cloud Architecture Framework Integration

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **Security** | IAM permissions (roles/logging.admin), CMEK for log buckets, VPC Service Controls, audit log access | `references/well-architected-assessment.md` §2.1 |
| **Stability** | Multi-region log buckets, retention policies, sink _Required bucket protection, cross-project aggregation | `references/well-architected-assessment.md` §2.2 |
| **Cost** | Log retention cost optimization, exclusion rules, _Default bucket vs custom buckets, log volume monitoring | `references/well-architected-assessment.md` §2.3 |
| **Efficiency** | Log-based metrics, aggregated sinks, exclusion automation, CI/CD pipeline integration | `references/well-architected-assessment.md` §2.4 |
| **Performance** | Log ingestion rate, query latency, _Default bucket quotas, Log Analytics | `references/well-architected-assessment.md` §2.5 |

See [references/well-architected-assessment.md](references/well-architected-assessment.md) for the complete specification.

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "Cloud Logging", "Logging", "log bucket", "log view", "log sink", "log metric", "log entry", "log exclusion", "log export"
- Task involves CRUD or lifecycle operations on **log buckets** (create, describe, update, delete, list, undelete)
- Task involves **log views** (create, describe, delete, list)
- Task involves **log sinks** (create, describe, update, delete, list)
- Task involves **log-based metrics** (create, describe, delete, list)
- Task involves **log entries** (list, read, tail)
- Task involves **log exclusions** (create, describe, update, delete, list)
- User describes logging scenarios: "can't find logs", "logs not showing up", "forward logs to BigQuery", "create a log metric for errors", "log export to Pub/Sub"
- Keywords: logs, logging, sink, bucket, metric, exclusion, _Default, _Required, log entry, log view, log router

### SHOULD NOT Use This Skill When

- Task is purely about Cloud Monitoring metrics and alerts → delegate to: `gcp-monitoring-ops`
- Task is purely about Error Reporting → delegate to: `gcp-monitoring-ops` (Error Reporting is part of Monitoring)
- Task is purely about Cloud Audit Logs IAM policies → delegate to: `gcp-iam-ops`
- Task is purely about BigQuery dataset management (even if logs are exported) → delegate to: `gcp-bigquery-ops`
- User insists on **console-only** flows with no API → state limitation; do not invent undocumented gcloud steps

### Delegation Rules

- **BigQuery sink destination**: If BigQuery dataset does not exist, delegate to `gcp-bigquery-ops` first.
- **Pub/Sub sink destination**: If Pub/Sub topic does not exist, delegate to `gcp-pubsub-ops` (when available).
- **Cloud Storage sink destination**: If GCS bucket does not exist, delegate to `gcp-gcs-ops` first.
- **Monitoring/Alerts**: For Cloud Monitoring, delegate to `gcp-monitoring-ops`.
- **GCL**: Execution quality gate uses `gcp-gcl-runner-ops`.

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.GOOGLE_APPLICATION_CREDENTIALS}}` | Path to SA key JSON | NEVER ask the user; fail if unset |
| `{{env.CLOUDSDK_CORE_PROJECT}}` | GCP project ID | NEVER ask the user; fail if unset |
| `{{env.CLOUDSDK_AUTH_ACCESS_TOKEN}}` | Temporary access token | NEVER ask the user; fail if needs refresh |
| `{{user.project}}` | User-supplied project (override) | Ask once; reuse |
| `{{user.region}}` | User-supplied region (e.g., global, us-central1) | Ask once; reuse; default: global |
| `{{user.log_bucket_name}}` | Log bucket name | Ask once; reuse |
| `{{user.log_view_name}}` | Log view name | Ask once; reuse |
| `{{user.sink_name}}` | Log sink name | Ask once; reuse |
| `{{user.metric_name}}` | Log-based metric name | Ask once; reuse |
| `{{user.exclusion_name}}` | Log exclusion name | Ask once; reuse |
| `{{user.filter_query}}` | Log filter expression | Ask once; reuse |
| `{{user.sink_destination}}` | Sink destination (bigquery/pubsub/storage URI) | Ask once; reuse |
| `{{user.retention_days}}` | Log bucket retention period | Ask once; reuse; default: 30 |
| `{{user.description}}` | Description for any resource | Ask once; reuse |
| `{{output.sink_writer_identity}}` | From create sink response | Parse from JSON path `$.writerIdentity` |
| `{{output.bucket_create_time}}` | From create bucket response | Parse from JSON path `$.createTime` |
| `{{output.metric_create_time}}` | From create metric response | Parse from JSON path `$.createTime` |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning (Credential Masking — MANDATORY):** NEVER log, print, or expose service account key content, `GOOGLE_APPLICATION_CREDENTIALS` path content, or any credential field value in console output, debug messages, error messages, or logs.

| Execution Path | Safe Pattern | Unsafe Pattern |
|----------------|-------------|----------------|
| Console output | `GOOGLE_APPLICATION_CREDENTIALS=<masked>` | `{"private_key": "-----BEGIN...` |
| Error messages | `Error: API call failed (credential omitted)` | `Error: ... actual SA key content...` |
| Log files | `[INFO] Credentials configured: SA=***` | `[INFO] SA key: {"private_key":"...` |
| Verification | `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA key file exists"` | `cat $GOOGLE_APPLICATION_CREDENTIALS` |
| Go SDK | `option.WithCredentialsFile(os.Getenv("..."))` (env read is safe) | `fmt.Printf("Config: %+v", config)` or `log.Printf("%+v", ...)` |

## API and Response Conventions (Agent-Readable)

- **REST API is canonical**: Cloud Logging v2 API (`logging.googleapis.com`). All JSON paths below are verified against the official REST API reference.
- **Errors**: Map HTTP/gRPC status codes to canonical error types.
- **Timestamps**: RFC 3339 (e.g., `2026-06-07T10:00:00.000Z`).
- **Idempotency**: Sink/metric/exclusion names are project-unique; buckets are location-unique.

### Key JSON Paths (Centralized per TE-4)

| Operation | JSON Path | Type | Description |
|-----------|-----------|------|-------------|
| List Log Entries | `$.entries[].{logName,resource,textPayload,jsonPayload,timestamp}` | array | Log entry fields |
| Create Sink | `$.{name,destination,writerIdentity,createTime}` | object | Sink details |
| Describe Sink | `$.{name,destination,filter,writerIdentity}` | object | Sink configuration |
| List Sinks | `$.sinks[].{name,destination,filter}` | array | Sink list |
| Create Metric | `$.{name,filter,description,createTime}` | object | Metric details |
| Describe Metric | `$.{name,filter,description,metricDescriptor}` | object | Metric configuration |
| List Metrics | `$.metrics[].{name,filter,description}` | array | Metric list |
| Create/Update Bucket | `$.{name,retentionDays,lifecycleState,createTime,updateTime}` | object | Bucket details |
| Describe Bucket | `$.{name,retentionDays,lifecycleState,locked}` | object | Bucket configuration |
| List Buckets | `$.buckets[].{name,retentionDays,lifecycleState}` | array | Bucket list |

### Expected State Transitions

| Operation | Initial State | Target State | Poll Interval | Max Wait |
|-----------|---------------|--------------|---------------|----------|
| Create Bucket | — | `ACTIVE` | 2s | 30s |
| Update Bucket | `ACTIVE` | `ACTIVE` | 2s | 30s |
| Delete Bucket | `ACTIVE` | `DELETE_REQUESTED` → absent | 5s | 120s |
| Create Sink | — | `ACTIVE` | Immediate | — |
| Create Metric | — | `ACTIVE` | Immediate | — |
| Create Exclusion | — | `ACTIVE` | Immediate | — |

## Quick Start

### What This Skill Does
This skill enables you to manage, configure, troubleshoot, and monitor Cloud Logging resources — log buckets, views, sinks, metrics, entries, and exclusions on Google Cloud using the `gcloud` CLI (primary) or Go SDK (fallback).

### Prerequisites
- [ ] `gcloud` CLI installed (or Go runtime for JIT fallback)
- [ ] Service account key configured: `GOOGLE_APPLICATION_CREDENTIALS`
- [ ] Project set: `gcloud config set project <project-id>` or `CLOUDSDK_CORE_PROJECT`
- [ ] IAM roles: `roles/logging.admin` (or `roles/logging.viewer` for read-only)

### Verify Setup
```bash
# Check gcloud and project
gcloud config get-value project
gcloud auth application-default print-access-token --quiet &>/dev/null && echo "✅ Auth OK"

# Quick list to verify Logging API access
gcloud logging logs list --limit=1 --format="json" &>/dev/null && echo "✅ Logging API OK"
```

### Your First Command
```bash
# Read recent logs
gcloud logging read "severity>=ERROR" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --limit=10 \
  --format="json"
```

### Next Steps
- [Core Concepts](references/core-concepts.md) — Logging architecture, quotas, regions
- [Common Operations](#execution-flows) — Manage buckets, sinks, metrics, and entries
- [Troubleshooting](references/troubleshooting.md) — Fix common issues

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| List Log Entries | Read/query log entries with filters | Low | None |
| Create Log Bucket | Create a new log bucket | Medium | Low |
| Update Log Bucket | Change bucket retention or description | Medium | Low |
| Delete Log Bucket | Remove a log bucket | Low | **High** — irreversible, data loss |
| Create Log View | Create a view over a bucket | Medium | Low |
| Delete Log View | Remove a log view | Low | Medium |
| Create Log Sink | Export logs to destination | Medium | Low |
| Update Log Sink | Change sink filter or destination | Medium | Medium |
| Delete Log Sink | Stop log export | Low | **High** — export stops |
| Create Log Metric | Create a log-based metric | Medium | Low |
| Delete Log Metric | Remove a log metric | Low | Medium |
| Create Log Exclusion | Exclude logs from ingestion | Medium | Low |
| Delete Log Exclusion | Remove an exclusion rule | Low | Medium |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-07 | Initial release: Logging bucket, view, sink, metric, entry, exclusion operations with dual-path gcloud+SDK, GCL quality gate |

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (gcloud + SDK/API) → Validate → Recover**. Do not skip phases.

### Operation: List Log Entries

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| gcloud CLI | `gcloud version` | Exit code 0 | HALT — install gcloud SDK |
| Credentials | `gcloud auth print-access-token` | Token returned | HALT — authenticate |
| Project | `gcloud config get-value project` | Set and valid | HALT — set project |
| Logging API | `gcloud services list --enabled | grep logging.googleapis.com` | Enabled | HALT — enable `logging.googleapis.com` |

#### Execution — CLI (`gcloud`) (Primary Path)

Full commands at [references/gcloud-usage.md](references/gcloud-usage.md) (Log Entries section).

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud logging read "severity>=ERROR"` | Read recent error logs (add `--freshness`, `--limit`) |
| 2 | `gcloud logging read "resource.type=gce_instance AND severity>=ERROR"` | Read with resource + time filter |
| 3 | `gcloud logging tail` | Stream logs live |

All commands use `--project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"`.

#### Execution — Python SDK (Primary Fallback)

> **API level note:** This skill uses two Python client levels:
> - `google.cloud.logging.Client` (high-level) — simpler API for log entries, sinks, and metrics
> - `google.cloud.logging_v2.ConfigClientV2` (low-level gapic) — full control for bucket and view operations
> Both are from the same `google-cloud-logging` package; choose the level that matches your operation.

Full script at [assets/code-snippets/list_log_entries.py](assets/code-snippets/list_log_entries.py)

Key steps:
1. Create client: `logging.Client(project=...)`
2. List entries: `client.list_entries(filter_=..., page_size=...)`

#### Execution — JIT Go SDK (Secondary Fallback)

Full Go snippet at [assets/code-snippets/list_log_entries.go](assets/code-snippets/list_log_entries.go). Bootstrap per [references/integration.md](references/integration.md) §Go SDK.

#### Present to User

| Field | JSON Path | Notes |
|-------|-----------|-------|
| Timestamp | `.timestamp` | RFC 3339 |
| Log Name | `.logName` | Full log name |
| Severity | `.severity` | DEFAULT/DEBUG/INFO/NOTICE/WARNING/ERROR/CRITICAL/ALERT/EMERGENCY |
| Resource | `.resource.type` | Resource type |
| Payload | `.textPayload` / `.jsonPayload` / `.protoPayload` | Log content |

#### Failure Recovery

| Error Code | Max retries | Backoff | Agent Action | UX Feedback |
|------------|-------------|---------|--------------|-------------|
| INVALID_ARGUMENT / 400 | 0-1 | — | Fix filter expression; retry | `[ERROR] Invalid filter expression` |
| PERMISSION_DENIED / 403 | 0 | — | HALT | `[ERROR] SA lacks roles/logging.viewer` |
| QUOTA_EXCEEDED / 429 | 3 | exp. | Back off; reduce page size | `⚠️ Read quota exceeded. Retrying...` |
| DEADLINE_EXCEEDED / 504 | 3 | exp. | Retry with shorter time range | `⚠️ Query timeout. Narrowing time range...` |
| UNAVAILABLE / 503 | 3 | exp. | Back off | `⚠️ Service temporarily unavailable` |
| INTERNAL / 500 | 3 | 2/4/8s | Retry; then HALT | `[ERROR] Internal error — escalate if persistent` |

---

### Operation: Create Log Bucket

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Logging API | `gcloud services list --enabled | grep logging.googleapis.com` | Enabled | HALT — enable API |
| Bucket name unique | `gcloud logging buckets describe "{{user.log_bucket_name}}" --location="{{user.region}}" --quiet` | NOT_FOUND | HALT — name in use |
| Retention valid | Validate `{{user.retention_days}}` is integer 1-3650 | Valid range | Fix to default 30 |
| CMEK key accessible | If user specifies CMEK, check key access | Key exists | Warn; proceed without CMEK |

#### Smart Defaults

| Field | Default | Rationale |
|-------|---------|-----------|
| region | `global` | Default Logging location |
| retention_days | `30` | Balanced cost/compliance for most use cases |

#### Execution — CLI (`gcloud`) (Primary Path)

Full commands at [references/gcloud-usage.md](references/gcloud-usage.md) (Log Buckets section).

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud logging buckets create NAME --location --retention-days` | Create bucket (defaults: `global`, `30`) |
| 2 | `... --cmek-kms-key=KEY` | Variant with CMEK encryption |

All commands use `--project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"`.

#### Execution — Python SDK (Primary Fallback)

Full script at [assets/code-snippets/create_log_bucket.py](assets/code-snippets/create_log_bucket.py)

Key steps:
1. Create client: `logging_v2.ConfigClientV2()`
2. Configure bucket: `logging_v2.LogBucket(retention_days=..., description=...)`
3. Create: `client.create_bucket(request=...)`

#### Post-execution Validation

`gcloud logging buckets describe "{{user.log_bucket_name}}" --location="{{user.region:-global}}" --format="json" | jq '{name, retentionDays, lifecycleState, createTime}'`

#### Failure Recovery

| Error Code | Max retries | Agent Action | UX Feedback |
|------------|-------------|--------------|-------------|
| INVALID_ARGUMENT / 400 | 1 | Fix params | `[ERROR] Invalid bucket parameters` |
| PERMISSION_DENIED / 403 | 0 | HALT | `[ERROR] SA lacks roles/logging.admin` |
| ALREADY_EXISTS / 409 | 0 | Ask rename | `[ERROR] Bucket name already exists` |
| QUOTA_EXCEEDED / 429 | 0 | HALT | `[ERROR] Bucket quota exceeded` |
| FAILED_PRECONDITION / 400 | 0 | HALT | `[ERROR] CMEK key not accessible` |

---

### Operation: Update Log Bucket

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Bucket exists | Describe | Exit 0 | HALT — not found |
| Bucket not locked | `.locked == false` | Not locked | HALT — cannot modify locked bucket |

#### Execution — CLI (`gcloud`)

Full command at [references/gcloud-usage.md](references/gcloud-usage.md) (Log Buckets → Update).

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud logging buckets update NAME --retention-days --description` | Update retention/description |

Uses `--location="{{user.region:-global}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"`.

#### Post-execution Validation

`gcloud logging buckets describe "{{user.log_bucket_name}}" --location="{{user.region:-global}}" --format="json"`

---

### Operation: Create Log View

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Bucket exists | Describe bucket | Exit 0 | HALT — create bucket first |
| View name unique | `gcloud logging views describe "{{user.log_view_name}}" --bucket="{{user.log_bucket_name}}" --location="{{user.region}}" --quiet` | NOT_FOUND | HALT — name in use |

#### Execution — CLI (`gcloud`)

Full command at [references/gcloud-usage.md](references/gcloud-usage.md) (Log Views → Create).

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud logging views create NAME --bucket --log-filter` | Create view over bucket |

Uses `--location="{{user.region:-global}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"`.

#### Post-execution Validation

`gcloud logging views describe "{{user.log_view_name}}" --bucket="{{user.log_bucket_name}}" --location="{{user.region:-global}}" --format="json" | jq '{name, filter, description}'`

---

### Operation: Delete Log View

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit user confirmation: deletion of view `{{user.log_view_name}}`

#### Execution — CLI (`gcloud`)

`gcloud logging views delete "{{user.log_view_name}}" --bucket="{{user.log_bucket_name}}" --location="{{user.region:-global}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"` (full map at [references/gcloud-usage.md](references/gcloud-usage.md) Log Views → Delete).

---

### Operation: Delete Log Bucket

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit user confirmation: irreversible delete of `{{user.log_bucket_name}}`
- **MUST** warn: `_Required` and `_Default` buckets cannot be deleted
- **MUST** warn: all log data in the bucket will be permanently lost
- **MUST** check if any sinks reference this bucket

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Bucket exists | Describe | Exit 0 | HALT — already deleted |
| Not _Required/_Default | `{{user.log_bucket_name}}` not in reserved names | Not reserved | HALT — protected bucket |
| Sinks referencing bucket | `gcloud logging sinks list --format=json \| jq '.[] \| select(.destination \| contains("{{user.log_bucket_name}}"))'` | Empty | Warn user about affected sinks |
| User confirmation | Ask: `Proceed with irreversible delete? (yes/bucket_name)` | Exact match | HALT — abort |

#### Execution — CLI (`gcloud`)

`gcloud logging buckets delete "{{user.log_bucket_name}}" --location="{{user.region:-global}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"` (full map at [references/gcloud-usage.md](references/gcloud-usage.md) Log Buckets → Delete).

**Never use `--quiet` to bypass this safety gate.**

#### Execution — Python SDK (Primary Fallback)

Full script at [assets/code-snippets/delete_log_bucket.py](assets/code-snippets/delete_log_bucket.py)

Key steps:
1. Create client: `logging_v2.ConfigClientV2()`
2. Build resource name: `projects/{project}/locations/{location}/buckets/{name}`
3. Delete: `client.delete_bucket(request=...)`

#### Post-execution Validation

`gcloud logging buckets describe "{{user.log_bucket_name}}" --location="{{user.region:-global}}" --quiet 2>&1 || echo "✅ Bucket confirmed deleted"`

---

### Operation: Create Log Sink

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Destination exists | Check BigQuery dataset / PubSub topic / GCS bucket | Exists | HALT — create destination first |
| Sink name unique | `gcloud logging sinks describe "{{user.sink_name}}" --quiet` | NOT_FOUND | HALT — name in use |

#### Execution — CLI (`gcloud`) (Primary Path)

Full commands at [references/gcloud-usage.md](references/gcloud-usage.md) (Log Sinks → Create).

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud logging sinks create NAME "bigquery.googleapis.com/.../datasets/ID"` | Sink to BigQuery |
| 2 | `... "storage.googleapis.com/ID"` | Sink to Cloud Storage |
| 3 | `... "pubsub.googleapis.com/.../topics/ID"` | Sink to Pub/Sub |

All use `--log-filter="{{user.filter_query}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"`.

#### Execution — Python SDK (Primary Fallback)

Full script at [assets/code-snippets/create_sink.py](assets/code-snippets/create_sink.py)

Key steps:
1. Create client: `logging.Client(project=...)`
2. Create sink config: `client.sink(name, filter_=..., destination=...)`
3. Create: `sink.create()`

#### Post-execution Validation

Grant the writer identity write access to the destination:

`WRITER_IDENTITY=$(gcloud logging sinks describe "{{user.sink_name}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" | jq -r '.writerIdentity')` — then grant `WRITER_IDENTITY` write access to the destination.

#### Failure Recovery

| Error Code | Max retries | Agent Action | UX Feedback |
|------------|-------------|--------------|-------------|
| INVALID_ARGUMENT / 400 | 1 | Fix destination format | `[ERROR] Invalid sink destination` |
| PERMISSION_DENIED / 403 | 0 | HALT | `[ERROR] SA lacks roles/logging.admin` |
| ALREADY_EXISTS / 409 | 0 | Ask rename | `[ERROR] Sink name already exists` |
| FAILED_PRECONDITION / 400 | 0 | HALT | `[ERROR] Destination not accessible — check IAM` |

---

### Operation: Delete Log Sink

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit user confirmation: deletion of sink `{{user.sink_name}}` stops all log exports
- **MUST** show current destination and filter before confirmation

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Sink exists | Describe | Exit 0 | HALT — already deleted |
| User confirmation | Show sink details; ask for name | Exact match | HALT — abort |

#### Execution — CLI (`gcloud`)

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud logging sinks describe NAME` | Show `name, destination, filter, writerIdentity` before delete |
| 2 | `gcloud logging sinks delete NAME` | Delete sink (stops export) |

Both use `--project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"` (full map at [references/gcloud-usage.md](references/gcloud-usage.md) Log Sinks → Delete).

---

### Operation: Create Log-Based Metric

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Metric name unique | `gcloud logging metrics describe "{{user.metric_name}}" --quiet` | NOT_FOUND | HALT — name in use |
| Filter valid | Validate filter expression syntax | Pass | Fix expression |

#### Execution — CLI (`gcloud`) (Primary Path)

Full commands at [references/gcloud-usage.md](references/gcloud-usage.md) (Log-Based Metrics → Create).

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud logging metrics create NAME --log-filter --description` | Counter metric |
| 2 | `... --label-extractor="response_code=jsonPayload.status" --bucket-values="0,100,...,500"` | Distribution metric |

All use `--project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"`.

#### Execution — Python SDK (Primary Fallback)

Full script at [assets/code-snippets/create_metric.py](assets/code-snippets/create_metric.py)

Key steps:
1. Create client: `logging.Client(project=...)`
2. Create metric config: `client.metric(name, filter_=..., description=...)`
3. Create: `metric.create()`

#### Post-execution Validation

`gcloud logging metrics describe "{{user.metric_name}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" | jq '{name, filter, description, createTime}'`

---

### Operation: Delete Log-Based Metric

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit user confirmation: deletion of metric `{{user.metric_name}}`

#### Execution — CLI (`gcloud`)

`gcloud logging metrics delete "{{user.metric_name}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"` (full map at [references/gcloud-usage.md](references/gcloud-usage.md) Log-Based Metrics → Delete).

---

### Operation: Create Log Exclusion

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Exclusion name unique | `gcloud logging exclusions describe "{{user.exclusion_name}}" --quiet` | NOT_FOUND | HALT — name in use |
| Filter valid | Validate filter syntax | Pass | Fix expression |

#### Execution — CLI (`gcloud`)

`gcloud logging exclusions create "{{user.exclusion_name}}" --log-filter="{{user.filter_query}}" --description="{{user.description}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"` (full map at [references/gcloud-usage.md](references/gcloud-usage.md) Log Exclusions → Create).

#### Post-execution Validation

`gcloud logging exclusions describe "{{user.exclusion_name}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" | jq '{name, filter, description, createTime}'`

---

### Operation: Delete Log Exclusion

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit user confirmation: deletion of exclusion `{{user.exclusion_name}}`

#### Execution — CLI (`gcloud`)

`gcloud logging exclusions delete "{{user.exclusion_name}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"` (full map at [references/gcloud-usage.md](references/gcloud-usage.md) Log Exclusions → Delete).

---

## Prerequisites

> **Self-Healing:** Installation flows include multi-path recovery (gcloud install → Go bootstrap → Python SDK fallback).

1. **Install gcloud CLI** (primary execution path):
   ```bash
   if ! command -v gcloud &> /dev/null; then
       curl https://sdk.cloud.google.com | bash 2>/dev/null \
       || (sudo apt-get update && sudo apt-get install -y google-cloud-sdk) \
       || (wget -q https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-x86_64.tar.gz \
           && tar -xf google-cloud-cli-*.tar.gz && ./google-cloud-sdk/install.sh --quiet)
       exec -l $SHELL
       gcloud init
   fi
   ```

2. **Bootstrap Go runtime** (for JIT SDK fallback):
   ```bash
   if ! command -v go &> /dev/null; then
       OS=$(uname -s | tr '[:upper:]' '[:lower:]')
       ARCH=$(uname -m); [ "$ARCH" = "x86_64" ] && ARCH="amd64"; [ "$ARCH" = "aarch64" ] && ARCH="arm64"
       mkdir -p /tmp/go-runtime
       curl -fsSL "https://go.dev/dl/go1.24.0.${OS}-${ARCH}.tar.gz" | tar -xz -C /tmp/go-runtime 2>/dev/null \
       || curl -fsSL "https://go.dev/dl/go1.24.0.linux-${ARCH}.tar.gz" | tar -xz -C /tmp/go-runtime
       if [ -f /tmp/go-runtime/go/bin/go ]; then
           export PATH="/tmp/go-runtime/go/bin:$PATH"
       else
           echo "Go download failed. Using Python SDK as fallback."
           pip install --quiet --user google-cloud-logging
       fi
   fi
   ```

3. **Configure Credentials**:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="{{env.GOOGLE_APPLICATION_CREDENTIALS}}"
   export CLOUDSDK_CORE_PROJECT="{{env.CLOUDSDK_CORE_PROJECT}}"
   gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS" 2>/dev/null \
   || gcloud auth login --quiet
   gcloud config set project "$CLOUDSDK_CORE_PROJECT"
   ```

4. **Verify Configuration**:
   ```bash
   gcloud config list
   gcloud auth application-default print-access-token --quiet &>/dev/null && echo "✅ Auth OK"
   ```

> **Security:** Never commit service account keys to version control. All credentials use `{{env.*}}` placeholders.

## Reference Directory

- [Core Concepts](references/core-concepts.md) — Architecture, quotas, regions
- [API & SDK Usage](references/api-sdk-usage.md) — REST API, Python SDK, operation map
- [gcloud Usage](references/gcloud-usage.md) — `gcloud logging` command map
- [Troubleshooting Guide](references/troubleshooting.md) — Error codes, diagnostics, recovery
- [Monitoring & Alerts](references/monitoring.md) — Cloud Monitoring metrics, dashboards, alerts
- [Integration](references/integration.md) — Go SDK bootstrap, env vars, credential rules
- [Idempotency Checklist](references/idempotency-checklist.md) — Retry-safe patterns
- [Well-Architected Assessment](references/well-architected-assessment.md) — Five-pillar assessment
- [Rubric — GCL](references/rubric.md) — Generator-Critic-Loop scoring rubric
- [Prompt Templates — GCL](references/prompt-templates.md) — GCL generator and critic templates

## Operational Best Practices

- **Least privilege:** Use `roles/logging.admin` for management; `roles/logging.viewer` for read-only
- **Availability:** Use multi-region (`global` or `eu`/`us`) log buckets for production
- **Cost:** Set appropriate retention periods; use exclusion filters to reduce log volume; monitor log ingestion costs
- **Security:** Use CMEK for sensitive log data; enable VPC Service Controls
- **Backup:** Sink critical logs to BigQuery or Cloud Storage for long-term retention
- **Naming:** Follow `{env}-{purpose}-logs` convention for bucket names

## Quality Gate (GCL)

> This skill implements the **Generator-Critic-Loop (GCL)** adversarial quality gate: an independent Critic scores each destructive operation against a quantified rubric (Correctness, Safety, Idempotency, Traceability, Spec Compliance, Factual Accuracy). Safety=0 → ABORT.

| Property | Value |
|----------|-------|
| Classification | **recommended** (bucket deletion present) |
| max_iter | 3 |
| Most-scrutinized operations | Delete Log Bucket, Delete Log Sink, Delete Log Metric |

- **Rubric**: [references/rubric.md](references/rubric.md) — 5 core dimensions + 3 GCP extensions
- **Prompt Templates**: [references/prompt-templates.md](references/prompt-templates.md) — Generator + Critic templates

> Token Efficiency 规则详见根目录 AGENTS.md §9（TE-1~TE-8，禁止跨文件重复 — TE-6）。

## See Also

- **Monitoring**: delegate log-based alerting to `gcp-monitoring-ops`
- **IAM**: delegate service-account/permission tasks to `gcp-iam-ops`
- **BigQuery**: delegate dataset management (log export destination) to `gcp-bigquery-ops`
- **GCL Runner**: cross-skill Generator-Critic-Loop execution runner

## AIOps 自愈 (Self-Healing)

日志管线（ingestion / sink / log router）故障需自愈能力。完整 runbook 见 [references/advanced/aiops-log-pipeline-anomaly.md](references/advanced/aiops-log-pipeline-anomaly.md)，覆盖：

- **ingestion 延迟/丢弃检测** — 仅诊断，不自动变更（根因多为上游 quota / 项目挂起，需分类并委派）
- **log sink / log router 配置漂移自愈** — dry-run → 门禁 → 幂等 re-create sink → 校验
- **自愈动作约束** — 每个变更动作 dry-run 优先、幂等、带门禁；破坏性动作（删 bucket/sink、改 `_Default`/`_Required`、跨项目）标 `HALT`，绝不自动变更
- **跨 skill 触发** — 异常根因/修复跨边界时委派（BigQuery/Pub/Sub/GCS 目的地、Monitoring alert、Billing、Security Command Center）

错误分类遵循 [docs/error-taxonomy.md](../docs/error-taxonomy.md)，爆炸半径门禁遵循 [docs/cross-skill-blast-radius.md](../docs/cross-skill-blast-radius.md)。凭证遮蔽见 AGENTS.md §0.1。