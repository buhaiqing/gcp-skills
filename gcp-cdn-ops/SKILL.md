---
name: gcp-cdn-ops
description: >-
  Use when the user needs to enable, disable, configure, monitor, or troubleshoot
  Google Cloud CDN — backend service CDN policies, cache modes, TTL management,
  cache invalidation, signed URLs, and CDN diagnostics. User mentions Cloud CDN,
  cache invalidation, signed URL, cache mode, CDN policy, edge cache, or describes
  CDN scenarios (e.g., "enable CDN", "invalidate cache", "cache not hitting",
  "signed URL setup", "CDN latency", "origin bypass") even without naming the
  product directly. Not for load balancer creation, SSL certificates, or VPC
  operations that have their own skills.
license: MIT
compatibility: >-
  Official Google Cloud CLI (`gcloud`, Python-based SDK), Go 1.21+ runtime
  (for JIT SDK fallback), valid service account credentials with Compute Admin
  IAM role, network access to Google Cloud endpoints.
metadata:
  author: gcp-skills
  version: "1.0.0"
  last_updated: "2026-06-07"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  go_version_minimum: "1.21"
  go_version_jit: "1.24+"
  api_profile: "https://compute.googleapis.com/$discovery/rest?version=v1"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    gcloud compute backend-services --help confirms --enable-cdn, --cache-mode,
    --client-ttl, --default-ttl, --max-ttl, --negative-caching, add-signed-url-key,
    delete-signed-url-key. URL map cache invalidation via gcloud compute url-maps
    invalidate-cache. See https://cloud.google.com/sdk/gcloud/reference/compute/backend-services
  environment:
    - GOOGLE_APPLICATION_CREDENTIALS
    - CLOUDSDK_CORE_PROJECT
    - CLOUDSDK_AUTH_ACCESS_TOKEN
---

> This skill follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Google Cloud CDN Operations Skill

## Overview

Google Cloud CDN caches content at Google's globally distributed edge points of presence, reducing latency and origin load for HTTP(S) load-balanced backends. CDN is not a standalone resource — it is enabled on backend services via CDN policy configuration. This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **dual-path execution** (official **SDK/API** and **`gcloud`** CLI), response validation, and failure recovery.

> **UX Compliance:** This skill follows the [User Experience Specification](../gcp-skill-generator/references/user-experience-spec.md). All operations include onboarding guidance, minimal prompts, smart defaults, clear feedback, and user-friendly error handling.

### CLI applicability (repository policy)

- **`cli_applicability: dual-path`:** Official `gcloud` fully supports CDN via `gcloud compute backend-services` with CDN flags. You MUST ship both **`references/gcloud-usage.md`** and, in each execution flow below, document **both** the SDK step **and** the `gcloud` step for every operation.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use conditions with precise triggers and delegation rules |
| 2 | **Structured I/O** | Placeholder conventions (`{{env.*}}`, `{{user.*}}`, `{{output.*}}`) with type and source documented |
| 3 | **Explicit Actionable Steps** | Every operation: Pre-flight → Execute → Validate → Recover, with numbered imperative steps |
| 4 | **Complete Failure Strategies** | Error taxonomy table with ≥ 10 product-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | One product (Cloud CDN) with clear delegation to related skills (LB, GCE, GCS) |

