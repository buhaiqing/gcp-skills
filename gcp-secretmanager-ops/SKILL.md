---
name: gcp-secretmanager-ops
description: >-
  Use when the user needs to manage, configure, troubleshoot, or monitor Google
  Cloud Secret Manager resources — secrets, secret versions, rotation, access,
  replication, IAM policy bindings, and Pub/Sub notification topics. User mentions
  Secret Manager, secrets, secret version, secret rotation, secret access, or
  describes secret management scenarios (e.g., "store API key", "rotate secret",
  "secret won't access", "create secret with automatic replication") even without
  naming the product directly. Not for Cloud KMS (encryption keys, key rotation,
  CMEK) which has its own ops skill.
license: MIT
compatibility: >-
  Official Google Cloud CLI (`gcloud`, Python-based SDK), Go 1.21+ runtime
  (for JIT SDK fallback), valid service account credentials with Secret Manager
  Admin or Secret Manager Secret Accessor IAM role, network access to Google
  Cloud endpoints.
metadata:
  author: gcp-skills
  version: "1.0.0"
  last_updated: "2026-06-07"
  runtime: Harness AI Agent, Claude Code, or compatible Agent runtimes
  go_version_minimum: "1.21"
  go_version_jit: "1.24+"
  api_profile: "https://secretmanager.googleapis.com/$discovery/rest?version=v1"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    gcloud secrets --help confirms subcommands: create, describe, update,
    delete, list, versions add/destroy/disable/enable/access/list/describe,
    add-iam-policy-binding, remove-iam-policy-binding, add-topic, remove-topic,
    replication set. See https://cloud.google.com/sdk/gcloud/reference/secrets
  environment:
    - GOOGLE_APPLICATION_CREDENTIALS
    - CLOUDSDK_CORE_PROJECT
    - CLOUDSDK_AUTH_ACCESS_TOKEN
---

> This skill follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Google Cloud Secret Manager Operations Skill

## Overview

Google Cloud Secret Manager provides centralized secret storage, version management, and access control — secrets with automatic or user-managed replication, secret versions, rotation policies, Pub/Sub notification topics, and fine-grained IAM controls. This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **dual-path execution** (official **SDK/API** and **`gcloud`** CLI), response validation, and failure recovery.

> **UX Compliance:** This skill follows the [User Experience Specification](../gcp-skill-generator/references/user-experience-spec.md). All operations include onboarding guidance, minimal prompts, smart defaults, clear feedback, and user-friendly error handling.

### CLI applicability (repository policy)

- **`cli_applicability: dual-path`:** Official `gcloud` fully supports Secret Manager via `gcloud secrets`, `gcloud secrets versions`, etc. You MUST ship both **`references/gcloud-usage.md`** and, in each execution flow below, document **both** the SDK step **and** the `gcloud` step for every operation. Coverage gaps (SDK-only operations) are listed in `references/gcloud-usage.md`.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use conditions with precise triggers and delegation rules |
| 2 | **Structured I/O** | Placeholder conventions (`{{env.*}}`, `{{user.*}}`, `{{output.*}}`) with type and source documented |
| 3 | **Explicit Actionable Steps** | Every operation: Pre-flight → Execute → Validate → Recover, with numbered imperative steps |
| 4 | **Complete Failure Strategies** | Error taxonomy table with ≥ 12 product-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | One product (Secret Manager) with clear delegation to related skills (KMS, IAM, Logging) |

