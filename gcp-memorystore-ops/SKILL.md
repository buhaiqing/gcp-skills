---
name: gcp-memorystore-ops
description: >-
  Use when the user needs to manage, configure, troubleshoot, or monitor Google
  Cloud Memorystore for Redis instances — instance lifecycle, scaling, backups,
  maintenance, security, and connections. User mentions Memorystore, Redis,
  Cloud Memorystore, Redis instance, cache, in-memory data store, or describes
  caching scenarios (e.g., "set up Redis cache", "create Redis instance",
  "Redis high memory", "scale Redis", "back up Redis", "Redis replication")
  even without naming the product directly. Not for Memorystore for Memcached,
  Cloud Bigtable, or Cloud Spanner that have their own ops skills.
license: MIT
compatibility: >-
  Official Google Cloud CLI (`gcloud`, Python-based SDK), Go 1.21+ runtime
  (for JIT SDK fallback), valid service account credentials with Redis Admin or
  Redis Viewer IAM role, network access to Google Cloud endpoints, VPC network
  configured for Redis connectivity.
metadata:
  author: gcp-skills
  version: "1.0.0"
  last_updated: "2026-06-07"
  runtime: Harness AI Agent, Claude Code, or compatible Agent runtimes
  go_version_minimum: "1.21"
  go_version_jit: "1.24+"
  api_profile: "https://redis.googleapis.com/$discovery/rest?version=v1"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    gcloud redis --help confirms subcommands: instances, operations, regions,
    zones. See
    https://cloud.google.com/sdk/gcloud/reference/redis
  environment:
    - GOOGLE_APPLICATION_CREDENTIALS
    - CLOUDSDK_CORE_PROJECT
    - CLOUDSDK_AUTH_ACCESS_TOKEN
---

> This skill follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Google Cloud Memorystore for Redis Operations Skill

## Overview

Cloud Memorystore for Redis provides fully managed in-memory data store for Redis on Google Cloud — instance lifecycle, scaling, high availability, backups, maintenance, and security. This skill is an **operational runbook** for agents: explicit scope, credential rules, pre-flight checks, **dual-path execution** (official **SDK/API** and **`gcloud`** CLI), response validation, and failure recovery.

> **UX Compliance:** This skill follows the [User Experience Specification](../gcp-skill-generator/references/user-experience-spec.md). All operations include onboarding guidance, minimal prompts, smart defaults, clear feedback, and user-friendly error handling.

### CLI applicability (repository policy)

- **`cli_applicability: dual-path`:** Official `gcloud` fully supports Memorystore for Redis via `gcloud redis instances`. You MUST ship both **`references/gcloud-usage.md`** and, in each execution flow below, document **both** the SDK step **and** the `gcloud` step for every operation. Coverage gaps (SDK-only operations) are listed in `references/gcloud-usage.md`.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use conditions with precise triggers and delegation rules |
| 2 | **Structured I/O** | Placeholder conventions (`{{env.*}}`, `{{user.*}}`, `{{output.*}}`) with type and source documented |
| 3 | **Explicit Actionable Steps** | Every operation: Pre-flight → Execute → Validate → Recover, with numbered imperative steps |
| 4 | **Complete Failure Strategies** | Error taxonomy table with ≥ 12 product-specific codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | One product (Memorystore for Redis) with clear delegation to related skills (VPC, Compute, Monitoring) |