Refer to the [meta-skill](../gcp-skill-generator/SKILL.md#five-core-standards-quality-gates) for detailed descriptions of each standard.

### Google Cloud Architecture Framework Integration

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **Security** | Signed URLs, Cloud Armor integration, VPC Service Controls, HTTPS-only origins | `references/well-architected-assessment.md` §2.1 |
| **Stability** | Cache invalidation, multi-region CDN, origin failover, TTL management | `references/well-architected-assessment.md` §2.2 |
| **Cost** | Egress cost savings, cache hit ratio optimization, Cloud Storage origin pricing | `references/well-architected-assessment.md` §2.3 |
| **Efficiency** | Cache mode selection, header optimization, negative caching, automation | `references/well-architected-assessment.md` §2.4 |
| **Performance** | Cache hit ratio, latency reduction, edge cache performance, TCP optimizations | `references/well-architected-assessment.md` §2.5 |

See [references/well-architected-assessment.md](references/well-architected-assessment.md) for the complete specification.

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "Cloud CDN", "CDN", "cache invalidation", "signed URL", "cache mode", "CDN policy", "edge cache"
- Task involves enabling/disabling CDN on backend services
- Task involves configuring CDN policy: cache mode, TTLs, negative caching, bypass/Include protocols, signed URL keys
- Task involves invalidating cached content by host/path pattern
- Task involves managing signed URL keys for private content
- User describes CDN scenarios: "cache not hitting", "content not refreshing", "stale content", "CDN latency", "origin bypass", "enable CDN", "disable CDN"
- Keywords: CDN, cache, invalidate, signed URL, cache mode, TTL, edge cache, cache hit, cache miss

### SHOULD NOT Use This Skill When

- Task is creating load balancers, forwarding rules, URL maps → delegate to: `gcp-lb-ops`
- Task is purely about instance groups or VM backends → delegate to: `gcp-gce-ops`
- Task is purely about Cloud Storage bucket configuration → delegate to: `gcp-gcs-ops`
- Task is purely about VPC / firewall rules → delegate to: `gcp-vpc-ops`
- Task is purely about monitoring dashboards/alerts → delegate to: `gcp-monitoring-ops`
- Task is purely about SSL certificates → delegate to: `gcp-lb-ops`
- User insists on console-only flows → state limitation; do not invent undocumented gcloud steps

### Delegation Rules

- **Load Balancer**: For URL maps, forwarding rules, target proxies, SSL certs → delegate to `gcp-lb-ops`
- **Backend Instances**: For instance group/MIG creation and management → delegate to `gcp-gce-ops`
- **Cloud Storage Origin**: For bucket creation, object upload, lifecycle policies → delegate to `gcp-gcs-ops`
- **VPC/Firewall**: For network, subnet, firewall rules → delegate to `gcp-vpc-ops`
- **Monitoring**: For Cloud Monitoring dashboards, alert policies, log-based metrics → delegate to `gcp-monitoring-ops`
- **GCL**: Execution quality gate uses `gcp-gcl-runner-ops`

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.GOOGLE_APPLICATION_CREDENTIALS}}` | Path to SA key JSON | NEVER ask the user; fail if unset |
| `{{env.CLOUDSDK_CORE_PROJECT}}` | GCP project ID | NEVER ask the user; fail if unset |
| `{{env.CLOUDSDK_AUTH_ACCESS_TOKEN}}` | Temporary access token | NEVER ask the user; fail if needs refresh |
| `{{user.backend_name}}` | Backend service name | Ask once; reuse |
| `{{user.cache_mode}}` | Cache mode | Default: CACHE_ALL_STATIC |
| `{{user.default_ttl}}` | Default TTL in seconds | Default: 3600 |
| `{{user.max_ttl}}` | Max TTL in seconds | Default: 86400 |
| `{{user.client_ttl}}` | Client TTL in seconds | Default: 3600 |
| `{{user.host_rule}}` | Host rule for invalidation | Ask once; reuse |
| `{{user.path_pattern}}` | Path pattern for invalidation | Ask once; reuse |
| `{{user.key_name}}` | Signed URL key name | Ask once; reuse |
| `{{user.url_map}}` | URL map name for invalidation | Ask once; reuse |
| `{{output.backend_name}}` | Backend service name from API | Parse from `$.name` |
| `{{output.cdn_policy}}` | CDN policy JSON from describe | Parse from `$.cdnPolicy` |
| `{{output.operation_id}}` | Operation ID from API | Parse from `$.name` |
| `{{output.invalidation_id}}` | Cache invalidation ID | Parse from `$.name` |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning (Credential Masking — MANDATORY):** NEVER log, print, or expose service account key content, `GOOGLE_APPLICATION_CREDENTIALS` path content, or any credential field value in console output, debug messages, error messages, or logs.

| Execution Path | Safe Pattern | Unsafe Pattern |
|----------------|-------------|----------------|
| Console output | `GOOGLE_APPLICATION_CREDENTIALS=<masked>` | `{"private_key": "-----BEGIN...` |
| Error messages | `Error: API call failed (credential omitted)` | `Error: ... actual SA key content...` |
| Verification | `test -f "$GOOGLE_APPLICATION_CREDENTIALS"` | `cat $GOOGLE_APPLICATION_CREDENTIALS` |
| Go SDK | `os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")` | `log.Printf("%+v", client)` |

## API and Response Conventions (Agent-Readable)

- **REST API is canonical**: Compute Engine v1 API (`compute.googleapis.com`). CDN is a property of backend services.
- **Errors**: Map HTTP/gRPC status codes to canonical error types.
- **Idempotency**: Update operations are idempotent; named resources use unique naming.

### Key JSON Paths (Centralized per TE-4)

| Operation | JSON Path | Type | Description |
|-----------|-----------|------|-------------|
| Backend Describe | `$.name` | string | Backend service name |
| Backend Describe | `$.enableCdn` | boolean | CDN enabled flag |
| Backend Describe | `$.cdnPolicy.cacheMode` | string | Cache mode |
| Backend Describe | `$.cdnPolicy.defaultTtl` | int32 | Default TTL (seconds) |
| Backend Describe | `$.cdnPolicy.maxTtl` | int32 | Max TTL (seconds) |
| Backend Describe | `$.cdnPolicy.clientTtl` | int32 | Client TTL (seconds) |
| Backend Describe | `$.cdnPolicy.negativeCaching` | boolean | Negative caching flag |
| Backend Describe | `$.cdnPolicy.signedUrlKeyMaxVersion` | int32 | Max signed URL key versions |
| Backend Describe | `$.cdnPolicy.signedUrlKeys[].keyName` | string | Signed URL key name |
| Backend Describe | `$.backends[].group` | string | Backend group URL |
| List Backends | `$.items[].name` | string | Backend service name |
| List Backends | `$.items[].enableCdn` | boolean | CDN enabled flag |
| Invalidate Cache | `$.name` | string | Operation ID |
| Invalidate Cache | `$.status` | string | Operation status (DONE/PENDING/RUNNING) |
| Invalidate Cache | `$.operationType` | string | Operation type |
| Operation Describe | `$.status` | string | Operation status |
| Operation Describe | `$.httpErrorStatusCode` | int | HTTP error code (if failed) |
| Operation Describe | `$.httpErrorMessage` | string | Error message (if failed) |

### Expected State Transitions

| Operation | Terminal State | Notes |
|-----------|---------------|-------|
| Enable CDN on backend | `DONE` (sync) | Propagation to edges takes ~60s |
| Update CDN policy | `DONE` (sync) | Propagation to edges takes ~60s |
| Disable CDN | `DONE` (sync) | Existing edge cache cleared gradually |
| Invalidate cache | `DONE` (async) | Takes 1-2 min to propagate |
| Add signed URL key | `DONE` (sync) | Key immediately available |
| Delete signed URL key | `DONE` (sync) | Key immediately revoked |

## Quick Start

### What This Skill Does

This skill enables you to enable, disable, configure, and troubleshoot Google Cloud CDN on backend services using the `gcloud` CLI (primary) and Python SDK (fallback).

### Prerequisites

- [ ] `gcloud` CLI installed (or Go runtime for JIT fallback)
- [ ] Service account key: `GOOGLE_APPLICATION_CREDENTIALS`
- [ ] Project set: `CLOUDSDK_CORE_PROJECT`
- [ ] IAM roles: `roles/compute.loadBalancerAdmin` or `roles/compute.admin`
- [ ] Backend service exists (created via `gcp-lb-ops`)

### Verify Setup

```bash
gcloud config get-value project
gcloud auth application-default print-access-token --quiet &>/dev/null && echo "✅ Auth OK"
gcloud compute backend-services list --global --project="{{env.CLOUDSDK_CORE_PROJECT}}" --limit=1 --format="json" &>/dev/null && echo "✅ CDN API OK"
```

### Your First Command

```bash
# List all CDN-enabled backend services
gcloud compute backend-services list \
  --global \
  --filter="enableCdn=true" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

### Next Steps

- [Core Concepts](references/core-concepts.md) — CDN architecture, cache modes, limits
- [Common Operations](#execution-flows) — Enable, configure, and manage CDN
- [Troubleshooting](references/troubleshooting.md) — Fix common issues

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| Enable CDN on Backend | Turn on CDN for existing backend service | Low | Low |
| Update CDN Configuration | Modify cache mode, TTLs, negative caching | Low | **Medium** — traffic behavior change |
| Describe Backend with CDN | View CDN policy details | Low | None |
| List CDN-Enabled Backends | Enumerate all CDN-configured services | Low | None |
| Disable CDN | Turn off CDN for backend service | Low | **Medium** — origin load increases |
| Configure Signed URLs | Add/manage signed URL keys for private content | Medium | Medium |
| Invalidate Cache | Purge cached content by host/path | Low | **Medium** — origin load spike |
| Delete Signed URL Key | Revoke a signed URL key | Low | **High** — existing signed URLs break |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-07 | Initial release: CDN enable/disable/configure, cache invalidation, signed URLs, dual-path gcloud+SDK, GCL quality gate |

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (gcloud + SDK/API) → Validate → Recover**. Do not skip phases.

### Operation: Enable CDN on Backend Service

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| gcloud CLI | `gcloud version` | Exit 0 | HALT — install gcloud |
| Credentials | `gcloud auth print-access-token --quiet` | Token valid | HALT — authenticate |
| Project | `gcloud config get-value project` | Set | HALT — set project |
| Backend exists | `gcloud compute backend-services describe {{user.backend_name}} --global --quiet` | Exit 0 | HALT — create backend via gcp-lb-ops first |
| CDN not already enabled | `gcloud compute backend-services describe {{user.backend_name}} --global --format=json \| jq -r '.enableCdn'` | `false` | Warn — CDN already enabled; skip or update policy |
| Load balancer configured | Backend has health check and backend group | Exit 0 | HALT — complete LB setup via gcp-lb-ops |

#### Smart Defaults

| Field | Default | Rationale |
|-------|---------|-----------|
| cache_mode | `CACHE_ALL_STATIC` | Safest default — caches static content only |
| default_ttl | `3600` | 1 hour — reasonable for most content |
| max_ttl | `86400` | 24 hours — upper bound for freshness |

#### Execution — CLI (`gcloud`)

```bash
gcloud compute backend-services update "{{user.backend_name}}" \
  --enable-cdn \
  --cache-mode="{{user.cache_mode:-CACHE_ALL_STATIC}}" \
  --default-ttl="{{user.default_ttl:-3600}}" \
  --max-ttl="{{user.max_ttl:-86400}}" \
  --client-ttl="{{user.client_ttl:-3600}}" \
  --global \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

#### Execution — Python SDK

```python
import os
from google.cloud import compute_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
backend_name = "{{user.backend_name}}"

client = compute_v1.BackendServicesClient()
backend = client.get(
    project=project,
    backend_service=backend_name,
)

policy = backend.cdn_policy or compute_v1.CdnPolicy()
policy.cache_mode = compute_v1.CdnPolicy.CacheMode.CACHE_ALL_STATIC
policy.default_ttl = 3600
policy.max_ttl = 86400
policy.client_ttl = 3600

backend.enable_cdn = True
backend.cdn_policy = policy

operation = client.patch(
    project=project,
    backend_service=backend_name,
    backend_service_resource=backend,
)
print(f"Operation: {operation.name}")
```

Execute:
```bash
pip install --quiet --user google-cloud-compute
python3 enable_cdn.py
```

#### Post-execution Validation

1. Describe backend service to verify CDN is enabled:
```bash
gcloud compute backend-services describe "{{user.backend_name}}" \
  --global \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{enableCdn: .enableCdn, cacheMode: .cdnPolicy.cacheMode, defaultTtl: .cdnPolicy.defaultTtl}'
```

2. Verify `enableCdn` is `true` and `cacheMode` matches request.

3. On failure, go to **Failure Recovery**.

#### Failure Recovery

| Error Code | Max retries | Agent Action | UX Feedback |
|------------|-------------|--------------|-------------|
| INVALID_ARGUMENT / 400 | 0-1 | Fix cache mode/TTL args; retry once | `[ERROR] Invalid CDN configuration — verify cache mode and TTL values` |
| PERMISSION_DENIED / 403 | 0 | HALT | `[ERROR] SA lacks compute.backendServices.update permission` |
| NOT_FOUND / 404 | 0 | HALT | `[ERROR] Backend service not found — create via gcp-lb-ops first` |
| QUOTA_EXCEEDED / 429 | 0 | HALT | `[ERROR] Compute API quota exceeded — request increase` |
| INTERNAL / 500 | 3 | 2/4/8s exponential backoff | `[ERROR] Compute service error — retry with backoff` |
| SERVICE_NOT_READY / 503 | 3 | 2/4/8s | `[ERROR] Service temporarily unavailable — retry with backoff` |

---

### Operation: Update CDN Configuration

#### Pre-flight (Safety Gate)

- **MUST** display current CDN configuration so user sees existing settings
- **MUST** warn: "Changing CDN policy will affect cache behavior within ~60 seconds"
- **MUST** validate cache mode is one of: CACHE_ALL_STATIC, USE_ORIGIN_HEADERS, FORCE_CACHE_ALL, CACHE_ALL_STATIC_WITH_PRIVATE
- **MUST** validate TTL values: 0 < default_ttl ≤ max_ttl ≤ 86400 (24h), client_ttl ≤ max_ttl

#### Execution — CLI (`gcloud`)

```bash
# Show current config first
gcloud compute backend-services describe "{{user.backend_name}}" \
  --global --format="json" | jq '.cdnPolicy'

# Update CDN policy
gcloud compute backend-services update "{{user.backend_name}}" \
  --enable-cdn \
  --cache-mode="{{user.cache_mode}}" \
  --default-ttl="{{user.default_ttl:-3600}}" \
  --max-ttl="{{user.max_ttl:-86400}}" \
  --client-ttl="{{user.client_ttl:-3600}}" \
  --{{user.negative_caching:-no-negative-caching}} \
  --global \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

#### Post-execution Validation

```bash
gcloud compute backend-services describe "{{user.backend_name}}" \
  --global \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{cacheMode: .cdnPolicy.cacheMode, defaultTtl: .cdnPolicy.defaultTtl, maxTtl: .cdnPolicy.maxTtl, negativeCaching: .cdnPolicy.negativeCaching}'
```

#### Failure Recovery

| Error Code | Max retries | Agent Action | UX Feedback |
|------------|-------------|--------------|-------------|
| invalidConfiguration / 400 | 0 | HALT | `[ERROR] CDN configuration invalid — check cache mode and TTL constraints` |
| resourceInUse / 409 | 1 | Retry after 30s | `[WARN] Backend in use by active operation — retry after delay` |
| rateLimited / 429 | 3 | 2/4/8s | `[ERROR] API rate limited — backing off` |

---

### Operation: Describe Backend Service with CDN

#### Execution — CLI (`gcloud`)

```bash
gcloud compute backend-services describe "{{user.backend_name}}" \
  --global \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{
  name: .name,
  enableCdn: .enableCdn,
  cdnPolicy: {
    cacheMode: .cdnPolicy.cacheMode,
    defaultTtl: .cdnPolicy.defaultTtl,
    maxTtl: .cdnPolicy.maxTtl,
    clientTtl: .cdnPolicy.clientTtl,
    negativeCaching: .cdnPolicy.negativeCaching,
    signedUrlKeyMaxVersion: .cdnPolicy.signedUrlKeyMaxVersion
  },
  backends: [.backends[] | (.group | split("/")[-1])],
  protocol: .protocol
}'
```

#### Present to User

| Field | Path | Notes |
|-------|------|-------|
| Backend name | `$.name` | Plain text |
| CDN enabled | `$.enableCdn` | true/false |
| Cache mode | `$.cdnPolicy.cacheMode` | See cache mode descriptions |
| Default TTL | `$.cdnPolicy.defaultTtl` | Seconds |
| Max TTL | `$.cdnPolicy.maxTtl` | Seconds |
| Client TTL | `$.cdnPolicy.clientTtl` | Seconds |
| Negative caching | `$.cdnPolicy.negativeCaching` | true/false |
| Backends | `$.backends[].group` | Instance group or NEG names |
| Protocol | `$.protocol` | HTTP/HTTPS/HTTP2 |

---

### Operation: List CDN-Enabled Backend Services

#### Execution — CLI (`gcloud`)

```bash
gcloud compute backend-services list \
  --global \
  --filter="enableCdn=true" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '[.[] | {name: .name, cacheMode: .cdnPolicy.cacheMode, backends: [.backends[] | (.group | split("/")[-1])]}]'
```

---

### Operation: Disable CDN

#### Pre-flight (Safety Gate)

- **MUST** warn: "Disabling CDN will increase origin load and latency for all clients"
- **MUST** display current CDN configuration before disable
- **MUST** ask: "Has a migration plan been prepared for the increased origin load?"
- **MUST** confirm: "Proceed with disabling CDN on {{user.backend_name}}? Type the backend name to confirm:"

#### Execution — CLI (`gcloud`)

```bash
gcloud compute backend-services update "{{user.backend_name}}" \
  --no-enable-cdn \
  --global \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

**Do NOT use `--quiet`** — the pre-flight safety gate above provides confirmation.

#### Post-execution Validation

```bash
gcloud compute backend-services describe "{{user.backend_name}}" \
  --global \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{enableCdn: .enableCdn}'
```

Verify `enableCdn` is `false`.

---

### Operation: Configure Signed URLs

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| CDN enabled | `gcloud compute backend-services describe {{user.backend_name}} --global --format=json \| jq -r '.enableCdn'` | `true` | HALT — enable CDN first |
| Key name unique | `gcloud compute backend-services describe {{user.backend_name}} --global --format=json \| jq -r '.cdnPolicy.signedUrlKeys[]?.keyName'` | Name not in list | HALT — key name already exists |

#### Execution — Add Signed URL Key (`gcloud`)

```bash
gcloud compute backend-services add-signed-url-key "{{user.backend_name}}" \
  --key-name="{{user.key_name}}" \
  --global \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

> **Key value is returned only on creation** — capture and securely store it. It cannot be retrieved later.

#### Post-execution Validation

```bash
gcloud compute backend-services describe "{{user.backend_name}}" \
  --global \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{signedUrlKeys: [.cdnPolicy.signedUrlKeys[] | {keyName: .keyName, keyVersion: .keyVersion}]}'
```

---

### Operation: Invalidate Cache

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| URL map exists | `gcloud compute url-maps describe {{user.url_map}} --global --quiet` | Exit 0 | HALT — URL map not found |
| CDN enabled on backend | Backend referenced by URL map has CDN enabled | true | HALT — enable CDN first |

#### Execution — CLI (`gcloud`)

```bash
gcloud compute url-maps invalidate-cache "{{user.url_map}}" \
  --host="*{{user.host_rule}}" \
  --path="{{user.path_pattern}}" \
  --global \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

#### Post-execution Validation

1. Capture operation ID from response:
```bash
OPERATION_ID=$(gcloud compute url-maps invalidate-cache "{{user.url_map}}" \
  --host="*{{user.host_rule}}" \
  --path="{{user.path_pattern}}" \
  --global \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq -r '.name')

echo "Cache invalidation operation: $OPERATION_ID"
```

2. Wait for operation completion (typically 60-120 seconds):
```bash
gcloud compute operations describe "$OPERATION_ID" \
  --global \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{status: .status, progress: .progress}'
```

3. Verify status is `DONE`.

#### Failure Recovery

| Error Code | Max retries | Agent Action | UX Feedback |
|------------|-------------|--------------|-------------|
| cacheInvalidationFailed / 500 | 1 | Retry once | `[ERROR] Cache invalidation failed — retry or check path pattern` |
| NOT_FOUND / 404 | 0 | HALT | `[ERROR] URL map not found — verify name` |
| OPERATION_PENDING | 3 | 10s intervals | `⚠️ Invalidation operation pending — waiting for completion` |

---

### Operation: Delete Signed URL Key

#### Pre-flight (Safety Gate)

- **MUST** warn: "Deleting this key will immediately invalidate ALL signed URLs using this key"
- **MUST** confirm: "Proceed with deleting signed URL key {{user.key_name}} on {{user.backend_name}}? Type the key name to confirm:"

#### Execution — CLI (`gcloud`)

```bash
gcloud compute backend-services delete-signed-url-key "{{user.backend_name}}" \
  --key-name="{{user.key_name}}" \
  --global \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

**Do NOT use `--quiet`** — the pre-flight safety gate above provides confirmation.

#### Post-execution Validation

```bash
gcloud compute backend-services describe "{{user.backend_name}}" \
  --global \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '.cdnPolicy.signedUrlKeys[] | select(.keyName == "{{user.key_name}}")'
```

Verify key is no longer present (empty output = success).

---

## Prerequisites

> **Self-Healing:** Installation flows include multi-path recovery per [enhanced-self-healing-framework.md](../gcp-skill-generator/references/enhanced-self-healing-framework.md). Each step has ≥ 3 error-handling strategies.

1. **Install gcloud CLI**:
   ```bash
   if ! command -v gcloud &> /dev/null; then
       curl https://sdk.cloud.google.com | bash 2>/dev/null \
       || (echo "⚠️ Installer failed, trying apt..." \
           && sudo apt-get update && sudo apt-get install -y google-cloud-sdk) \
       || (echo "⚠️ apt failed, trying manual..." \
           && wget -q https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-x86_64.tar.gz \
           && tar -xf google-cloud-cli-*.tar.gz && ./google-cloud-sdk/install.sh --quiet)
       exec -l $SHELL
       gcloud init
   fi
   ```

2. **Bootstrap Go runtime** (JIT fallback):
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
           echo "⚠️ Go download failed. Using Python SDK as fallback."
           pip install --quiet --user google-cloud-compute
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

## Reference Directory

- [Core Concepts](references/core-concepts.md) — CDN architecture, cache modes, limits, quotas
- [API & SDK Usage](references/api-sdk-usage.md) — REST API, operation map, Python/Go SDK
- [gcloud Usage](references/gcloud-usage.md) — `gcloud compute backend-services` CDN command map
- [Troubleshooting Guide](references/troubleshooting.md) — Error codes, diagnostics, recovery
- [Monitoring & Alerts](references/monitoring.md) — Cloud Monitoring CDN metrics, dashboards
- [Integration](references/integration.md) — Go SDK bootstrap, env vars, credential rules
- [Well-Architected Assessment](references/well-architected-assessment.md) — Five-pillar assessment
- [Rubric — GCL](references/rubric.md) — Generator-Critic-Loop scoring rubric
- [Prompt Templates — GCL](references/prompt-templates.md) — GCL generator and critic templates

## Operational Best Practices

- **Cache mode selection**: Use `CACHE_ALL_STATIC` for most web apps; `FORCE_CACHE_ALL` only for static asset delivery; `USE_ORIGIN_HEADERS` when origin controls caching.
- **TTL management**: Set `max_ttl` to 24h maximum; use `default_ttl` aligned with content update frequency; `client_ttl` should not exceed `max_ttl`.
- **Cache invalidation**: Use targeted path patterns, not wildcards, to minimize origin load spike. Invalidate only changed paths.
- **Signed URLs**: Rotate keys regularly (90 days recommended); use `signedUrlKeyMaxVersion` to limit active key versions.
- **Negative caching**: Enable for 4xx/5xx responses to reduce origin load from bad requests; set short TTLs (10-30s) for 5xx.
- **Monitoring**: Track cache hit ratio, origin egress, and error rates; alert on hit ratio drops below 80%.
- **Origin protection**: Use Cloud Armor security policies to protect origins from direct access attacks.
- **HTTPS origins**: Always use HTTPS backend protocol for CDN to origin communication.

## Quality Gate (GCL)

> This skill implements the **Generator-Critic-Loop (GCL)** adversarial quality gate per `AGENTS.md §12`.

| Property | Value |
|----------|-------|
| Classification | **recommended** (CDN config changes without destructive delete of resources) |
| max_iter | 3 |
| Most-scrutinized operations | Disable CDN, Delete Signed URL Key, Invalidate Cache |

- **Rubric**: [references/rubric.md](references/rubric.md) — 5 core dimensions + 3 CDN-specific extensions
- **Prompt Templates**: [references/prompt-templates.md](references/prompt-templates.md) — Generator + Critic templates

## Token Efficiency Guidelines (P0 — 强制)

### TE-1: API Query > Static Tables
Use gcloud to fetch live cache mode options and quota info:
```bash
gcloud compute backend-services describe "{{user.backend_name}}" --global --format="json" | jq '.cdnPolicy'
```

### TE-2: No docstrings in code
Inline comments only in SDK snippets.

### TE-3: Compact error tables
Error tables use 1 row per code, ≤ 3 columns.

### TE-4: Centralized JSON paths
See [Key JSON Paths](#key-json-paths-centralized-per-te-4) above.

### TE-5: YAML anchors
See `assets/example-config.yaml` for anchor usage.

### TE-6: Eliminate cross-file duplicate flows
SKILL.md has full flow; references do not repeat execution steps.

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-07 | Initial release: CDN enable/disable/configure, cache invalidation, signed URLs, dual-path gcloud+SDK, GCL quality gate |

## See Also

- **Meta-Skill**: [gcp-skill-generator](../gcp-skill-generator/SKILL.md)
- **Load Balancing**: [gcp-lb-ops](../gcp-lb-ops/SKILL.md) — Backend services, URL maps, forwarding rules
- **Compute Engine**: [gcp-gce-ops](../gcp-gce-ops/SKILL.md) — Instance groups as CDN backends
- **Cloud Storage**: [gcp-gcs-ops](../gcp-gcs-ops/SKILL.md) — Cloud Storage as CDN origin
- **Monitoring**: [gcp-monitoring-ops](../gcp-monitoring-ops/SKILL.md) — Dashboards and alerts for CDN metrics
- **GCL Runner**: [gcp-gcl-runner-ops](../gcp-gcl-runner-ops/SKILL.md) — Execution quality gate
