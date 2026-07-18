---
name: gcp-filestore-ops
description: >-
  Use when the user needs to manage, configure, troubleshoot, or monitor Google
  Cloud Filestore instances — instance lifecycle, file shares, backups,
  snapshots, and NFS connectivity. User mentions Filestore, Cloud Filestore,
  managed NFS, file storage, NFS mount, or describes file storage scenarios
  (e.g., "create NFS share", "set up Filestore", "Filestore backup",
  "mount NFS volume", "Filestore snapshot", "Filestore restore")
  even without naming the product directly. Not for Cloud Storage,
  Persistent Disk, or Local SSD that have their own ops skills.
license: MIT
compatibility: >-
  Official Google Cloud CLI (`gcloud`, Python-based SDK), Go 1.21+ runtime
  (for JIT SDK fallback), valid service account credentials with Filestore
  Admin or Viewer IAM role, network access to Google Cloud endpoints, VPC
  network configured for Filestore connectivity.
metadata:
  author: gcp-skills
  version: "1.0.0"
  last_updated: "2026-06-13"
  runtime: Harness AI Agent, Claude Code, or compatible Agent runtimes
  go_version_minimum: "1.21"
  go_version_jit: "1.24+"
  api_profile: "https://file.googleapis.com/$discovery/rest?version=v1"
  cli_applicability: "cli-first"
  cli_support_evidence: >-
    gcloud filestore --help confirms subcommands: instances, backups,
    locations, operations, regions, zones. See
    https://cloud.google.com/sdk/gcloud/reference/filestore
  environment:
    - GOOGLE_APPLICATION_CREDENTIALS
    - CLOUDSDK_CORE_PROJECT
    - CLOUDSDK_AUTH_ACCESS_TOKEN
---

> This skill follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Google Cloud Filestore Operations Skill

## Overview

Cloud Filestore provides fully managed NFS file storage on Google Cloud — instance lifecycle, file shares, backups, snapshots, and connectivity. This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **CLI-first execution** (official **`gcloud`** CLI as primary path), response validation, and failure recovery.

> **UX Compliance:** This skill follows the [User Experience Specification](../gcp-skill-generator/references/user-experience-spec.md). All operations include onboarding guidance, minimal prompts, smart defaults, clear feedback, and user-friendly error handling.

### CLI applicability (repository policy)

- **`cli_applicability: cli-first`:** Official `gcloud` fully supports Filestore via `gcloud filestore instances`. CLI is the **primary** execution path. JIT Go SDK is the **fallback** only for edge-case operations CLI doesn't expose.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use conditions with precise triggers and delegation rules |
| 2 | **Structured I/O** | Placeholder conventions (`{{env.*}}`, `{{user.*}}`, `{{output.*}}`) with type and source documented |
| 3 | **Explicit Actionable Steps** | Every operation: Pre-flight → Execute → Validate → Recover, with numbered imperative steps |
| 4 | **Complete Failure Strategies** | Error taxonomy table with ≥ 10 product-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | One product (Filestore) with clear delegation to related skills (VPC, Compute, Monitoring) |

