# AIOps Self-Healing — Google Cloud Run

> 为 Cloud Run 提供 AIOps 驱动的自愈 runbook：冷启动/延迟突增、并发与内存超限（OOM）、健康检查失败等常见故障的自动诊断与自愈动作。所有自愈动作遵循 **dry-run + 幂等 + 门禁** 三原则，凭证处理遵循 AGENTS.md §0.1。

## Table of Contents

1. [Overview](#overview)
2. [Self-Healing Principles](#self-healing-principles)
3. [Anomaly Catalog](#anomaly-catalog)
4. [Remediation Playbooks](#remediation-playbooks)
5. [Blast Radius](#blast-radius)
6. [Credential Masking](#credential-masking)
7. [See Also](#see-also)

## Overview

Cloud Run 是 serverless 容器平台，常见故障模式与自愈策略：

| Anomaly | Symptom | Self-Heal Action | Gate |
|---------|---------|------------------|------|
| Cold start / latency spike | p95 latency ↑, startup CPU boost 不足 | 调整 `min-instances` | dry-run + 门禁 |
| Concurrency / OOM | `memory limit exceeded`, 实例重启 | 调整 CPU/memory/concurrency | 幂等 |
| Health check failed | `Ready=False`, startup/health probe 失败 | 回滚到上次稳定 revision | HALT 人工确认 |

错误分类与恢复策略引用 [`docs/error-taxonomy.md`](../../../docs/error-taxonomy.md)；跨产品影响范围引用 [`docs/cross-skill-blast-radius.md`](../../../docs/cross-skill-blast-radius.md)。

## Self-Healing Principles

所有自愈动作必须满足：

- **Dry-run**：先 `--format=json` 输出拟变更，不实际写入；确认后再执行。
- **幂等**：重复执行同一自愈动作结果一致（如 `min-instances` 已是目标值则跳过）。
- **门禁（Gate）**：
  - 资源调整类（min-instances / cpu / memory / concurrency）→ 自动执行，但需 dry-run 确认 + 记录变更。
  - 回滚 revision 类 → **HALT**，必须人工确认（可能造成流量回退、数据不一致）。

> 凭证处理见 [Credential Masking](#credential-masking) 与 AGENTS.md §0.1。

## Anomaly Catalog

### A1 — Cold Start / Latency Spike

**Detection**：`request_latencies` p95 较基线 >2x，或 `container_startup_latencies` 突增；`min-instances=0` 时新实例冷启动叠加请求峰值。

**Root cause**：空闲缩容至 0，突发流量触发冷启动；或 startup CPU boost 未开启。

**Self-heal**：提升 `min-instances` 预热实例，开启 `--startup-cpu-boost`。

### A2 — Concurrency / Memory Limit (OOM)

**Detection**：`container_oom_count` > 0，或 revision 状态 `Ready=False` 且 reason 含 `OOMKilled` / `memory limit exceeded`；`concurrency` 过高导致单实例堆积。

**Root cause**：内存配额不足、并发上限过高、单请求内存占用大。

**Self-heal**：提升 `memory` / `cpu`，或下调 `concurrency`（幂等资源调整）。

### A3 — Health Check Failed

**Detection**：revision `Ready=False`，condition message 含 `Healthcheck failed` / `Startup probe failed`；新 revision 无法进入服务状态。

**Root cause**：新镜像启动失败、端口不匹配、依赖（下游 cloudsql/bigquery）不可达、探针超时过短。

**Self-heal**：回滚到上次稳定 revision（**HALT 人工确认**）。

## Remediation Playbooks

### Playbook A1 — Min-Instances Tuning (dry-run + gate)

#### Pre-flight

| Check | Method | Expected |
|-------|--------|----------|
| Service exists | `gcloud run services describe` | Found |
| Current min-instances | `jq '.spec.template.scaling.minInstanceCount'` | 当前值 |

#### Dry-run (no mutation)

```bash
# 仅输出拟变更，不写入
gcloud run services describe "{{user.service_name}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{
    current_min: .spec.template.scaling.minInstanceCount,
    proposed_min: 2
  }'
```

#### Execute (idempotent)

```bash
# 幂等：若已是目标值则跳过
CUR=$(gcloud run services describe "{{user.service_name}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq -r '.spec.template.scaling.minInstanceCount // 0')
if [ "$CUR" -ne 2 ]; then
  gcloud run services deploy "{{user.service_name}}" \
    --image="$(gcloud run services describe "{{user.service_name}}" \
      --region="{{user.region:-us-central1}}" \
      --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
      --format="json" | jq -r '.spec.template.spec.containers[0].image')" \
    --min-instances=2 \
    --startup-cpu-boost \
    --region="{{user.region:-us-central1}}" \
    --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
    --format="json"
fi
```

#### Validate

```bash
gcloud run services describe "{{user.service_name}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '.spec.template.scaling.minInstanceCount'
```

### Playbook A2 — Resource Right-Sizing (idempotent)

#### Dry-run

```bash
gcloud run services describe "{{user.service_name}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{
    current_memory: .spec.template.spec.containers[0].resources.limits.memory,
    current_cpu: .spec.template.spec.containers[0].resources.limits.cpu,
    current_concurrency: .spec.template.spec.containers[0].resources.limits.concurrency
  }'
```

#### Execute (idempotent)

```bash
# 幂等：仅当资源与当前不一致时调整
gcloud run services deploy "{{user.service_name}}" \
  --image="$(gcloud run services describe "{{user.service_name}}" \
    --region="{{user.region:-us-central1}}" \
    --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
    --format="json" | jq -r '.spec.template.spec.containers[0].image')" \
  --memory="{{user.memory:-1Gi}}" \
  --cpu="{{user.cpu:-1}}" \
  --concurrency="{{user.concurrency:-50}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

#### Validate

```bash
gcloud run services describe "{{user.service_name}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '.spec.template.spec.containers[0].resources.limits'
```

### Playbook A3 — Rollback to Last Stable Revision (HALT)

> **HALT — 需人工确认。** 回滚会改变线上流量指向，可能影响进行中的请求与下游一致性。

#### Pre-flight

| Check | Method | Expected |
|-------|--------|----------|
| Service exists | `gcloud run services describe` | Found |
| Stable revision identified | `gcloud run revisions list` | 上一 Ready revision |

#### Dry-run (show target only)

```bash
gcloud run revisions list \
  --service="{{user.service_name}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '[.[] | select(.status.conditions[].status=="True")] | .[1:] | .[0].metadata.name' \
  && echo "Proposed rollback target above — requires human confirmation"
```

#### Execute (HALT gate)

```bash
# 仅在人工确认后执行；禁止自动回滚
read -r "CONFIRM?Rollback {{user.service_name}} to revision above? type service name to confirm: "
[ "$CONFIRM" = "{{user.service_name}}" ] || { echo "Aborted"; exit 1; }
gcloud run services update-traffic "{{user.service_name}}" \
  --to-revisions="$(gcloud run revisions list \
    --service="{{user.service_name}}" \
    --region="{{user.region:-us-central1}}" \
    --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
    --format="json" | jq -r '[.[] | select(.status.conditions[].status=="True")][1].metadata.name')=100" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

#### Validate

```bash
gcloud run services describe "{{user.service_name}}" \
  --region="{{user.region:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '.status.traffic[] | {revision: .revisionName, percent: .percent}'
```

## Blast Radius

Cloud Run 故障的级联影响（详见 [`docs/cross-skill-blast-radius.md`](../../../docs/cross-skill-blast-radius.md)）：

| Layer | Affected | Impact |
|-------|----------|--------|
| Ingress | Cloud Load Balancing / Cloud CDN | 上游 LB 健康检查失败 → 摘除后端；CDN 回源失败 → 5xx 上升 |
| Data plane | Cloud SQL (via VPC connector) | 实例 OOM/重启 → 连接池耗尽，下游查询超时 |
| Data plane | BigQuery | 健康检查失败导致任务提交失败，ETL 中断 |
| Consumers | 调用方服务 / 终端用户 | 请求延迟或错误率上升 |

**Gate implication**：自愈动作（尤其回滚）可能放大或缩小 blast radius，故 A3 强制 HALT。

## Credential Masking

遵循 AGENTS.md §0.1 — **NEVER** 输出 SA key 内容或 `GOOGLE_APPLICATION_CREDENTIALS` 路径内容。

| Context | Safe | Unsafe |
|---------|------|--------|
| Verify SA | `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "SA exists"` | `cat $GOOGLE_APPLICATION_CREDENTIALS` |
| Error msg | `Error: API call failed (credential omitted)` | actual SA key content |
| Log | `[INFO] SA=***` | `SA key: {"private_key":"...` |

## See Also

- [Cloud Run Operations SKILL](../../SKILL.md)
- [Troubleshooting](../troubleshooting.md)
- [Error Taxonomy](../../../docs/error-taxonomy.md)
- [Cross-Skill Blast Radius](../../../docs/cross-skill-blast-radius.md)
- [VPC AIOps Anomaly](../../../gcp-vpc-ops/references/advanced/aiops-network-anomaly.md)
