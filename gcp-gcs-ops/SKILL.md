---
name: gcp-gcs-ops
description: >-
  Use when the user needs to manage, configure, troubleshoot, or monitor Google
  Cloud Storage resources — buckets, objects, lifecycle policies, storage
  classes, IAM, encryption, versioning, retention policies (with irreversible
  lock warning), holds, signed URLs, notifications, Requester Pays, CORS, and
  public access prevention. User mentions Cloud Storage, GCS, bucket, object,
  blob, gsutil, gcloud storage, storage class, lifecycle, signed URL, or
  describes storage scenarios (e.g., "upload a file", "bucket won't create",
  "set up lifecycle rules", "generate download link") even without naming the
  product directly. Not for Cloud SQL, Filestore, Bigtable, or other storage
  products that have their own ops skills.
license: MIT
compatibility: >-
  Official Google Cloud CLI (`gcloud` including `gcloud storage` module and
  `gsutil`), Python SDK, valid service account credentials with Storage Admin
  or Storage Object Admin IAM roles, network access to Google Cloud endpoints.
metadata:
  author: gcp-skills
  version: "1.0.0"
  last_updated: "2026-06-07"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  go_version_minimum: "1.21"
  go_version_jit: "1.24+"
  api_profile: "https://storage.googleapis.com/$discovery/rest?version=v1"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    gcloud storage buckets --help and gsutil --help confirm subcommands:
    buckets (create, describe, list, update, delete), objects (cp, mv, rsync,
    rm, ls, cat, compose, signurl), lifecycle, IAM, retention, notifications,
    logging, requesterpays. See https://cloud.google.com/sdk/gcloud/reference/storage
    and https://cloud.google.com/storage/docs/gsutil
  environment:
    - GOOGLE_APPLICATION_CREDENTIALS
    - CLOUDSDK_CORE_PROJECT
    - CLOUDSDK_AUTH_ACCESS_TOKEN
---

> This skill follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Google Cloud Storage Operations Skill

## Overview

GCS provides unified object storage — buckets as containers, objects as data blobs. This skill uses a **dual-path CLI approach**: `gcloud storage` for bucket-level ops, `gsutil` for object-level ops. Python SDK and JIT Go SDK are documented in references.

> **UX Compliance**: Follows the [User Experience Specification](../gcp-skill-generator/references/user-experience-spec.md).

### Core Standards

| # | Standard | How Fulfilled |
|---|----------|---------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT with precise triggers and delegation rules |
| 2 | **Structured I/O** | `{{env.*}}`, `{{user.*}}`, `{{output.*}}` with documented types |
| 3 | **Explicit Steps** | Pre-flight → Execute → Validate → Recover for each operation |
| 4 | **Failure Strategies** | Error taxonomy (≥10 codes), HALT vs retry logic |
| 5 | **Single Responsibility** | GCS only; delegation to IAM, Pub/Sub, KMS, Monitoring skills |

### Google Cloud Architecture Framework

| Pillar | Reference |
|--------|-----------|
| **Security** | IAM, CMEK/CSEK, VPC-SC, PAP, signed URLs, retention/holds |
| **Stability** | Multi-region, versioning, lifecycle, object holds, retention |
| **Cost** | Storage classes, Autoclass, lifecycle transitions, Requester Pays |
| **Efficiency** | Bucket naming, uniform access, batch ops, parallel uploads |
| **Performance** | Regional vs multi-region, CDN, gRPC vs JSON API |

Full details: [references/well-architected-assessment.md](references/well-architected-assessment.md)

## Trigger & Scope

### SHOULD Use When
- User mentions "Cloud Storage", "GCS", "bucket", "object", "blob", "gsutil", "gcloud storage"
- Task: bucket CRUD, object CRUD, storage classes, Autoclass, lifecycle, IAM, encryption, versioning, retention/lock, holds, signed URLs, notifications, Requester Pays, CORS, PAP

### SHOULD NOT Use When
- Relational DBs → `gcp-cloudsql-ops`; NoSQL → respective skill; Filestore → `gcp-filestore-ops`
- IAM/SA → `gcp-iam-ops`; Pub/Sub → `gcp-pubsub-ops` (planned); KMS → `gcp-kms-ops` (planned)
- Console-only flows with no API

## Variable Convention