Refer to the [meta-skill](../gcp-skill-generator/SKILL.md#five-core-standards-quality-gates) for detailed descriptions of each standard.

### Google Cloud Architecture Framework Integration

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **Security** | IAM permissions (roles/redis.admin), VPC-private connectivity, Auth String, in-transit encryption, RDB/AOF persistence | `references/well-architected-assessment.md` §2.1 |
| **Stability** | Standard tier (HA with replication), backup/restore, maintenance window, multi-zone avoidance | `references/well-architected-assessment.md` §2.2 |
| **Cost** | Pricing by tier (Basic vs Standard), capacity (GB), read replicas, data export snapshot costs | `references/well-architected-assessment.md` §2.3 |
| **Efficiency** | Auto-calculated Redis config (memory size), scaling read replicas, export/import for data portability | `references/well-architected-assessment.md` §2.4 |
| **Performance** | Memory size selection, read replicas for read-heavy workloads, connectivity and latency optimization | `references/well-architected-assessment.md` §2.5 |

See [references/well-architected-assessment.md](references/well-architected-assessment.md) for the complete specification.

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions "Memorystore", "Redis", "Cloud Memorystore", "Redis instance", "in-memory cache", "Redis cache"
- Task involves CRUD or lifecycle operations on **Redis instances** (create, describe, update, delete, list)
- Task involves **scaling** (increase/decrease memory size, change tier)
- Task involves **backup and restore** (export, import)
- Task involves **connection info** (host, port, auth string, network connectivity)
- Task involves **maintenance** (schedule maintenance window, apply updates)
- Keywords: Redis, cache, memorystore, in-memory, key-value, redis-cli, AUTH, replication, failover

### SHOULD NOT Use This Skill When

- Task is purely about Memorystore for Memcached → delegate to: `gcp-memorystore-ops` (Memcached as separate section)
- Task is purely about Cloud Bigtable → delegate to: `gcp-bigtable-ops`
- Task is purely about Cloud Spanner → delegate to: `gcp-spanner-ops`
- Task is purely about VPC networking (Shared VPC, VPC peering) → delegate to: `gcp-vpc-ops`
- Task is purely about GCE instances connecting to Redis → use this skill for Redis connection info
- User insists on **console-only** flows with no API → state limitation; do not invent undocumented gcloud steps

### Delegation Rules

- **VPC Network**: If the VPC does not exist or is not properly configured, delegate to `gcp-vpc-ops`.
- **Monitoring/Alerts**: For Cloud Monitoring of Redis, delegate to `gcp-monitoring-ops`.
- **Compute Engine**: For connecting applications from GCE, use `gcp-gce-ops`.
- **GCL**: Execution quality gate uses `gcp-gcl-runner-ops`.

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.GOOGLE_APPLICATION_CREDENTIALS}}` | Path to SA key JSON | NEVER ask the user; fail if unset |
| `{{env.CLOUDSDK_CORE_PROJECT}}` | GCP project ID | NEVER ask the user; fail if unset |
| `{{env.CLOUDSDK_AUTH_ACCESS_TOKEN}}` | Temporary access token | NEVER ask the user; fail if needs refresh |
| `{{user.project}}` | User-supplied project (override) | Ask once; reuse |
| `{{user.region}}` | Redis instance region | Ask once; reuse; default: us-central1 |
| `{{user.instance_name}}` | Redis instance name | Ask once; reuse |
| `{{user.memory_size_gb}}` | Memory size in GB | Ask once; reuse; default: 1 |
| `{{user.tier}}` | Basic (standalone) or Standard (HA) | Ask once; reuse; default: basic |
| `{{user.redis_version}}` | Redis version (e.g., redis_7_0) | Ask once; reuse; default: latest |
| `{{user.network}}` | VPC network name | Ask once; reuse; default: default |
| `{{user.auth_string}}` | Redis AUTH password | Ask once; reuse |
| `{{user.display_name}}` | Human-readable display name | Ask once; reuse |
| `{{user.maintenance_window_day}}` | Day (SUNDAY, MONDAY, etc.) | Ask once; reuse; default: SUNDAY |
| `{{user.maintenance_window_hour}}` | Hour (UTC, 0-23) | Ask once; reuse; default: 2 |
| `{{user.export_gcs_uri}}` | GCS URI for export (gs://bucket/export.rdb) | Ask once; reuse |
| `{{output.host}}` | Redis instance hostname | From describe `.host` |
| `{{output.port}}` | Redis port | From describe `.port` |
| `{{output.current_location_id}}` | Zone where instance runs | From describe `.currentLocationId` |
| `{{output.state}}` | Instance state | From describe `.state` |
| `{{output.server_ca_certs}}` | Server CA certificates | From describe `.serverCaCerts` |

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

- **REST API is canonical**: Memorystore for Redis v1 API (`redis.googleapis.com`). All JSON paths below are verified against the official REST API reference.
- **Errors**: Map HTTP/gRPC status codes to canonical error types.
- **Timestamps**: RFC 3339 (e.g., `2026-06-07T10:00:00.000Z`).
- **Idempotency**: Instance names are region-unique.

### Key JSON Paths (Centralized per TE-4)

| Operation | JSON Path | Type | Description |
|-----------|-----------|------|-------------|
| Create Instance | `$.{name,host,port,state,createTime}` | object | Instance details |
| Describe Instance | `$.{name,host,port,state,memorySizeGb,redisVersion,tier,displayName,currentLocationId,serverCaCerts,persistenceConfig}` | object | Full instance details |
| List Instances | `$.instances[].{name,host,state,memorySizeGb,tier,redisVersion}` | array | Instance list |
| Update Instance | `$.{name,state,memorySizeGb,displayName,updateTime}` | object | Updated details |
| Export | `$.{name,state}` | object | Operation details |
| Import | `$.{name,state}` | object | Operation details |

### Expected State Transitions

| Operation | Initial State | Target State | Poll Interval | Max Wait |
|-----------|---------------|--------------|---------------|----------|
| Create Instance | — | `READY` | 30s | 600s |
| Update (scale) | `READY` | `UPDATING` → `READY` | 30s | 600s |
| Delete Instance | `READY` | absent | 15s | 300s |
| Export | `READY` | `READY` | 30s | 3600s |
| Import | `READY` | `READY` | 30s | 3600s |

## Quick Start

### What This Skill Does
This skill enables you to manage Memorystore for Redis instances — create, describe, update, delete, scale, backup, and restore — using the `gcloud` CLI (primary) or Go SDK (fallback).

### Prerequisites
- [ ] `gcloud` CLI installed (or Go runtime for JIT fallback)
- [ ] Service account key configured: `GOOGLE_APPLICATION_CREDENTIALS`
- [ ] Project set: `gcloud config set project <project-id>` or `CLOUDSDK_CORE_PROJECT`
- [ ] IAM roles: `roles/redis.admin` (or `roles/redis.viewer` for read-only)
- [ ] VPC network exists in the region

### Verify Setup
```bash
# Check gcloud and project
gcloud config get-value project
gcloud auth application-default print-access-token --quiet &>/dev/null && echo "✅ Auth OK"

