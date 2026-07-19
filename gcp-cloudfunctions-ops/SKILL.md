---
name: gcp-cloudfunctions-ops
description: >-
  Use when the user needs to deploy, configure, troubleshoot, or monitor Google
  Cloud Functions (2nd gen) — function lifecycle, HTTP and event triggers,
  scaling, secrets mounting, and diagnostics. User mentions Cloud Functions,
  serverless function, function deploy, trigger, Eventarc, or describes
  function deployment scenarios ("deploy a function", "HTTP endpoint", "cloud
  event handler", "function logs") even without naming the product directly.
  Not for Cloud Run, GKE, Cloud Build, or other compute products that have
  their own ops skills.
license: MIT
compatibility: >-
  Official Google Cloud CLI (`gcloud`, Python-based SDK), Go 1.21+ runtime
  (for JIT SDK fallback), valid service account credentials with Cloud Functions
  Admin or Developer IAM role, network access to Google Cloud endpoints.
metadata:
  author: gcp-skills
  version: "1.0.0"
  last_updated: "2026-06-08"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  go_version_minimum: "1.21"
  go_version_jit: "1.24+"
  api_profile: "https://cloudfunctions.googleapis.com/$discovery/rest?version=v2beta"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    gcloud functions --help confirms subcommands: deploy, describe, delete, list,
    call, logs, gen1-to-gen2. See https://cloud.google.com/sdk/gcloud/reference/functions
  environment:
    - GOOGLE_APPLICATION_CREDENTIALS
    - CLOUDSDK_CORE_PROJECT
    - CLOUDSDK_AUTH_ACCESS_TOKEN
---

> This skill follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Google Cloud Cloud Functions Operations Skill

## Overview

Cloud Functions (2nd gen) provides event-driven, serverless function execution backed by Cloud Run. This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **dual-path execution** (Python SDK + `gcloud` CLI), response validation, and failure recovery.

### CLI Applicability

- **`cli_applicability: dual-path`**: `gcloud` fully supports Cloud Functions (gen1 + gen2). Ship both `references/gcloud-usage.md` and document SDK + `gcloud` steps for every operation. Coverage gaps listed in `references/gcloud-usage.md`.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use conditions with precise triggers and delegation rules |
| 2 | **Structured I/O** | Placeholder conventions (`{{env.*}}`, `{{user.*}}`, `{{output.*}}`) with type and source documented |
| 3 | **Explicit Actionable Steps** | Every operation: Pre-flight → Execute → Validate → Recover, with numbered imperative steps |
| 4 | **Complete Failure Strategies** | Error taxonomy table with ≥ 10 product-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | One product (Cloud Functions), one primary resource model (Function); cross-product delegation to other skills |

### Google Cloud Architecture Framework Integration

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **Security** | IAM authentication, VPC connector, secret mounting, ingress settings, service identity | `references/well-architected-assessment.md` §2.1 |
| **Stability** | Retry configuration, dead letter queues, error handling, multi-region considerations | `references/well-architected-assessment.md` §2.2 |
| **Cost** | Per-invocation pricing, memory/CPU right-sizing, idle scaling (min-instances=0) | `references/well-architected-assessment.md` §2.3 |
| **Efficiency** | CI/CD integration, buildpack optimization, source size management | `references/well-architected-assessment.md` §2.4 |
| **Performance** | Cold start mitigation, concurrency tuning, memory allocation, execution time | `references/well-architected-assessment.md` §2.5 |

See [references/well-architected-assessment.md](references/well-architected-assessment.md) for the complete specification.

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "Google Cloud Functions" OR "Cloud Functions" OR "serverless function" OR "function deploy"
- Task involves CRUD or lifecycle operations on **Cloud Functions** (deploy, describe, update, delete, list, call, logs)
- Task involves **HTTP triggers** or **event triggers** (Eventarc, Cloud Storage, Pub/Sub, Firestore, Firebase)
- Task involves **scaling configuration** (memory, CPU, min/max instances, concurrency, timeout)
- Task involves **secrets mounting** from Secret Manager
- Task involves **VPC connector** configuration for Cloud Functions
- Task involves **gen1 to gen2 migration**
- Task keywords: Cloud Functions, function deploy, trigger-http, trigger-event, Eventarc, gen2, serverless function, cloudfunctions.googleapis.com
- User asks to deploy, configure, troubleshoot, or monitor Cloud Functions **via gcloud, SDK, API, or automation**

### SHOULD NOT Use This Skill When

- Task is purely billing / cost management → delegate to: `gcp-billing-ops`
- Task is IAM / permission model only → delegate to: `gcp-iam-ops`
- Task is about **Cloud Run** → delegate to: `gcp-cloudrun-ops`
- Task is about **GKE** → delegate to: `gcp-gke-ops`
- Task is about **Cloud Build** (container builds) → delegate to: `gcp-cloudbuild-ops`
- Task is about **Artifact Registry** (container images) → delegate to: `gcp-artifactregistry-ops`
- Task is about **Cloud Scheduler** (cron triggers) → delegate to: `gcp-scheduler-ops`
- Task is about **Eventarc** (event routing) → delegate to: `gcp-eventarc-ops`
- Task is about **Cloud Monitoring** (dashboards, alerts) → delegate to: `gcp-monitoring-ops`
- Task is about **Secret Manager** (create/manage secrets) → delegate to: `gcp-secretmanager-ops`
- User insists on **console-only** flows with no API → state limitation; do not invent undocumented gcloud steps

### Delegation Rules

- Source code repository (Cloud Source Repositories, GitHub connections): Delegate to `gcp-sourcerepo-ops` when present
- Container registry for packaged functions: Delegate to `gcp-artifactregistry-ops` when present
- EventArc triggers / Eventarc routing: Delegate to `gcp-eventarc-ops` when present
- Cloud Scheduler triggers: Delegate to `gcp-scheduler-ops` when present
- VPC connector setup: Delegate to `gcp-vpc-ops`
- Secrets from Secret Manager: Delegate to `gcp-secretmanager-ops`
- Cloud Build for CI/CD: Delegate to `gcp-cloudbuild-ops`
- Monitoring/Alerts: Delegate to `gcp-monitoring-ops`
- Cloud Run migration (gen2 functions are backed by Cloud Run): Delegate to `gcp-cloudrun-ops`

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.GOOGLE_APPLICATION_CREDENTIALS}}` | Path to SA key JSON | NEVER ask the user; fail if unset |
| `{{env.CLOUDSDK_CORE_PROJECT}}` | GCP project ID | NEVER ask the user; fail if unset |
| `{{env.CLOUDSDK_AUTH_ACCESS_TOKEN}}` | Temporary access token | NEVER ask the user; fail if needs refresh |
| `{{user.function_name}}` | Cloud Function name | Ask once; reuse |
| `{{user.runtime}}` | Runtime (python312, nodejs20, go122, java21, dotnet8, ruby33) | Ask once; reuse |
| `{{user.region}}` | Region (e.g., us-central1, europe-west1) | Ask once; reuse; default us-central1 |
| `{{user.entry_point}}` | Function entry point name | Ask once; reuse |
| `{{user.source_dir}}` | Source code directory | Ask once; reuse |
| `{{user.trigger_type}}` | http or event | Ask once; default http |
| `{{user.event_filters}}` | Event filters (type=...,bucket=...,topic=...) | Ask once (for event triggers) |
| `{{user.memory}}` | Memory allocation (128Mi to 32Gi, gen2) | Ask once; default 256Mi |
| `{{user.cpu}}` | CPU allocation (default, 1, 2, 4, etc) | Ask once; default derived from memory |
| `{{user.timeout}}` | Timeout in seconds (max 3600 for gen2) | Ask once; default 60 |
| `{{user.max_instances}}` | Max instances (default 100 HTTP, 3000 events) | Ask once |
| `{{user.min_instances}}` | Min instances (default 0) | Ask once |
| `{{user.concurrency}}` | Concurrency (default 1 for gen2) | Ask once |
| `{{user.env_vars}}` | Environment variables (KEY=VALUE,...) | Ask once |
| `{{user.secrets}}` | Secrets (KEY=SECRET:VERSION,...) | Ask once |
| `{{user.service_account}}` | Service account email | Ask once; default compute SA |
| `{{user.ingress}}` | Ingress settings (all, internal-only, internal-and-gclb) | Ask once; default all |
| `{{user.vpc_connector}}` | VPC Serverless Connector name | Ask once |
| `{{user.gen}}` | Function generation: 1 or 2 (default 2) | Ask once; default 2 |
| `{{user.no_allow_unauthenticated}}` | Require authentication (true/false) | Ask once; default false |
| `{{output.function_url}}` | Function invocation URL | Parse from API response |
| `{{output.function_state}}` | Function state (ACTIVE/FAILED/DEPLOYING/DELETING) | Parse from API response |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning (Credential Masking — MANDATORY):** **NEVER** log, print, or expose service account key content, `GOOGLE_APPLICATION_CREDENTIALS` path content, or any credential field value in console output, debug messages, error messages, or logs.

## API and Response Conventions (Agent-Readable)

- **REST API is canonical**: Cloud Functions v2beta API (`cloudfunctions.googleapis.com`). JSON paths verified against official reference.
- **Errors:** Map SDK/gRPC/HTTP errors to canonical gRPC status codes and messages.
- **Timestamps:** RFC 3339 with timezone.
- **Long-running operations:** Deploy and delete return LROs; poll via operations API.

### Key JSON Paths

| Operation | JSON Path |
|-----------|-----------|
| Deploy | `$.name`, `$.serviceConfig.uri`, `$.serviceConfig.status`, `$.eventTrigger` |
| Describe | `$.state`, `$.serviceConfig.uri`, `$.serviceConfig.status`, `$.serviceConfig.memoryMiB`, `$.serviceConfig.timeout`, `$.updateTime` |
| List | `$.functions[].name`, `$.functions[].state`, `$.functions[].serviceConfig.uri` |
| Delete | `$.metadata.target`, `$.metadata.verb` (LRO) |
| Call | `$.responseBody` (base64 encoded), `$.status` |
| Logs | `$.entries[].textPayload`, `$.entries[].timestamp`, `$.entries[].severity` |

### Function States

| State | Meaning |
|-------|---------|
| ACTIVE | Function is deployed and ready |
| FAILED | Deployment failed |
| DEPLOYING | Function is being deployed |
| DELETING | Function is being deleted |
| UNKNOWN | State unknown (transient) |

### Expected State Transitions

| Operation | Initial State | Target State | Max Wait |
|-----------|---------------|--------------|----------|
| Deploy | — | ACTIVE | 600s |
| Update | ACTIVE | ACTIVE | 600s |
| Delete | any stable state | absent | 300s |

## Quick Start

### What This Skill Does

This skill enables you to deploy, configure, troubleshoot, and monitor Cloud Functions (2nd gen) on Google Cloud using the `gcloud` CLI (primary) or JIT Go SDK (fallback).

### Prerequisites

- [ ] `gcloud` CLI installed (or Go runtime for JIT fallback)
- [ ] Service account key configured: `GOOGLE_APPLICATION_CREDENTIALS`
- [ ] Project set: `gcloud config set project <project-id>` or `CLOUDSDK_CORE_PROJECT`

### Verify Setup

```bash
gcloud config get-value project
gcloud auth application-default print-access-token --quiet &>/dev/null && echo "Auth OK"
```

### Your First Command

```bash
gcloud functions list --gen2 --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"
```

### Next Steps

- [Core Concepts](references/core-concepts.md) — Understand Cloud Functions architecture
- [Common Operations](#execution-flows) — Deploy, manage, and delete functions
- [Troubleshooting](references/troubleshooting.md) — Fix common issues

## Capabilities at a Glance

| Operation | Description | Risk Level |
|-----------|-------------|------------|
| Deploy HTTP Function | Create/update function with HTTP trigger | Low |
| Deploy Event-Triggered Function | Create/update function with Eventarc trigger | Low |
| Describe Function | View function details | None |
| List Functions | View all functions in project/region | None |
| Update Function | Modify function configuration | Low |
| Delete Function | Remove a function | **High** — irreversible |
| Invoke Function (call) | Test HTTP function invocation | None |
| Read Logs | View function execution logs | None |
| List Gen1 Functions | View legacy 1st gen functions | None |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-08 | Function lifecycle (deploy/describe/update/delete/list/call/logs), HTTP and event triggers, gen1 vs gen2, scaling configuration, secrets mounting, VPC connector; dual-path gcloud+SDK; GCL quality gate |

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (gcloud and/or SDK/API) → Validate → Recover**. Do not skip phases.

### Operation: Deploy HTTP Function

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| gcloud CLI installed | `gcloud version` | Exit code 0 | Document gcloud install |
| Credentials configured | `gcloud auth describe` | Active account | HALT; user authenticates |
| Project set | `gcloud config get-value project` or env | Valid project ID | HALT; user sets project |
| Cloud Functions API enabled | `gcloud services list --filter="cloudfunctions.googleapis.com"` | cloudfunctions.googleapis.com listed | `gcloud services enable cloudfunctions.googleapis.com` |
| Build API enabled | `gcloud services list --filter="cloudbuild.googleapis.com"` | cloudbuild.googleapis.com listed | `gcloud services enable cloudbuild.googleapis.com` |
| Function name unique | `gcloud functions describe NAME --gen2` | NOT_FOUND | Rename or use existing |
| Source directory exists | `test -d {{user.source_dir}}` | Directory exists | HALT; verify source path |
| Runtime supported | Check `{{user.runtime}}` against supported list | Valid runtime | HALT; use supported runtime |

#### Execution — CLI (`gcloud`) / Python SDK

Full command invocations and SDK examples are in `references/gcloud-usage.md` (Command Map, Common Recipes) and `references/api-sdk-usage.md` (Python/Go SDK). Summary:

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud functions deploy NAME --gen2 --trigger-http` | Create/update HTTP function |
| 2 | `--runtime/--entry-point/--source/--region/--project` | Core identity flags (see Variable Convention) |
| 3 | `--memory/--timeout/--max-instances/--min-instances/--concurrency` | Scaling config |
| 4 | `--set-env-vars/--set-secrets/--ingress-settings` | Env, secrets, ingress |
| 5 | conditional `--vpc-connector/--service-account/--no-allow-unauthenticated` | Optional flags (only when set) |
| 6 | `--format=json` | Machine-parseable output |