| Placeholder | Meaning | Source |
|-------------|---------|--------|
| `{{env.GOOGLE_APPLICATION_CREDENTIALS}}` | Path to SA key JSON | NEVER ask; HALT if unset |
| `{{env.CLOUDSDK_CORE_PROJECT}}` | GCP project ID | NEVER ask; HALT if unset |
| `{{env.CLOUDSDK_AUTH_ACCESS_TOKEN}}` | Access token | NEVER ask; refresh if expired |
| `{{user.bucket_name}}` | Bucket name (globally unique) | Ask once, reuse |
| `{{user.object_name}}` | Object key path | Ask once, reuse |
| `{{user.source_file}}` / `{{user.destination_file}}` | Local file paths | Ask once |
| `{{user.storage_class}}` | STANDARD/NEARLINE/COLDLINE/ARCHIVE | Ask once; default STANDARD |
| `{{user.location}}` | US/EU/ASIA or region | Ask once; default US |
| `{{user.lifecycle_policy}}` | Lifecycle rule JSON | Ask once |
| `{{user.retention_period}}` | Retention duration in seconds | Ask once |
| `{{output.*}}` | Previous step result | Parse from API response |

> **Security**: Never output credentials. Mask in logs. Verify with `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA key exists"`.

## API Conventions

- **REST API**: Cloud Storage v1 (`storage.googleapis.com`). JSON paths centralized in [references/api-sdk-usage.md](references/api-sdk-usage.md).
- **Errors**: HTTP/gRPC → canonical types. See [references/troubleshooting.md](references/troubleshooting.md).
- **Idempotency**: `-n` (no-clobber) for uploads; `--metageneration` for atomic updates.

## Capabilities

| Operation | CLI Tool | Risk |
|-----------|----------|------|
| Create Bucket | `gcloud storage` | Low |
| Describe Bucket | `gcloud storage` | None |
| List Buckets | `gcloud storage` | None |
| Update Bucket | `gcloud storage` | Medium |
| Delete Bucket | `gcloud storage` | **High** |
| Upload Object | `gsutil` | Low |
| Download Object | `gsutil` | None |
| Copy/Move Object | `gsutil` | Low |
| Delete Object | `gsutil` | **High** |
| List Objects | `gcloud storage` | None |
| Set Lifecycle | `gcloud storage` | Medium |
| Get Lifecycle | `gcloud storage` | None |
| Set Retention | `gcloud storage` | Medium |
| **Lock Retention** | `gcloud storage` | **Critical** |
| Signed URL | `gsutil signurl` | Low |
| IAM | `gcloud storage` | Medium |
| Autoclass | `gcloud storage` | Low |
| Compose | `gsutil` | Low |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-07 | Initial release |

## Execution Flows

> All SDK (Python/Go) code snippets are in [references/api-sdk-usage.md](references/api-sdk-usage.md). For detailed CLI variants, see [references/gcloud-usage.md](references/gcloud-usage.md). For error recovery, see [references/troubleshooting.md](references/troubleshooting.md). For idempotent patterns, see [references/idempotency-checklist.md](references/idempotency-checklist.md).

### Create Bucket

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Name unique | `gcloud storage buckets describe "gs://{{user.bucket_name}}" --quiet` | NOT_FOUND | HALT — choose another |
| Location valid | US, EU, ASIA, or region | Valid | HALT |
| Storage class | STANDARD/NEARLINE/COLDLINE/ARCHIVE | Valid | HALT |

**CLI**: `gcloud storage buckets create "gs://{{user.bucket_name}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --default-storage-class="{{user.storage_class:-STANDARD}}" --location="{{user.location:-US}}" --uniform-bucket-level-access --public-access-prevention --format="json"`
*Variants*: `--autoclass`, `--default-encryption-key="{{user.kms_key_name}}"`

**Validate**: `gcloud storage buckets describe "gs://{{user.bucket_name}}" --format="json" | jq '{name, location, storageClass, timeCreated}'`

### Describe Bucket

**CLI**: `gcloud storage buckets describe "gs://{{user.bucket_name}}" --format="json"`
*Extract*: `jq '{name, location, storageClass, versioning, etag, metageneration, timeCreated, encryption, lifecycle, retentionPolicy, iamConfiguration, labels, autoclass}'`
*IAM*: `gcloud storage buckets get-iam-policy "gs://{{user.bucket_name}}" --format="json"`

### List Buckets

**CLI**: `gcloud storage buckets list --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"`
*Filter*: `jq '[.[] | {name, location, storageClass, timeCreated}]'`

