---
name: gcp-gke-ops
description: >-
  Use when managing GKE clusters — lifecycle (create, describe, update, delete),
  node pools, upgrades, VPC-native networking, security (Workload Identity,
  private clusters), autoscaling (CA, VPA, HPA), Backup for GKE, and monitoring.
  User mentions GKE, Kubernetes, cluster, node pool, kubectl, K8s, autopilot.
  Not for Compute Engine, Cloud Run, or Cloud Functions.
license: MIT
compatibility: >-
  Official Google Cloud CLI (`gcloud`, Python-based SDK), Go 1.21+ runtime
  (for JIT SDK fallback), valid service account credentials with Kubernetes
  Engine Admin or Kubernetes Engine Viewer IAM role, network access to Google
  Cloud endpoints.
metadata:
  author: gcp-skills
  version: "1.0.0"
  last_updated: "2026-06-07"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  go_version_minimum: "1.21"
  go_version_jit: "1.24+"
  api_profile: "https://container.googleapis.com/$discovery/rest?version=v1alpha1"
  cli_applicability: "dual-path"
  cli_support_evidence: >-
    gcloud container --help confirms subcommands: clusters, node-pools,
    operations, subnets, binauthz, hub, backup-restore. See
    https://cloud.google.com/sdk/gcloud/reference/container
  environment:
    - GOOGLE_APPLICATION_CREDENTIALS
    - CLOUDSDK_CORE_PROJECT
    - CLOUDSDK_CONTAINER_CLUSTER
    - CLOUDSDK_AUTH_ACCESS_TOKEN
---

## Overview

Google Kubernetes Engine (GKE) provides a managed Kubernetes service. This skill is an **operational runbook**: scope, credential rules, pre-flight checks, dual-path execution (SDK/API + `gcloud`), validation, and recovery.  
> **UX Compliance:** Follows [User Experience Spec](../gcp-skill-generator/references/user-experience-spec.md).

### CLI applicability

- **dual-path**: `gcloud` fully supports GKE (`gcloud container`). Ship both [references/gcloud-usage.md](references/gcloud-usage.md) and SDK flows.

## Five Core Standards & Architecture Framework