> **SDK fallback**: `pip install --quiet --user google-cloud-functions`, then `FunctionServiceClient().create_function(...)`. See `references/api-sdk-usage.md` §Python SDK.

#### Post-execution Validation

```bash
gcloud functions describe "{{user.function_name}}" \
  --gen2 \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format=json | jq '{
    name: .name,
    state: .state,
    url: .serviceConfig.uri,
    memory: .serviceConfig.availableMemory,
    timeout: .serviceConfig.timeoutSeconds,
    updateTime: .updateTime
  }'
```

Validate: `.state == "ACTIVE"`. Report `{{output.function_url}}` from `.serviceConfig.uri`.

#### Failure Recovery

| Error Code | Meaning | Agent Action |
|------------|---------|--------------|
| invalidArgument/400 | Invalid configuration | Fix params per deployment flags; retry once |
| permissionDenied/403 | Insufficient IAM | HALT — grant roles/cloudfunctions.admin |
| alreadyExists/409 | Name taken | Use update flow instead |
| sourceUploadError/400 | Source upload failed | HALT — verify source dir and perms |
| buildFailed/400 | Buildpack build failed | HALT — check source code + runtime |
| deadlineExceeded/504 | Deployment timeout | Retry; check network + build time |
| resourceExhausted/429 | Quota exceeded | HALT — increase quota or reduce resources |
| unavailable/503 | Temporarily unavailable | Retry 3x with exponential backoff |

