---
name: gcp-gce-ops
description: >-
  Use when the user needs to deploy, manage, configure, troubleshoot, or monitor
  Google Cloud Compute Engine resources — VM instances, persistent disks,
  snapshots, instance groups, sole-tenant nodes, and machine images. User
  mentions Compute Engine, GCE, VM, instance, virtual machine, disk, snapshot,
  instance group, sole tenant, or describes compute scenarios (e.g., "create a
  server", "SSH into instance", "resize disk", "instance won't start", "back up
  instance") even without naming the product directly. Not for GKE, Cloud Run,
  Cloud Functions, or other compute products that have their own ops skills.
license: MIT
compatibility: >-
  Official Google Cloud CLI (`gcloud`, Python-based SDK), Go 1.21+ runtime
  (for JIT SDK fallback), valid service account credentials with Compute Admin
  or Compute Viewer IAM role, network access to Google Cloud endpoints.
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
    gcloud compute --help confirms subcommands: instances, disks, snapshots,
    instance-groups, sole-tenancy, machine-images. See
    https://cloud.google.com/sdk/gcloud/reference/compute
  environment:
    - GOOGLE_APPLICATION_CREDENTIALS
    - CLOUDSDK_CORE_PROJECT
    - CLOUDSDK_AUTH_ACCESS_TOKEN
---

> This skill follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Google Cloud Compute Engine Operations Skill

## Overview

Google Compute Engine (GCE) on Google Cloud provides scalable virtual machines — VM instances, persistent disks, snapshots, instance groups, sole-tenant nodes, and machine images. This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **dual-path execution** (official **SDK/API** and **`gcloud`** CLI), response validation, and failure recovery.

> **UX Compliance:** This skill follows the [User Experience Specification](../gcp-skill-generator/references/user-experience-spec.md). All operations include onboarding guidance, minimal prompts, smart defaults, clear feedback, and user-friendly error handling.

### CLI applicability (repository policy)

- **`cli_applicability: dual-path`:** Official `gcloud` fully supports Compute Engine via `gcloud compute instances`, `gcloud compute disks`, etc. You MUST ship both **`references/gcloud-usage.md`** and, in each execution flow below, document **both** the SDK step **and** the `gcloud` step for every operation. Coverage gaps (SDK-only operations) are listed in `references/gcloud-usage.md`.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use conditions with precise triggers and delegation rules |
| 2 | **Structured I/O** | Placeholder conventions (`{{env.*}}`, `{{user.*}}`, `{{output.*}}`) with type and source documented |
| 3 | **Explicit Actionable Steps** | Every operation: Pre-flight → Execute → Validate → Recover, with numbered imperative steps |
| 4 | **Complete Failure Strategies** | Error taxonomy table with ≥ 10 product-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | One product (Compute Engine) with clear delegation to related skills (VPC, IAM, Cloud DNS) |

Refer to the [meta-skill](../gcp-skill-generator/SKILL.md#five-core-standards-quality-gates) for detailed descriptions of each standard.

### Google Cloud Architecture Framework Integration

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **Security** | IAM permissions (roles/compute.instanceAdmin), shielded VMs, CMEK, VPC Service Controls, OS Login | `references/well-architected-assessment.md` §2.1 |
| **Stability** | Managed instance groups (MIG), auto-healing, multi-region deployment, snapshots, instance templates | `references/well-architected-assessment.md` §2.2 |
| **Cost** | Pricing model (sustained use, committed use, preemptible/spot), right-sizing recommendations, idle instance detection | `references/well-architected-assessment.md` §2.3 |
| **Efficiency** | Instance templates, custom machine types, sole-tenant nodes, reservation management, batch operations | `references/well-architected-assessment.md` §2.4 |
| **Performance** | Machine type selection, local SSD, balanced/pd-ssd/extreme disk types, placement policies | `references/well-architected-assessment.md` §2.5 |

See [references/well-architected-assessment.md](references/well-architected-assessment.md) for the complete specification.

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "Compute Engine", "GCE", "GCP VM", "instance", "virtual machine", "disk", "snapshot"
- Task involves CRUD or lifecycle operations on VM instances (create, describe, modify, delete, start, stop, reset, list)
- Task involves persistent disks (create, describe, resize, delete, list, attach, detach, snapshot)
- Task involves snapshots (create, describe, delete, list, create image)
- Task involves instance groups (managed/unmanaged: create, describe, resize, delete, list, set autohealing, set autoscaling)
- Task involves sole-tenant nodes or node groups
- Task involves machine images (create, describe, delete, list, use for instance creation)
- User describes compute scenarios: "instance unreachable", "SSH connection refused", "disk full", "high CPU", "can't create VM", "resize disk", "back up server"
- Keywords: instance, VM, disk, snapshot, MIG, instance group, sole tenant, machine image, boot disk, persistent disk, SSH, OS Login, serial console, metadata, startup script, shutdown script

### SHOULD NOT Use This Skill When

- Task is purely about container orchestration (GKE) → delegate to: `gcp-gke-ops`
- Task is purely about serverless compute (Cloud Run, Cloud Functions) → delegate to: `gcp-cloudrun-ops` / `gcp-cloudfunctions-ops`
- Task is purely about networking (VPC, subnets, firewall rules, VPN) → delegate to: `gcp-vpc-ops`
- Task is purely about IAM / service accounts → delegate to: `gcp-iam-ops`
- Task is purely about load balancing → delegate to: `gcp-lb-ops`
- Task is purely about DNS → delegate to: `gcp-dns-ops`
- User insists on **console-only** flows with no API → state limitation; do not invent undocumented gcloud steps

### Delegation Rules

- **VPC/Subnet/Firewall**: If VPC does not exist, delegate to `gcp-vpc-ops` first; do not duplicate VPC creation flows.
- **IAM/Service Accounts**: For non-default SA operations, delegate to `gcp-iam-ops`.
- **Monitoring/Alerts**: For Cloud Monitoring, delegate to `gcp-monitoring-ops`.
- **Load Balancing**: Instance group backend configuration uses `gcp-lb-ops`.
- **GCL**: Execution quality gate uses `gcp-gcl-runner-ops`.

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.GOOGLE_APPLICATION_CREDENTIALS}}` | Path to SA key JSON | NEVER ask the user; fail if unset |
| `{{env.CLOUDSDK_CORE_PROJECT}}` | GCP project ID | NEVER ask the user; fail if unset |
| `{{env.CLOUDSDK_AUTH_ACCESS_TOKEN}}` | Temporary access token | NEVER ask the user; fail if needs refresh |
| `{{user.project}}` | User-supplied project (override) | Ask once; reuse |
| `{{user.zone}}` | User-supplied zone | Ask once; reuse |
| `{{user.region}}` | User-supplied region | Ask once; reuse |
| `{{user.instance_name}}` | VM instance name | Ask once; reuse |
| `{{user.disk_name}}` | Persistent disk name | Ask once; reuse |
| `{{user.snapshot_name}}` | Snapshot name | Ask once; reuse |
| `{{user.machine_type}}` | Machine type (e.g., n2-standard-4) | Ask once; reuse; default: n2-standard-2 |
| `{{user.image_project}}` | Image project (e.g., debian-cloud) | Ask once; reuse; default: debian-cloud |
| `{{user.image_family}}` | Image family (e.g., debian-12) | Ask once; reuse; default: debian-12 |
| `{{output.instance_id}}` | From create/describe response | Parse from JSON path `$.id` |
| `{{output.instance_self_link}}` | From create/describe response | Parse from JSON path `$.selfLink` |
| `{{output.instance_status}}` | From describe response | Parse from JSON path `$.status` |
| `{{output.disk_self_link}}` | From create/describe response | Parse from JSON path `$.selfLink` |
| `{{output.snapshot_self_link}}` | From create/describe response | Parse from JSON path `$.selfLink` |
| `{{output.operation_name}}` | From any long-running operation | Parse from JSON path `$.name` |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Security Warning (Credential Masking — MANDATORY):** NEVER log, print, or expose service account key content, `GOOGLE_APPLICATION_CREDENTIALS` path content, or any credential field value in console output, debug messages, error messages, or logs.
>
| Execution Path | Safe Pattern | Unsafe Pattern |
|----------------|-------------|----------------|
| Console output | `GOOGLE_APPLICATION_CREDENTIALS=<masked>` | `{"private_key": "-----BEGIN...` |
| Error messages | `Error: API call failed (credential omitted)` | `Error: ... actual SA key content...` |
| Log files | `[INFO] Credentials configured: SA=***` | `[INFO] SA key: {"private_key":"...` |
| Verification | `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA key file exists"` | `cat $GOOGLE_APPLICATION_CREDENTIALS` |
| Go SDK | `option.WithCredentialsFile(os.Getenv("..."))` (env read is safe) | `fmt.Printf("Config: %+v", config)` or `log.Printf("%+v", ...)` |

## API and Response Conventions (Agent-Readable)

- **REST API is canonical**: Compute Engine v1 API (`compute.googleapis.com`). All JSON paths below are verified against the official REST API reference.
- **Errors**: Map HTTP/gRPC status codes to canonical error types.
- **Timestamps**: RFC 3339 (e.g., `2026-06-07T10:00:00.000Z`).
- **Idempotency**: Create with unique names is naturally idempotent; use resource labels for de-duplication.

### Key JSON Paths (Common — centralized per TE-4)

| Operation | JSON Path | Type | Description |
|-----------|-----------|------|-------------|
| Create/Start/Stop/Delete | `$.name` | string | Operation name for polling |
| Create Instance | `$.targetLink` | string | Self-link of created instance |
| Describe Instance | `$.{status,id,name,zone,machineType,disks,networkInterfaces}` | mixed | Instance details |
| List Instances | `$.items[].{name,status,zone,machineType}` | array | Instance list fields |
| Create Disk | `$.targetLink` | string | Self-link of created disk |
| Create Snapshot | `$.targetLink` | string | Self-link of created snapshot |
| Describe Operation | `$.{status,httpErrorMessage,error}` | mixed | Operation tracking |

### Expected State Transitions

| Operation | Initial State | Target State | Poll Interval | Max Wait |
|-----------|---------------|--------------|---------------|----------|
| Create Instance | — | `RUNNING` | 10s | 300s |
| Start Instance | `TERMINATED` | `RUNNING` | 5s | 180s |
| Stop Instance | `RUNNING` | `TERMINATED` | 5s | 180s |
| Reset Instance | `RUNNING` | `RUNNING` | 5s | 120s |
| Delete Instance | `RUNNING`/`TERMINATED` | absent | 10s | 300s |
| Disk Create | — | `READY` | 10s | 300s |
| Disk Resize | `READY` | `READY` | 10s | 180s |
| Snapshot Create | — | `READY` | 30s | 600s |

## Quick Start

### What This Skill Does
This skill enables you to deploy, manage, configure, troubleshoot, and monitor Compute Engine VM instances, disks, and snapshots on Google Cloud using the `gcloud` CLI (primary) or Go SDK (fallback).

### Prerequisites
- [ ] `gcloud` CLI installed (or Go runtime for JIT fallback)
- [ ] Service account key configured: `GOOGLE_APPLICATION_CREDENTIALS`
- [ ] Project set: `gcloud config set project <project-id>` or `CLOUDSDK_CORE_PROJECT`
- [ ] IAM roles: `roles/compute.instanceAdmin` (or `roles/compute.admin`)

### Verify Setup
```bash
# Check gcloud and project
gcloud config get-value project
gcloud auth application-default print-access-token --quiet &>/dev/null && echo "✅ Auth OK"

# Quick list to verify compute API access
gcloud compute instances list --limit=1 --format="json" &>/dev/null && echo "✅ Compute API OK"
```

### Your First Command
```bash
# List all instances in the project
gcloud compute instances list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

### Next Steps
- [Core Concepts](references/core-concepts.md) — GCE architecture, quotas, regions, zones
- [Common Operations](#execution-flows) — Create, manage, and delete instances/disks/snapshots
- [Troubleshooting](references/troubleshooting.md) — Fix common issues

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| VM Create | Create a new VM instance | Medium | Low |
| VM Describe | View VM instance details | Low | None |
| VM Modify | Update instance metadata, labels, tags, machine type | Medium | Medium |
| VM Start | Start a stopped instance | Low | None |
| VM Stop | Stop a running instance | Low | **Medium** — data loss risk without backup |
| VM Reset | Hard reset of a running instance | Low | **Medium** — unflushed data loss |
| VM Delete | Remove instance and boot disk | Low | **High** — irreversible |
| Disk Create | Create a persistent disk | Medium | Low |
| Disk Resize | Expand persistent disk capacity | Medium | Medium |
| Disk Delete | Remove a persistent disk | Low | **High** — irreversible |
| Snapshot Create | Create a disk snapshot | Medium | None |
| Snapshot Delete | Remove a snapshot | Low | **High** — irreversible |
| MIG Create | Create a managed instance group | Medium | Low |
| MIG Resize | Scale MIG up/down | Low | Medium |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-07 | Initial release: GCE VM, disk, snapshot, instance group operations with dual-path gcloud+SDK, GCL quality gate |

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (gcloud + SDK/API) → Validate → Recover**. Do not skip phases.

### Operation: Create VM Instance

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| gcloud CLI | `gcloud version` | Exit code 0 | HALT — install gcloud SDK |
| Credentials | `gcloud auth print-access-token` | Token returned | HALT — authenticate |
| Project | `gcloud config get-value project` | Set and valid | HALT — set project |
| Compute API | `gcloud services list --enabled | grep compute.googleapis.com` | Enabled | HALT — enable `compute.googleapis.com` |
| Quota | `gcloud compute regions describe {{user.zone%-*} --format="json"` | Sufficient CPU quota | HALT — request increase |
| Instance name | Check uniqueness: `gcloud compute instances describe "{{user.instance_name}}" --zone="{{user.zone}}" --quiet` | NOT_FOUND (exit != 0) | HALT — name in use |
| Zone availability | Verify zone exists: `gcloud compute zones list --filter=name={{user.zone}} --format="json"` | Zone listed | HALT — fix zone |
| Image family | `gcloud compute images list --project={{user.image_project}} --filter=family={{user.image_family}} --format="json"` | Image found | Warn; fall back to common family |
| Boot disk GB | Default: 20GB | ≥ 10GB | Fix default |
| VPC network | `gcloud compute networks list --format="json"` | Default VPC or custom exists | HALT — create VPC via gcp-vpc-ops |
| Subnet | `gcloud compute networks subnets list --regions={{user.zone%-*}} --format="json"` | Subnet exists in region | HALT — create subnet via gcp-vpc-ops |

#### Smart Defaults

| Field | Default | Rationale |
|-------|---------|-----------|
| machine_type | `n2-standard-2` | Balanced cost/performance for most workloads |
| zone | `us-central1-a` | Lowest latency for common deployments |
| image_project | `debian-cloud` | Lightweight, well-maintained public OS |
| image_family | `debian-12` | Latest stable Debian LTS |
| boot_disk_size | 20GB | Minimum for Debian + basic workloads |
| boot_disk_type | `pd-balanced` | Balanced performance/cost |
| network_tier | `STANDARD` | Default Google Cloud tier |

#### Execution (dual-path)

Full `gcloud` command at [references/gcloud-usage.md](references/gcloud-usage.md) §Instances (Create). SDK/API scripts at `assets/code-snippets/create_instance.{py,go}`.

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud compute instances create` | Create with `--zone`, `--machine-type`, `--image-project`, `--image-family`, `--boot-disk-size/type`, `--network-tier`, `--format=json` |
| 2 | Python SDK fallback | `compute_v1.InstancesClient().insert(...)` — full script in `assets/code-snippets/create_instance.py` |
| 3 | Go SDK fallback | `compute.NewInstancesRESTClient().Insert(ctx, req)` — full script in `assets/code-snippets/create_instance.go` |

#### Post-execution Validation

1. Poll the zone-level operations API until `status: DONE`: `gcloud compute operations describe "{{output.operation_name}}" --zone="{{user.zone}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" | jq -r '.status'`
2. Describe the instance to verify `RUNNING` state: `gcloud compute instances describe "{{user.instance_name}}" --zone="{{user.zone}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" | jq '{name:.name,status:.status,zone:.zone,machineType:.machineType,networkIP:.networkInterfaces[0].networkIP}'`
3. On success, report instance summary: name, status, zone, machine type, internal IP, external IP (if assigned).
4. On terminal failure, go to **Failure Recovery**.

#### Failure Recovery

| Error Code | Max retries | Backoff | Agent Action | UX Feedback |
|------------|-------------|---------|--------------|-------------|
| INVALID_ARGUMENT / 400 | 0-1 | — | Fix args from REST API; retry once | `[ERROR] INVALID_ARGUMENT: Parameter invalid — see API reference` |
| QUOTA_EXCEEDED / 429 | 0 | — | HALT | `[ERROR] QUOTA_EXCEEDED: CPU/disk/IP quota exceeded. Request increase via Cloud Console` |
| PERMISSION_DENIED / 403 | 0 | — | HALT | `[ERROR] PERMISSION_DENIED: SA lacks compute.instances.create` |
| ALREADY_EXISTS / 409 | 0 | — | Ask rename | `[ERROR] ALREADY_EXISTS: Instance name already in use — choose a different name` |
| RESOURCE_EXHAUSTED / 429 | 0 | — | HALT | `[ERROR] Quota exhausted in {{user.zone}} — try another zone` |
| UNAVAILABLE / 503 | 3 | exp. | Back off; respect Retry-After | `⚠️ Service unavailable. Retrying in {backoff}s ({current}/{max})` |
| INTERNAL / 500 | 3 | 2/4/8s | Retry; then HALT | `[ERROR] INTERNAL: GCP server error. Escalate if persistent` |
| `ZONE_RESOURCE_POOL_EXHAUSTED` | 3 | exp. | Try another zone | `⚠️ {{user.zone}} resource constrained — retrying in {backoff}s` |
| `BILLING_NOT_ENABLED` | 0 | — | HALT | `[ERROR] Billing not enabled for project — enable in Cloud Console` |

---

### Operation: Describe VM Instance

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Instance exists | `gcloud compute instances describe "{{user.instance_name}}" --zone="{{user.zone}}" --quiet` | Exit 0 | HALT — instance not found |

#### Execution (dual-path)

Full `gcloud` command at [references/gcloud-usage.md](references/gcloud-usage.md) §Instances (Describe). SDK script at `assets/code-snippets/describe_instance.py` (`compute_v1.InstancesClient().get(...)`).

Extract with jq (single-line, parse all fields):
```bash
gcloud compute instances describe "{{user.instance_name}}" --zone="{{user.zone}}" --format="json" | jq '{name:.name,id:.id,status:.status,zone:.zone,machineType:(.machineType|split("/")[-1]),cpuPlatform:.cpuPlatform,creationTimestamp:.creationTimestamp,networkIP:.networkInterfaces[0].networkIP,natIP:.networkInterfaces[0].accessConfigs[0].natIP,disks:[.disks[]|{deviceName,boot,diskSizeGb,diskType:(.initializeParams.diskType//.type)}],labels:.labels,tags:.tags.items,metadata:{items:.metadata.items}}'
```

#### Present to User

| Field | Path | Notes |
|-------|------|-------|
| Name | `.name` | Instance name |
| ID | `.id` | Unique numeric ID |
| Status | `.status` | RUNNING / TERMINATED / STOPPING / etc. |
| Zone | `.zone` (last segment) | Deployment zone |
| Machine Type | `.machineType` (last segment) | e.g., n2-standard-2 |
| Internal IP | `.networkInterfaces[0].networkIP` | Primary internal VPC IP |
| External IP | `.networkInterfaces[0].accessConfigs[0].natIP` | May be absent |
| Boot Disk | `.disks[0].initializeParams.sourceImage` | Source image |
| Created | `.creationTimestamp` | RFC 3339 |

---

### Operation: Modify VM Instance

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Instance exists | Describe | Status RUNNING or TERMINATED | HALT |
| Change type compatible | For machine type change: instance TERMINATED | TERMINATED | HALT — stop first |
| Metadata/labels safe | Verify change is non-destructive | — | Warn user |

#### Execution (CLI — `gcloud`)

Full commands at [references/gcloud-usage.md](references/gcloud-usage.md) §Instances (Add metadata / Add labels / Set machine type / Add tags). All use `--zone`, `--project="{{env.CLOUDSDK_CORE_PROJECT}}"`, `--format="json"`.

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud compute instances add-metadata` | Update `--metadata=key={{user.metadata_key}},value={{user.metadata_value}}` |
| 2 | `gcloud compute instances add-labels` | Update `--labels=env={{user.label_env}},team={{user.label_team}}` |
| 3 | `gcloud compute instances set-machine-type` | Change `--machine-type={{user.new_machine_type}}` (instance MUST be TERMINATED) |
| 4 | `gcloud compute instances add-tags` | Update `--tags="{{user.tags}}` |

#### Post-execution Validation

Describe instance and verify changes applied: `gcloud compute instances describe "{{user.instance_name}}" --zone="{{user.zone}}" --format="json" | jq '.metadata.items[] | select(.key == "{{user.metadata_key}}")'`

---

### Operation: Stop VM Instance

#### Pre-flight (Safety Gate)

- **MUST** warn: stopping instance may cause data loss for non-persistent disks
- **MUST** suggest snapshot before stop for critical workloads

#### Execution (CLI — `gcloud`)

Full command at [references/gcloud-usage.md](references/gcloud-usage.md) §Instances (Stop): `gcloud compute instances stop "{{user.instance_name}}" --zone="{{user.zone}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"`

#### Post-execution Validation

Poll until `.status == "TERMINATED"`: `gcloud compute instances describe "{{user.instance_name}}" --zone="{{user.zone}}" --format="json" | jq -r '.status'`

---

### Operation: Delete VM Instance

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit user confirmation: irreversible delete of `{{user.instance_name}}` in `{{user.zone}}`
- **MUST** warn: boot disk will be deleted by default (`--delete-disks=boot`)
- **MUST** suggest snapshot backup before delete for critical instances

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Instance exists | Describe `{{user.instance_name}}` | Exit 0 | HALT — already deleted |
| User confirmation | Ask: `Proceed with irreversible delete of instance <name>? (yes/instance_name)` | Exact match with instance name | HALT — abort |
| Backup check | Ask: `Create snapshot before delete?` | User responds | If yes → run snapshot create first |

#### Execution (dual-path)

Full `gcloud` command at [references/gcloud-usage.md](references/gcloud-usage.md) §Instances (Delete): `gcloud compute instances delete "{{user.instance_name}}" --zone="{{user.zone}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --delete-disks="boot" --format="json"`. SDK script at `assets/code-snippets/delete_instance.py` (`compute_v1.InstancesClient().delete(...)`).

**Never use `--quiet` to bypass this safety gate.**

#### Post-execution Validation

Confirm NOT_FOUND: `gcloud compute instances describe "{{user.instance_name}}" --zone="{{user.zone}}" --quiet 2>&1 || echo "✅ Instance confirmed deleted"`

---

### Operation: Create Snapshot

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Source disk exists | Describe | Exit 0 | HALT |
| Snapshot quota | `gcloud compute regions describe {{user.zone%-*}} --format=json` | Check quotas | HALT |

#### Execution (CLI — `gcloud`)

Full command at [references/gcloud-usage.md](references/gcloud-usage.md) §Snapshots (Snapshot create): `gcloud compute disks snapshot "{{user.disk_name}}" --snapshot-names="{{user.snapshot_name}}" --zone="{{user.zone}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --labels=created-by=gcp-skills --format="json"`

#### Post-execution Validation

Poll until `status: READY`: `gcloud compute snapshots describe "{{user.snapshot_name}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" | jq -r '.status'`

---

### Operation: Delete Snapshot

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit user confirmation: irreversible delete of snapshot `{{user.snapshot_name}}`

#### Execution (CLI — `gcloud`)

Full command at [references/gcloud-usage.md](references/gcloud-usage.md) §Snapshots (Snapshot delete): `gcloud compute snapshots delete "{{user.snapshot_name}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"`

---

### Operation: Create Managed Instance Group (MIG)

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Instance template | `gcloud compute instance-templates describe {{user.template_name}} --quiet` | Exit 0 | HALT — create template first |
| Zone/location | Match template regional requirement | Compatible | HALT |

#### Execution (CLI — `gcloud`)

Full commands at [references/gcloud-usage.md](references/gcloud-usage.md) §Snapshots & MIGs (MIG create / regional). All use `--template`, `--size`, `--project="{{env.CLOUDSDK_CORE_PROJECT}}"`, `--format="json"`.

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud compute instance-groups managed create` (zonal) | `--base-instance-name={{user.base_name}} --zone={{user.zone}} --size={{user.size:-3}}` |
| 2 | `gcloud compute instance-groups managed create` (regional) | `--region={{user.region}} --distribution-policy-zones={{user.zone1}},{{user.zone2}}` |

#### Post-execution Validation

`gcloud compute instance-groups managed describe "{{user.mig_name}}" --zone="{{user.zone}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" | jq '{name, targetSize, currentActions}'`

---

### Operation: Create Disk

#### Execution (CLI — `gcloud`)

Full command at [references/gcloud-usage.md](references/gcloud-usage.md) §Disks (Create): `gcloud compute disks create "{{user.disk_name}}" --zone="{{user.zone}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --size="{{user.disk_size:-100}}" --type="{{user.disk_type:-pd-balanced}}" --format="json"`

#### Post-execution Validation

`gcloud compute disks describe "{{user.disk_name}}" --zone="{{user.zone}}" --format="json" | jq '{name, status, sizeGb, type}'`

---

### Operation: Attach Disk to Instance

#### Execution (CLI — `gcloud`)

Full command at [references/gcloud-usage.md](references/gcloud-usage.md) §Instances (Attach disk): `gcloud compute instances attach-disk "{{user.instance_name}}" --disk="{{user.disk_name}}" --zone="{{user.zone}}" --device-name="{{user.device_name}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"`

---

### Operation: Resize Disk

#### Pre-flight (Safety Gate)

- **MUST** warn: only expansion is supported; shrinking may cause data loss and requires backup first
- **MUST** obtain explicit confirmation from user

#### Execution (CLI — `gcloud`)

Full command at [references/gcloud-usage.md](references/gcloud-usage.md) §Disks (Resize): `gcloud compute disks resize "{{user.disk_name}}" --zone="{{user.zone}}" --size="{{user.new_size}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"`

#### Post-execution Validation

`gcloud compute disks describe "{{user.disk_name}}" --zone="{{user.zone}}" --format="json" | jq -r '.sizeGb'`

---

## Prerequisites

> **Self-Healing:** Installation flows include multi-path recovery per [enhanced-self-healing-framework.md](../gcp-skill-generator/references/enhanced-self-healing-framework.md). Each step has >= 3 error-handling strategies.

1. **Install gcloud CLI** (primary execution path):
   ```bash
   # Primary: official installer
   if ! command -v gcloud &> /dev/null; then
       curl https://sdk.cloud.google.com | bash 2>/dev/null \
       || (echo "\u26a0\ufe0f Installer failed, trying apt..." \
           && sudo apt-get update && sudo apt-get install -y google-cloud-sdk) \
       || (echo "\u26a0\ufe0f apt failed, trying manual..." \
           && wget -q https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-x86_64.tar.gz \
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
       # Primary: official tarball; fallback: alternative download
       curl -fsSL "https://go.dev/dl/go1.24.0.${OS}-${ARCH}.tar.gz" | tar -xz -C /tmp/go-runtime 2>/dev/null \
       || curl -fsSL "https://go.dev/dl/go1.24.0.linux-${ARCH}.tar.gz" | tar -xz -C /tmp/go-runtime
       if [ -f /tmp/go-runtime/go/bin/go ]; then
           export PATH="/tmp/go-runtime/go/bin:$PATH"
       else
           echo "Go download failed. Using Python SDK as fallback."
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
   gcloud auth application-default print-access-token --quiet &>/dev/null && echo "\u2705 Auth OK"
   gcloud compute zones list --limit=1 --format="json" &>/dev/null && echo "\u2705 Compute API OK"
   ```

> **Security:** Never commit service account keys to version control. All credentials use `{{env.*}}` placeholders.

## Reference Directory

- [Core Concepts](references/core-concepts.md) — Architecture, quotas, regions, zones
- [API & SDK Usage](references/api-sdk-usage.md) — REST API, Python SDK, operation map
- [gcloud Usage](references/gcloud-usage.md) — `gcloud compute` command map
- [Troubleshooting Guide](references/troubleshooting.md) — Error codes, diagnostics, recovery
- [Monitoring & Alerts](references/monitoring.md) — Cloud Monitoring metrics, dashboards, alerts
- [Integration](references/integration.md) — Go SDK bootstrap, env vars, credential rules
- [Idempotency Checklist](references/idempotency-checklist.md) — Retry-safe patterns
- [Well-Architected Assessment](references/well-architected-assessment.md) — Five-pillar assessment
- [Rubric — GCL](references/rubric.md) — Generator-Critic-Loop scoring rubric
- [Prompt Templates — GCL](references/prompt-templates.md) — GCL generator and critic templates

## Operational Best Practices

- **Least privilege:** Use `roles/compute.instanceAdmin` for operations; avoid `roles/compute.admin` unless needed
- **Availability:** Use MIG with auto-healing and regional deployment for production workloads
- **Cost:** Right-size instances; use committed use discounts for steady-state workloads; use spot VMs for fault-tolerant batch jobs
- **Security:** Enable shielded VM (Secure Boot, vTPM, Integrity Monitoring); use OS Login instead of SSH keys
- **Backup:** Schedule regular snapshots; use instance scheduling for dev instances
- **Naming:** Follow `{env}-{app}-{purpose}-{sequence}` convention for instance names

## Quality Gate (GCL)

> This skill implements the **Generator-Critic-Loop (GCL)** adversarial quality gate per `AGENTS.md §11`.

| Property | Value |
|----------|-------|
| Classification | **required** (Delete operations present) |
| max_iter | 2 |
| Most-scrutinized operations | Delete Instance, Delete Disk, Delete Snapshot, Resize Disk |

- **Rubric**: [references/rubric.md](references/rubric.md) — 5 core dimensions + 3 GCP extensions
- **Prompt Templates**: [references/prompt-templates.md](references/prompt-templates.md) — Generator + Critic templates

> Token Efficiency 规则详见根目录 AGENTS.md §9（TE-1~TE-8，禁止跨文件重复 — TE-6）。

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-07 | Initial release: VM, disk, snapshot, MIG operations; dual-path gcloud+SDK; GCL quality gate |

## See Also

- **Meta-Skill**: [gcp-skill-generator](../gcp-skill-generator/SKILL.md)
- **VPC**: [gcp-vpc-ops](../gcp-vpc-ops/SKILL.md) — Networking for GCE instances
- **IAM**: [gcp-iam-ops](../gcp-iam-ops/SKILL.md) — Service accounts and permissions
- **Monitoring**: [gcp-monitoring-ops](../gcp-monitoring-ops/SKILL.md) — Dashboards and alerts
- **GCL Runner**: [gcp-gcl-runner-ops](../gcp-gcl-runner-ops/SKILL.md) — Execution quality gate

## AIOps 自愈 (Self-Healing)

> Compute Engine 异常检测与自愈锚点（实例不健康、磁盘满、实例卡在 PROVISIONING）见 [references/advanced/aiops-gce-anomaly.md](references/advanced/aiops-gce-anomaly.md)。所有自愈动作均带 **dry-run + 幂等 + 人工复核门禁**，破坏性操作标 **HALT**，绝不自动执行。