See [meta-skill](../gcp-skill-generator/SKILL.md#five-core-standards-quality-gates) and [well-architected-assessment.md](references/well-architected-assessment.md).

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- GKE cluster lifecycle (create, describe, update, delete, list)
- Node pool operations (create, describe, resize, upgrade, delete)
- Cluster networking, security (Workload Identity), autoscaling, upgrades
- Cluster credentials (get-credentials for kubectl)
- Backup for GKE
- Keywords: GKE, Kubernetes, cluster, node pool, kubectl, k8s, autopilot, release channel, Backup for GKE

### SHOULD NOT Use This Skill When

- Compute Engine VMs → `gcp-gce-ops`
- Cloud Run / Cloud Functions → `gcp-cloudrun-ops` / `gcp-cloudfunctions-ops`
- VPC/Subnet/Firewall/DNS → `gcp-vpc-ops` / `gcp-dns-ops`
- IAM/Service Accounts only → `gcp-iam-ops`
- Load Balancing only → `gcp-lb-ops`
- Console-only flows → state limitation; do not invent undocumented gcloud steps

### Delegation Rules

- **VPC/Subnet**: Delegate secondary range setup to `gcp-vpc-ops`.
- **IAM**: Delegate Workload Identity configuration to `gcp-iam-ops`.
- **Monitoring**: Delegate dashboards/alerts to `gcp-monitoring-ops`.
- **Load Balancing**: For Kubernetes Service type LoadBalancer or Ingress configuration, delegate to `gcp-lb-ops`.
- **GCL**: Execution quality gate uses `gcp-gcl-runner-ops`.

## Variable Convention (Agent-Readable)

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.GOOGLE_APPLICATION_CREDENTIALS}}` | Path to SA key JSON | NEVER ask the user; fail if unset |
| `{{env.CLOUDSDK_CORE_PROJECT}}` | GCP project ID | NEVER ask the user; fail if unset |
| `{{env.CLOUDSDK_CONTAINER_CLUSTER}}` | Default cluster name | NEVER ask the user; optional hint |
| `{{env.CLOUDSDK_AUTH_ACCESS_TOKEN}}` | Temporary access token | NEVER ask the user; fail if needs refresh |
| `{{user.project}}` | User-supplied project (override) | Ask once; reuse |
| `{{user.cluster_name}}` | GKE cluster name | Ask once; reuse |
| `{{user.zone}}` | User-supplied compute zone | Ask once; reuse |
| `{{user.region}}` | User-supplied region | Ask once; reuse |
| `{{user.node_count}}` | Initial node count per zone | Ask; default: 3 |
| `{{user.machine_type}}` | Node machine type | Ask; default: e2-medium |
| `{{user.disk_size_gb}}` | Node boot disk size | Ask; default: 100 |
| `{{user.disk_type}}` | Node boot disk type | Ask; default: pd-balanced |
| `{{user.release_channel}}` | Release channel (rapid/regular/stable) | Ask; default: regular |
| `{{user.cluster_version}}` | Specific GKE version override | Optional |
| `{{user.node_pool_name}}` | Node pool name | Ask once; reuse |
| `{{user.location}}` | Cluster location (zone or region) | Ask once; reuse |
| `{{output.cluster_endpoint}}` | Cluster API endpoint | Parse from `$.endpoint` |
| `{{output.cluster_status}}` | Cluster status | Parse from `$.status` |
| `{{output.operation_name}}` | Operation name | Parse from `$.name` |
| `{{output.node_pool_status}}` | Node pool status | Parse from `$.status` |
| `{{output.current_node_count}}` | Current node count | Parse from `$.currentNodeCount` |

> **`{{env.*}}` MUST NOT** be collected from the user. **`{{user.*}}`** MUST be collected interactively when missing.

> **Credential Masking**: NEVER log credential values. Verify: `test -f "$GOOGLE_APPLICATION_CREDENTIALS"`. Go SDK use `option.WithCredentialsFile(os.Getenv(...))`. Never `fmt.Printf("%+v", config)`.

## API and Response Conventions (Agent-Readable)

- **REST API**: GKE v1 API (`container.googleapis.com`). JSON paths verified against official reference.
- **Errors**: Map gRPC status codes to error types.
- **Timestamps**: RFC 3339.
- **Idempotency**: Create with unique names; use Labels for de-duplication.

### Key JSON Paths

See [references/api-sdk-usage.md](references/api-sdk-usage.md#key-json-paths) for the complete table.

### Expected State Transitions

### Expected State Transitions

| Operation | Init → Target | Poll | Max |
|-----------|--------------|------|-----|
| Create Standard | — → `RUNNING` | 30s | 600s |
| Create Autopilot | — → `RUNNING` | 30s | 900s |
| Update/Upgrade | `RUNNING` → `RUNNING` | 30s | 1200s |
| Delete Cluster | `RUNNING` → absent | 30s | 600s |
| Create Node Pool | — → `RUNNING` | 15s | 600s |
| Resize/Upgrade NP | `RUNNING` → `RUNNING` | 15-30s | 300-1200s |
| Delete Node Pool | `RUNNING` → absent | 15s | 300s |

## Quick Start

### Prerequisites
gcloud CLI, SA via `GOOGLE_APPLICATION_CREDENTIALS`, project, IAM `roles/container.clusterAdmin`, APIs enabled.

### First Commands
```bash
gcloud config get-value project
gcloud container clusters list --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json
```

### Next Steps
- [Core Concepts](references/core-concepts.md)
- [Troubleshooting](references/troubleshooting.md)

## Capabilities at a Glance

| Operation | Complexity | Risk |
|-----------|------------|------|
| Create Standard / Autopilot | High / Low | Medium / Low |
| Describe / List Cluster | Low | None |
| Update Cluster | Medium | Medium |
| Delete Cluster | Low | **High** |
| Create / Resize / Delete Node Pool | Medium / Low / Low | Low / Medium / **High** |
| Get Cluster Credentials | Low | None |

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (gcloud) → Validate → Recover**. See [API & SDK Usage](references/api-sdk-usage.md) for Python/Go SDK alternatives.

### Operation: Create Standard Cluster

Create a zonal or regional GKE Standard cluster with Workload Identity, VPC-native, and release channel.

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| gcloud / API | `gcloud version` + services enabled | gcloud ready, container+compute APIs enabled | HALT — install/enable |
| Credentials | `gcloud auth print-access-token` | Token returned | HALT — authenticate |
| Cluster name | `gcloud container clusters describe "{{user.cluster_name}}" --zone="{{user.location}}" --quiet` | NOT_FOUND | HALT — name in use |
| Location | `gcloud compute zones list --filter=name={{user.location}} --format=json` | Zone exists | HALT — fix location |
| Quota | `gcloud compute regions describe "{{user.region}}" --format=json \| jq '.quotas[]'` | Sufficient CPU/IP quota | HALT — request increase |
| Release channel | `gcloud container get-server-config --zone="{{user.location}}" --format=json` | Channel valid | Warn; fall back to REGULAR |

#### Execution — CLI (`gcloud`)

```bash
gcloud container clusters create "{{user.cluster_name}}" --zone="{{user.location}}" --num-nodes="{{user.node_count:-3}}" --machine-type="{{user.machine_type:-e2-medium}}" --format=json --release-channel="{{user.release_channel:-regular}}" --workload-pool="{{env.CLOUDSDK_CORE_PROJECT}}.svc.id.goog" --enable-ip-alias