---

### Operation: Deploy Event-Triggered Function

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| gcloud CLI installed | `gcloud version` | Exit code 0 | Document gcloud install |
| Credentials configured | `gcloud auth describe` | Active account | HALT; user authenticates |
| Project set | `gcloud config get-value project` or env | Valid project ID | HALT; user sets project |
| Cloud Functions API enabled | `gcloud services list --filter="cloudfunctions.googleapis.com"` | Listed | `gcloud services enable cloudfunctions.googleapis.com` |
| Build API enabled | `gcloud services list --filter="cloudbuild.googleapis.com"` | Listed | `gcloud services enable cloudbuild.googleapis.com` |
| Event source exists | Check bucket/topic/resource | Resource exists | HALT — create event source first |
| Eventarc API enabled | `gcloud services list --filter="eventarc.googleapis.com"` | Listed (for gen2) | `gcloud services enable eventarc.googleapis.com` |
| Function name unique | `gcloud functions describe NAME --gen2` | NOT_FOUND | Rename or use existing |
| Source directory exists | `test -d {{user.source_dir}}` | Directory exists | HALT; verify source path |

#### Execution — CLI (`gcloud`)

Full command in `references/gcloud-usage.md` (Command Map: "Deploy event function", Common Recipes: Pub/Sub, Cloud Storage). Summary:

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud functions deploy NAME --gen2 --trigger-event-filters=FILTERS` | Create event-triggered function |
| 2 | `--runtime/--entry-point/--source/--region/--project` | Core identity flags |
| 3 | `--max-instances` (default 3000 events) / `--min-instances` / `--service-account` | Scaling + identity |
| 4 | `--set-env-vars/--set-secrets` | Env + secrets |
| 5 | `--format=json` | Machine-parseable output |

Common event filter syntax (passed to `--trigger-event-filters`):
- Cloud Storage: `type=google.cloud.storage.object.v1.final,bucket=my-bucket`
- Pub/Sub: `type=google.cloud.pubsub.topic.v1.messagePublished,topic=my-topic`
- Firestore: `type=google.cloud.firestore.document.v1.written,database=(default),namespace=(default),document=collection/{docId}`

#### Post-execution Validation

```bash
gcloud functions describe "{{user.function_name}}" \
  --gen2 \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format=json | jq '{
    name: .name,
    state: .state,
    eventTrigger: .eventTrigger,
    eventFilters: .eventTrigger.eventFilters,
    updateTime: .updateTime
  }'