### Update Bucket

**Pre-flight**: Bucket exists, metageneration not stale.

**CLI**:
- Versioning: `gcloud storage buckets update "gs://{{user.bucket_name}}" --versioning --format="json"`
- Labels: `gcloud storage buckets update "gs://{{user.bucket_name}}" --update-labels=K=V --format="json"`
- CMEK: `gcloud storage buckets update "gs://{{user.bucket_name}}" --default-encryption-key="{{user.kms_key_name}}" --format="json"`
- Retention: `gcloud storage buckets update "gs://{{user.bucket_name}}" --retention-period="{{user.retention_period}}" --format="json"`
- CORS: `gcloud storage buckets update "gs://{{user.bucket_name}}" --cors-file="{{user.cors_file}}" --format="json"`

**Validate**: `gcloud storage buckets describe "gs://{{user.bucket_name}}" --format="json" | jq '{name, versioning, labels, encryption}'`

### Delete Bucket

**Pre-flight (EXTREME Safety Gate)**:
| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Bucket empty | `gcloud storage objects list "gs://{{user.bucket_name}}" --limit=1 --format="json"` | Empty | HALT — user must force |
| User confirms | User types exact bucket name | Match | HALT |

**WARN**: Irreversible — all objects permanently lost. If versioned, all versions lost.

**CLI**: `gcloud storage buckets delete "gs://{{user.bucket_name}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}"`
*Force delete*: `gsutil rm -r "gs://{{user.bucket_name}}"` (requires explicit confirmation)

**Never use `--quiet` to bypass this safety gate.**

**Validate**: `gcloud storage buckets describe "gs://{{user.bucket_name}}" --quiet 2>&1 || echo "✅ Bucket confirmed deleted"`

### Upload Object

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Source file | `test -f "{{user.source_file}}"` | Exit 0 | HALT |
| Source readable | `test -r "{{user.source_file}}"` | Exit 0 | HALT |

**CLI**: `gsutil cp "{{user.source_file}}" "gs://{{user.bucket_name}}/{{user.object_name}}"`
*Variants*: `-s {{user.storage_class}}`, `-o "GSUtil:encryption_key={{user.encryption_key}}"`

**Validate**: `gsutil stat "gs://{{user.bucket_name}}/{{user.object_name}}" | head -5`

### Download Object

**Pre-flight**: `gsutil stat "gs://{{user.bucket_name}}/{{user.object_name}}" --quiet` → Exit 0 or HALT.

**CLI**: `gsutil cp "gs://{{user.bucket_name}}/{{user.object_name}}" "{{user.destination_file}}"`
*Version*: `gsutil cp "gs://{{user.bucket_name}}/{{user.object_name}}#{{user.version_id}}" "{{user.destination_file}}"`

**Validate**: `test -f "{{user.destination_file}}" && echo "✅ Download successful"`

### Copy / Move / Rename Object

**CLI**:
- Copy: `gsutil cp "gs://{{user.bucket_name}}/{{user.object_name}}" "gs://{{user.destination_bucket}}/{{user.destination_object}}"`
- Move: `gsutil mv "gs://{{user.bucket_name}}/{{user.object_name}}" "gs://{{user.destination_bucket}}/{{user.destination_object}}"`
- Rename: `gsutil mv "gs://{{user.bucket_name}}/{{user.object_name}}" "gs://{{user.bucket_name}}/{{user.new_object_name}}"`

**Validate**: `gsutil stat "gs://{{user.destination_bucket}}/{{user.destination_object}}" && echo "✅ Success"`
*Move*: Also confirm source gone: `gsutil stat "gs://{{user.bucket_name}}/{{user.object_name}}" --quiet 2>&1 | grep -q "404"`

### Delete Object

**Pre-flight (Safety Gate)**:
| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| User conf. | User types exact object name `{{user.object_name}}` | Match | HALT |
| Versioned? | `gcloud storage buckets describe` → `.versioning.enabled` | Warn if false | Warn — permanent loss |

**WARN**: If bucket is NOT versioned, deletion is permanent. With versioning, a delete marker is created.

**CLI**: `gsutil rm "gs://{{user.bucket_name}}/{{user.object_name}}"`
*Version*: `gsutil rm "gs://{{user.bucket_name}}/{{user.object_name}}#{{user.version_id}}"`

