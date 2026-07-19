---
name: gcp-kms-ops
description: >-
  Use when the user needs to manage, configure, troubleshoot, or monitor Google
  Cloud KMS (Key Management Service) resources — key rings, crypto keys, key
  versions, key rotation, encryption, decryption, and IAM policy bindings. User
  mentions Cloud KMS, KMS, key ring, crypto key, encryption key, CMEK, HSM key,
  key rotation, or describes key management scenarios (e.g., "create encryption
  key", "rotate keys", "encrypt file", "key won't decrypt", "CMEK setup") even
  without naming the product directly. Not for Secret Manager (secrets, versions,
  rotation) or Cloud HSM directly that have their own ops skills.
license: MIT
compatibility: >-
  Official Google Cloud CLI (`gcloud`, Python-based SDK), Go 1.21+ runtime
  (for JIT SDK fallback), valid service account credentials with Cloud KMS Admin
  or Cloud KMS CryptoKey Encrypter/Decrypter IAM role, network access to Google
  Cloud endpoints.
metadata:
  author: gcp-skills
  version: "1.0.0"
  last_updated: "2026-06-07"
  runtime: Harness AI Agent, Claude Code, or compatible Agent runtimes
  go_version_minimum: "1.21"
  go_version_jit: "1.24+"
  api_profile: "https://cloudkms.googleapis.com/$discovery/rest?version=v1"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    gcloud kms --help confirms subcommands: keyrings, keys, keys versions,
    encrypt, decrypt, sign, verify, import-jobs. See
    https://cloud.google.com/sdk/gcloud/reference/kms
  environment:
    - GOOGLE_APPLICATION_CREDENTIALS
    - CLOUDSDK_CORE_PROJECT
    - CLOUDSDK_AUTH_ACCESS_TOKEN
---

> This skill follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Google Cloud KMS Operations Skill

## Overview

Google Cloud KMS provides cryptographic key management for Google Cloud services and customer applications — key rings, crypto keys, key versions, rotation policies, encryption/decryption, and IAM controls. This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **dual-path execution** (official **SDK/API** and **`gcloud`** CLI), response validation, and failure recovery.

> **UX Compliance:** This skill follows the [User Experience Specification](../gcp-skill-generator/references/user-experience-spec.md). All operations include onboarding guidance, minimal prompts, smart defaults, clear feedback, and user-friendly error handling.

### CLI applicability (repository policy)

- **`cli_applicability: dual-path`:** Official `gcloud` fully supports Cloud KMS via `gcloud kms keyrings`, `gcloud kms keys`, `gcloud kms encrypt`, `gcloud kms decrypt`, etc. You MUST ship both **`references/gcloud-usage.md`** and, in each execution flow below, document **both** the SDK step **and** the `gcloud` step for every operation. Coverage gaps (SDK-only operations) are listed in `references/gcloud-usage.md`.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use conditions with precise triggers and delegation rules |
| 2 | **Structured I/O** | Placeholder conventions (`{{env.*}}`, `{{user.*}}`, `{{output.*}}`) with type and source documented |
| 3 | **Explicit Actionable Steps** | Every operation: Pre-flight → Execute → Validate → Recover, with numbered imperative steps |
| 4 | **Complete Failure Strategies** | Error taxonomy table with ≥ 12 product-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | One product (Cloud KMS) with clear delegation to related skills (IAM, Secret Manager, Logging) |

Refer to the [meta-skill](../gcp-skill-generator/SKILL.md#five-core-standards-quality-gates) for detailed descriptions of each standard.

### Google Cloud Architecture Framework Integration

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **Security** | IAM permissions (roles/cloudkms.admin), key rotation policies, key destruction safeguards, CMEK integration | `references/well-architected-assessment.md` §2.1 |
| **Stability** | Key version lifecycle, automatic rotation, multi-region key rings, import key material | `references/well-architected-assessment.md` §2.2 |
| **Cost** | Key version cost, HSM vs software keys, key rotation cost | `references/well-architected-assessment.md` §2.3 |
| **Efficiency** | Key ring organization, key labeling, batch operations, rotation automation | `references/well-architected-assessment.md` §2.4 |
| **Performance** | Encrypt/decrypt latency, HSM vs software throughput, key caching | `references/well-architected-assessment.md` §2.5 |

See [references/well-architected-assessment.md](references/well-architected-assessment.md) for the complete specification.

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "Cloud KMS", "KMS", "key management", "key ring", "crypto key", "encryption key", "CMEK"
- Task involves CRUD or lifecycle operations on **key rings** (create, describe, list)
- Task involves **crypto keys** (create, describe, update, destroy, restore, list)
- Task involves **key versions** (list, destroy, restore, enable, disable)
- Task involves **encryption/decryption** (encrypt, decrypt, asymmetric sign, asymmetric decrypt)
- Task involves **key rotation** (schedule rotation, automatic rotation)
- Task involves **import** of key material (import job, import key version)
- Keywords: key, encrypt, decrypt, KMS, CMEK, HSM, signing, key rotation, key ring, crypto key

### SHOULD NOT Use This Skill When

- Task is purely about Secret Manager (secrets, versions, rotation) → delegate to: `gcp-secretmanager-ops`
- Task is purely about IAM / service accounts → delegate to: `gcp-iam-ops`
- Task is purely about Cloud HSM directly (KMS is the interface to HSM) → use this skill
- Task is purely about compute instance disk encryption (CMEK in GCE) → delegate to: `gcp-gce-ops`
- User insists on **console-only** flows with no API → state limitation; do not invent undocumented gcloud steps

### Delegation Rules

- **IAM on Keys**: For non-default IAM bindings on KMS keys, use `gcloud kms keys add-iam-policy-binding` within this skill.
- **Secret Manager**: For storing encrypted values, delegate to `gcp-secretmanager-ops`.
- **Monitoring/Alerts**: For Cloud Monitoring, delegate to `gcp-monitoring-ops`.
- **GCL**: Execution quality gate uses `gcp-gcl-runner-ops`.

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.GOOGLE_APPLICATION_CREDENTIALS}}` | Path to SA key JSON | NEVER ask the user; fail if unset |
| `{{env.CLOUDSDK_CORE_PROJECT}}` | GCP project ID | NEVER ask the user; fail if unset |
| `{{env.CLOUDSDK_AUTH_ACCESS_TOKEN}}` | Temporary access token | NEVER ask the user; fail if needs refresh |
| `{{user.project}}` | User-supplied project (override) | Ask once; reuse |
| `{{user.location}}` | KMS location (e.g., global, us-central1) | Ask once; reuse; default: global |
| `{{user.keyring_name}}` | Key ring name | Ask once; reuse |
| `{{user.key_name}}` | Crypto key name | Ask once; reuse |
| `{{user.key_version}}` | Key version number | Ask once; reuse |
| `{{user.protection_level}}` | software / hsm / external | Ask once; reuse; default: software |
| `{{user.purpose}}` | encryption / asymmetric-signing / etc. | Ask once; reuse; default: encryption |
| `{{user.rotation_period}}` | Rotation period (e.g., 7776000s, 90d) | Ask once; reuse |
| `{{user.next_rotation_time}}` | Next rotation (e.g., 2027-01-01T00:00:00Z) | Ask once; reuse |
| `{{user.plaintext_file}}` | Path to plaintext file | Ask once; reuse |
| `{{user.ciphertext_file}}` | Output path for ciphertext | Ask once; reuse; default: ciphertext.bin |
| `{{user.algorithm}}` | Encryption algorithm | Ask once; reuse |
| `{{output.key_primary_version}}` | From describe key | Parse from JSON path `$.primary.name` |
| `{{output.key_state}}` | From describe key version | Parse from JSON path `$.state` |
| `{{output.ciphertext_base64}}` | From encrypt result | Parse from JSON path `$.ciphertext` |

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

- **REST API is canonical**: Cloud KMS v1 API (`cloudkms.googleapis.com`). All JSON paths below are verified against the official REST API reference.
- **Errors**: Map HTTP/gRPC status codes to canonical error types.
- **Timestamps**: RFC 3339 (e.g., `2026-06-07T10:00:00.000Z`).
- **Idempotency**: Key rings and keys are location-unique.

### Key JSON Paths (Centralized per TE-4)

| Operation | JSON Path | Type | Description |
|-----------|-----------|------|-------------|
| Create Key Ring | `$.{name,createTime}` | object | Key ring details |
| List Key Rings | `$.keyRings[].{name,createTime}` | array | Key ring list |
| Create Key | `$.{name,primary,versionTemplate,purpose}` | object | Key details |
| Describe Key | `$.{name,primary,rotationPeriod,nextRotationTime,labels}` | object | Key configuration |
| List Keys | `$.cryptoKeys[].{name,primary,purpose}` | array | Key list |
| Describe Key Version | `$.{name,state,protectionLevel,algorithm,createTime}` | object | Version details |
| List Key Versions | `$.cryptoKeyVersions[].{name,state,protectionLevel}` | array | Version list |
| Encrypt | `$.{name,ciphertext}` | object | Encrypted data (base64) |
| Decrypt | `$.{plaintext}` | object | Decrypted data (base64) |

### Expected State Transitions

| Operation | Initial State | Target State | Poll Interval | Max Wait |
|-----------|---------------|--------------|---------------|----------|
| Create Key Ring | — | ACTIVE | Immediate | — |
| Create Key | — | ENABLED (v1) | Immediate | — |
| Destroy Key Version | ENABLED/DISABLED | DESTROY_SCHEDULED | 5s | 30s |
| Restore Key Version | DESTROY_SCHEDULED | DISABLED | Immediate | — |
| Enable Key Version | DISABLED | ENABLED | Immediate | — |
| Disable Key Version | ENABLED | DISABLED | Immediate | — |

## Quick Start

### What This Skill Does
This skill enables you to manage cryptographic keys — key rings, crypto keys, key versions, encryption/decryption — on Google Cloud using the `gcloud` CLI (primary) or Go SDK (fallback).

### Prerequisites
- [ ] `gcloud` CLI installed (or Go runtime for JIT fallback)
- [ ] Service account key configured: `GOOGLE_APPLICATION_CREDENTIALS`
- [ ] Project set: `gcloud config set project <project-id>` or `CLOUDSDK_CORE_PROJECT`
- [ ] IAM roles: `roles/cloudkms.admin` (management) or `roles/cloudkms.cryptoKeyEncrypterDecrypter` (encrypt/decrypt)

### Verify Setup
```bash
# Check gcloud and project
gcloud config get-value project
gcloud auth application-default print-access-token --quiet &>/dev/null && echo "✅ Auth OK"