```

Validate: `.state == "ACTIVE"` and `.eventTrigger` is populated.

#### Failure Recovery

| Error Code | Meaning | Agent Action |
|------------|---------|--------------|
| invalidArgument/400 | Invalid event filter | Fix filter syntax; check event type |
| permissionDenied/403 | Missing eventarc role | HALT — grant roles/eventarc.eventReceiver |
| notFound/404 | Event source missing | HALT — create bucket/topic first |
| buildFailed/400 | Build failed | HALT — check source code + runtime |
| deadlineExceeded/504 | Deployment timeout | Retry; check network + build time |

---

### Operation: Describe Function

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Function exists | `gcloud functions describe NAME --gen2` | Found | HALT — function missing |

#### Execution — CLI (`gcloud`)

Full command + jq extraction in `references/gcloud-usage.md` (Command Map: "Describe function", JQ Extraction Patterns: Deploy/List Validation). Summary:

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud functions describe NAME --gen2` | Fetch full function config |
| 2 | `--region/--project/--format=json` | Scope + machine output |

#### Post-execution Validation

Report: function name, state, URL, trigger type, runtime, memory, timeout, max/min instances, concurrency, service account, environment variables, update time. (jq extraction pattern: `references/gcloud-usage.md` §JQ Extraction Patterns.)