# Quick list to verify Redis API access
gcloud redis instances list --region=us-central1 --limit=1 --format="json" &>/dev/null && echo "✅ Redis API OK"
```

### Your First Command
```bash
# List Redis instances
gcloud redis instances list \
  --region=us-central1 \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

### Next Steps
- [Core Concepts](references/core-concepts.md) — Redis architecture, tiers, regions
- [Common Operations](#execution-flows) — Create, manage, scale, backup, restore
- [Troubleshooting](references/troubleshooting.md) — Fix common issues

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| Instance Create | Create a new Redis instance | Medium | Low |
| Instance Describe | View instance details | Low | None |
| Instance Update | Scale memory, update labels/tier | Medium | Medium |
| Instance Delete | Remove a Redis instance permanently | Low | **High** — data loss |
| Instance List | List all instances in a region | Low | None |
| Export | Export instance data to GCS | Medium | None |
| Import | Import instance data from GCS | Medium | **High** — overwrites existing data |
| Failover | Trigger HA failover | Low | Medium — brief downtime |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-07 | Initial release: Redis instance lifecycle, scaling, export/import operations with dual-path gcloud+SDK, GCL quality gate |

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (gcloud + SDK/API) → Validate → Recover**. Do not skip phases.

### Operation: Create Redis Instance

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| gcloud CLI | `gcloud version` | Exit code 0 | HALT — install gcloud SDK |
| Credentials | `gcloud auth print-access-token` | Token returned | HALT — authenticate |
| Project | `gcloud config get-value project` | Set and valid | HALT — set project |
| Redis API | `gcloud services list --enabled | grep redis.googleapis.com` | Enabled | HALT — enable `redis.googleapis.com` |
| Instance name unique | `gcloud redis instances describe "{{user.instance_name}}" --region="{{user.region}}" --quiet` | NOT_FOUND | HALT — name in use |
| VPC exists | `gcloud compute networks list --filter=name={{user.network:-default}} --format="json"` | Network listed | HALT — create VPC via gcp-vpc-ops |
| Memory size valid | `{{user.memory_size_gb}}` is 1-300 | 1 ≤ x ≤ 300 | Fix to valid range |

#### Smart Defaults

| Field | Default | Rationale |
|-------|---------|-----------|
| region | `us-central1` | Common deployment region |
| memory_size_gb | `1` | Minimum size for testing and small workloads |
| tier | `basic` | No replication overhead for dev/testing |
| network | `default` | Available in all projects |

#### Execution — CLI (`gcloud`) (Primary Path)

```bash
# Basic tier (standalone)
gcloud redis instances create "{{user.instance_name}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --memory-size="{{user.memory_size_gb:-1}}GB" \
  --redis-version="{{user.redis_version:-redis_7_0}}" \
  --network="{{user.network:-default}}" \
  --display-name="{{user.display_name}}" \
  --format="json"

# Standard tier (HA with replication)
gcloud redis instances create "{{user.instance_name}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --memory-size="{{user.memory_size_gb:-1}}GB" \
  --tier=standard \
  --redis-version="{{user.redis_version:-redis_7_0}}" \
  --network="{{user.network:-default}}" \
  --display-name="{{user.display_name}}" \
  --format="json"

# With auth string and transit encryption
gcloud redis instances create "{{user.instance_name}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --memory-size="{{user.memory_size_gb:-1}}GB" \
  --tier=standard \
  --redis-config="auth_string={{user.auth_string}}" \
  --transit-encryption-enabled \
  --format="json"
```

#### Execution — Python SDK (Primary Fallback)

```python
# create_instance.py
import os
from google.cloud import redis_v1
client = redis_v1.CloudRedisClient()
parent = f"projects/{os.environ['CLOUDSDK_CORE_PROJECT']}/locations/{os.environ.get('REDIS_REGION', 'us-central1')}"
instance = redis_v1.Instance(
    name="{{user.instance_name}}",
    memory_size_gb=1,
    tier=redis_v1.Instance.Tier.BASIC,
    redis_version="redis_7_0",
    network=f"projects/{os.environ['CLOUDSDK_CORE_PROJECT']}/global/networks/default")
request = redis_v1.CreateInstanceRequest(
    parent=parent, instance_id="{{user.instance_name}}", instance=instance)
operation = client.create_instance(request=request)
response = operation.result(timeout=600)
print(f"Created: {response.host}:{response.port}")
```

#### Execution — JIT Go SDK (Secondary Fallback)

```go
package main
import (
    "context"
    "fmt"
    "log"
    "os"
    redis "cloud.google.com/go/redis/apiv1"
    "cloud.google.com/go/redis/apiv1/redispb"
    "google.golang.org/api/option"
)
func main() {
    ctx := context.Background()
    project := os.Getenv("CLOUDSDK_CORE_PROJECT")
    region := os.Getenv("REDIS_REGION")
    if region == "" { region = "us-central1" }
    client, err := redis.NewCloudRedisClient(ctx,
        option.WithCredentialsFile(os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")))
    if err != nil { log.Fatalf("NewClient: %v", err) }
    defer client.Close()
    req := &redispb.CreateInstanceRequest{
        Parent:     fmt.Sprintf("projects/%s/locations/%s", project, region),
        InstanceId: "{{user.instance_name}}",
        Instance: &redispb.Instance{
            MemorySizeGb:  1,
            Tier:          redispb.Instance_BASIC,
            RedisVersion:  "redis_7_0",
        },
    }
    op, err := client.CreateInstance(ctx, req)
    if err != nil { log.Fatalf("CreateInstance: %v", err) }
    resp, err := op.Wait(ctx); if err != nil { log.Fatalf("Wait: %v", err) }
    fmt.Printf("Created: %s:%d\n", resp.Host, resp.Port)
}
```

#### Post-execution Validation

```bash
gcloud redis instances describe "{{user.instance_name}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{name, host, port, state, memorySizeGb, tier, redisVersion}'
```

#### Failure Recovery

| Error Code | Max retries | Agent Action | UX Feedback |
|------------|-------------|--------------|-------------|
| INVALID_ARGUMENT / 400 | 1 | Fix params | `[ERROR] Invalid parameter — check memory size, version` |
| PERMISSION_DENIED / 403 | 0 | HALT | `[ERROR] SA lacks roles/redis.admin` |
| ALREADY_EXISTS / 409 | 0 | Ask rename | `[ERROR] Instance name already exists` |
| QUOTA_EXCEEDED / 429 | 0 | HALT | `[ERROR] Redis instance quota exceeded` |
| FAILED_PRECONDITION / 400 | 0 | HALT | `[ERROR] VPC network not found or private service connection required` |
| UNAVAILABLE / 503 | 3 | exp. | `⚠️ Service unavailable. Retrying...` |
| INTERNAL / 500 | 3 | 2/4/8s Retry | `[ERROR] Internal error — escalate if persistent` |

---

### Operation: Describe Redis Instance

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Instance exists | `gcloud redis instances describe "{{user.instance_name}}" --region="{{user.region}}" --quiet` | Exit 0 | HALT — instance not found |

#### Execution — CLI (`gcloud`)

```bash
gcloud redis instances describe "{{user.instance_name}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

Extract key fields:
```bash
gcloud redis instances describe "{{user.instance_name}}" \
  --region="{{user.region}}" --format="json" | jq '{
    name: .name,
    host: .host,
    port: .port,
    state: .state,
    tier: .tier,
    memorySizeGb: .memorySizeGb,
    redisVersion: .redisVersion,
    currentLocationId: .currentLocationId,
    authEnabled: .authEnabled,
    transitEncryptionEnabled: .transitEncryptionEnabled,
    persistenceMode: .persistenceConfig.persistenceMode,
    createTime: .createTime
  }'