Refer to the [meta-skill](../gcp-skill-generator/SKILL.md#five-core-standards-quality-gates) for detailed descriptions of each standard.

### Google Cloud Architecture Framework Integration

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **Security** | IAM permissions (roles/file.editor), VPC network, private connectivity, NFS access control | `references/well-architected-assessment.md` §2.1 |
| **Stability** | Backups, snapshots, multi-zone, DR runbook, failure-oriented design | `references/well-architected-assessment.md` §2.2 |
| **Cost** | Pricing by tier (BASIC_HDD, BASIC_SSD, HIGH_SCALE_SSD, ENTERPRISE), capacity (GB), snapshot costs | `references/well-architected-assessment.md` §2.3 |
| **Efficiency** | File share configuration, NFS mount options, batch operations | `references/well-architected-assessment.md` §2.4 |
| **Performance** | Tier selection, capacity planning, Cloud Monitoring metrics, performance baselines | `references/well-architected-assessment.md` §2.5 |

See [references/well-architected-assessment.md](references/well-architected-assessment.md) for the complete specification.

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "Filestore", "Cloud Filestore", "managed NFS", "NFS file share", "file storage"
- Task involves CRUD or lifecycle operations on **Filestore instances** (create, describe, update, delete, list)
- Task involves **file shares** (create, update, delete file shares within an instance)
- Task involves **backups** (create, delete, describe, list)
- Task involves **snapshots** (create, delete, describe, list, update)
- Task involves **NFS connectivity** (mount options, IP addresses, VPC networking)
- Keywords: filestore, nfs, file share, backup, snapshot, mount, nfs-client, file storage

### SHOULD NOT Use This Skill When

- Task is purely about Cloud Storage → delegate to: `gcp-gcs-ops`
- Task is purely about Persistent Disk → delegate to: `gcp-gce-ops` (disk operations)
- Task is purely about VPC networking (VPC peering, firewall) → delegate to: `gcp-vpc-ops`
- Task is purely about GCE instances mounting NFS → use this skill for Filestore connection info, then `gcp-gce-ops` for compute
- User insists on **console-only** flows with no API → state limitation; do not invent undocumented gcloud steps

### Delegation Rules

- **VPC Network**: If the VPC does not exist or is not properly configured, delegate to `gcp-vpc-ops`.
- **Monitoring/Alerts**: For Cloud Monitoring of Filestore, delegate to `gcp-monitoring-ops`.
- **Compute Engine**: For mounting Filestore from GCE, use `gcp-gce-ops`.
- **GCL**: Execution quality gate uses `gcp-gcl-runner-ops`.

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.GOOGLE_APPLICATION_CREDENTIALS}}` | Path to SA key JSON | NEVER ask the user; fail if unset |
| `{{env.CLOUDSDK_CORE_PROJECT}}` | GCP project ID | NEVER ask the user; fail if unset |
| `{{env.CLOUDSDK_AUTH_ACCESS_TOKEN}}` | Temporary access token | NEVER ask the user; fail if needs refresh |
| `{{user.project}}` | User-supplied project (override) | Ask once; reuse |
| `{{user.zone}}` | Filestore instance zone | Ask once; reuse; default: us-central1-a |
| `{{user.instance_name}}` | Filestore instance name | Ask once; reuse |
| `{{user.tier}}` | Instance tier (BASIC_HDD, BASIC_SSD, HIGH_SCALE_SSD, ENTERPRISE) | Ask once; reuse; default: BASIC_SSD |
| `{{user.file_share_name}}` | File share name | Ask once; reuse; default: share1 |
| `{{user.file_share_capacity_gb}}` | File share capacity in GB | Ask once; reuse; default: 1024 |
| `{{user.network}}` | VPC network name | Ask once; reuse; default: default |
| `{{user.reserved_ip_range}}` | Reserved IP range (CIDR) | Ask once; reuse; default: 10.0.0.0/29 |
| `{{user.backup_name}}` | Backup name | Ask once; reuse |
| `{{user.snapshot_name}}` | Snapshot name | Ask once; reuse |
| `{{user.nfs_mount_options}}` | NFS mount options | Ask once; reuse; default: defaults |
| `{{output.instance_ip}}` | Filestore instance IP | From describe `.networks[0].ipAddresses[0]` |
| `{{output.state}}` | Instance state | From describe `.state` |
| `{{output.file_share_path}}` | NFS export path | From describe `.fileShares[0].name` |

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

- **REST API is canonical**: Filestore API (`file.googleapis.com`). All JSON paths below are verified against the official REST API reference.
- **Errors**: Map HTTP/gRPC status codes to canonical error types.
- **Timestamps**: RFC 3339 (e.g., `2026-06-13T10:00:00.000Z`).
- **Idempotency**: Instance names are zone-unique.

### Key JSON Paths (Centralized per TE-4)

| Operation | JSON Path | Type | Description |
|-----------|-----------|------|-------------|
| Create Instance | `$.{name,createTime,state}` | object | Instance details |
| Describe Instance | `$.{name,state,tier,networks,fileShares,createTime}` | object | Full instance details |
| List Instances | `$.instances[].{name,state,tier,createTime}` | array | Instance list |
| Update Instance | `$.{name,state,updateTime}` | object | Updated details |
| Create Backup | `$.{name,state,createTime}` | object | Backup details |
| Describe Backup | `$.{name,state,sourceInstance,createTime}` | object | Backup details |
| Create Snapshot | `$.{name,state,createTime}` | object | Snapshot details |

### Expected State Transitions

| Operation | Initial State | Target State | Poll Interval | Max Wait |
|-----------|---------------|--------------|---------------|----------|
| Create Instance | — | `READY` | 30s | 600s |
| Update Instance | `READY` | `REPAIRING` → `READY` | 30s | 600s |
| Delete Instance | `READY` | absent | 15s | 300s |
| Create Backup | — | `READY` | 30s | 1800s |
| Create Snapshot | — | `READY` | 30s | 1800s |
| Restore Instance | — | `READY` | 30s | 600s |

## Quick Start

### What This Skill Does

This skill enables you to manage Cloud Filestore instances — create, describe, update, delete, manage file shares, backups, snapshots, and NFS connectivity — using the `gcloud` CLI (primary).

### Prerequisites

- [ ] `gcloud` CLI installed
- [ ] Service account key configured: `GOOGLE_APPLICATION_CREDENTIALS`
- [ ] Project set: `gcloud config set project <project-id>` or `CLOUDSDK_CORE_PROJECT`
- [ ] IAM roles: `roles/file.editor` (or `roles/file.viewer` for read-only)
- [ ] VPC network exists in the zone

### Verify Setup

```bash
# Check gcloud and project
gcloud config get-value project
gcloud auth application-default print-access-token --quiet &>/dev/null && echo "✅ Auth OK"