**Regional:** `--zone` → `--region`. Add `--network`, `--subnetwork`, `--cluster-ipv4-cidr`, `--services-ipv4-cidr`.

#### Execution — Python SDK

See [references/api-sdk-usage.md](references/api-sdk-usage.md#python-sdk) for the Python SDK script.

#### Execution — JIT Go SDK (Secondary Fallback)

See [references/integration.md](references/integration.md#go-sdk) for the Go SDK script.

#### Post-execution Validation

#### Post-execution

1. Poll: `gcloud container operations describe "{{output.operation_name}}" --zone="{{user.location}}" --format=json | jq -r '.status'`
2. Verify: `gcloud container clusters describe "{{user.cluster_name}}" --zone="{{user.location}}" --format=json | jq '{name, status, endpoint}'
3. Report summary.

#### Failure Recovery

| Error Code | Max retries | Agent Action |
|------------|-------------|--------------|
| INVALID_ARGUMENT / 400 | 0-1 | Fix args; retry once |
| QUOTA_EXCEEDED / 429 | 0 | HALT — request quota increase |
| PERMISSION_DENIED / 403 | 0 | HALT — check IAM: container.clusterAdmin |
| ALREADY_EXISTS / 409 | 0 | HALT — cluster name in use |
| RESOURCE_EXHAUSTED / 429 | 0 | HALT — try another zone/region |
| VERSION_NOT_AVAILABLE / 400 | 0 | HALT — pick valid version from channel |
| INSUFFICIENT_CIDR / 400 | 0 | HALT — increase pod/service CIDR |
| INTERNAL / 500 | 3 | Retry 2/4/8s; then HALT |

For generic GKE errors, see [troubleshooting.md](references/troubleshooting.md).

---

### Operation: Create Autopilot Cluster

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Region supports Autopilot | `gcloud container get-server-config --zone="{{user.location}}" --format=json` | Autopilot supported | HALT — choose another region |
| Cluster name unique | `gcloud container clusters describe "{{user.cluster_name}}" --zone="{{user.location}}" --quiet` | NOT_FOUND | HALT — name in use |

#### Execution — CLI (`gcloud`)

```bash
gcloud container clusters create-auto "{{user.cluster_name}}" --location="{{user.location}}" --release-channel="{{user.release_channel:-regular}}" --network="{{user.network:-default}}" --subnetwork="{{user.subnet}}" --format=json
```

#### Post-execution Validation

Same as Standard cluster — verify `RUNNING` state.

#### Failure Recovery

| Error Code | Max retries | Agent Action |
|------------|-------------|--------------|
| INVALID_ARGUMENT / 400 | 0-1 | Fix parameter; retry once |
| PERMISSION_DENIED / 403 | 0 | HALT — check IAM |
| ALREADY_EXISTS / 409 | 0 | HALT — cluster name in use |
| RESOURCE_EXHAUSTED / 429 | 0 | HALT — Autopilot not supported in region |
| INTERNAL / 500 | 3 | Retry 2/4/8s; then HALT |

For generic GKE errors, see [troubleshooting.md](references/troubleshooting.md).

---

### Operation: Describe Cluster

#### Execution — CLI (`gcloud`)

```bash
gcloud container clusters describe "{{user.cluster_name}}" --zone="{{user.location}}" --format=json | jq '{name, status, endpoint, currentMasterVersion, currentNodeCount}'
```

Full jq: [references/gcloud-usage.md](references/gcloud-usage.md).

---

### Operation: List Clusters

#### Execution — CLI (`gcloud`)

```bash
gcloud container clusters list --format=json | jq '[.[] | {name, status, location, currentMasterVersion}]'
```

---

### Operation: Update Cluster

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Cluster exists | Describe cluster | Exit 0 | HALT |
| Cluster RUNNING | Describe `.status` | RUNNING | HALT — cluster not ready |
| Change validity | Verify requested change is supported | | Warn if incompatible |

#### Execution — CLI (`gcloud`)

See [references/gcloud-usage.md](references/gcloud-usage.md#cluster-update-commands) for update commands: upgrade control plane, toggle Workload Identity, update autoscaling, and change logging/monitoring.

#### Post-execution Validation

```bash
gcloud container clusters describe "{{user.cluster_name}}" --zone="{{user.location}}" --format=json | jq '{currentMasterVersion, status}'
```

---

### Operation: Delete Cluster

#### Pre-flight (Safety Gate)

- Confirm irreversible delete of cluster `{{user.cluster_name}}` in `{{user.location}}`
- Suggest Backup for GKE before deletion
- Warn all workloads, node pools, and PVs deleted

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| User confirmation | Ask: exact cluster name | Match | HALT |

#### Execution — CLI (`gcloud`)

```bash
gcloud container clusters delete "{{user.cluster_name}}" --zone="{{user.location}}" --format=json
```

#### Post-execution Validation

```bash
gcloud container clusters describe "{{user.cluster_name}}" --zone="{{user.location}}" --quiet 2>&1 || echo "✅ Cluster confirmed deleted"
```

---

### Operation: Create Node Pool

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Cluster exists | Describe cluster | Exit 0 | HALT |
| Cluster RUNNING | Describe `.status` | RUNNING | HALT |
| Node pool name | Check uniqueness: `gcloud container node-pools describe "{{user.node_pool_name}}" --cluster="{{user.cluster_name}}" --zone="{{user.location}}" --quiet` | NOT_FOUND | HALT — rename |
| Machine type valid | `gcloud compute machine-types list --filter=name={{user.machine_type}} --format="json"` | Found | HALT — specify valid type |

#### Execution — CLI (`gcloud`)

```bash
gcloud container node-pools create "{{user.node_pool_name}}" --cluster="{{user.cluster_name}}" --zone="{{user.location}}" --num-nodes="{{user.node_count:-3}}" --machine-type="{{user.machine_type:-e2-medium}}" --disk-size="{{user.disk_size_gb:-100}}" --disk-type="{{user.disk_type:-pd-balanced}}" --enable-autoscaling --min-nodes="{{user.min_nodes:-1}}" --max-nodes="{{user.max_nodes:-10}}" --scopes=cloud-platform --format=json
```

Optional flags: `--node-taints`, `--node-labels`, `--spot` — see [gcloud-usage.md](references/gcloud-usage.md).

#### Post-execution Validation

```bash
gcloud container node-pools describe "{{user.node_pool_name}}" --cluster="{{user.cluster_name}}" --zone="{{user.location}}" --format=json | jq '{name, status, currentNodeCount, version}'
```

---

### Operation: Describe Node Pool

#### Execution — CLI (`gcloud`)

```bash
gcloud container node-pools describe "{{user.node_pool_name}}" --cluster="{{user.cluster_name}}" --zone="{{user.location}}" --format=json | jq '{name, status, currentNodeCount, machineType: .config.machineType}'
```

Full extraction: [references/gcloud-usage.md](references/gcloud-usage.md).

---

### Operation: Resize Node Pool

#### Pre-flight (Safety Gate)

- If shrinking: **MUST** warn that running workloads may be disrupted
- Suggest draining nodes before scale-down for stateful workloads

#### Execution — CLI (`gcloud`)

```bash
# Manual resize
gcloud container clusters resize "{{user.cluster_name}}" --node-pool="{{user.node_pool_name}}" --num-nodes="{{user.new_node_count}}" --zone="{{user.location}}" --format="json"
# Enable autoscaling
gcloud container clusters update "{{user.cluster_name}}" --zone="{{user.location}}" --node-pool="{{user.node_pool_name}}" --enable-autoscaling --min-nodes="{{user.min_nodes:-1}}" --max-nodes="{{user.max_nodes:-10}}" --format="json"
```

#### Post-execution Validation

```bash
gcloud container node-pools describe "{{user.node_pool_name}}" --cluster="{{user.cluster_name}}" --zone="{{user.location}}" --format=json | jq '{name, currentNodeCount, status}'
```

---

### Operation: Upgrade Node Pool

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Cluster RUNNING | Describe | RUNNING | HALT |
| Version available | `gcloud container get-server-config --zone="{{user.location}}" --format="json"` | Version exists in channel | HALT — pick valid version |
| Workload impact | Warn: nodes will be cordoned/drained during upgrade | User acknowledges | Warn and continue |

#### Execution — CLI (`gcloud`)

```bash
gcloud container clusters upgrade "{{user.cluster_name}}" --zone="{{user.location}}" --node-pool="{{user.node_pool_name}}" --cluster-version="{{user.cluster_version}}" --format=json
```

#### Post-execution Validation

```bash
gcloud container node-pools describe "{{user.node_pool_name}}" --cluster="{{user.cluster_name}}" --zone="{{user.location}}" --format=json | jq '{name, version, status}'
```

---

### Operation: Delete Node Pool

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit user confirmation: irreversible delete of node pool `{{user.node_pool_name}}` on cluster `{{user.cluster_name}}`
- **MUST** warn: running workloads on this node pool will be disrupted/drained
- **MUST** check that the node pool is not the only pool with system workloads

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| User confirmation | Ask: exact name | Match | HALT |
| System workload check | `kubectl get pods -n kube-system --field-selector spec.nodeName=$(kubectl get nodes -l cloud.google.com/gke-nodepool={{user.node_pool_name}} -o name \| head -1)` | Other pools can host system pods | HALT — migrate first |

#### Execution — CLI (`gcloud`)

```bash
gcloud container node-pools delete "{{user.node_pool_name}}" --cluster="{{user.cluster_name}}" --zone="{{user.location}}" --format=json
```

#### Post-execution Validation

```bash
gcloud container node-pools describe "{{user.node_pool_name}}" --cluster="{{user.cluster_name}}" --zone="{{user.location}}" --quiet 2>&1 || echo "✅ Node pool confirmed deleted"
```

---

### Operation: Get Cluster Credentials

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Cluster RUNNING | Describe | RUNNING | HALT |
| kubectl | `command -v kubectl` | Found | HALT — install |

#### Execution — CLI (`gcloud`)

```bash
gcloud container clusters get-credentials "{{user.cluster_name}}" --zone="{{user.location}}"
```

For private clusters: `--internal-ip`

#### Post-execution Validation

```bash
kubectl cluster-info --request-timeout=10s && kubectl get nodes -o wide
```

---

## Prerequisites

See [references/core-concepts.md](references/core-concepts.md) for installation and credential config. Never commit SA keys.

## Reference Directory

- [Core Concepts](references/core-concepts.md)
- [API & SDK Usage](references/api-sdk-usage.md)
- [gcloud Usage](references/gcloud-usage.md)
- [Troubleshooting](references/troubleshooting.md)
- [Monitoring](references/monitoring.md)
- [Integration](references/integration.md)
- [Idempotency Checklist](references/idempotency-checklist.md)
- [Well-Architected Assessment](references/well-architected-assessment.md)
- [Rubric (GCL)](references/rubric.md)
- [Prompt Templates (GCL)](references/prompt-templates.md)

Best practices: [references/well-architected-assessment.md](references/well-architected-assessment.md).

## Quality Gate (GCL)

Implements the **Generator-Critic-Loop (GCL)** per `AGENTS.md §11`.

| Property | Value |
|----------|-------|
| Classification | **required** (Delete operations present) |
| max_iter | 2 |
| Most-scrutinized | Delete Cluster, Delete Node Pool |

- **Rubric**: [references/rubric.md](references/rubric.md)
- **Prompt Templates**: [references/prompt-templates.md](references/prompt-templates.md)

> Token Efficiency 规则详见根目录 AGENTS.md §9（TE-1~TE-8，禁止跨文件重复 — TE-6）。

## AIOps 自愈 (Self-Healing)

GKE 异常检测与自愈闭环（节点 NotReady / 节点池扩容失败 / 工作负载 CrashLoopBackOff / HPA 上限）的完整 runbook，含 detection → DRY-RUN preview → 门禁 → 幂等 apply，以及 HALT 路径（节点池删除/版本升级回滚）与闭环反馈模式：

- [AIOps 自愈 Playbook](references/advanced/aiops-gke-anomaly.md#self-healing-playbook)

> 自愈遵循 `AGENTS.md §0.1` 凭证遮蔽、`docs/error-taxonomy.md` 错误分类、`AGENTS.md §5/§7` 跨技能爆炸半径约束，并通过 `gcp-gcl-runner-ops/trace_feedback.py` 回写 GCL 闭环。

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-07 | Initial release: GKE cluster and node pool operations; dual-path gcloud+SDK; GCL quality gate |