```

---

### Operation: Update Redis Instance (Scale)

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Instance exists | Describe | State READY | HALT |
| Scale down allowed | Check if decreasing memory | Warn about data loss | Warn user |
| Auth string change | If updating auth: affects all connections | User acknowledges | Warn about connection disruption |

#### Execution — CLI (`gcloud`)

```bash
# Scale memory
gcloud redis instances update "{{user.instance_name}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --memory-size="{{user.memory_size_gb}}GB" \
  --display-name="{{user.display_name}}" \
  --format="json"

# Update Redis config
gcloud redis instances update "{{user.instance_name}}" \
  --region="{{user.region}}" \
  --redis-config="maxmemory-policy=allkeys-lru"
```

#### Post-execution Validation

```bash
gcloud redis instances describe "{{user.instance_name}}" \
  --region="{{user.region}}" --format="json" | jq '{memorySizeGb, displayName}'
```

---

### Operation: Delete Redis Instance

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit user confirmation: irreversible delete of instance `{{user.instance_name}}` in `{{user.region}}`
- **MUST** warn: all data in the instance will be permanently lost
- **MUST** suggest export to GCS before delete for critical instances

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Instance exists | Describe | Exit 0 | HALT — already deleted |
| User confirmation | Ask: `Proceed with irreversible delete? (yes/instance_name)` | Exact match | HALT — abort |
| Backup check | Ask: `Create export before delete?` | User responds | If yes → run export first |

#### Execution — CLI (`gcloud`)

```bash
gcloud redis instances delete "{{user.instance_name}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