# Quick list to verify Filestore API access
gcloud filestore instances list --zone=us-central1-a --limit=1 --format="json" &>/dev/null && echo "✅ Filestore API OK"
```

### Your First Command

```bash
# List Filestore instances
gcloud filestore instances list \
  --zone=us-central1-a \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

### Next Steps

- [Core Concepts](references/core-concepts.md) — Filestore architecture, tiers, zones
- [Common Operations](#execution-flows) — Create, manage, backup, restore
- [Troubleshooting](references/troubleshooting.md) — Fix common issues

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| Instance Create | Create a new Filestore instance | Medium | Low |
| Instance Describe | View instance details | Low | None |
| Instance Update | Update instance (labels, file share) | Medium | Medium |
| Instance Delete | Remove a Filestore instance permanently | Low | **High** — data loss |
| Instance List | List all instances in a zone | Low | None |
| File Share Create | Create a file share | Medium | Low |
| File Share Update | Update file share capacity | Medium | Medium |
| File Share Delete | Delete a file share | Low | **High** — data loss |
| Backup Create | Create a backup of an instance | Medium | None |
| Backup Delete | Delete a backup | Low | **High** — cannot restore |
| Backup Describe | View backup details | Low | None |
| Backup List | List all backups | Low | None |
| Snapshot Create | Create a snapshot | Medium | None |
| Snapshot Delete | Delete a snapshot | Low | **High** — cannot restore |
| Snapshot Describe | View snapshot details | Low | None |
| Snapshot List | List all snapshots | Low | None |
| Snapshot Update | Update snapshot labels | Low | None |
| Restore Instance | Restore from backup/snapshot | Medium | **High** — overwrites data |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-13 | Initial release: Filestore instance lifecycle, file shares, backups, snapshots with CLI-first execution, GCL quality gate |

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (gcloud) → Validate → Recover**. Do not skip phases.

### Operation: Create Filestore Instance

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| gcloud CLI | `gcloud version` | Exit code 0 | HALT — install gcloud SDK |
| Credentials | `gcloud auth print-access-token` | Token returned | HALT — authenticate |
| Project | `gcloud config get-value project` | Set and valid | HALT — set project |
| Filestore API | `gcloud services list --enabled \| grep file.googleapis.com` | Enabled | HALT — enable `file.googleapis.com` |
| Instance name unique | `gcloud filestore instances describe "{{user.instance_name}}" --zone="{{user.zone}}" --quiet` | NOT_FOUND | HALT — name in use |
| VPC exists | `gcloud compute networks list --filter=name={{user.network:-default}} --format="json"` | Network listed | HALT — create VPC via gcp-vpc-ops |
| IP range valid | `{{user.reserved_ip_range}}` is valid CIDR | Valid CIDR | Fix to valid range |
| Tier valid | `{{user.tier}}` is valid tier | BASIC_HDD/BASIC_SSD/HIGH_SCALE_SSD/ENTERPRISE | Fix to valid tier |

#### Smart Defaults

| Field | Default | Rationale |
|-------|---------|-----------|
| zone | `us-central1-a` | Common deployment zone |
| tier | `BASIC_SSD` | Balanced performance and cost |
| file_share_capacity_gb | `1024` | 1 TB minimum for testing |
| network | `default` | Available in all projects |
| reserved_ip_range | `10.0.0.0/29` | Standard private range |

#### Execution — CLI (`gcloud`) (Primary Path)

```bash
# Create BASIC_SSD instance with file share
gcloud filestore instances create "{{user.instance_name}}" \
  --zone="{{user.zone:-us-central1-a}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --tier=BASIC_SSD \
  --file-share=name="{{user.file_share_name:-share1}}",capacity="{{user.file_share_capacity_gb:-1024}}GB" \
  --network=name="{{user.network:-default}}",reserved-ip-range="{{user.reserved_ip_range:-10.0.0.0/29}}" \
  --format="json"

# Create HIGH_SCALE_SSD instance
gcloud filestore instances create "{{user.instance_name}}" \
  --zone="{{user.zone}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --tier=HIGH_SCALE_SSD \
  --file-share=name="{{user.file_share_name}}",capacity="{{user.file_share_capacity_gb}}GB" \
  --network=name="{{user.network}}",reserved-ip-range="{{user.reserved_ip_range}}" \
  --format="json"

# Create instance with labels
gcloud filestore instances create "{{user.instance_name}}" \
  --zone="{{user.zone}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --tier=BASIC_SSD \
  --file-share=name="{{user.file_share_name}}",capacity="{{user.file_share_capacity_gb}}GB" \
  --network=name="{{user.network}}",reserved-ip-range="{{user.reserved_ip_range}}" \
  --labels=env=prod,team=storage \
  --format="json"
```

#### Post-execution Validation

```bash
gcloud filestore instances describe "{{user.instance_name}}" \
  --zone="{{user.zone:-us-central1-a}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{name, state, tier, createTime, networks, fileShares}'
```

#### Failure Recovery

| Error Code | Max retries | Agent Action | UX Feedback |
|------------|-------------|--------------|-------------|
| INVALID_ARGUMENT / 400 | 1 | Fix params | `[ERROR] Invalid parameter — check tier, capacity, network` |
| PERMISSION_DENIED / 403 | 0 | HALT | `[ERROR] SA lacks roles/file.editor` |
| ALREADY_EXISTS / 409 | 0 | Ask rename | `[ERROR] Instance name already exists` |
| QUOTA_EXCEEDED / 429 | 0 | HALT | `[ERROR] Filestore instance quota exceeded` |
| FAILED_PRECONDITION / 400 | 0 | HALT | `[ERROR] VPC network not found or IP range conflict` |
| UNAVAILABLE / 503 | 3 | exp. | `⚠️ Service unavailable. Retrying...` |
| INTERNAL / 500 | 3 | 2/4/8s Retry | `[ERROR] Internal error — escalate if persistent` |

---

### Operation: Describe Filestore Instance

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Instance exists | `gcloud filestore instances describe "{{user.instance_name}}" --zone="{{user.zone}}" --quiet` | Exit 0 | HALT — instance not found |

#### Execution — CLI (`gcloud`)

```bash
gcloud filestore instances describe "{{user.instance_name}}" \
  --zone="{{user.zone:-us-central1-a}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

Extract key fields:

```bash
gcloud filestore instances describe "{{user.instance_name}}" \
  --zone="{{user.zone}}" --format="json" | jq '{
    name: .name,
    state: .state,
    tier: .tier,
    createTime: .createTime,
    instanceIP: .networks[0].ipAddresses[0],
    fileSharePath: .fileShares[0].name,
    capacityGb: .fileShares[0].capacityGb,
    network: .networks[0].network
  }'