**Validate**: `gsutil stat "gs://{{user.bucket_name}}/{{user.object_name}}" --quiet 2>&1 | grep -q "404" && echo "✅ Object deleted"`

### List Objects

**CLI**:
- All: `gcloud storage objects list "gs://{{user.bucket_name}}" --format="json"`
- Prefix: `gcloud storage objects list "gs://{{user.bucket_name}}/{{user.prefix}}/" --format="json" | jq '[.[] | {name, size, contentType, updated, storageClass}]'`
- Versions: `gcloud storage objects list "gs://{{user.bucket_name}}" --all-versions --format="json"`
- gsutil: `gsutil ls "gs://{{user.bucket_name}}"`, `gsutil ls -l "gs://{{user.bucket_name}}"`, `gsutil ls -lR "gs://{{user.bucket_name}}/{{user.prefix}}/"`

### Set Lifecycle Policy

**CLI**: `gcloud storage buckets update "gs://{{user.bucket_name}}" --lifecycle-file="{{user.lifecycle_file}}" --format="json"`
*Example rules*: See [assets/example-config.yaml](assets/example-config.yaml) for lifecycle rule structure.

**Validate**: `gcloud storage buckets describe "gs://{{user.bucket_name}}" --format="json" | jq '.lifecycle.rule'`

### Get Lifecycle Policy

**CLI**: `gcloud storage buckets describe "gs://{{user.bucket_name}}" --format="json" | jq '.lifecycle'`

### Set Retention Policy

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Unlocked | `.retentionPolicy.isLocked` false or absent | Unlocked | HALT — already locked |

**WARN**: Locking is **IRREVERSIBLE**. Once locked, only lengthening is allowed.

**CLI**: `gcloud storage buckets update "gs://{{user.bucket_name}}" --retention-period="{{user.retention_period}}" --format="json"`

**Validate**: `gcloud storage buckets describe "gs://{{user.bucket_name}}" --format="json" | jq '.retentionPolicy'`

### Lock Retention Policy — EXTREME SAFETY GATE

#### ⚠️ CRITICAL WARNING — Read Carefully ⚠️

Locking a retention policy is **PERMANENT AND IRREVERSIBLE**. Once locked: cannot be removed/shortened/disabled; only lengthening allowed; legal implications apply.

**Pre-flight (EXTREME Safety Gate)**:
| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Current metageneration | `gcloud storage buckets describe "gs://{{user.bucket_name}}" --format="json" | jq -r '.metageneration'` | Numeric value | HALT |
| Current retention period | `.retentionPolicy.retentionPeriod` | Display to user | HALT — no policy set |
| User confirms | User types exactly: `LOCK {{user.bucket_name}}` | Exact match | HALT |

**CLI (metageneration REQUIRED)**:
```bash
# 1. Fetch metageneration
META=$(gcloud storage buckets describe "gs://{{user.bucket_name}}" --format="json" | jq -r '.metageneration')
# 2. Lock with precondition
gcloud storage buckets update "gs://{{user.bucket_name}}" \
  --lock-retention-period \
  --metageneration="$META" \
  --format="json"
```

**SDK**: See [references/api-sdk-usage.md](references/api-sdk-usage.md) — Python snippet fetches metageneration via `bucket.reload()`.

**Validate**: `gcloud storage buckets describe "gs://{{user.bucket_name}}" --format="json" | jq '{name, retentionPolicy}'` — confirm `.retentionPolicy.isLocked` is `true`.

### Generate Signed URL (Download)

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Object exists | `gsutil stat "gs://{{user.bucket_name}}/{{user.object_name}}" --quiet` | Exit 0 | HALT |

**CLI**: `gsutil signurl -d {{user.signed_url_duration:-3600}}s "{{env.GOOGLE_APPLICATION_CREDENTIALS}}" "gs://{{user.bucket_name}}/{{user.object_name}}"`
*PUT method*: `gsutil signurl -m PUT -d {{user.signed_url_duration:-3600}}s "{{env.GOOGLE_APPLICATION_CREDENTIALS}}" "gs://{{user.bucket_name}}/{{user.object_name}}"`

**Usage**: `curl -I "<signed_url>"` should return 200 OK.

### Set Bucket IAM (Uniform Access)