**Never use `--quiet` to bypass this safety gate.**

#### Post-execution Validation

```bash
gcloud redis instances describe "{{user.instance_name}}" \
  --region="{{user.region}}" --quiet 2>&1 || echo "✅ Instance confirmed deleted"
```

---

### Operation: Export Instance (Backup)

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Instance exists | Describe | State READY | HALT |
| GCS bucket exists | `gcloud storage buckets describe GCS_BUCKET` | Exit 0 | HALT — create bucket first |
| Export path valid | gs://bucket/path/export.rdb | Valid GCS path | Fix path |
| Persistence enabled | RDB or AOF enabled | RDB preferred for export | Warn: no persistence may lose recent data |

#### Execution — CLI (`gcloud`)

```bash
gcloud redis instances export "{{user.instance_name}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  "{{user.export_gcs_uri}}" \
  --format="json"
```

---

### Operation: Import Instance (Restore)

#### Pre-flight (Safety Gate)

- **MUST** warn: import overwrites all existing data in the instance
- **MUST** obtain explicit confirmation before proceeding

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Instance exists | Describe | State READY | HALT |
| Import file exists | `gcloud storage ls "{{user.export_gcs_uri}}"` | File exists | HALT — file not found |
| Import file format | Ends in .rdb | Valid format | HALT — only .rdb supported |

#### Execution — CLI (`gcloud`)

```bash
gcloud redis instances import "{{user.instance_name}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  "{{user.export_gcs_uri}}" \
  --format="json"
```

---

### Operation: Trigger HA Failover

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Instance is STANDARD_HA | `gcloud redis instances describe "{{user.instance_name}}" --region="{{user.region}}" --format=json \| jq -r '.tier'` | STANDARD_HA | HALT — basic tier has no failover |
| Instance is READY | Describe | State = READY | HALT — instance not available |

#### Execution — CLI (`gcloud`)

```bash
gcloud redis instances failover "{{user.instance_name}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

#### Post-execution Validation

```bash
gcloud redis instances describe "{{user.instance_name}}" \
  --region="{{user.region}}" --format="json" | jq '{host, port, state, currentLocationId}'