Refer to the [meta-skill](../gcp-skill-generator/SKILL.md#five-core-standards-quality-gates) for detailed descriptions of each standard.

### Google Cloud Architecture Framework Integration

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **Security** | IAM permissions (roles/secretmanager.admin), replication config, secret access controls, Pub/Sub notification topics | `references/well-architected-assessment.md` §2.1 |
| **Stability** | Secret version lifecycle, rotation policies, multi-region replication, deletion safeguards | `references/well-architected-assessment.md` §2.2 |
| **Cost** | Active secret cost, version storage cost, API call cost, automatic vs user-managed replication | `references/well-architected-assessment.md` §2.3 |
| **Efficiency** | Secret organization with labels, batch access patterns, rotation automation | `references/well-architected-assessment.md` §2.4 |
| **Performance** | Access latency, replication lag, rate limits per secret | `references/well-architected-assessment.md` §2.5 |

See [references/well-architected-assessment.md](references/well-architected-assessment.md) for the complete specification.

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "Secret Manager", "secrets", "secret version", "secret rotation"
- Task involves CRUD or lifecycle operations on **secrets** (create, describe, update, delete, list)
- Task involves **secret versions** (add, access, list, describe, destroy, disable, enable)
- Task involves **secret rotation** (rotation schedule, automatic rotation)
- Task involves **replication** (automatic multi-region, user-managed per-region)
- Task involves **Pub/Sub notification topics** (add-topic, remove-topic)
- Task involves **IAM policy** on secrets (add-iam-policy-binding, remove-iam-policy-binding)
- Keywords: secret, secret manager, API key storage, password storage, credential storage, secret rotation, secret access

### SHOULD NOT Use This Skill When

- Task is about encryption keys, key rotation, CMEK → delegate to: `gcp-kms-ops`
- Task is purely about IAM / service accounts → delegate to: `gcp-iam-ops`
- Task is about Pub/Sub topics/subscriptions management → delegate to: `gcp-pubsub-ops`
- Task is purely about compute instance disk encryption → delegate to: `gcp-gce-ops`
- User insists on **console-only** flows with no API → state limitation; do not invent undocumented gcloud steps

### Delegation Rules

- **KMS for CMEK secrets**: For user-managed replication using CMEK keys, verify KMS key exists via `gcp-kms-ops` before creating secret.
- **IAM on Secrets**: Use `gcloud secrets add-iam-policy-binding` within this skill for non-default IAM bindings.
- **Monitoring/Alerts**: For Secret Manager Cloud Monitoring metrics, delegate to `gcp-monitoring-ops`.
- **GCL**: Execution quality gate uses `gcp-gcl-runner-ops`.

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.GOOGLE_APPLICATION_CREDENTIALS}}` | Path to SA key JSON | NEVER ask the user; fail if unset |
| `{{env.CLOUDSDK_CORE_PROJECT}}` | GCP project ID | NEVER ask the user; fail if unset |
| `{{env.CLOUDSDK_AUTH_ACCESS_TOKEN}}` | Temporary access token | NEVER ask the user; fail if needs refresh |
| `{{user.project}}` | User-supplied project (override) | Ask once; reuse |
| `{{user.location}}` | Secret location (for user-managed replication, e.g., us-central1) | Ask once; reuse; default: global (automatic) |
| `{{user.secret_id}}` | Secret name/ID | Ask once; reuse |
| `{{user.secret_data}}` | Secret payload (string or file path) | Ask once; reuse |
| `{{user.secret_data_file}}` | Path to file containing secret payload | Ask once; reuse |
| `{{user.version_id}}` | Secret version number | Ask once; reuse |
| `{{user.labels}}` | Secret labels (key=value pairs) | Ask once; reuse |
| `{{user.ttl}}` | Secret version TTL (e.g., 30d, 7776000s) | Ask once; reuse |
| `{{user.rotation_period}}` | Rotation period (e.g., 30d, 2592000s) | Ask once; reuse |
| `{{user.next_rotation_time}}` | Next rotation time (RFC 3339) | Ask once; reuse |
| `{{user.topic_id}}` | Pub/Sub topic ID for notifications | Ask once; reuse |
| `{{user.replication}}` | Replication type (automatic/user-managed) | Ask once; reuse; default: automatic |
| `{{output.secret_name}}` | From create/describe secret | Parse from JSON path `$.name` |
| `{{output.latest_version}}` | From describe secret | Parse from JSON path `$.versionAliases.latest` |
| `{{output.version_state}}` | From describe version | Parse from JSON path `$.state` |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning (Credential Masking — MANDATORY):** NEVER log, print, or expose service account key content, `GOOGLE_APPLICATION_CREDENTIALS` path content, or any secret payload value in console output, debug messages, error messages, or logs.

| Execution Path | Safe Pattern | Unsafe Pattern |
|----------------|-------------|----------------|
| Console output | `GOOGLE_APPLICATION_CREDENTIALS=<masked>` | `{"private_key": "-----BEGIN...` |
| Error messages | `Error: API call failed (credential omitted)` | `Error: ... actual SA key content...` |
| Secret payload display | `Secret payload stored (****)` | `Secret payload: my-api-key-12345` |
| Log files | `[INFO] Secret created: {{user.secret_id}}` | `[INFO] Secret data: actual-value` |
| Go SDK | `option.WithCredentialsFile(os.Getenv("..."))` (env read is safe) | `fmt.Printf("Config: %+v", config)` or `log.Printf("%+v", ...)` |

## API and Response Conventions (Agent-Readable)

- **REST API is canonical**: Secret Manager v1 API (`secretmanager.googleapis.com`). All JSON paths below are verified against the official REST API reference.
- **Errors**: Map HTTP/gRPC status codes to canonical error types.
- **Timestamps**: RFC 3339 (e.g., `2026-06-07T10:00:00.000Z`).
- **Idempotency**: Secret names are project-unique.

### Key JSON Paths (Centralized per TE-4)

| Operation | JSON Path | Type | Description |
|-----------|-----------|------|-------------|
| Create Secret | `$.{name,createTime,replication}` | object | Secret details |
| Describe Secret | `$.{name,createTime,labels,replication,rotation,versionAliases}` | object | Secret configuration |
| List Secrets | `$.secrets[].{name,createTime,replication}` | array | Secret list |
| Add Version | `$.{name,createTime,version}` | object | New version details |
| Access Version | `$.payload.data` (base64) | string | Secret payload |
| Describe Version | `$.{name,state,createTime}` | object | Version state |
| List Versions | `$.versions[].{name,state,createTime}` | array | Version list |

### Expected State Transitions

| Operation | Initial State | Target State | Poll Interval | Max Wait |
|-----------|---------------|--------------|---------------|----------|
| Create Secret | — | ACTIVE | Immediate | — |
| Add Version | — | ENABLED | Immediate | — |
| Disable Version | ENABLED | DISABLED | Immediate | — |
| Enable Version | DISABLED | ENABLED | Immediate | — |
| Destroy Version | ENABLED/DISABLED | DESTROYED | 5s | 30s |

## Quick Start

### What This Skill Does
This skill enables you to manage secrets — secret creation, versions, rotation, access, replication — on Google Cloud using the `gcloud` CLI (primary) or Go SDK (fallback).

### Prerequisites
- [ ] `gcloud` CLI installed (or Go runtime for JIT fallback)
- [ ] Service account key configured: `GOOGLE_APPLICATION_CREDENTIALS`
- [ ] Project set: `gcloud config set project <project-id>` or `CLOUDSDK_CORE_PROJECT`
- [ ] IAM roles: `roles/secretmanager.admin` (management) or `roles/secretmanager.secretAccessor` (access)

### Verify Setup
```bash
# Check gcloud and project
gcloud config get-value project
gcloud auth application-default print-access-token --quiet &>/dev/null && echo "✅ Auth OK"

# Quick list to verify Secret Manager API access
gcloud secrets list --project="{{env.CLOUDSDK_CORE_PROJECT}}" --limit=1 --format="json" &>/dev/null && echo "✅ Secret Manager API OK"
```

### Your First Command
```bash
# Create a secret
gcloud secrets create "my-api-key" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --replication-policy="automatic" \
  --data-file=- <<< "my-secret-value" \
  --format="json"
```

### Next Steps
- [Core Concepts](references/core-concepts.md) — Secret Manager architecture, replication, rotation
- [Common Operations](#execution-flows) — Create secrets, manage versions, access secrets
- [Troubleshooting](references/troubleshooting.md) — Fix common issues

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| Secret Create | Create a new secret with payload | Low | Low |
| Secret Describe | View secret details | Low | None |
| Secret Update | Update labels, rotation, topics | Medium | Low |
| Secret Delete | Delete a secret and all versions | Low | **High** — irreversible |
| Version Add | Add a new secret version | Low | Low |
| Version Access | Read secret version payload | Low | None |
| Version Disable | Disable a secret version | Low | Medium |
| Version Enable | Re-enable a disabled version | Low | Low |
| Version Destroy | Permanently destroy a version | Low | **High** — irreversible |
| Replication Set | Configure replication policy | Medium | Medium |
| Topic Add | Add Pub/Sub notification topic | Low | Low |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-07 | Initial release: Secret Manager secret, version, rotation, replication, topic operations with dual-path gcloud+SDK, GCL quality gate |

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (gcloud + SDK/API) → Validate → Recover**. Do not skip phases.

### Operation: Create Secret

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| gcloud CLI | `gcloud version` | Exit code 0 | HALT — install gcloud SDK |
| Credentials | `gcloud auth print-access-token` | Token returned | HALT — authenticate |
| Project | `gcloud config get-value project` | Set and valid | HALT — set project |
| Secret Manager API | `gcloud services list --enabled \| grep secretmanager.googleapis.com` | Enabled | HALT — enable `secretmanager.googleapis.com` |
| Secret name unique | `gcloud secrets describe "{{user.secret_id}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --quiet` | NOT_FOUND (exit != 0) | HALT — name in use |

#### Execution — CLI (`gcloud`) (Primary Path)

```bash
# Create secret with inline data
gcloud secrets create "{{user.secret_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --replication-policy="{{user.replication:-automatic}}" \
  --data-file=- <<< "{{user.secret_data}}" \
  --labels="{{user.labels}}" \
  --format="json"

# Create secret from file
gcloud secrets create "{{user.secret_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --replication-policy="{{user.replication:-automatic}}" \
  --data-file="{{user.secret_data_file}}" \
  --format="json"
```

#### Execution — Python SDK (Primary Fallback)

```python
# create_secret.py
import os
from google.cloud import secretmanager_v1 as sm
client = sm.SecretManagerServiceClient()
parent = f"projects/{os.environ['CLOUDSDK_CORE_PROJECT']}"
secret = sm.Secret(replication=sm.Replication(automatic=sm.Replication.Automatic()))
request = sm.CreateSecretRequest(parent=parent, secret_id="{{user.secret_id}}", secret=secret)
response = client.create_secret(request=request)
print(f"Created secret: {response.name}")
# Add version
version_request = sm.AddSecretVersionRequest(parent=response.name, payload=sm.SecretPayload(data=b"{{user.secret_data}}"))
version_response = client.add_secret_version(request=version_request)
print(f"Added version: {version_response.name}")
```

#### Execution — JIT Go SDK (Secondary Fallback)

```go
package main
import (
    "context"
    "fmt"
    "log"
    "os"
    sm "cloud.google.com/go/secretmanager/apiv1"
    smpb "cloud.google.com/go/secretmanager/apiv1/secretmanagerpb"
    "google.golang.org/api/option"
)
func main() {
    ctx := context.Background()
    project := os.Getenv("CLOUDSDK_CORE_PROJECT")
    client, err := sm.NewClient(ctx,
        option.WithCredentialsFile(os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")))
    if err != nil { log.Fatalf("NewClient: %v", err) }
    defer client.Close()
    req := &smpb.CreateSecretRequest{
        Parent:   fmt.Sprintf("projects/%s", project),
        SecretId: "{{user.secret_id}}",
        Secret:   &smpb.Secret{Replication: &smpb.Replication{Automatic: &smpb.Replication_Automatic{}}},
    }
    resp, err := client.CreateSecret(ctx, req)
    if err != nil { log.Fatalf("CreateSecret: %v", err) }
    fmt.Printf("Created secret: %s\n", resp.Name)
}
```

#### Post-execution Validation

```bash
gcloud secrets describe "{{user.secret_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{name, createTime, replication}'
```

#### Failure Recovery

| Error Code | Max retries | Agent Action | UX Feedback |
|------------|-------------|--------------|-------------|
| INVALID_ARGUMENT / 400 | 1 | Fix secret ID format | `[ERROR] Invalid secret ID (must match [a-zA-Z0-9_-]+)` |
| PERMISSION_DENIED / 403 | 0 | HALT | `[ERROR] SA lacks roles/secretmanager.admin` |
| ALREADY_EXISTS / 409 | 0 | Ask rename | `[ERROR] Secret already exists` |
| QUOTA_EXCEEDED / 429 | 0 | HALT | `[ERROR] Secret quota exceeded` |
| UNAVAILABLE / 503 | 3 | exp. backoff | `⚠️ Service unavailable. Retrying...` |
| INTERNAL / 500 | 3 | 2/4/8s Retry | `[ERROR] Internal error — escalate if persistent` |

---

### Operation: Add Secret Version

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Secret exists | `gcloud secrets describe "{{user.secret_id}}"` | Exit 0 | HALT — create secret first |
| Payload provided | Data or file not empty | Non-empty | HALT — provide payload |
| Payload size | File size check | ≤ 64KB | HALT — use Cloud Storage for large data |

#### Execution — CLI (`gcloud`)

```bash
gcloud secrets versions add "{{user.secret_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --data-file=- <<< "{{user.secret_data}}" \
  --format="json"
```

#### Post-execution Validation

```bash
gcloud secrets versions list "{{user.secret_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --limit=3 \
  --format="json" | jq '.[].{name,state,createTime}'
```

---

### Operation: Access Secret Version

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Secret exists | Describe secret | Exit 0 | HALT — secret not found |
| Version enabled | `.state == "ENABLED"` on target version | ENABLED | HALT — version disabled/destroyed |

#### Execution — CLI (`gcloud`)

```bash
# Access latest version
gcloud secrets versions access latest \
  --secret="{{user.secret_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"

# Access specific version
gcloud secrets versions access "{{user.version_id}}" \
  --secret="{{user.secret_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

> **Security:** Secret payload is returned in response. Do NOT log or echo the payload value.

---

### Operation: Delete Secret

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit user confirmation: deletion of secret `{{user.secret_id}}` will permanently remove the secret and ALL its versions
- **MUST** warn: this operation is IRREVERSIBLE — all versions and data will be permanently lost
- **MUST** show current secret details before proceeding

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Secret exists | Describe secret | Exit 0 | HALT — not found |
| Version count | `gcloud secrets versions list` | Show count | Warn user of version count |
| User confirmation | Ask: `Proceed with deletion? (yes/secret_id)` | Exact match | HALT — abort |

#### Execution — CLI (`gcloud`)

```bash
gcloud secrets delete "{{user.secret_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

**Never use `--quiet` to bypass this safety gate.**

#### Post-execution Validation

```bash
gcloud secrets describe "{{user.secret_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --quiet 2>/dev/null
# Expected: NOT_FOUND (exit != 0) confirms deletion
```

#### Failure Recovery

| Error Code | Max retries | Agent Action | UX Feedback |
|------------|-------------|--------------|-------------|
| NOT_FOUND / 404 | 0 | Already deleted | `[ERROR] Secret not found` |
| PERMISSION_DENIED / 403 | 0 | HALT | `[ERROR] Insufficient permissions` |

---

### Operation: Destroy Secret Version

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit user confirmation: destruction of version `{{user.version_id}}` for secret `{{user.secret_id}}`
- **MUST** warn: destruction is IRREVERSIBLE — the version data cannot be recovered
- **MUST** show current version state before proceeding

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Version exists | Describe version | Exit 0 | HALT — not found |
| Current state | `.state` is ENABLED or DISABLED | Can be destroyed | HALT — already destroyed |
| User confirmation | Ask: `Proceed with version destruction? (yes/version_id)` | Exact match | HALT — abort |

#### Execution — CLI (`gcloud`)

```bash
gcloud secrets versions destroy "{{user.version_id}}" \
  --secret="{{user.secret_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

**Never use `--quiet` to bypass this safety gate.**

---

### Operation: Disable/Enable Secret Version

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Version exists | Describe version | Exit 0 | HALT — not found |
| Current state | `.state` | Not already in target state | HALT — already in target state |

#### Execution — CLI (`gcloud`)

```bash
# Disable
gcloud secrets versions disable "{{user.version_id}}" \
  --secret="{{user.secret_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"

# Enable
gcloud secrets versions enable "{{user.version_id}}" \
  --secret="{{user.secret_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

---

### Operation: Update Secret (Rotation, Labels, Topics)

#### Execution — CLI (`gcloud`)

```bash
# Update rotation schedule
gcloud secrets update "{{user.secret_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --rotation-period="{{user.rotation_period}}" \
  --next-rotation-time="{{user.next_rotation_time}}" \
  --format="json"

# Remove rotation
gcloud secrets update "{{user.secret_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --remove-rotation \
  --format="json"

# Update labels
gcloud secrets update "{{user.secret_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --update-labels="{{user.labels}}" \
  --format="json"

# Add Pub/Sub notification topic
gcloud secrets add-topic "{{user.secret_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --topic="projects/{{env.CLOUDSDK_CORE_PROJECT}}/topics/{{user.topic_id}}" \
  --format="json"
```

#### Post-execution Validation

```bash
gcloud secrets describe "{{user.secret_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{rotation, labels, topics}'
```

## Prerequisites

> **Self-Healing:** Installation flows include multi-path recovery per [enhanced-self-healing-framework.md](../gcp-skill-generator/references/enhanced-self-healing-framework.md).

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
           pip install --quiet --user google-cloud-secret-manager
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
   gcloud secrets list --project="{{env.CLOUDSDK_CORE_PROJECT}}" --limit=1 --format="json" &>/dev/null && echo "✅ Secret Manager API OK"
   ```

> **Security:** Never commit service account keys to version control. All credentials use `{{env.*}}` placeholders.

## Reference Directory

- [Core Concepts](references/core-concepts.md) — Architecture, replication, rotation, security
- [API & SDK Usage](references/api-sdk-usage.md) — REST API, Python SDK, operation map
- [gcloud Usage](references/gcloud-usage.md) — `gcloud secrets` command map
- [Troubleshooting Guide](references/troubleshooting.md) — Error codes, diagnostics, recovery
- [Integration](references/integration.md) — Go SDK bootstrap, env vars, credential rules
- [Well-Architected Assessment](references/well-architected-assessment.md) — Five-pillar assessment
- [Rubric — GCL](references/rubric.md) — Generator-Critic-Loop scoring rubric
- [Prompt Templates — GCL](references/prompt-templates.md) — GCL generator and critic templates

## Operational Best Practices

- **Least privilege:** Use `roles/secretmanager.secretAccessor` for read access; `roles/secretmanager.admin` for management
- **Rotation:** Enable automatic rotation for high-value secrets (API keys, passwords); document rotation schedule
- **Secret destruction:** Always confirm with user; version destruction is irreversible
- **Security:** Use user-managed replication with CMEK for compliance workloads; enable VPC Service Controls
- **Naming:** Follow `{env}-{purpose}-secret` convention; use labels for metadata and cost tracking
- **Topics:** Configure Pub/Sub notification topics for secret rotation alerts and access monitoring

## Quality Gate (GCL)

> This skill implements the **Generator-Critic-Loop (GCL)** adversarial quality gate per `AGENTS.md §11`.

| Property | Value |
|----------|-------|
| Classification | **required** (Secret/Version delete/destroy operations present) |
| max_iter | 2 |
| Most-scrutinized operations | Delete Secret, Destroy Secret Version |

- **Rubric**: [references/rubric.md](references/rubric.md) — 5 core dimensions + 3 GCP extensions
- **Prompt Templates**: [references/prompt-templates.md](references/prompt-templates.md) — Generator + Critic templates

## Token Efficiency Guidelines (P0 — 强制)

### TE-1: API Query > Static Tables
Use gcloud to fetch live data:
```bash
gcloud secrets list --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"
gcloud secrets versions list "{{user.secret_id}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"
```

### TE-2: No docstrings in code
Inline comments only; no function-level docstrings in SDK snippets.

### TE-3: Compact error tables
Error tables use 1 row per code, ≤ 3 columns.

### TE-4: Centralized JSON paths
See [Key JSON Paths](#key-json-paths-centralized-per-te-4) at top of Execution Flows section.

### TE-5: YAML anchors
Use `&anchor` in example-config.yaml to eliminate duplication.

### TE-6: Eliminate cross-file duplication
SKILL.md has full flow; references/ doesn't repeat execution steps — only expands concepts, diagnostics, and monitoring.

### TE-7: Layer professional content
Advanced AIOps/FinOps topics in `references/advanced/` (future expansion).