# Quick list to verify KMS API access
gcloud kms keyrings list --location=global --limit=1 --format="json" &>/dev/null && echo "✅ KMS API OK"
```

### Your First Command
```bash
# Create a key ring
gcloud kms keyrings create "my-keyring" \
  --location=global \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

### Next Steps
- [Core Concepts](references/core-concepts.md) — KMS architecture, key types, protection levels
- [Common Operations](#execution-flows) — Create key rings/keys, encrypt/decrypt, manage versions
- [Troubleshooting](references/troubleshooting.md) — Fix common issues

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| Key Ring Create | Create a new key ring | Low | Low |
| Key Create | Create a crypto key | Medium | Low |
| Key Describe | View key details | Low | None |
| Key Update | Update rotation period or labels | Medium | Low |
| Key Version Destroy | Schedule key version destruction | Low | **High** — irreversible after 24h |
| Key Version Restore | Restore a DESTROY_SCHEDULED version | Medium | None |
| Key Version Enable/Disable | Toggle key version state | Low | Medium |
| Encrypt | Encrypt plaintext with key | Low | None |
| Decrypt | Decrypt ciphertext with key | Low | None |
| Key Import | Import key material | High | Medium |
| Key Ring List | List all key rings | Low | None |
| Key List | List all keys in a key ring | Low | None |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-07 | Initial release: KMS key ring, crypto key, key version, encrypt/decrypt operations with dual-path gcloud+SDK, GCL quality gate |

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (gcloud + SDK/API) → Validate → Recover**. Do not skip phases.

### Operation: Create Key Ring

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| gcloud CLI | `gcloud version` | Exit code 0 | HALT — install gcloud SDK |
| Credentials | `gcloud auth print-access-token` | Token returned | HALT — authenticate |
| Project | `gcloud config get-value project` | Set and valid | HALT — set project |
| KMS API | `gcloud services list --enabled | grep cloudkms.googleapis.com` | Enabled | HALT — enable `cloudkms.googleapis.com` |
| Key ring name unique | `gcloud kms keyrings describe "{{user.keyring_name}}" --location="{{user.location:-global}}" --quiet` | NOT_FOUND (exit != 0) | HALT — name in use |

#### Execution — CLI (`gcloud`) (Primary Path)

```bash
gcloud kms keyrings create "{{user.keyring_name}}" \
  --location="{{user.location:-global}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

#### Execution — Python SDK (Primary Fallback)

```python
# create_keyring.py
import os
from google.cloud import kms_v1
client = kms_v1.KeyManagementServiceClient()
parent = f"projects/{os.environ['CLOUDSDK_CORE_PROJECT']}/locations/{os.environ.get('KMS_LOCATION', 'global')}"
request = kms_v1.CreateKeyRingRequest(parent=parent, key_ring_id="{{user.keyring_name}}")
response = client.create_key_ring(request=request)
print(f"Created key ring: {response.name}")
```

#### Execution — JIT Go SDK (Secondary Fallback)

```go
package main
import (
    "context"
    "fmt"
    "log"
    "os"
    kms "cloud.google.com/go/kms/apiv1"
    "cloud.google.com/go/kms/apiv1/kmspb"
    "google.golang.org/api/option"
)
func main() {
    ctx := context.Background()
    project := os.Getenv("CLOUDSDK_CORE_PROJECT")
    client, err := kms.NewKeyManagementClient(ctx,
        option.WithCredentialsFile(os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")))
    if err != nil { log.Fatalf("NewClient: %v", err) }
    defer client.Close()
    req := &kmspb.CreateKeyRingRequest{
        Parent:    fmt.Sprintf("projects/%s/locations/global", project),
        KeyRingId: "{{user.keyring_name}}",
    }
    resp, err := client.CreateKeyRing(ctx, req)
    if err != nil { log.Fatalf("CreateKeyRing: %v", err) }
    fmt.Printf("Created key ring: %s\n", resp.Name)
}
```

#### Post-execution Validation

```bash
gcloud kms keyrings describe "{{user.keyring_name}}" \
  --location="{{user.location:-global}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

#### Failure Recovery

| Error Code | Max retries | Agent Action | UX Feedback |
|------------|-------------|--------------|-------------|
| INVALID_ARGUMENT / 400 | 1 | Fix location | `[ERROR] Invalid location format` |
| PERMISSION_DENIED / 403 | 0 | HALT | `[ERROR] SA lacks roles/cloudkms.admin` |
| ALREADY_EXISTS / 409 | 0 | Ask rename | `[ERROR] Key ring already exists` |
| QUOTA_EXCEEDED / 429 | 0 | HALT | `[ERROR] Key ring quota exceeded` |
| UNAVAILABLE / 503 | 3 | exp. | `⚠️ Service unavailable. Retrying...` |
| INTERNAL / 500 | 3 | 2/4/8s Retry | `[ERROR] Internal error — escalate if persistent` |

---

### Operation: Create Crypto Key

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Key ring exists | Describe key ring | Exit 0 | HALT — create key ring first |
| Key name unique | `gcloud kms keys describe "{{user.key_name}}" --keyring=KEYRING --location=LOC --quiet` | NOT_FOUND | HALT — name in use |
| Protection level valid | software/hsm/external | One of allowed | Fix to software |

#### Smart Defaults

| Field | Default | Rationale |
|-------|---------|-----------|
| purpose | `encryption` | Most common use case |
| protection_level | `software` | No extra cost vs HSM |
| rotation_period | No rotation | User sets explicitly |

#### Execution — CLI (`gcloud`) (Primary Path)

```bash
# Create a symmetric encryption key
gcloud kms keys create "{{user.key_name}}" \
  --keyring="{{user.keyring_name}}" \
  --location="{{user.location:-global}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --purpose="encryption" \
  --protection-level="{{user.protection_level:-software}}" \
  --rotation-period="{{user.rotation_period}}" \
  --next-rotation-time="{{user.next_rotation_time}}" \
  --format="json"

# Create an asymmetric signing key
gcloud kms keys create "{{user.key_name}}" \
  --keyring="{{user.keyring_name}}" \
  --location="{{user.location:-global}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --purpose="asymmetric-signing" \
  --default-algorithm="ec-sign-p256-sha256" \
  --format="json"
```

#### Execution — Python SDK (Primary Fallback)

```python
# create_key.py
import os
from google.cloud import kms_v1
client = kms_v1.KeyManagementServiceClient()
parent = f"projects/{os.environ['CLOUDSDK_CORE_PROJECT']}/locations/{os.environ.get('KMS_LOCATION','global')}/keyRings/{{user.keyring_name}}"
key = kms_v1.CryptoKey(
    purpose=kms_v1.CryptoKey.CryptoKeyPurpose.ENCRYPT_DECRYPT,
    version_template=kms_v1.CryptoKeyVersionTemplate(
        protection_level=kms_v1.ProtectionLevel.SOFTWARE,
        algorithm=kms_v1.CryptoKeyVersion.CryptoKeyVersionAlgorithm.GOOGLE_SYMMETRIC_ENCRYPTION))
request = kms_v1.CreateCryptoKeyRequest(parent=parent, crypto_key_id="{{user.key_name}}", crypto_key=key)
response = client.create_crypto_key(request=request)
print(f"Created key: {response.name}")
```

#### Post-execution Validation

```bash
gcloud kms keys describe "{{user.key_name}}" \
  --keyring="{{user.keyring_name}}" \
  --location="{{user.location:-global}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{name, primary, purpose, rotationPeriod, createTime}'
```

---

### Operation: Encrypt

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Key exists | Describe key | Exit 0 | HALT — key not found |
| Key version enabled | `.primary.state == "ENABLED"` | ENABLED | HALT — key disabled/destroyed |
| Plaintext file | `test -f "{{user.plaintext_file}}"` | Exists | HALT — file not found |
| Plaintext size | `stat -f%z "{{user.plaintext_file}}"` | ≤ 64KB | HALT — use CMEK instead |

#### Execution — CLI (`gcloud`)

```bash
gcloud kms encrypt \
  --key="{{user.key_name}}" \
  --keyring="{{user.keyring_name}}" \
  --location="{{user.location:-global}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --plaintext-file="{{user.plaintext_file}}" \
  --ciphertext-file="{{user.ciphertext_file:-ciphertext.bin}}" \
  --format="json"
```

#### Execution — Python SDK

```python
# encrypt.py
import os, base64
from google.cloud import kms_v1
client = kms_v1.KeyManagementServiceClient()
name = f"projects/{os.environ['CLOUDSDK_CORE_PROJECT']}/locations/{os.environ.get('KMS_LOCATION','global')}/keyRings/{{user.keyring_name}}/cryptoKeys/{{user.key_name}}"
with open("{{user.plaintext_file}}", "rb") as f:
    plaintext = f.read()
request = kms_v1.EncryptRequest(name=name, plaintext=plaintext)
response = client.encrypt(request=request)
ciphertext = base64.b64encode(response.ciphertext).decode()
with open("{{user.ciphertext_file:-ciphertext.bin}}", "wb") as f:
    f.write(response.ciphertext)
print(f"Encrypted to: {{user.ciphertext_file:-ciphertext.bin}}")
```

#### Post-execution Validation

```bash
ls -la "{{user.ciphertext_file:-ciphertext.bin}}"
```

---

### Operation: Decrypt

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Key exists | Describe key | Exit 0 | HALT |
| Ciphertext file | `test -f "{{user.ciphertext_file}}"` | Exists | HALT |

#### Execution — CLI (`gcloud`)

```bash
gcloud kms decrypt \
  --key="{{user.key_name}}" \
  --keyring="{{user.keyring_name}}" \
  --location="{{user.location:-global}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --ciphertext-file="{{user.ciphertext_file}}" \
  --plaintext-file="decrypted_output.txt" \
  --format="json"
```

---

### Operation: Destroy Key Version

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit user confirmation: destruction of key version `{{user.key_version}}` for key `{{user.key_name}}`
- **MUST** warn: after destruction, the key is scheduled for deletion in 24 hours; within 24h it can be restored
- **MUST** show current state before proceeding

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Key version exists | Describe version | Exit 0 | HALT — not found |
| Current state | `.state` is ENABLED or DISABLED | Can be destroyed | HALT — already destroyed |
| Primary version warning | If primary: warn about encrypt/decrypt impact | User acknowledges | HALT — abort |
| User confirmation | Ask: `Proceed with destruction? (yes/version_name)` | Exact match | HALT — abort |

#### Execution — CLI (`gcloud`)

```bash
gcloud kms keys versions destroy "{{user.key_version}}" \
  --key="{{user.key_name}}" \
  --keyring="{{user.keyring_name}}" \
  --location="{{user.location:-global}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

**Never use `--quiet` to bypass this safety gate.**

#### Post-execution Validation

```bash
gcloud kms keys versions describe "{{user.key_version}}" \
  --key="{{user.key_name}}" \
  --keyring="{{user.keyring_name}}" \
  --location="{{user.location:-global}}" \
  --format="json" | jq '{name, state}'
```

---

### Operation: Restore Key Version

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Key version exists | Describe version | Exit 0 | HALT — not found |
| State is DESTROY_SCHEDULED | `.state == "DESTROY_SCHEDULED"` | Correct state | HALT — cannot restore (already destroyed) |
| Within 24h window | Check `destroyTime` | ≤ 24h from now | HALT — past restore window |

#### Execution — CLI (`gcloud`)

```bash
gcloud kms keys versions restore "{{user.key_version}}" \
  --key="{{user.key_name}}" \
  --keyring="{{user.keyring_name}}" \
  --location="{{user.location:-global}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

---

### Operation: Enable/Disable Key Version

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Key version exists | Describe | Exit 0 | HALT |
| Current state | `.state` | Not already in target state | HALT — already in target state |

#### Execution — CLI (`gcloud`)

```bash
# Enable
gcloud kms keys versions enable "{{user.key_version}}" \
  --key="{{user.key_name}}" \
  --keyring="{{user.keyring_name}}" \
  --location="{{user.location:-global}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"

# Disable
gcloud kms keys versions disable "{{user.key_version}}" \
  --key="{{user.key_name}}" \
  --keyring="{{user.keyring_name}}" \
  --location="{{user.location:-global}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

---

### Operation: Update Key Rotation

#### Execution — CLI (`gcloud`)

```bash
gcloud kms keys update "{{user.key_name}}" \
  --keyring="{{user.keyring_name}}" \
  --location="{{user.location:-global}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --rotation-period="{{user.rotation_period}}" \
  --next-rotation-time="{{user.next_rotation_time}}" \
  --format="json"

# Remove rotation
gcloud kms keys update "{{user.key_name}}" \
  --keyring="{{user.keyring_name}}" \
  --location="{{user.location:-global}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --remove-rotation \
  --format="json"
```

#### Post-execution Validation

```bash
gcloud kms keys describe "{{user.key_name}}" \
  --keyring="{{user.keyring_name}}" \
  --location="{{user.location:-global}}" \
  --format="json" | jq '{rotationPeriod, nextRotationTime}'
```

---

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
           pip install --quiet --user google-cloud-kms
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
   gcloud kms keyrings list --location=global --limit=1 --format="json" &>/dev/null && echo "✅ KMS API OK"
   ```

> **Security:** Never commit service account keys to version control. All credentials use `{{env.*}}` placeholders.

## Reference Directory

- [Core Concepts](references/core-concepts.md) — Architecture, key types, protection levels
- [API & SDK Usage](references/api-sdk-usage.md) — REST API, Python SDK, operation map
- [gcloud Usage](references/gcloud-usage.md) — `gcloud kms` command map
- [Troubleshooting Guide](references/troubleshooting.md) — Error codes, diagnostics, recovery
- [Monitoring & Alerts](references/monitoring.md) — Cloud Monitoring metrics, dashboards, alerts
- [Integration](references/integration.md) — Go SDK bootstrap, env vars, credential rules
- [Idempotency Checklist](references/idempotency-checklist.md) — Retry-safe patterns
- [Well-Architected Assessment](references/well-architected-assessment.md) — Five-pillar assessment
- [Rubric — GCL](references/rubric.md) — Generator-Critic-Loop scoring rubric
- [Prompt Templates — GCL](references/prompt-templates.md) — GCL generator and critic templates

## Operational Best Practices

- **Least privilege:** Use `roles/cloudkms.cryptoKeyEncrypterDecrypter` for encrypt/decrypt; `roles/cloudkms.admin` for management
- **Key rotation:** Enable automatic rotation for long-lived keys; document rotation schedule
- **Key destruction:** Always confirm with user; respect the 24-hour destruction window
- **Security:** Use HSM protection level for compliance workloads; enable VPC Service Controls
- **Backup:** Export key material using import/export; store encrypted backup of key metadata
- **Naming:** Follow `{env}-{purpose}-key` convention; use labels for metadata

## Quality Gate (GCL)

> This skill implements the **Generator-Critic-Loop (GCL)** adversarial quality gate per `AGENTS.md §11`.

| Property | Value |
|----------|-------|
| Classification | **required** (Key version destroy operation present) |
| max_iter | 2 |
| Most-scrutinized operations | Destroy Key Version, Disable Key Version |

- **Rubric**: [references/rubric.md](references/rubric.md) — 5 core dimensions + 3 GCP extensions
- **Prompt Templates**: [references/prompt-templates.md](references/prompt-templates.md) — Generator + Critic templates

## Token Efficiency Guidelines (P0 — 强制)

### TE-1: API Query > Static Tables
Use gcloud to fetch live data:
```bash
gcloud kms keyrings list --location=global --format="json"
gcloud kms keys list --keyring=KEYRING --location=LOC --format="json"
```

### TE-2: No docstrings in code
Inline comments only; no function-level docstrings in SDK snippets.

### TE-3: Compact error tables
Error tables use 1 row per code, ≤ 3 columns.

### TE-4: Centralized JSON paths
See [Key JSON Paths](#key-json-paths-centralized-per-te-4) at top of Execution Flows section.

### TE-5: YAML anchors
See `assets/example-config.yaml` for anchor usage.

### TE-6: Eliminate cross-file duplication
SKILL.md has full flow; references do not repeat SKILL.md content.

## See Also

- **Meta-Skill**: [gcp-skill-generator](../gcp-skill-generator/SKILL.md)
- **IAM**: [gcp-iam-ops](../gcp-iam-ops/SKILL.md) — Service accounts and permissions
- **Secret Manager**: [gcp-secretmanager-ops](../gcp-secretmanager-ops/SKILL.md) — Store encrypted values
- **Monitoring**: [gcp-monitoring-ops](../gcp-monitoring-ops/SKILL.md) — Dashboards and alerts
- **GCL Runner**: [gcp-gcl-runner-ops](../gcp-gcl-runner-ops/SKILL.md) — Execution quality gate

## AIOps 自愈 (Self-Healing)

> Cloud KMS 异常检测与自愈锚点（密钥轮转逾期、加解密权限漂移、密钥误销毁）见 [references/advanced/aiops-kms-anomaly.md](references/advanced/aiops-kms-anomaly.md)。所有自愈动作均带 **dry-run + 幂等 + 人工复核门禁**，破坏性操作标 **HALT**，绝不自动执行。