```

---

### Operation: List Instances

#### Execution — CLI (`gcloud`)

```bash
gcloud redis instances list \
  --region="{{user.region}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
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
           pip install --quiet --user google-cloud-redis
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
   gcloud redis instances list --region=us-central1 --limit=1 --format="json" &>/dev/null && echo "✅ Redis API OK"
   ```

> **Security:** Never commit service account keys to version control. All credentials use `{{env.*}}` placeholders.

## Reference Directory

- [Core Concepts](references/core-concepts.md) — Architecture, tiers, regions, quotas
- [API & SDK Usage](references/api-sdk-usage.md) — REST API, Python SDK, operation map
- [gcloud Usage](references/gcloud-usage.md) — `gcloud redis` command map
- [Troubleshooting Guide](references/troubleshooting.md) — Error codes, diagnostics, recovery
- [Monitoring & Alerts](references/monitoring.md) — Cloud Monitoring metrics, dashboards, alerts
- [Integration](references/integration.md) — Go SDK bootstrap, env vars, credential rules
- [Idempotency Checklist](references/idempotency-checklist.md) — Retry-safe patterns
- [Well-Architected Assessment](references/well-architected-assessment.md) — Five-pillar assessment
- [Rubric — GCL](references/rubric.md) — Generator-Critic-Loop scoring rubric
- [Prompt Templates — GCL](references/prompt-templates.md) — GCL generator and critic templates

## Operational Best Practices

- **Tier selection:** Use Basic for dev/test; Standard (HA) for production with automatic failover
- **Scaling:** Scale memory up (always safe); test scale-down on non-production first
- **Security:** Enable Auth String and in-transit encryption for production; use VPC-private connectivity
- **Backup:** Schedule regular exports to GCS for critical data
- **Monitoring:** Set alerts for memory usage, CPU, connections, replication lag
- **Naming:** Follow `{env}-{app}-redis` convention for instance names

## Quality Gate (GCL)

> This skill implements the **Generator-Critic-Loop (GCL)** adversarial quality gate per `AGENTS.md §11`.

| Property | Value |
|----------|-------|
| Classification | **required** (Delete instance operation present) |
| max_iter | 2 |
| Most-scrutinized operations | Delete Instance, Import Instance, Scale Down |

- **Rubric**: [references/rubric.md](references/rubric.md) — 5 core dimensions + 3 GCP extensions
- **Prompt Templates**: [references/prompt-templates.md](references/prompt-templates.md) — Generator + Critic templates

## Token Efficiency Guidelines (P0 — 强制)

### TE-1: API Query > Static Tables
Use gcloud to fetch live data:
```bash
gcloud redis instances list --region=REGION --format="json"
gcloud redis regions list --format="json"
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

## AIOps 自愈 (Self-Healing)

> Memorystore for Redis 类故障（内存满、慢查询/阻塞、主从 failover）需要自愈能力。完整 runbook 见 [references/advanced/aiops-memorystore-anomaly.md](references/advanced/aiops-memorystore-anomaly.md)：内存阈值告警 → 自动扩容/eviction 策略（dry-run 预览 + 门禁）、慢查询/阻塞诊断命令与建议、主从 failover 自愈验证（副本健康 + 幂等重连）、blast-radius（影响 GCE/GKE 应用）、自愈动作 dry-run + 幂等 + 门禁、破坏性标 HALT、凭证遮蔽 §0.1。错误码遵循 [docs/error-taxonomy.md](../../docs/error-taxonomy.md)，故障辐射模型遵循 [docs/cross-skill-blast-radius.md](../../docs/cross-skill-blast-radius.md)。

## See Also

- **AIOps Self-Healing**: [references/advanced/aiops-memorystore-anomaly.md](references/advanced/aiops-memorystore-anomaly.md) — anomaly detection & self-healing runbook
- **Meta-Skill**: [gcp-skill-generator](../gcp-skill-generator/SKILL.md)
- **VPC**: [gcp-vpc-ops](../gcp-vpc-ops/SKILL.md) — Networking for Redis instances
- **Compute Engine**: [gcp-gce-ops](../gcp-gce-ops/SKILL.md) — Connect applications to Redis
- **Monitoring**: [gcp-monitoring-ops](../gcp-monitoring-ops/SKILL.md) — Dashboards and alerts
- **GCL Runner**: [gcp-gcl-runner-ops](../gcp-gcl-runner-ops/SKILL.md) — Execution quality gate