---

### Operation: List Functions

#### Execution — CLI (`gcloud`)

Full command + jq extraction in `references/gcloud-usage.md` (Command Map: "List functions (gen2)", JQ Extraction Patterns: List Validation). Summary:

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud functions list --gen2` | List all gen2 functions |
| 2 | `--region/--project/--format=json` | Scope + machine output |

#### Post-execution Validation

Report: function names, states, URLs, trigger types, runtimes, creation times. (jq extraction pattern: `references/gcloud-usage.md` §JQ Extraction Patterns.)

---

### Operation: Update Function

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Function exists | `gcloud functions describe NAME --gen2` | Found | HALT — function missing |
| Function in ACTIVE state | `.state` | ACTIVE | HALT — wait for ACTIVE |
| Source directory exists | `test -d {{user.source_dir}}` | Directory exists | HALT; verify source path |

#### Execution — CLI (`gcloud`)

Full command in `references/gcloud-usage.md` (Command Map: "Update function", Common Recipes: "Update Scaling Configuration"). Summary:

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud functions deploy NAME --gen2` | Acts as update when function exists |
| 2 | `--runtime/--entry-point/--source/--region/--project` | Core identity flags |
| 3 | `--memory/--timeout/--max-instances/--min-instances/--concurrency` | Scaling config |
| 4 | `--update-env-vars/--set-secrets` | Env (update merges) + secrets |
| 5 | `--format=json` | Machine-parseable output |

