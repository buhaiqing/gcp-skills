---
name: gcp-cloudrun-ops
description: >-
  Use when the user needs to deploy, configure, troubleshoot, or monitor Google
  Cloud Run (fully managed) — service lifecycle, revision management, traffic
  splitting, secrets mounting, custom domains, scaling, and IAM. User mentions
  Cloud Run, serverless container, service deploy, revision, traffic split, or
  describes container deployment scenarios ("deploy a container", "scale
  serverless", "cold start", "split traffic between revisions") even without
  naming the product directly. Not for Cloud Functions, GKE, Cloud Build,
  Container Registry, or other compute/container products that have their own
  ops skills.
license: MIT
compatibility: >-
  Official Google Cloud CLI (`gcloud`, Python-based SDK), Go 1.21+ runtime
  (for JIT SDK fallback), valid service account credentials with Cloud Run Admin
  or Cloud Run Viewer IAM role, network access to Google Cloud endpoints.
metadata:
  author: gcp-skills
  version: "1.0.0"
  last_updated: "2026-06-07"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  go_version_minimum: "1.21"
  go_version_jit: "1.24+"
  api_profile: "https://run.googleapis.com/$discovery/rest?version=v1"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    gcloud run --help confirms subcommands: services, revisions, configurations,
    transports. See https://cloud.google.com/sdk/gcloud/reference/run
  environment:
    - GOOGLE_APPLICATION_CREDENTIALS
    - CLOUDSDK_CORE_PROJECT
    - CLOUDSDK_AUTH_ACCESS_TOKEN
---

> This skill follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Google Cloud Cloud Run Operations Skill

## Overview

Cloud Run (fully managed) provides serverless execution of stateless container images. This skill is an **operational runbook** with explicit scope, credential rules, pre-flight checks, **dual-path execution** (SDK + `gcloud` CLI), response validation, and failure recovery.

> **UX Compliance:** Follows the [User Experience Specification](../gcp-skill-generator/references/user-experience-spec.md).

### CLI Applicability

- **`cli_applicability: dual-path`**: `gcloud` fully supports Cloud Run. Ship both `references/gcloud-usage.md` and document SDK + `gcloud` steps for every operation. Coverage gaps listed in `references/gcloud-usage.md`.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use conditions with precise triggers and delegation rules |
| 2 | **Structured I/O** | Placeholder conventions (`{{env.*}}`, `{{user.*}}`, `{{output.*}}`) with type and source documented |
| 3 | **Explicit Actionable Steps** | Every operation: Pre-flight → Execute → Validate → Recover, with numbered imperative steps |
| 4 | **Complete Failure Strategies** | Error taxonomy table with ≥ 10 product-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | One product (Cloud Run), one primary resource model (Service); cross-product delegation to other skills |

### Google Cloud Architecture Framework Integration

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **Security** | IAM authentication, VPC connector, secret mounting, service identity, CMEK | `references/well-architected-assessment.md` §2.1 |
| **Stability** | Multi-region deployment, traffic splitting, revision rollback, min instances | `references/well-architected-assessment.md` §2.2 |
| **Cost** | Per-request pricing, idle scaling (min-instances=0), CPU/memory right-sizing | `references/well-architected-assessment.md` §2.3 |
| **Efficiency** | CI/CD integration with Cloud Build, container image optimization, concurrency tuning | `references/well-architected-assessment.md` §2.4 |
| **Performance** | Cold start mitigation, concurrency tuning, CPU/memory allocation, health checks | `references/well-architected-assessment.md` §2.5 |

See [references/well-architected-assessment.md](references/well-architected-assessment.md) for the complete specification.

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "Google Cloud Run" OR "Cloud Run" OR "serverless container"
- Task involves CRUD or lifecycle operations on **Cloud Run Services** (create, deploy, describe, update, delete, list)
- Task involves **revision management** (list revisions, describe revision, rollback)
- Task involves **traffic splitting** between revisions
- Task involves **secrets mounting** from Secret Manager
- Task involves **VPC connector** configuration for Cloud Run
- Task involves **custom domains** or health checks
- Task keywords: Cloud Run, service deploy, revision, traffic split, cold start, serverless container, concurrency, min-instances, max-instances, invoker, run.googleapis.com
- User asks to deploy, configure, troubleshoot, or monitor Cloud Run **via gcloud, SDK, API, or automation**

### SHOULD NOT Use This Skill When

- Task is purely billing / cost management → delegate to: `gcp-billing-ops`
- Task is IAM / permission model only → delegate to: `gcp-iam-ops`
- Task is about **GKE** → delegate to: `gcp-gke-ops`
- Task is about **Cloud Functions** → delegate to: `gcp-cloudfunctions-ops`
- Task is about **Cloud Build** (container builds) → delegate to: `gcp-cloudbuild-ops`
- Task is about **Artifact Registry** (container images) → delegate to: `gcp-artifactregistry-ops`
- Task is about **Cloud Scheduler** (cron triggers) → delegate to: `gcp-scheduler-ops`
- Task is about **Cloud Load Balancing** with Cloud Run → delegate to: `gcp-lb-ops`
- Task is about **Cloud Monitoring** (dashboards, alerts) → delegate to: `gcp-monitoring-ops`
- Task is about **Secret Manager** (create/manage secrets) → delegate to: `gcp-secretmanager-ops`
- User insists on **console-only** flows with no API → state limitation; do not invent undocumented gcloud steps

### Delegation Rules

- Container registry (Artifact Registry, Container Registry): Delegate to `gcp-artifactregistry-ops` when present
- VPC connector setup: Delegate to `gcp-vpc-ops`
- Load balancer with Cloud Run: Delegate to `gcp-lb-ops`
- Cloud Scheduler triggers: Delegate to `gcp-scheduler-ops` when present
- Cloud Build for container builds: Delegate to `gcp-cloudbuild-ops`
- Monitoring/Alerts: Delegate to `gcp-monitoring-ops`
- Secrets from Secret Manager: Delegate to `gcp-secretmanager-ops` (reference for setup)

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.GOOGLE_APPLICATION_CREDENTIALS}}` | Path to SA key JSON | NEVER ask the user; fail if unset |
| `{{env.CLOUDSDK_CORE_PROJECT}}` | GCP project ID | NEVER ask the user; fail if unset |
| `{{env.CLOUDSDK_AUTH_ACCESS_TOKEN}}` | Temporary access token | NEVER ask the user; fail if needs refresh |
| `{{user.service_name}}` | Cloud Run service name | Ask once; reuse |
| `{{user.image}}` | Container image URL (gcr.io, docker.io, etc) | Ask once; reuse |
| `{{user.region}}` | Region (e.g., us-central1, europe-west1) | Ask once; reuse; default us-central1 |
| `{{user.cpu}}` | CPU allocation (e.g., "1", "2", "4") | Ask once; default "1" |
| `{{user.memory}}` | Memory allocation (e.g., "512Mi", "1Gi") | Ask once; default "512Mi" |
| `{{user.max_instances}}` | Max instances | Ask once; default 1000 |
| `{{user.min_instances}}` | Min instances | Ask once; default 0 |
| `{{user.concurrency}}` | Max concurrent requests per instance | Ask once; default 80 |
| `{{user.timeout}}` | Request timeout in seconds (max 3600) | Ask once; default 300 |
| `{{user.env_vars}}` | Environment variables (KEY=VALUE,...) | Ask once |
| `{{user.secrets}}` | Secrets (KEY=SECRET:VERSION,...) | Ask once |
| `{{user.allow_unauthenticated}}` | Public access (true/false) | Ask once; default true |
| `{{user.traffic_split}}` | Traffic split (REV1=80,REV2=20) | Ask once |
| `{{output.service_url}}` | Service URL | Parse from API response |
| `{{output.revision_name}}` | Latest revision name | Parse from API response |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning (Credential Masking — MANDATORY):** **NEVER** log, print, or expose service account key content, `GOOGLE_APPLICATION_CREDENTIALS` path content, or any credential field value in console output, debug messages, error messages, or logs.

## API and Response Conventions (Agent-Readable)

- **REST API is canonical**: Cloud Run Admin API v1 (`run.googleapis.com`). JSON paths verified against official reference.
- **Errors:** Map SDK/gRPC/HTTP errors to canonical gRPC status codes and messages.
- **Timestamps:** RFC 3339 with timezone.
- **Cloud Run uses Kubernetes-style API**: Conditions follow Ready/ConfigurationsReady/RoutesReady pattern.

### Key JSON Paths

| Operation | JSON Path |
|-----------|-----------|
| Create/Deploy | `$.metadata.name`, `$.spec.template.spec.containers[0].image`, `$.status.url` |
| Describe | `$.spec.template.spec.containers[0].image`, `$.spec.template.spec.containers[0].resources`, `$.spec.template.spec.containers[0].env` |
| Describe (traffic) | `$.status.traffic[].revisionName`, `$.status.traffic[].percent`, `$.status.url` |
| List | `$.items[].metadata.name`, `$.items[].status.url`, `$.items[].status.conditions[].type` |
| Update traffic | `$.spec.traffic[].revisionName`, `$.spec.traffic[].percent` |
| List revisions | `$.items[].metadata.name`, `$.items[].spec.containers[0].image`, `$.items[].status.conditions[].type` |

### Conditions

| Condition Type | Meaning |
|----------------|---------|
| Ready | Service is fully ready to serve traffic |
| ConfigurationsReady | Configuration has been applied |
| RoutesReady | Route is configured and traffic can reach the service |

### Expected State Transitions

| Operation | Initial State | Target State | Max Wait |
|-----------|---------------|--------------|----------|
| Create Service | — | Ready | 300s |
| Deploy/Update | Ready | Ready | 300s |
| Delete Service | Ready | absent | 120s |
| Traffic Split | Ready | Ready | 60s |

## Quick Start

### What This Skill Does

This skill enables you to deploy, configure, troubleshoot, and monitor Cloud Run (fully managed) services on Google Cloud using the `gcloud` CLI (primary) or JIT Go SDK (fallback).

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
gcloud run services list --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"
```