```

---

### Operation: Update Filestore Instance

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Instance exists | Describe | State READY | HALT |
| Labels update | Valid labels | Valid | Fix labels |

#### Execution — CLI (`gcloud`)

```bash
# Update labels
gcloud filestore instances update "{{user.instance_name}}" \
  --zone="{{user.zone:-us-central1-a}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --update-labels=env=prod,team=storage \
  --format="json"

# Update file share capacity (increase only for most tiers)
gcloud filestore instances update "{{user.instance_name}}" \
  --zone="{{user.zone}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --file-share=name="{{user.file_share_name}}",capacity="{{user.file_share_capacity_gb}}GB" \
  --format="json"
```

#### Post-execution Validation

```bash
gcloud filestore instances describe "{{user.instance_name}}" \
  --zone="{{user.zone}}" --format="json" | jq '{state, labels, fileShares}'
```

---

### Operation: Delete Filestore Instance

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit user confirmation: irreversible delete of instance `{{user.instance_name}}` in `{{user.zone}}`
- **MUST** warn: all data in the instance will be permanently lost
- **MUST** suggest backup before delete for critical instances

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Instance exists | Describe | Exit 0 | HALT — already deleted |
| User confirmation | Ask: `Proceed with irreversible delete? (yes/instance_name)` | Exact match | HALT — abort |
| Backup check | Ask: `Create backup before delete?` | User responds | If yes → run backup first |

#### Execution — CLI (`gcloud`)

```bash
gcloud filestore instances delete "{{user.instance_name}}" \
  --zone="{{user.zone:-us-central1-a}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