> **Note:** For gen2, `gcloud functions deploy` acts as an update when the function already exists. Use `--update-env-vars` to modify env vars without replacing all of them.

#### Post-execution Validation

Validate `.state == "ACTIVE"` via `gcloud functions describe NAME --gen2 --format=json` (jq pattern: `references/gcloud-usage.md` §JQ Extraction Patterns).

#### Failure Recovery

| Error Code | Meaning | Agent Action |
|------------|---------|--------------|
| notFound/404 | Function missing | Use deploy flow instead |
| failedPrecondition/412 | Invalid state | HALT — wait for ACTIVE |
| permissionDenied/403 | Insufficient IAM | HALT — grant roles/cloudfunctions.admin |
| buildFailed/400 | Build failed | HALT — check source code |

---

### Operation: Delete Function

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit confirmation: irreversible delete of `{{user.function_name}}`.
- **MUST NOT** proceed without clear user assent.
- **SUGGEST** traffic drain: verify no active consumers before delete.

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Function exists | `gcloud functions describe NAME --gen2` | Found | HALT — nothing to delete |
| User confirms | User types exact function name | Exact match | HALT — name mismatch |

#### Execution — CLI (`gcloud`)

Full command in `references/gcloud-usage.md` (Command Map: "Delete function", Common Recipes: "Delete Function (Non-Interactive)"). Summary:

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud functions delete NAME --gen2` | Irreversible delete |
| 2 | `--region/--project/--format=json` | Scope + machine output |

#### Post-execution Validation

Confirm absence: `gcloud functions describe NAME --gen2 --format=json 2>&1 | grep -q "NOT_FOUND" && echo "Deleted successfully" || echo "Still exists"`.

#### Failure Recovery

| Error Code | Meaning | Agent Action |
|------------|---------|--------------|
| notFound/404 | Already deleted | Success |
| permissionDenied/403 | Insufficient IAM | HALT |
| aborted/409 | Concurrent modification | Retry 3x with backoff |

---

### Operation: Invoke Function (call)

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Function exists | Describe function | Found | HALT — function missing |
| Function state ACTIVE | `.state` | ACTIVE | HALT — function not ready |
| Function has HTTP trigger | Check trigger type | HTTP trigger | HALT — cannot call event-triggered function |
| Invoker permission | IAM check or unauthenticated | Allowed | HALT — grant roles/cloudfunctions.invoker |

#### Execution — CLI (`gcloud`)

Full command in `references/gcloud-usage.md` (Command Map: "Invoke function"). Summary:

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud functions call NAME --gen2 --data='JSON'` | Invoke HTTP function |
| 2 | `--region/--project/--format=json` | Scope + machine output |

For authenticated functions, call the function URL with an identity token (never log the token — see Credential Masking):
```bash
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  "$(gcloud functions describe NAME --gen2 --region=REGION --project=PROJECT --format=json | jq -r '.serviceConfig.uri')" \
  -H "Content-Type: application/json" -d '{"key":"value"}'
```

#### Post-execution Validation

Report: response body, HTTP status code. Validate via `gcloud functions call NAME --gen2 --data='{"test": true}' --format=json | jq '{status: .status, body: .responseBody}'`.

#### Failure Recovery

| Error Code | Meaning | Agent Action |
|------------|---------|--------------|
| notFound/404 | Function missing | HALT — verify name |
| permissionDenied/403 | No invoker permission | HALT — grant IAM role |
| functionFailed/400 | Runtime error | Check logs for function error |
| deadlineExceeded/504 | Function timeout | Increase timeout or optimize code |

---

