---
name: gcp-[product-name]-ops
description: >-
  Use when the user needs to deploy, configure, troubleshoot, or monitor Google
  Cloud [Product Name] — [Resource Type] lifecycle, configuration, and
  diagnostics. User mentions [Product Name], [Product Abbreviation],
  or describes product-specific scenarios (e.g., connection drops, performance
  degradation, resource creation failures) even without naming the product
  directly. Not for billing, IAM, or related products that have their own ops
  skills.
license: MIT
compatibility: >-
  Official Google Cloud CLI (`gcloud`, Python-based SDK), Go 1.21+ runtime
  (for JIT SDK fallback), valid service account credentials, network access to
  Google Cloud endpoints.
metadata:
  author: gcp-skills
  version: "1.0.0"
  last_updated: "YYYY-MM-DD"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  go_version_minimum: "1.21"
  go_version_jit: "1.24+"
  api_profile: "[Paste API version or doc link]"
  cli_applicability: "dual-path"  # Choose: cli-first / dual-path / sdk-only / cli-only
  cli_support_evidence: >-
    [If CLI covers this product: cite confirmation via `gcloud <product> --help`.
    If CLI does NOT cover: note JIT Go SDK fallback required.]
  environment:
    - GOOGLE_APPLICATION_CREDENTIALS
    - CLOUDSDK_CORE_PROJECT
    - CLOUDSDK_AUTH_ACCESS_TOKEN
---

> This template follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Google Cloud [Product Name] Operations Skill

## Overview

[Product Name] on Google Cloud provides [brief description]. This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **dual-path execution** (official **SDK/API** and, when the product is supported by official **`gcloud`**, the matching **CLI** flows), response validation, and failure recovery.

> **UX Compliance:** This skill follows the [User Experience Specification](../references/user-experience-spec.md). All operations include onboarding guidance, minimal prompts, smart defaults, clear feedback, and user-friendly error handling.

### CLI applicability (repository policy)

- **`cli_applicability: cli-first`:** Official `gcloud` fully supports this product. CLI is the **primary** execution path. JIT Go SDK is the **fallback** only for edge-case operations CLI doesn't expose. Omit `references/gcloud-usage.md` content gaps unless partial coverage exists.
- **`cli_applicability: dual-path`:** Official `gcloud` supports this product. You **MUST** ship **`references/gcloud-usage.md`** and, in **each** execution flow below, document **both** the SDK step **and** the `gcloud` step for every operation the CLI exposes. If the CLI covers **only part** of the API, add a **coverage gap** table (SDK-only operations) in `references/gcloud-usage.md`.
- **`cli_applicability: sdk-only`:** Official `gcloud` does **not** expose this product. **Omit** `references/gcloud-usage.md`. Keep **`cli_support_evidence`** pointing at official proof. SDK/API remains mandatory for all operations.
- **`cli_applicability: cli-only`:** Read-only/discovery skills that ONLY query cloud resources (e.g., `gcp-topo-discovery`). No write operations, no SDK fallback needed.

## Five Core Standards (Quality Gates)

Every generated skill MUST satisfy these five standards. Use them as a design checklist during population:

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use conditions with precise triggers and delegation rules |
| 2 | **Structured I/O** | Placeholder conventions (`{{env.*}}`, `{{user.*}}`, `{{output.*}}`) with type and source documented |
| 3 | **Explicit Actionable Steps** | Every operation: Pre-flight → Execute → Validate → Recover, with numbered imperative steps |
| 4 | **Complete Failure Strategies** | Error taxonomy table with ≥ 10 product-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | One product, one primary resource model; cross-product delegation to other skills |