**Never use `--quiet` to bypass this safety gate.**

#### Post-execution Validation

```bash
gcloud filestore instances describe "{{user.instance_name}}" \
  --zone="{{user.zone}}" --quiet 2>&1 || echo "✅ Instance confirmed deleted"
```

---

### Operation: Create Backup

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Instance exists | Describe | State READY | HALT |
| Backup name unique | `gcloud filestore backups describe "{{user.backup_name}}" --region="{{user.region:-us-central1}}" --quiet` | NOT_FOUND | HALT — name in use |
| Source instance valid | Instance in stable state | READY | Wait or HALT |

#### Execution — CLI (`gcloud`)

```bash
gcloud filestore backups create "{{user.backup_name}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --instance="{{user.instance_name}}" \
  --instance-zone="{{user.zone:-us-central1-a}}" \
  --format="json"
```

#### Post-execution Validation

```bash
gcloud filestore backups describe "{{user.backup_name}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{name, state, sourceInstance, createTime}'
```

---

### Operation: Delete Backup

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit user confirmation: irreversible delete of backup `{{user.backup_name}}`
- **MUST** warn: backup cannot be recovered after deletion

#### Execution — CLI (`gcloud`)

```bash
gcloud filestore backups delete "{{user.backup_name}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

---

### Operation: List Backups

#### Execution — CLI (`gcloud`)

```bash
gcloud filestore backups list \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

---

### Operation: Create Snapshot

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Instance exists | Describe | State READY | HALT |
| Snapshot name unique | `gcloud filestore instances snapshots describe "{{user.snapshot_name}}" --instance="{{user.instance_name}}" --zone="{{user.zone}}" --quiet` | NOT_FOUND | HALT — name in use |

#### Execution — CLI (`gcloud`)

```bash
gcloud filestore instances snapshots create "{{user.snapshot_name}}" \
  --instance="{{user.instance_name}}" \
  --zone="{{user.zone:-us-central1-a}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

#### Post-execution Validation

```bash
gcloud filestore instances snapshots describe "{{user.snapshot_name}}" \
  --instance="{{user.instance_name}}" \
  --zone="{{user.zone}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{name, state, createTime}'
```

---

### Operation: Delete Snapshot

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit user confirmation: irreversible delete of snapshot `{{user.snapshot_name}}`

#### Execution — CLI (`gcloud`)

```bash
gcloud filestore instances snapshots delete "{{user.snapshot_name}}" \
  --instance="{{user.instance_name}}" \
  --zone="{{user.zone:-us-central1-a}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

---

### Operation: List Snapshots

#### Execution — CLI (`gcloud`)

```bash
gcloud filestore instances snapshots list \
  --instance="{{user.instance_name}}" \
  --zone="{{user.zone:-us-central1-a}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

---

### Operation: Restore Instance from Backup

#### Pre-flight (Safety Gate)

- **MUST** warn user: restore creates a new instance; suggest pre-restore backup
- **MUST** confirm: target instance `{{user.instance_name}}`, backup source `{{user.backup_name}}`

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Backup exists | `gcloud filestore backups describe "{{user.backup_name}}" --region="{{user.region}}" --quiet` | Exit 0 | HALT — backup not found |
| Target instance name available | Describe target | NOT_FOUND | HALT — name in use |

#### Execution — CLI (`gcloud`)

```bash
gcloud filestore instances create "{{user.instance_name}}" \
  --zone="{{user.zone:-us-central1-a}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --tier=BASIC_SSD \
  --source-backup="projects/{{env.CLOUDSDK_CORE_PROJECT}}/locations/{{user.region:-us-central1}}/backups/{{user.backup_name}}" \
  --file-share=name="{{user.file_share_name:-share1}}",capacity="{{user.file_share_capacity_gb:-1024}}GB" \
  --network=name="{{user.network:-default}}",reserved-ip-range="{{user.reserved_ip_range:-10.0.0.0/29}}" \
  --format="json"