### Operation: Read Logs

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Function exists | Describe function | Found | HALT — function missing |
| Logging API enabled | `gcloud services list --filter="logging.googleapis.com"` | Listed | `gcloud services enable logging.googleapis.com` |

#### Execution — CLI (`gcloud`)

Full commands in `references/gcloud-usage.md` (Command Map: "Read logs", "Read error logs"). Summary:

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud functions logs read NAME --gen2 --limit=50` | Recent execution logs |
| 2 | `--min-log-level=error` | Error-only logs |
| 3 | `--start-time/--end-time` | Time-filtered logs |
| 4 | `--region/--project/--format=json` | Scope + machine output |

#### Post-execution Validation

Report: log entries with timestamps, severity, and text payload. jq extraction pattern: `references/gcloud-usage.md` §JQ Extraction Patterns (Logs Validation).

---

### Operation: List Gen1 Functions

#### Execution — CLI (`gcloud`)

Full command in `references/gcloud-usage.md` (Command Map: "List functions (gen1)"). Summary:

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud functions list --gen1` | List legacy 1st gen functions |
| 2 | `--region/--project/--format=json` | Scope + machine output |

#### Post-execution Validation

Report: function names, states, URLs, runtimes. Note: gen1 functions use a different resource model and lack many gen2 features. jq extraction pattern: `references/gcloud-usage.md` §JQ Extraction Patterns.

> **Migration note:** To migrate gen1 to gen2, use `gcloud functions gen1-to-gen2` or redeploy manually with `--gen2`. Gen2 offers better scaling, longer timeouts, VPC connector, and more runtimes.

## References

| Document | Description |
|----------|-------------|
| [core-concepts.md](references/core-concepts.md) | Architecture, runtimes, quotas, gen1 vs gen2 |
| [api-sdk-usage.md](references/api-sdk-usage.md) | REST API, Python SDK, Go SDK, operation map |
| [gcloud-usage.md](references/gcloud-usage.md) | `gcloud functions` command map, jq extracts, coverage gaps |
| [troubleshooting.md](references/troubleshooting.md) | 13+ error codes, diagnostics, recovery |
| [monitoring.md](references/monitoring.md) | Metrics, dashboards, alerts |
| [integration.md](references/integration.md) | Go SDK, environment setup, credential rules |
| [well-architected-assessment.md](references/well-architected-assessment.md) | 5-pillar assessment |
| [rubric.md](references/rubric.md) | GCL scoring rubric |
| [prompt-templates.md](references/prompt-templates.md) | GCL templates |

## GCL Quality Gate

**Classification**: recommended | **max_iter**: 3 | **Most-scrutinized**: Delete Function, Deploy (can cause downtime if misconfigured)

> Token Efficiency 规则详见根目录 AGENTS.md §9（TE-1~TE-8，禁止跨文件重复 — TE-6）。

## Operational Best Practices

- **Least privilege:** IAM roles scoped to required permissions only (roles/cloudfunctions.admin for full access, roles/cloudfunctions.developer for deploy, roles/cloudfunctions.viewer for read-only, roles/cloudfunctions.invoker for invocation).
- **Availability:** Use min-instances > 0 for critical functions; configure retries and dead letter queues for event-triggered functions.
- **Cost:** Set min-instances=0 for idle cost savings; right-size memory/CPU; tune concurrency; prefer gen2 over gen1.
- **Security:** Mount secrets via Secret Manager, use VPC connector for private access, restrict ingress to internal-only when possible, use `--no-allow-unauthenticated` for HTTP functions.

## See Also

Cross-product delegation targets (IAM, VPC, Secret Manager, Cloud Run, Monitoring, Eventarc, Scheduler, Cloud Build) are listed in [Delegation Rules](#delegation-rules) above. Full command references and recovery detail live in `references/` (see [References](#references)).

## AIOps 自愈 (Self-Healing)

> Cloud Functions 异常检测与自愈锚点（冷启动超时、并发超限、部署/回滚失败）见 [references/advanced/aiops-cloudfunctions-anomaly.md](references/advanced/aiops-cloudfunctions-anomaly.md)。所有自愈动作均带 **dry-run + 幂等 + 人工复核门禁**，破坏性操作标 **HALT**，绝不自动执行。