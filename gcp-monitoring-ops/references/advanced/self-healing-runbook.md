# AIOps Self-Healing Runbook — Google Cloud Monitoring

> 监控面的自愈 runbook：当 Cloud Monitoring 自身或其观测目标出现可自愈异常时，按 **检测 → 自愈动作（dry-run + 幂等 + 人工复核门禁）→ GCL 反馈** 的闭环处置。自愈词汇（HALT / RETRY / REMEDIATE / ESCALATE）来自 [docs/error-taxonomy.md](../../../docs/error-taxonomy.md)。监控只负责静默/抑制自身告警面与补回缺失指标采集，底层资源修复一律委托对应 skill 的 AIOps runbook。

## Table of Contents

1. [触发条件 (Trigger)](#触发条件-trigger)
2. [检测 (Detection)](#检测-detection)
3. [自愈动作 (Self-Healing Actions)](#自愈动作-self-healing-actions)
4. [GCL 连接段 (GCL Connection)](#gcl-连接段-gcl-connection)
5. [Error Taxonomy 引用](#error-taxonomy-引用)
6. [跨域关联 (Cross-Skill)](#跨域关联-cross-skill)
7. [See Also](#see-also)

## 触发条件 (Trigger)

当以下任一信号出现时，激活本 runbook 的自愈流程：

| 触发信号 | 判定条件 | 典型 error-taxonomy 维度 | 默认自愈动作 |
|----------|----------|--------------------------|--------------|
| 告警疲劳 (alert fatigue) | 单策略 10 min 内 OPEN 事件 >10（详见 [aiops-alert-anomaly.md](aiops-alert-anomaly.md)） | `UNCLASSIFIED` | `REMEDIATE`（静默）+ `ESCALATE` |
| 指标缺失 (missing metrics) | 期望采集的指标最近 30 min 无数据点，但采集器健康 | `FAILED_PRECONDITION` | `RETRY` / `REMEDIATE`（重新启用采集） |
| 可用性检查失败 (uptime-check failure) | uptime check 连续失败 ≥3 次、且被检端点非本 skill 管辖 | `UNAVAILABLE` | `RETRY` → `ESCALATE`（委托 `gcp-gce-ops` / `gcp-gke-ops`） |
| 告警抖动 (flapping) | 单策略 1 h 内 open→close 周期 >5 | `UNCLASSIFIED` | `REMEDIATE`（静默）+ `ESCALATE` |
| 通知渠道失效 (channel broken) | 通知渠道最近投递失败率 >50% | `UNAVAILABLE` | `REMEDIATE`（重建/切换渠道）+ `ESCALATE` |

> **激活边界：** 监控自愈只作用于「监控面自身」（告警、渠道、采集配置、可用性检查配置）。任何指向底层资源（VM / GKE / DB / 网络）的根因，一律按 [跨域关联](#跨域关联-cross-skill) 委托，本 runbook 不擅自修复资源。

## 检测 (Detection)

### 检测 1 — 指标缺失（MQL 查询）

用 Monitoring Query Language 检查某指标最近窗口是否缺数据：

```bash
# MQL: 拉取最近 30m 的 cpu utilization 时间序列，若结果为空即缺失
gcloud monitoring query \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" \
  --query='fetch gce_instance
  | metric '"'"'compute.googleapis.com/instance/cpu/utilization'"'"'
  | within 30m
  | every 1m
  | group_by [resource.instance_id], [value_utilization_mean: mean(value.utilization)]'
```

```bash
# 空结果判定：点数明显少于预期（30 个点）
gcloud monitoring query \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --query='fetch gce_instance
  | metric '"'"'compute.googleapis.com/instance/cpu/utilization'"'"'
  | within 30m
  | every 1m
  | count()' --format="json" | jq '.[].pointData | length'
```

### 检测 2 — 可用性检查失败（gcloud monitoring）

```bash
# 列出处于 FAILING 状态的 uptime check
gcloud monitoring uptime-check list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq -r '
    .[] | select(.checkStatusSummary // .state == "FAILING")
    | {name, displayName, state}'

# 查看某 uptime check 的最近失败事件
gcloud monitoring uptime-check describe "{{user.uptime_check_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{name, displayName, checkStatusSummary}'
```

### 检测 3 — 通知渠道投递失败（日志查询）

```bash
# 查询 NotificationDelivery 失败日志
gcloud logging read \
  "resource.type=monitoring_notification_channel AND jsonPayload.event_type=notification_failure" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --freshness=1h --format="json" | jq -r '.[].jsonPayload'
```

### 检测 4 — 告警风暴 / 抖动（复用）

告警风暴与抖动判定逻辑见 [aiops-alert-anomaly.md](aiops-alert-anomaly.md) 的 Detection 章节，本 runbook 不再重复。

## 自愈动作 (Self-Healing Actions)

每条自愈动作包含 **dry-run 步骤**、**幂等性说明**、**人工复核门禁**，并标注 [docs/error-taxonomy.md](../../../docs/error-taxonomy.md) 的 Recovery Action Vocabulary。

### 动作 A — 静默告警风暴策略（REMEDIATE，带门禁）

**Dry-run：**

```bash
# 预览将被静默的策略，不产生任何变更
gcloud monitoring policies describe "{{user.alert_policy_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{name, displayName, enabled}'
echo "[DRY-RUN] Would silence policy {{user.alert_policy_id}} for 30m (no mutation)"
```

**Apply（幂等）：** 重复执行 `enabled=false` 在已禁用策略上是 no-op。

```bash
# 人工复核门禁通过后才执行（生产策略必须显式批准令牌/交互确认）
gcloud monitoring policies update "{{user.alert_policy_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --no-enabled
```

**幂等性说明：** `enabled=false` 在已禁用策略上返回相同终态，无副作用，可安全重试（对应 taxonomy `idempotent_safe=true`）。

**人工复核门禁：** 生产策略的静默一律 HALT 于人工复核门禁——未持批准令牌不得自动静默。

### 动作 B — 重新启用缺失指标采集（REMEDIATE）

**Dry-run：**

```bash
# 预览当前采集器/agent 状态
gcloud monitoring agents describe "{{user.agent_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" \
  | jq '{name, state}'
echo "[DRY-RUN] Would re-enable metric collection for {{user.agent_id}}"
```

**Apply（幂等）：** 重新启用一个已启用的采集器是 no-op。

```bash
# 重新启动 collection（例如 ops-agent 配置失效后的自愈）
gcloud compute ssh "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --zone="{{user.zone}}" \
  --command="sudo service google-cloud-ops-agent restart"
```

**幂等性说明：** 重启一个健康运行的采集器不改变采集终态；若采集本就正常，动作结果为 no-op（`idempotent_safe=true`）。

**人工复核门禁：** 仅当缺失指标确认非下游资源故障（已排除 VMs/DB 真正宕机）时执行；否则按 [跨域关联](#跨域关联-cross-skill) 委托，动作降为 `ESCALATE`。

### 动作 C — 重建失效通知渠道（REMEDIATE + ESCALATE）

**Dry-run：**

```bash
# 预览失效渠道，不删除不新建
gcloud monitoring channels describe "{{user.channel_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{name, displayName, type, enabled}'
echo "[DRY-RUN] Would create fallback channel and re-link policies"
```

**Apply（需门禁）：** 新建渠道属可回滚变更，但会重排通知路由，须人工复核。

```bash
# 1) 新建备用渠道（如 email / webhook）
gcloud monitoring channels create \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --display-name="fallback-{{user.channel_id}}" \
  --type="email" --email-address="{{user.fallback_email}}"
# 2) 将受影响策略重新指向新渠道（REMEDIATE）
#    gcloud monitoring policies update <id> --notification-channels=<new>
```

**幂等性说明：** 新建带唯一 `display-name` 的渠道若已存在则 `ALREADY_EXISTS`（taxonomy `HALT` 提示换名）；重链策略是覆盖式更新，重复执行终态一致（`idempotent_safe=true`）。

**人工复核门禁：** 渠道重建与重链影响告警送达路径，须人工确认后备邮箱/Webhook 有效后再执行。

### 动作 D — 可用性检查失败升级（RETRY → ESCALATE）

**Dry-run / 判定：**

```bash
# 先确认失败是否来自被检端点本身（而非监控配置错误）
gcloud monitoring uptime-check describe "{{user.uptime_check_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" \
  | jq '{name, checkStatusSummary, configured_on_resource}'
echo "[DRY-RUN] Would escalate endpoint failure to owning skill (no config mutation)"
```

**Apply：** 监控不修改被检端点，仅 `RETRY` 复查；持续失败则 `ESCALATE` 工单并委托资源 owner skill。

**幂等性说明：** `RETRY` 查阅动作无副作用；`ESCALATE` 仅建单，重复建单应做去重（`idempotent_safe=true`）。

**人工复核门禁：** 不需要静默监控自身，但要等待资源 owner 接手；监控侧不自动改端点配置（HALT 于配置变更）。

### 动作门禁总表

| 动作 | Recovery | 幂等 | 门禁级别 |
|------|----------|------|----------|
| A 静默策略 | `REMEDIATE` | true | HALT（人工复核） |
| B 重启采集 | `REMEDIATE` | true | 条件门禁（先排除资源故障） |
| C 重建渠道 | `REMEDIATE`+`ESCALATE` | true (重链) | HALT（人工复核路由） |
| D 升级端点 | `RETRY`→`ESCALATE` | true | HALT（配置变更） |

## GCL 连接段 (GCL Connection)

本 runbook 的自愈执行可纳入 GCL Runner 的定时编排，形成「检测 → 处置 → 反馈」闭环：

- **调度执行**：自愈流程可由 `gcp-gcl-runner-ops/scripts/gcl_runner_enhanced.py` 周期调度。执行前后分别抓取 `StateSnapshot`（策略 enabled 状态、采集器状态、渠道健康度），用于变更前后对比与回滚判定；`DegradationDetector` 在自愈后检测监控面是否引入新的降级（如误静默导致检测盲区扩大）。
- **失败回流**：自愈动作若触发 HALT、门禁未过、或执行异常，结论通过 `gcp-gcl-runner-ops/trace_feedback.py` 回流到 GCL 评分与知识库，沉淀为检测→处置→反馈闭环（与 [docs/cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md) 的「闭环反馈」条目一致）。
- **证据留存**：每次自愈写入 JSON trace（gitignored），字段含 `before_snapshot` / `after_snapshot` / `recovery_action` / `gate_passed`。

> 监控自愈只改「监控面」状态；任何回滚动作（如自动 un-silence）必须在 StateSnapshot 记录窗口内完成，避免永久盲区。

## Error Taxonomy 引用

本 runbook 的 Recovery Action Vocabulary 严格对齐 [docs/error-taxonomy.md](../../../docs/error-taxonomy.md)：

- `HALT` — 停止并交人工决策（删除策略、改阈值、批量静默、改被检端点配置）。
- `RETRY` — 带退避重试（可用性检查复查、`RATE_LIMITED` 场景）。
- `REMEDIATE` — 已知安全动作自动修复（静默、`enabled=false/true`、重启采集、重链渠道）。
- `ESCALATE` — 升级工单 / 委托资源 owner skill，不再自动动作。

`idempotent_safe` 标记约定同 taxonomy：安全可重放的动作为 `true`，创建/删除/重链等须加护栏。

## 跨域关联 (Cross-Skill)

监控检测到资源根因异常时，**只检测 + 转交**，不修复资源本身：

```
监控告警触发
   ├─ VM CPU/内存越界 ─────► gcp-gce-ops (resize/restart runbook)
   ├─ GKE 节点压力 ─────────► gcp-gke-ops (drain/scale runbook)
   ├─ DB 慢查询/故障切换 ──► gcp-cloudsql-ops (failover runbook)
   ├─ 网络出口异常 ────────► gcp-vpc-ops (aiops-network-anomaly.md)
   ├─ 安全发现 ────────────► gcp-securitycenter-ops (auto-mute runbook)
   └─ 告警风暴/抖动/渠道失效 ► 本 runbook（仅修监控面）
```

> 跨域 blast-radius 描述不在此展开。详见 docs/cross-skill-blast-radius.md。

## See Also

- [Alert Anomaly Runbook](aiops-alert-anomaly.md) — 告警风暴/抖动检测细节
- [Error Taxonomy (repo-wide)](../../../docs/error-taxonomy.md) — Recovery Action Vocabulary 权威来源
- [Cross-Skill Blast Radius](../../../docs/cross-skill-blast-radius.md) — 跨域关联与爆炸半径
- [GCL Runner Enhanced](../../../gcp-gcl-runner-ops/scripts/gcl_runner_enhanced.py) — 自愈调度与 StateSnapshot
- [GCL Trace Feedback](../../../gcp-gcl-runner-ops/trace_feedback.py) — 自愈结论回流
- [Cloud Monitoring Docs](https://cloud.google.com/monitoring/docs)