### Next Steps

- [Core Concepts](references/core-concepts.md) — Understand Cloud Run architecture
- [Common Operations](#execution-flows) — Create, manage, and delete services
- [Troubleshooting](references/troubleshooting.md) — Fix common issues

## Capabilities at a Glance

| Operation | Description | Risk Level | Operation | Risk Level |
|-----------|-------------|------------|-----------|------------|
| Create Service | Deploy new service | Low | Describe Service | None |
| Deploy/Update Service | Update container/config | Low | List Services | None |
| Update Traffic Splitting | Route traffic across revisions | Medium | List Revisions | None |
| Delete Service | Remove service | **High** | Mount Secrets | Low |
| Configure VPC Connector | Attach to VPC | Low | Configure Health Checks | Low |
| Configure Custom Domain | Map custom hostname | Low | IAM Policy Binding | Low |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-07 | Service lifecycle, revision management, traffic splitting, secrets mounting, VPC connector, health checks, custom domains; dual-path gcloud+SDK; GCL quality gate |

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (gcloud and/or SDK/API) → Validate → Recover**. Do not skip phases.

### Operation: Create Service

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| gcloud CLI installed | `gcloud version` | Exit code 0 | Document gcloud install |
| Credentials configured | `gcloud auth describe` | Active account | HALT; user authenticates |
| Project set | `gcloud config get-value project` or env | Valid project ID | HALT; user sets project |
| Run API enabled | `gcloud services list --filter="run.googleapis.com"` | run.googleapis.com listed | `gcloud services enable run.googleapis.com` |
| Container image accessible | Image exists in registry | Image pullable | HALT; verify image path + perms |
| Service name unique | `gcloud run services describe NAME` | NOT_FOUND | Rename or use existing |

#### Execution — CLI (`gcloud`)

```bash
gcloud run services create "{{user.service_name}}" \
  --image="{{user.image}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --cpu="{{user.cpu:-1}}" \
  --memory="{{user.memory:-512Mi}}" \
  --max-instances="{{user.max_instances:-1000}}" \
  --min-instances="{{user.min_instances:-0}}" \
  --concurrency="{{user.concurrency:-80}}" \
  --timeout="{{user.timeout:-300}}" \
  --port="{{user.port:-8080}}" \
  --set-env-vars="{{user.env_vars}}" \
  --set-secrets="{{user.secrets}}" \
  --ingress="{{user.ingress:-all}}" \
  $({{user.allow_unauthenticated:-true}} == true && echo "--allow-unauthenticated" || echo "--no-allow-unauthenticated") \
  --format=json
```

#### Execution — Python SDK

```python
import os
from google.cloud import run_v2

client = run_v2.ServicesClient()
parent = f"projects/{os.environ['CLOUDSDK_CORE_PROJECT']}/locations/{{user.region:-us-central1}}"
service = run_v2.Service(
    template=run_v2.RevisionTemplate(
        containers=[run_v2.Container(image="{{user.image}}")],
        scaling=run_v2.RevisionScaling(
            min_instance_count={{user.min_instances:-0}},
            max_instance_count={{user.max_instances:-1000}},
        ),
    ),
)
operation = client.create_service(parent=parent, service=service, service_id="{{user.service_name}}")
result = operation.result()
print(f"Created: {result.uri}")
```

#### Post-execution Validation

```bash
gcloud run services describe "{{user.service_name}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format=json | jq '{url: .status.url, conditions: [.status.conditions[] | select(.type=="Ready")]}'
```

Validate: `.status.conditions[] | select(.type=="Ready" and .status=="True")`. Report `{{output.service_url}}`.

#### Failure Recovery

| Error Code | Meaning | Agent Action |
|------------|---------|--------------|
| 400/invalidArgument | Invalid config | Fix params per deployment flags; retry |
| 403/permissionDenied | Insufficient IAM | HALT — grant roles/run.admin |
| 404/notFound | Image not found | HALT — verify image path |
| 409/alreadyExists | Name taken | Rename service |
| 429/resourceExhausted | Quota exceeded | HALT — increase quota |
| 503/unavailable | Temporarily unavailable | Retry 3x with backoff |
| revisionFailed | Container pull/startup failed | HALT — check image + health check |
| imagePullError | Registry access denied | HALT — check SA perms on registry |

---

### Operation: Deploy/Update Service

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Service exists | `gcloud run services describe NAME` | Service found | HALT — service missing |
| Service in Ready state | `.status.conditions[].status` | True for Ready | Wait until Ready |
| New image accessible | Image exists in registry | Pullable | HALT — verify image |

#### Execution — CLI (`gcloud`)

```bash
gcloud run services deploy "{{user.service_name}}" \
  --image="{{user.image}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --cpu="{{user.cpu}}" \
  --memory="{{user.memory}}" \
  --max-instances="{{user.max_instances}}" \
  --min-instances="{{user.min_instances}}" \
  --concurrency="{{user.concurrency}}" \
  --timeout="{{user.timeout}}" \
  --set-env-vars="{{user.env_vars}}" \
  --set-secrets="{{user.secrets}}" \
  --format=json
```

#### Execution — Python SDK

```python
import os
from google.cloud import run_v2

client = run_v2.ServicesClient()
name = f"projects/{os.environ['CLOUDSDK_CORE_PROJECT']}/locations/{{user.region:-us-central1}}/services/{{user.service_name}}"
service = run_v2.Service(
    template=run_v2.RevisionTemplate(
        containers=[run_v2.Container(image="{{user.image}}")],
    ),
)
operation = client.update_service(service=service, name=name)
result = operation.result()
print(f"Deployed: {result.uri}")
```

#### Post-execution Validation

```bash
gcloud run services describe "{{user.service_name}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format=json | jq '{latestRevision: .status.latestReadyRevisionName, url: .status.url}'
```

#### Failure Recovery

| Error Code | Meaning | Agent Action |
|------------|---------|--------------|
| 404/notFound | Service missing | Use create instead |
| 403/permissionDenied | Insufficient IAM | HALT — grant roles/run.admin |
| 412/failedPrecondition | Invalid state | HALT — wait for Ready |
| 504/deadlineExceeded | Deployment timeout | Retry; check container startup |

---

### Operation: Describe Service

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Service exists | `gcloud run services describe NAME` | Found | HALT — service missing |

#### Execution — CLI (`gcloud`)

```bash
gcloud run services describe "{{user.service_name}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format=json
```

#### Post-execution Validation

Report: service name, URL, latest revision, image, CPU, memory, concurrency, traffic split, conditions, creation time.

```bash
gcloud run services describe "{{user.service_name}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format=json | jq '{
    name: .metadata.name,
    url: .status.url,
    image: .spec.template.spec.containers[0].image,
    cpu: .spec.template.spec.containers[0].resources.limits.cpu,
    memory: .spec.template.spec.containers[0].resources.limits.memory,
    traffic: .status.traffic,
    conditions: .status.conditions
  }'
```

---

### Operation: List Services

#### Execution — CLI (`gcloud`)

```bash
gcloud run services list \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format=json
```

#### Post-execution Validation

Report: service names, URLs, statuses, creation times.

```bash
gcloud run services list \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format=json | jq '[.[] | {name: .metadata.name, url: .status.url, conditions: .status.conditions}]'
```

---

### Operation: Update Traffic Splitting

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Service exists | Describe service | Found | HALT — service missing |
| Revisions exist | `gcloud run revisions list --service=NAME` | Target revisions listed | HALT — revision missing |
| Traffic sums to 100% | Validate `{{user.traffic_split}}` | Sum == 100 | Fix split values |

#### Execution — CLI (`gcloud`)

To latest revision:
```bash
gcloud run services update-traffic "{{user.service_name}}" \
  --to-latest \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format=json
```

To specific revisions:
```bash
gcloud run services update-traffic "{{user.service_name}}" \
  --to-revisions="{{user.traffic_split}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format=json
```

#### Post-execution Validation

```bash
gcloud run services describe "{{user.service_name}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format=json | jq '.status.traffic[] | {revision: .revisionName, percent: .percent, latest: .latestRevision}'
```

#### Failure Recovery

| Error Code | Meaning | Agent Action |
|------------|---------|--------------|
| 404/notFound | Service/revision missing | HALT — verify names |
| 400/invalidArgument | Invalid split | Fix percentages; retry |
| 412/failedPrecondition | Service not ready | Wait; retry |

---

### Operation: List Revisions

#### Execution — CLI (`gcloud`)

```bash
gcloud run revisions list \
  --service="{{user.service_name}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format=json
```

#### Post-execution Validation

Report: revision names, images, creation times, traffic percentages, conditions.

```bash
gcloud run revisions list \
  --service="{{user.service_name}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format=json | jq '[.[] | {name: .metadata.name, image: .spec.containers[0].image, createTime: .metadata.creationTimestamp, conditions: .status.conditions}]'
```

---

### Operation: Delete Service

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit confirmation: irreversible delete of `{{user.service_name}}`.
- **MUST NOT** proceed without clear user assent.
- **SUGGEST** traffic drain: set `--to-revisions=` to 0% before delete.

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Service exists | Describe service | Found | HALT — nothing to delete |
| User confirms | User types exact service name | Exact match | HALT — name mismatch |

#### Execution — CLI (`gcloud`)

```bash
gcloud run services delete "{{user.service_name}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format=json
```

#### Post-execution Validation

```bash
gcloud run services describe "{{user.service_name}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format=json 2>&1 | grep -q "NOT_FOUND" && echo "Deleted successfully" || echo "Still exists"
```

#### Failure Recovery

| Error Code | Meaning | Agent Action |
|------------|---------|--------------|
| 404/notFound | Already deleted | Success |
| 403/permissionDenied | Insufficient IAM | HALT |
| 409/aborted | Concurrent modification | Retry 3x with backoff |

---

### Operation: Mount Secrets

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Secret exists in Secret Manager | `gcloud secrets describe NAME` | Found | HALT — create secret first (delegate to `gcp-secretmanager-ops`) |
| SA has secret accessor role | IAM check | roles/secretmanager.secretAccessor | HALT — grant IAM role |
| Service exists | Describe service | Found | HALT — service missing |

#### Execution — CLI (`gcloud`)

```bash
gcloud run services deploy "{{user.service_name}}" \
  --image="$(gcloud run services describe "{{user.service_name}}" \
    --region="{{user.region:-us-central1}}" \
    --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
    --format=json | jq -r '.spec.template.spec.containers[0].image')" \
  --set-secrets="{{user.secrets}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format=json
```

#### Post-execution Validation

```bash
gcloud run services describe "{{user.service_name}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format=json | jq '.spec.template.spec.containers[0].env[].valueFrom.secretKeyRef'
```

#### Failure Recovery

| Error Code | Meaning | Agent Action |
|------------|---------|--------------|
| 404/notFound | Secret not found | HALT — verify secret name/version |
| 403/permissionDenied | No secret accessor role | HALT — grant IAM role |

---

### Operation: Configure VPC Connector

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| VPC connector exists | `gcloud compute networks vpc-access connectors describe` | Found | HALT — create connector (delegate to `gcp-vpc-ops`) |
| Service exists | Describe service | Found | HALT — service missing |
| VPC Serverless Access role | IAM check | roles/vpcaccess.user | HALT — grant IAM role |

#### Execution — CLI (`gcloud`)

```bash
gcloud run services deploy "{{user.service_name}}" \
  --image="$(gcloud run services describe "{{user.service_name}}" \
    --region="{{user.region:-us-central1}}" \
    --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
    --format=json | jq -r '.spec.template.spec.containers[0].image')" \
  --vpc-connector="{{user.vpc_connector}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format=json
```

#### Post-execution Validation

```bash
gcloud run services describe "{{user.service_name}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format=json | jq '.spec.template.spec.vpcAccess'
```

---

### Operation: Configure Health Checks

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Service exists | Describe service | Found | HALT — service missing |
| Container listens on port | Container docs / image inspection | Port matches `--port` | Fix port value |

#### Execution — CLI (`gcloud`)

```bash
gcloud run services deploy "{{user.service_name}}" \
  --image="{{user.image}}" \
  --port="{{user.port:-8080}}" \
  --startup-cpu-boost \
  --no-cpu-throttling \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format=json
```

#### Post-execution Validation

```bash
gcloud run services describe "{{user.service_name}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format=json | jq '{
    port: .spec.template.spec.containers[0].ports[0].containerPort,
    conditions: [.status.conditions[] | select(.status != "True")]
  }'
```

If conditions show `Ready: False`, check `.status.conditions[] | select(.status=="False") | {type, message, reason}` for root cause.

---

## References

| Document | Description |
|----------|-------------|
| [core-concepts.md](references/core-concepts.md) | Architecture, quotas, regions, prerequisites |
| [api-sdk-usage.md](references/api-sdk-usage.md) | REST API, Python SDK, Go SDK, operation map |
| [gcloud-usage.md](references/gcloud-usage.md) | `gcloud run` command map, jq extracts, coverage gaps |
| [troubleshooting.md](references/troubleshooting.md) | 13+ error codes, diagnostics, recovery |
| [monitoring.md](references/monitoring.md) | Metrics, dashboards, alerts |
| [integration.md](references/integration.md) | Go SDK, environment setup, credential rules |
| [well-architected-assessment.md](references/well-architected-assessment.md) | 5-pillar assessment |
| [rubric.md](references/rubric.md) | GCL scoring rubric |
| [prompt-templates.md](references/prompt-templates.md) | GCL templates |

## GCL Quality Gate

**Classification**: recommended | **max_iter**: 3 | **Most-scrutinized**: Delete Service, Traffic Split (can cause downtime if misconfigured)

## Token Efficiency

| Rule | Practice | Rule | Practice |
|------|----------|------|----------|
| TE-1 | `gcloud run services describe` for current config instead of hardcoding | TE-2 | No docstrings; inline comments only |
| TE-3 | Error tables: 1 row, ≤3 cols | TE-4 | JSON paths centralized above |
| TE-5 | `example-config.yaml` uses YAML anchors | TE-6 | SKILL.md references/ don't repeat |

## Operational Best Practices

- **Least privilege:** IAM roles scoped to required permissions only (roles/run.admin for full access, roles/run.viewer for read-only, roles/run.invoker for invocation).
- **Availability:** Use multi-region deployments and traffic splitting for zero-downtime updates.
- **Cost:** Set `min-instances=0` for idle cost savings; right-size CPU/memory; tune concurrency.
- **Security:** Mount secrets via Secret Manager, use VPC connector for private access, restrict ingress to internal or LB-only.

## AIOps 自愈

Cloud Run 常见故障（冷启动/延迟突增、并发与内存超限 OOM、健康检查失败）的自愈 runbook，覆盖 dry-run + 幂等 + 门禁原则、blast-radius 分析与凭证遮蔽：

- [AIOps Self-Healing Runbook](references/advanced/aiops-cloudrun-anomaly.md) — 异常目录、自愈 playbook（min-instances 调整 / 资源 right-sizing / 回滚稳定 revision）、跨产品影响范围

> 自愈动作遵循 AGENTS.md §0.1 凭证遮蔽；回滚 revision 类动作强制 HALT 人工确认。错误分类见 `docs/error-taxonomy.md`，级联影响见 `docs/cross-skill-blast-radius.md`。

## See Also

[gcp-skill-generator](../gcp-skill-generator/SKILL.md) | [gcp-gke-ops](../gcp-gke-ops/SKILL.md) | [gcp-cloudfunctions-ops](../gcp-cloudfunctions-ops/SKILL.md) | [gcp-iam-ops](../gcp-iam-ops/SKILL.md) | [gcp-vpc-ops](../gcp-vpc-ops/SKILL.md) | [gcp-monitoring-ops](../gcp-monitoring-ops/SKILL.md) | [gcp-secretmanager-ops](../gcp-secretmanager-ops/SKILL.md) | [gcp-gcl-runner-ops](../gcp-gcl-runner-ops/SKILL.md)