**CLI**:
- Add: `gcloud storage buckets add-iam-policy-binding "gs://{{user.bucket_name}}" --member="{{user.member}}" --role="{{user.role}}" --format="json"`
- Remove: `gcloud storage buckets remove-iam-policy-binding "gs://{{user.bucket_name}}" --member="{{user.member}}" --role="{{user.role}}" --format="json"`

**Validate**: `gcloud storage buckets get-iam-policy "gs://{{user.bucket_name}}" --format="json" | jq '.bindings[] | select(.role == "{{user.role}}")'`

### Enable/Disable Autoclass

**CLI**:
- Enable: `gcloud storage buckets update "gs://{{user.bucket_name}}" --autoclass --format="json"`
- Disable: `gcloud storage buckets update "gs://{{user.bucket_name}}" --no-autoclass --format="json"`

**Validate**: `gcloud storage buckets describe "gs://{{user.bucket_name}}" --format="json" | jq '.autoclass'`

### Compose Objects

**Pre-flight**: All source objects exist. Warn if destination exists.

**CLI**: `gsutil compose "gs://{{user.bucket_name}}/{{user.object1}}" "gs://{{user.bucket_name}}/{{user.object2}}" "gs://{{user.bucket_name}}/{{user.composed_object}}"`

**Validate**: `gsutil stat "gs://{{user.bucket_name}}/{{user.composed_object}}" && echo "✅ Compose successful"`

## Quality Gate (GCL)

| Property | Value |
|----------|-------|
| Classification | **required** (Delete + RetentionLock) |
| max_iter | 2 |
| Most-scrutinized | Delete Bucket, Delete Object, Lock Retention |

- **Rubric**: [references/rubric.md](references/rubric.md)
- **Prompt Templates**: [references/prompt-templates.md](references/prompt-templates.md)

## Token Efficiency (P0 — 强制)

| Rule | Implementation |
|------|---------------|
| **TE-1** API query > static | Use `gcloud storage buckets list --format="json"` instead of hardcoding |
| **TE-2** No docstrings | `#` comments only in SDK snippets |
| **TE-3** Compact errors | ≤3 columns, 1 row per code |
| **TE-4** Centralized JSON | See [references/api-sdk-usage.md](references/api-sdk-usage.md) |
| **TE-5** YAML anchors | See [assets/example-config.yaml](assets/example-config.yaml) |
| **TE-6** No duplication | SKILL.md = what; references/ = how |
| **TE-7** Advanced content | AIOps/FinOps in `references/advanced/` |

## Reference Directory

- [Core Concepts](references/core-concepts.md) — Architecture, quotas, Prerequisites
- [API & SDK Usage](references/api-sdk-usage.md) — REST API map, Python/Go SDK code
- [gcloud Usage](references/gcloud-usage.md) — CLI commands for all operations
- [Troubleshooting](references/troubleshooting.md) — Error codes (≥10), diagnostics, recovery
- [Integration](references/integration.md) — Go bootstrap, env vars, credential rules
- [Monitoring](references/monitoring.md) — Metrics, dashboards, alerts
- [Idempotency Checklist](references/idempotency-checklist.md) — Retry-safe patterns
- [Well-Architected Assessment](references/well-architected-assessment.md)
- [Rubric](references/rubric.md) — GCL scoring
- [Prompt Templates](references/prompt-templates.md) — GCL templates

## See Also

- **Meta-Skill**: [gcp-skill-generator](../gcp-skill-generator/SKILL.md)
- **IAM**: [gcp-iam-ops](../gcp-iam-ops/SKILL.md) — Service accounts and permissions
- **Pub/Sub**: (planned) — Bucket notification topics
- **KMS**: (planned) — CMEK key management
- **Monitoring**: [gcp-monitoring-ops](../gcp-monitoring-ops/SKILL.md) — Dashboards and alerts
- **GCL Runner**: [gcp-gcl-runner-ops](../gcp-gcl-runner-ops/SKILL.md) — Execution quality gate

## Operational Best Practices

- **Least privilege**: `roles/storage.objectViewer` (read), `roles/storage.objectAdmin` (CRUD), `roles/storage.admin` (full)
- **Security**: PAP enforced, uniform access, VPC-SC, CMEK for sensitive data
- **Cost**: Autoclass, lifecycle rules, labels for cost tracking
- **Durability**: 11 9s with multi-region; versioning for data protection
- **Backup**: Versioning, retention policies with lock (if needed), Object holds
- **Naming**: `{project}-{env}-{purpose}-{sequence}` — lowercase, globally unique