```

#### Post-execution Validation

```bash
gcloud filestore instances describe "{{user.instance_name}}" \
  --zone="{{user.zone}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{name, state, createTime}'
```

---

### Operation: List Instances

#### Execution — CLI (`gcloud`)

```bash
gcloud filestore instances list \
  --zone="{{user.zone}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

---

### Operation: Get NFS Mount Command

#### Execution — CLI (`gcloud`)

```bash
# Get instance details for NFS mount
gcloud filestore instances describe "{{user.instance_name}}" \
  --zone="{{user.zone:-us-central1-a}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{
    instanceIP: .networks[0].ipAddresses[0],
    fileSharePath: .fileShares[0].name,
    nfsMountOptions: .fileShares[0].nfsMountOptions
  }'

# Generate mount command (for Linux client)
INSTANCE_IP=$(gcloud filestore instances describe "{{user.instance_name}}" \
  --zone="{{user.zone}}" \
  --format="json" | jq -r '.networks[0].ipAddresses[0]')
FILE_SHARE=$(gcloud filestore instances describe "{{user.instance_name}}" \
  --zone="{{user.zone}}" \
  --format="json" | jq -r '.fileShares[0].name')

echo "Mount command:"
echo "sudo mkdir -p /mnt/filestore"
echo "sudo mount -o vers=3,proto=tcp {{instance_ip}}:{{file_share_path}} /mnt/filestore"
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

2. **Configure Credentials**:

   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="{{env.GOOGLE_APPLICATION_CREDENTIALS}}"
   export CLOUDSDK_CORE_PROJECT="{{env.CLOUDSDK_CORE_PROJECT}}"
   gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS" 2>/dev/null \
   || gcloud auth login --quiet
   gcloud config set project "$CLOUDSDK_CORE_PROJECT"
   ```

3. **Verify Configuration**:

   ```bash
   gcloud config list
   gcloud auth application-default print-access-token --quiet &>/dev/null && echo "✅ Auth OK"
   gcloud filestore instances list --zone=us-central1-a --limit=1 --format="json" &>/dev/null && echo "✅ Filestore API OK"
   ```

> **Security:** Never commit service account keys to version control. All credentials use `{{env.*}}` placeholders.

## Reference Directory

- [Core Concepts](references/core-concepts.md) — Architecture, tiers, zones, quotas
- [API & SDK Usage](references/api-sdk-usage.md) — REST API, Python SDK, operation map
- [gcloud Usage](references/gcloud-usage.md) — `gcloud filestore` command map
- [Troubleshooting Guide](references/troubleshooting.md) — Error codes, diagnostics, recovery
- [Monitoring & Alerts](references/monitoring.md) — Cloud Monitoring metrics, dashboards, alerts
- [Integration](references/integration.md) — Go SDK bootstrap, env vars, credential rules
- [Well-Architected Assessment](references/well-architected-assessment.md) — Five-pillar assessment
- [Rubric — GCL](references/rubric.md) — Generator-Critic-Loop scoring rubric
- [Prompt Templates — GCL](references/prompt-templates.md) — GCL generator and critic templates

## Quality Gate (GCL)

> This skill implements the **Generator-Critic-Loop (GCL)** adversarial quality gate per `AGENTS.md §11`.

- **Rubric**: [references/rubric.md](references/rubric.md)
- **Prompt Templates**: [references/prompt-templates.md](references/prompt-templates.md)
- **Best Practices**: [references/operational-best-practices.md](references/operational-best-practices.md)

## Token Efficiency Guidelines (P0 — MANDATORY)

### TE-1: API Query > Static Tables

Use gcloud to fetch live data:

```bash
gcloud filestore instances list --zone=ZONE --format="json"
gcloud filestore locations list --format="json"
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
- **VPC**: [gcp-vpc-ops](../gcp-vpc-ops/SKILL.md) — Networking for Filestore instances
- **Compute Engine**: [gcp-gce-ops](../gcp-gce-ops/SKILL.md) — Mount Filestore from GCE
- **Monitoring**: [gcp-monitoring-ops](../gcp-monitoring-ops/SKILL.md) — Dashboards and alerts
- **GCL Runner**: [gcp-gcl-runner-ops](../gcp-gcl-runner-ops/SKILL.md) — Execution quality gate