Refer to the [meta-skill](../SKILL.md#five-core-standards-quality-gates) for detailed descriptions of each standard.

### Google Cloud Architecture Framework Integration

In addition to the Five Core Standards, every generated skill MUST map its operations to the [Google Cloud Architecture Framework](https://cloud.google.com/architecture/framework) five pillars:

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **Security** | IAM permissions, credential masking, VPC SC, data encryption | `references/well-architected-assessment.md` §2.1 |
| **Stability** | Backup/restore, multi-region, DR runbook, failure-oriented design | `references/well-architected-assessment.md` §2.2 |
| **Cost** | Pricing model comparison, waste detection, right-sizing, committed use | `references/well-architected-assessment.md` §2.3 |
| **Efficiency** | Batch operations, CI/CD integration, automation patterns | `references/well-architected-assessment.md` §2.4 |
| **Performance** | Cloud Monitoring metrics, auto-scaling, performance baselines | `references/well-architected-assessment.md` §2.5 |

See [references/well-architected-assessment.md](references/well-architected-assessment.md) for the complete specification.

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "Google Cloud [Product Name]" OR "[Product Abbreviation]"
- Task involves CRUD or lifecycle operations on **[Resource Type]** (create, describe, modify, delete, list, and product-specific actions)
- Task keywords: [keyword1], [keyword2], [keyword3], …
- User asks to deploy, configure, troubleshoot, or monitor [Product Name] **via gcloud, SDK, API, or automation**

### SHOULD NOT Use This Skill When

- Task is purely billing / cost management → delegate to: `gcp-billing-ops` (when present)
- Task is IAM / permission model only → delegate to: `gcp-iam-ops` (when present)
- Task is about **[related product]** → delegate to: `gcp-[other]-ops`
- User insists on **console-only** flows with no API → state limitation; do not invent undocumented gcloud steps

### Delegation Rules

- If resource B depends on resource A, complete or verify A (via the A skill) before B's SDK or CLI steps.
- Multi-product requests: handle each product with its skill; do not merge unrelated APIs into one ambiguous flow.

## Variable Convention (Agent-Readable)

Structured placeholders reduce injection ambiguity and unsafe prompts:

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.GOOGLE_APPLICATION_CREDENTIALS}}` | Path to SA key JSON | NEVER ask the user; fail if unset |
| `{{env.CLOUDSDK_CORE_PROJECT}}` | GCP project ID | NEVER ask the user; fail if unset |
| `{{env.CLOUDSDK_AUTH_ACCESS_TOKEN}}` | Temporary access token | NEVER ask the user; fail if needs refresh |
| `{{user.project}}` | User-supplied project (override) | Ask once; reuse |
| `{{user.zone}}` | User-supplied zone | Ask once; reuse |
| `{{user.region}}` | User-supplied region | Ask once; reuse |
| `{{user.resource_name}}` | User-supplied resource name | Ask once; reuse |
| `{{output.resource_id}}` | From last API or `gcloud` JSON response | Parse per **REST API** (SDK) or **verified gcloud** path for this operation |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning (Credential Masking — MANDATORY):** **NEVER** log, print, or expose service account key content, `GOOGLE_APPLICATION_CREDENTIALS` path content, or any credential field value in console output, debug messages, error messages, or logs.
>
> **Masking rules across all execution paths:**
> | Execution Path | Safe Pattern | Unsafe Pattern |
> |----------------|-------------|----------------|
> | Console output | `GOOGLE_APPLICATION_CREDENTIALS=<masked>` | `{"private_key": "-----BEGIN...` |
> | Error messages | `Error: API call failed (credential omitted)` | `Error: ... actual SA key content...` |
> | Log files | `[INFO] Credentials configured: SA=***` | `[INFO] SA key: {"private_key":"...` |
> | Verification | `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA key file exists"` | `cat $GOOGLE_APPLICATION_CREDENTIALS` |
> | JIT Go SDK | `option.WithCredentialsFile(os.Getenv("..."))` (env read is safe) | `fmt.Printf("Config: %+v", config)` or `log.Printf("%+v", ...)` |
> | Debug/verbose | `⚠️ Debug mode may expose credential values` (warning only) | `--log-http` with un-masked credential output |
>
> **Credential verification MUST check existence only**, never echo the value:
> - Bash: `test -n "$GOOGLE_APPLICATION_CREDENTIALS"` ✅ | `cat $GOOGLE_APPLICATION_CREDENTIALS` ❌
> - Go: `if os.Getenv("GOOGLE_APPLICATION_CREDENTIALS") == ""` ✅ | `fmt.Println(os.Getenv("GOOGLE_APPLICATION_CREDENTIALS"))` ❌
>
> **If any execution flow violates this rule, the skill SHALL be blocked from merge as a security incident.**

## API and Response Conventions (Agent-Readable)

- **REST API is canonical** for path, query, body fields, enums, and response shapes. Replace generic JSON paths below with **real** schema field names from the GCP API reference.
- **Errors:** Map SDK/gRPC/HTTP errors to canonical gRPC status codes and messages.
- **Timestamps:** RFC 3339 with timezone when the API returns strings (e.g. `2026-04-28T10:00:00Z`).
- **Idempotency:** Document request IDs, resource labels (for uniqueness), and `ALREADY_EXISTS` / `ABORTED` behavior per API.

### Example Response Field Table (Replace with REST API-Accurate Paths)

| Operation | JSON Path (example) | Type | Description |
|-----------|---------------------|------|-------------|
| Create | `$.targetLink` or `$.name` | string | New resource URL/name |
| Describe | `$.status` | string | Lifecycle state |
| List | `$.items[].name` | array | Resource names (verify array structure) |
| Modify / Delete | `$.operationType` or `$.status` | string | Operation tracking |

### Expected State Transitions (Adjust to Product)

| Operation | Initial State | Target State | Poll Interval | Max Wait |
|-----------|---------------|--------------|---------------|----------|
| Create | — | `RUNNING` or product equivalent | via Operations API | 300s |
| Start | `TERMINATED` | `RUNNING` | 5s | 120s |
| Stop | `RUNNING` | `TERMINATED` | 5s | 120s |
| Delete | any stable state | absent or deleted | via Operations API | 300s |

## Quick Start

### What This Skill Does
This skill enables you to deploy, configure, troubleshoot, and monitor [Product Name] resources on Google Cloud using the `gcloud` CLI (primary) or JIT Go SDK (fallback).

### Prerequisites
- [ ] `gcloud` CLI installed (or Go runtime for JIT fallback)
- [ ] Service account key configured: `GOOGLE_APPLICATION_CREDENTIALS`
- [ ] Project set: `gcloud config set project <project-id>` or `CLOUDSDK_CORE_PROJECT`

### Verify Setup
```bash
# Check gcloud and project
gcloud config get-value project
gcloud auth application-default print-access-token --quiet &>/dev/null && echo "✅ Auth OK"
```

### Your First Command
```bash
# Example: List resources
gcloud [product] [resources] list --project={{env.CLOUDSDK_CORE_PROJECT}} --format="json"
```

### Next Steps
- [Core Concepts](references/core-concepts.md) — Understand [Product Name] architecture
- [Common Operations](#execution-flows) — Create, manage, and delete resources
- [Troubleshooting](references/troubleshooting.md) — Fix common issues

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| Create | Create a new [Resource] | Medium | Low |
| Describe | View [Resource] details | Low | None |
| Modify | Change [Resource] configuration | Medium | Medium |
| Delete | Remove a [Resource] | Low | **High** — irreversible |
| List | View all [Resources] | Low | None |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | YYYY-MM-DD | Initial API/SDK-oriented template with gcloud CLI support |

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (gcloud and/or SDK/API) → Validate → Recover**. Do not skip phases.

**Preference hint:** When `gcloud` does not support a specific operation, JIT build a Go SDK script. `gcloud` is preferred for coverage and simplicity; Go SDK is used for operations `gcloud` does not expose.

### Operation: Create [Resource]

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| SDK / deps | Import client; version matches `metadata.api_profile` | No import error | Document install pin |
| CLI / deps | `gcloud version` (**required** when `cli_applicability: cli-first` / `dual-path` / `cli-only`) | Exit code 0 | Document gcloud install |
| Credentials | gcloud auth / SA key file | Non-empty / valid | HALT; user authenticates |
| Project | `gcloud config get-value project` or env var | Set and valid | HALT; user sets project |
| Quota | Check project quotas per API | Sufficient quota | HALT; user requests increase |

#### Execution — CLI (`gcloud`) (Primary Path)

Use the [Google Cloud SDK gcloud CLI](https://cloud.google.com/sdk/gcloud) as the **primary execution path**.

> **Critical CLI Notes** (verified through gcloud CLI reference):
> - All output is **human-readable by default** — ALWAYS use `--format=json` for machine parsing
> - `--format=json` is the recommended output format for agent execution
> - Credentials can be passed via `GOOGLE_APPLICATION_CREDENTIALS` env var
> - Project is set via `CLOUDSDK_CORE_PROJECT` env var or `gcloud config set project`
> - For long-running operations, use `gcloud` built-in polling (returns when operation completes)

```bash
# gcloud API call with JSON output
gcloud [product] [resources] create [RESOURCE_NAME] \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --zone="{{user.zone}}" \
  --format="json"
```

#### Execution — Python SDK (Primary Fallback)

When `gcloud` CLI does not support a specific operation, use the **Python SDK** first. Only fall back to Go SDK if Python 3.8+ is unavailable.

```python
# list_instances.py (generated dynamically in /tmp/gcp-sdk-workspace)
# REST: GET /v1/projects/{project}/zones/{zone}/instances
import os
from google.cloud import compute_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
zone = os.environ.get("CLOUDSDK_COMPUTE_ZONE", "us-central1-a")

client = compute_v1.InstancesClient()
request = compute_v1.ListInstancesRequest(project=project, zone=zone)
instances = client.list(request=request)
for inst in instances:
    print(f"Instance: {inst.name} (status: {inst.status})")
```

Execute:
```bash
pip install --quiet --user google-cloud-compute
python3 list_instances.py
```

#### Execution — JIT Go SDK (Secondary Fallback)

When Python 3.8+ is not available, JIT build a Go SDK script:

```go
// main.go (generated dynamically in /tmp/gcp-sdk-workspace)
package main

import (
    "context"
    "fmt"
    "log"
    "os"
    
    "google.golang.org/api/option"
    // Replace with product-specific SDK
    [product] "cloud.google.com/go/[product]/apiv1"
    [product]pb "cloud.google.com/go/[product]/apiv1/[product]pb"
)

func main() {
    ctx := context.Background()
    
    // Use SA key from environment
    client, err := [product].NewClient(ctx,
        option.WithCredentialsFile(os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")))
    if err != nil {
        log.Fatalf("Failed to create client: %v", err)
    }
    defer client.Close()
    
    // Operation-specific request (generated per API reference)
    req := &[product]pb.Create[Resource]Request{
        Parent: fmt.Sprintf("projects/%s/locations/%s",
            os.Getenv("CLOUDSDK_CORE_PROJECT"), "{{user.zone}}"),
        // Add fields per REST API request schema
    }
    
    resp, err := client.Create[Resource](ctx, req)
    if err != nil {
        log.Fatalf("Failed to create resource: %v", err)
    }
    
    fmt.Printf("Created: %s\n", resp.Name)
}
```

Execute:
```bash
# In /tmp/gcp-sdk-workspace
go mod init sdk-script
go get cloud.google.com/go/[product]/apiv1
go run ./main.go
```

#### Post-execution Validation

1. Read `{{output.resource_id}}` from the **documented** response path.
2. Poll via Operations API or Describe until terminal success state or timeout:

```bash
# Describe after creation (verify state)
gcloud [product] [resources] describe [RESOURCE_NAME] \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --zone="{{user.zone}}" \
  --format="json" | jq -r '.status'
```

```bash
# Loop polling (if no built-in waiter)
# for i in $(seq 1 60); do
#   STATUS=$(gcloud [product] [resources] describe ... --format="json" | jq -r '.status')
#   [ "$STATUS" = "RUNNING" ] && break
#   sleep 5
# done
```

3. On success, report `{{output.resource_id}}` and key fields to the user.
4. On terminal failure, go to **Failure Recovery**.

#### Failure Recovery

| Error pattern (gRPC code / HTTP status) | Max retries | Backoff | Agent Action | UX Feedback |
|------------------------------|-------------|---------|--------------|-------------|
| `INVALID_ARGUMENT` / 400 | 0–1 | — | Fix args from API reference; retry once if safe | `[ERROR] INVALID_ARGUMENT: The request parameter is invalid. What happened: One or more parameters do not meet the API specification. How to fix: Check the parameter against REST API docs and retry. Next step: Review the parameter table above.` |
| `QUOTA_EXCEEDED` / 429 | 0 | — | HALT | `[ERROR] QUOTA_EXCEEDED: Resource quota limit reached. What happened: Your project has reached the maximum allowed number of this resource type. How to fix: Delete unused resources or request a quota increase. Next step: Check quotas in Cloud Console or raise a support ticket.` |
| `PERMISSION_DENIED` / 403 | 0 | — | HALT | `[ERROR] PERMISSION_DENIED: Insufficient IAM permissions. What happened: The service account lacks the required permissions. How to fix: Grant the necessary IAM role to the service account. Next step: Check IAM bindings in Cloud Console.` |
| `ALREADY_EXISTS` / 409 | 0 | — | Ask reuse vs new name | `[ERROR] ALREADY_EXISTS: A resource with this name already exists. What happened: The specified resource name is already in use. How to fix: Use a different name or reuse the existing resource. Next step: Choose a unique name or describe the existing resource.` |
| `UNAVAILABLE` / `ABORTED` / 503 | 3 | exponential | Back off; respect `Retry-After` if present | `⚠️ Service temporarily unavailable. Retrying in {backoff}s... (Attempt {current}/{max})` |
| `INTERNAL` / 500 | 3 | 2s, 4s, 8s | Retry; then HALT | `[ERROR] INTERNAL: Server-side error occurred. What happened: GCP encountered an internal error. How to fix: Retry the operation. If it persists, escalate with the error details. Next step: Retry now or file a support case.` |

### Operation: Describe [Resource]

#### Execution

Use the SDK **describe/get** API matching REST API reference. When **`cli_applicability`** is `cli-first` / `dual-path` / `cli-only`, also document the equivalent `gcloud [product] [resources] describe ...`, passing `{{user.resource_name}}`, project, and location.

```bash
# gcloud — JSON output for machine parsing
gcloud [product] [resources] describe "{{user.resource_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --zone="{{user.zone}}" \
  --format="json"

# gcloud — extract specific fields with jq
gcloud [product] [resources] describe "{{user.resource_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --zone="{{user.zone}}" \
  --format="json" | jq '{name: .name, status: .status, createTime: .createTime}'
```

#### Present to User

| Field | Path (example) | Notes |
|-------|----------------|-------|
| Name | from describe result | Plain text |
| Status | from describe result | Human-readable state |
| Zone/Region | from describe result | Location deployment info |
| Created time | from describe result | Format RFC 3339 per API |

### Operation: Delete [Resource]

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit confirmation: irreversible delete of `{{user.resource_name}}`.
- **MUST NOT** proceed without clear user assent.

#### Execution

Call delete API per REST API (skip for `cli-only`). When **`cli_applicability`** is `cli-first` / `dual-path`, also document the `gcloud` delete subcommand; capture operation details from **verified** output shape for **each** path.

#### Post-execution Validation

Poll describe (or get) until **NOT_FOUND**, or status indicates deleted—per API semantics—within **max wait**.

### Operation: Backup [Resource]

> **Stability Pillar:** Following Google Cloud Architecture Framework §应急快恢 (Emergency Recovery), every writable skill MUST document backup and recovery operations.

#### When to Use
- Before any destructive operation (delete, resize, upgrade)
- Scheduled per organizational RPO requirements
- Migration or region transfer prerequisites

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Resource exists | Describe with name | Resource in stable state (RUNNING/READY) | HALT — cannot backup non-existent or transitioning resource |
| Backup window | Check snapshot/backup schedule | Within allowed window | Warn user; proceed with confirmation |
| Storage quota | Check snapshot quotas | Sufficient snapshot storage | HALT — user must free space or raise quota |
| Existing backup | List existing backups with resource filter | None or list existing backups | Inform user of existing backups |

#### Execution — CLI (`gcloud`) (Primary Path)

```bash
# Create backup/snapshot (adjust per product API)
gcloud [product] [backups] create \
  --source=[resource]/{{user.resource_name}} \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# For Snapshot (e.g., Compute Engine disks)
gcloud compute disks snapshot "{{user.resource_name}}" \
  --snapshot-names="auto-backup-$(date +%Y%m%d-%H%M%S)" \
  --zone="{{user.zone}}"
```

#### Execution — JIT Go SDK (Fallback Path)

```go
// Snapshot creation example
req := &computepb.CreateSnapshotRequest{
    Disk: fmt.Sprintf("projects/%s/zones/%s/disks/%s",
        os.Getenv("CLOUDSDK_CORE_PROJECT"), zone, diskName),
    SnapshotResource: &computepb.Snapshot{
        Name: tea.String("auto-backup-" + time.Now().Format("20060102-150405")),
    },
}
```

#### Post-execution Validation

1. Capture `{{output.snapshot_id}}` or `{{output.backup_id}}` from response
2. Poll backup status until terminal state (`READY`/`SUCCESS`):

```bash
gcloud compute snapshots describe "{{output.snapshot_id}}" --format="json" | jq -r '.status'
```

3. Record backup metadata: creation time, size, storage location

#### Failure Recovery

| Error pattern | Max retries | Agent Action | UX Feedback |
|--------------|-------------|--------------|-------------|
| `ABORTED` / operation conflict | 3, 30s backoff | Wait for conflicting operation; retry | `⚠️ Another operation is in progress. Retrying after completion...` |
| `QUOTA_EXCEEDED` | 0 | HALT | `[ERROR] Backup quota exceeded. How to fix: Delete old backups or raise quota.` |
| `FAILED_PRECONDITION` | 0 | HALT | `[ERROR] Resource not in a backup-ready state. How to fix: Wait for resource to reach stable state.` |

---

### Operation: Restore from Backup

> **Stability Pillar — Emergency Recovery:** Follow the phased runbook structure per `well-architected-assessment.md` §2.2.3.

#### Pre-flight (Safety Gate)

- **MUST** warn user: restore overwrites current data; suggest pre-restore backup
- **MUST** confirm: target resource `{{user.resource_name}}`, backup source `{{user.backup_id}}`, expected data loss window

#### Execution — CLI (`gcloud`) (Primary Path)

```bash
# Restore from snapshot/backup (adjust per product API)
gcloud compute disks create "{{user.resource_name}}-restored" \
  --source-snapshot="{{user.backup_id}}" \
  --zone="{{user.zone}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

#### Execution — JIT Go SDK (Fallback Path)

```go
req := &computepb.InsertDiskRequest{
    Project: os.Getenv("CLOUDSDK_CORE_PROJECT"),
    Zone:    zone,
    SourceSnapshot: backupID,
}
```

#### Post-execution Validation

1. Poll restore operation until terminal state (same intervals as create)
2. **Recovery verification:** run connectivity check against restored resource
3. Verify data integrity: compare row counts, checksums, or product-specific validation
4. Document actual recovery time vs target RPO

#### Failure Recovery

| Error pattern | Agent Action | UX Feedback |
|--------------|--------------|-------------|
| `NOT_FOUND` — backup not found | HALT | `[ERROR] Backup not found. How to fix: Verify backup ID with list command.` |
| `ABORTED` — conflict | Wait and retry | `⚠️ Resource has conflicting operation. Retrying...` |
| `INTERNAL` — data integrity | HALT + suggest support | `[ERROR] Restore failed. Escalate with operation ID.` |

## Prerequisites

1. **Install gcloud CLI** (primary execution path):

   ```bash
   # Official installer (auto-detects OS and architecture)
   curl https://sdk.cloud.google.com | bash
   exec -l $SHELL
   gcloud init
   
   # Or via apt (Linux)
   sudo apt-get install google-cloud-sdk
   
   # Or Homebrew (macOS)
   brew install google-cloud-sdk
   ```

2. **Bootstrap Go runtime** (for JIT SDK fallback — only needed if CLI does not support operation):

   ```bash
   # Check if Go exists
   if ! command -v go &> /dev/null; then
       # JIT download Go 1.24 (auto-detects OS and architecture)
       OS=$(uname -s | tr '[:upper:]' '[:lower:]')
       ARCH=$(uname -m)
       [ "$ARCH" = "x86_64" ] && ARCH="amd64"
       [ "$ARCH" = "aarch64" ] && ARCH="arm64"
       
       mkdir -p /tmp/go-runtime
       curl -fsSL "https://go.dev/dl/go1.24.0.${OS}-${ARCH}.tar.gz" | tar -xz -C /tmp/go-runtime
       
       export PATH="/tmp/go-runtime/go/bin:$PATH"
       export GOPATH="/tmp/go-workspace"
       export GOCACHE="/tmp/go-cache"
       export GOMODCACHE="/tmp/go-modcache"
       export GOPROXY="https://proxy.golang.org,direct"
   fi
   
   go version
   ```

   > Go version strategy: **JIT download Go 1.24+**, **Script compatibility Go 1.21+** (minimum).

3. **Configure Credentials** — Service Account (recommended for Agent execution):

   ```bash
   # Set service account key path (recommended for automation)
   export GOOGLE_APPLICATION_CREDENTIALS="{{env.GOOGLE_APPLICATION_CREDENTIALS}}"
   
   # Set project
   export CLOUDSDK_CORE_PROJECT="{{env.CLOUDSDK_CORE_PROJECT}}"
   
   # Or configure gcloud
   gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS"
   gcloud config set project "$CLOUDSDK_CORE_PROJECT"
   ```

   **Alternative — User Credentials:**
   ```bash
   gcloud auth application-default login
   ```

4. **Verify Configuration**:
   ```bash
   # Quick validation
   gcloud config list
   gcloud auth application-default print-access-token --quiet &>/dev/null && echo "✅ Auth OK"
   ```

> **Security:** Never commit service account keys to version control (already in `.gitignore`). All credentials use `{{env.*}}` placeholders in generated Skills — never real values.

## Reference Directory

- [Core Concepts](references/core-concepts.md)
- [API & SDK Usage](references/api-sdk-usage.md)
- [gcloud Usage](references/gcloud-usage.md) (**required** when `cli_applicability: cli-first` or `dual-path`; omit for `sdk-only`; basic examples for `cli-only`)
- [Troubleshooting Guide](references/troubleshooting.md)
- [Monitoring & Alerts](references/monitoring.md)
- [Integration](references/integration.md)
- [Knowledge Base](references/knowledge-base.md) — fault pattern library (AIOps diagnostic skills)
- [Observability Integration](references/observability.md) — Metrics/Logs/Traces linkage (AIOps diagnostic skills)
- [Prompts Handbook](references/prompts.md) — common prompt templates (AIOps diagnostic skills)
- [User Experience Specification](references/user-experience-spec.md) — mandatory UX compliance reference
- [AIOps Best Practices](references/aiops-best-practices.md) — mandatory AIOps patterns for monitoring/diagnosis skills
- [Optimization Analysis](references/optimization-analysis.md) — three-dimensional optimization framework
- [Execution Environment Setup](references/execution-environment.md) — CLI install, Go JIT download, credential config, verification
- [CLI Behavioral Reference](references/cli-behavior.md) — verified `gcloud` CLI conventions (--format=json, env vars, invocation patterns)
- [Enhanced Self-Healing Framework](references/enhanced-self-healing-framework.md) — **MANDATORY** self-healing patterns for all installation flows
- [Well-Architected Assessment](references/well-architected-assessment.md) — **MANDATORY** Google Cloud Architecture Framework five-pillar integration

## Operational Best Practices

- **Least privilege:** IAM roles scoped to required permissions only.
- **Availability:** Multi-region or product-specific HA patterns per docs.
- **Cost:** Right-size resources; use committed use discounts where applicable.
- **Security:** Use VPC Service Controls, IAM conditions, and CMEK for sensitive workloads.

## Token Efficiency Guidelines (P0 — 强制)

Generated skills MUST follow these 6 rules. See meta-skill SKILL.md for detailed examples.

### TE-1: API Query > Static Tables
Use gcloud commands instead of hardcoding machine type / version tables.
```bash
gcloud compute machine-types list --zone={{user.zone}} --format="json"
```
### TE-2: No docstrings in code
Inline comments only. No function-level docstring.
```go
// DO: inline comment only
func createResource() { ... }
```
### TE-3: Compact error tables
| gRPC Code | Agent Action |
|------------|-------------|
### TE-4: Centralized JSON paths
File-top comment block; one per resource type.
### TE-5: YAML anchors in example-config.yaml
Use anchors to eliminate repeated fields.
### TE-6: Eliminate cross-file duplicate flows
SKILL.md already has full flow, no Complete Workflow in config or SDK files.

---

# Appendix: Reference File Templates

## references/troubleshooting.md

```markdown
# Troubleshooting [Product Name]

## Common API Error Codes
| gRPC Code / HTTP | Meaning | Agent Action |
|-------------|---------|--------------|
| INVALID_ARGUMENT / 400 | Request failed validation | Align body with REST API |
| PERMISSION_DENIED / 403 | Insufficient IAM permissions | User grants IAM role |
| NOT_FOUND / 404 | Resource does not exist | Verify resource name |
| INTERNAL / 500 | Server-side error | Retry with backoff; then HALT |

## Diagnostic Order
1. Describe resource by name.
2. List related resources if API supports filters.
3. Check project / region / zone consistency.
4. Verify gcloud metadata coverage: `gcloud [product] --help`
```

## references/api-sdk-usage.md

```markdown
# API & SDK — [Product Name]

## REST API
- Discovery doc: `https://[product].googleapis.com/$discovery/rest?version=v1`
- Base URL: `https://[product].googleapis.com/v1/`

## SDK Operations Map
| Goal | REST Method & Path | Go SDK Method |
|------|-------------------|---------------|
| Create | `POST /v1/projects/{project}/...` | `Create[Resource]` |
| Describe | `GET /v1/projects/{project}/.../{resource}` | `Get[Resource]` |

## Request / Response Notes
- Required fields: …
- Pagination: `pageToken` in request, `nextPageToken` in response
```

## references/gcloud-usage.md

```markdown
# gcloud — [Product Name] CLI

## Install and config
- Install: see [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
- **CRITICAL Credentials:** Set `GOOGLE_APPLICATION_CREDENTIALS` or run `gcloud auth login`

## Conventions (agent execution)
- Always use `--format=json` for machine-parseable output
- Use `jq` for field extraction from JSON output
- Long-running operations return immediately; poll via describe/Operations API

## CLI vs API coverage gap
| Operation (REST API) | Available via `gcloud`? | Notes |
|------------------------|---------------------|-------|
| Create | yes / no | … |
| Describe | yes / no | … |

## Command map
| Goal | Example `gcloud` invocation | Notes |
|------|--------------------------|-------|
| Create | `gcloud [product] [resources] create [NAME] --project={{env.CLOUDSDK_CORE_PROJECT}} --format=json` | JSON output |
| Describe | `gcloud [product] [resources] describe [NAME] --project={{env.CLOUDSDK_CORE_PROJECT}} --format=json` | JSON output |
| List | `gcloud [product] [resources] list --project={{env.CLOUDSDK_CORE_PROJECT}} --format=json` | JSON output |
```

## references/monitoring.md

```markdown
# Monitoring [Product Name]

## Key Metrics (examples — replace with product namespaces)
- Metric A: `[product].googleapis.com/[metric]`
- Metric B: `[product].googleapis.com/[metric]`

## Cloud Monitoring Setup
- Dashboards: ...
- Alert policies: ...
```

## references/integration.md

````markdown
# Integration

## Environment Setup

**Primary path:** `gcloud` CLI (Google Cloud SDK, Python-based)

**Fallback path:** JIT Go SDK (dynamic script generation + `go run`)

### Go Runtime Bootstrap

If Agent Runtime lacks Go, JIT download from official source:

```bash
# Check Go runtime
if ! command -v go &> /dev/null; then
    OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    ARCH=$(uname -m)
    [ "$ARCH" = "x86_64" ] && ARCH="amd64"
    [ "$ARCH" = "aarch64" ] && ARCH="arm64"
    
    mkdir -p /tmp/go-runtime
    curl -fsSL "https://go.dev/dl/go1.24.0.${OS}-${ARCH}.tar.gz" | tar -xz -C /tmp/go-runtime
    export PATH="/tmp/go-runtime/go/bin:$PATH"
    export GOPATH="/tmp/go-workspace"
    export GOCACHE="/tmp/go-cache"
fi

go version
```

> **Go version strategy:**
> - **JIT download:** Go 1.24+ (latest stable)
> - **Script compatibility:** Go 1.21+ (minimum)

### JIT Go SDK Workflow

1. **Initialize workspace:**
   ```bash
   mkdir -p /tmp/gcp-sdk-workspace
   cd /tmp/gcp-sdk-workspace
   go mod init sdk-script
   ```

2. **Get dependencies:**
   ```bash
   export GOPROXY="https://proxy.golang.org,direct"
   
   # Core dependencies
   go get google.golang.org/api/option
   go get google.golang.org/genproto
   
   # Product-specific SDK
   go get cloud.google.com/go/[product]/apiv1
   ```

3. **Generate script** (Agent dynamically creates operation-specific .go file)

4. **Execute:**
   ```bash
   go run ./main.go
   ```

### SDK Package Naming

| GCP Product | Go SDK Package |
|-------------|---------------|
| Compute Engine | `cloud.google.com/go/compute/apiv1` |
| Cloud SQL | `cloud.google.com/go/sql/apiv1` |
| Cloud Storage | `cloud.google.com/go/storage` |
| Cloud Run | `cloud.google.com/go/run/apiv2` |
| GKE | `cloud.google.com/go/container/apiv1` |

> Find package names at: https://pkg.go.dev/cloud.google.com/go

## Environment Variable Loading

Credentials can be sourced from multiple locations:

```
Shell env (highest) > `.env` file > gcloud config (lowest)
```

### `.env` File Format

```ini
# Google Cloud credentials
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
CLOUDSDK_CORE_PROJECT=my-gcp-project
```

- **Security**: `.env` MUST be in `.gitignore` — never commit credentials

### Go `.env` Loading (optional)

```go
package main

import (
    "os"
    "github.com/joho/godotenv"
)

func init() {
    godotenv.Load(".env") // Optional: load .env if present
}

func main() {
    creds := os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")
    project := os.Getenv("CLOUDSDK_CORE_PROJECT")
    // ...
}
```

## Go SDK Script Template

```go
// main.go (single-file script template)
package main

import (
    "context"
    "fmt"
    "log"
    "os"
    
    "google.golang.org/api/option"
    [product] "cloud.google.com/go/[product]/apiv1"
    [product]pb "cloud.google.com/go/[product]/apiv1/[product]pb"
)

func main() {
    ctx := context.Background()
    
    client, err := [product].NewClient(ctx,
        option.WithCredentialsFile(os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")))
    if err != nil {
        log.Fatalf("Failed to create client: %v", err)
    }
    defer client.Close()
    
    // Operation-specific code (generated per REST API)
    req := &[product]pb.List[Resources]Request{
        Parent: fmt.Sprintf("projects/%s", os.Getenv("CLOUDSDK_CORE_PROJECT")),
    }
    
    resp, err := client.List[Resources](ctx, req)
    if err != nil {
        log.Fatalf("Failed to list: %v", err)
    }
    
    for _, r := range resp.Items {
        fmt.Println(r.Name)
    }
}
```

> Use `os.Getenv("KEY")` for all credentials. Never hardcode secrets in scripts.
````