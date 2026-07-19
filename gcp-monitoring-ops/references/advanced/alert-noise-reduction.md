# Alert Noise Reduction — Google Cloud Monitoring

> 告警降噪 runbook：通过去重、分组、抑制窗口降低告警疲劳，并对瞬时（transient）告警做带门禁 + 幂等的自动静音（auto-mute）。Recovery 词汇对齐 [docs/error-taxonomy.md](../../../docs/error-taxonomy.md)。监控只降自身告警面噪声，底层根因仍委托对应 skill。

## Table of Contents

1. [Overview](#overview)
2. [触发条件 (Trigger)](#触发条件-trigger)
3. [检测 (Detection)](#检测-detection)
4. [自愈动作 (Self-Healing Actions)](#自愈动作-self-healing-actions)
5. [GCL 连接段 (GCL Connection)](#gcl-连接段-gcl-connection)
6. [Error Taxonomy 引用](#error-taxonomy-引用)
7. [跨域关联 (Cross-Skill)](#跨域关联-cross-skill)
8. [See Also](#see-also)

## Overview

告警疲劳来自重复、冗余、瞬时抖动类告警。降噪三板斧：**去重 (dedup)**、**分组 (grouping)**、**抑制窗口 (suppression window)**。对确认属于瞬时的告警（如一次性抖动、可自愈的短时超时），监控可做自动静音——但必须 dry-run 先、幂等、且过人工复核门禁。

> **Credential Masking (§0.1):** 永不打印 SA key 内容或 `GOOGLE_APPLICATION_CREDENTIALS` 取值。仅验证存在：`test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA exists"`。

## 触发条件 (Trigger)

| 触发信号 | 判定条件 | 典型 error-taxonomy 维度 | 默认自愈动作 |
|----------|----------|--------------------------|--------------|
| 重复告警 (duplicate) | 同一条件 10 min 内 ≥5 条相似 incident | `UNCLASSIFIED` | `REMEDIATE`（合并/去重）+ `ESCALATE` |
| 瞬时抖动 (transient) | incident 生命周期 <60s 且自动恢复 | `TIMEOUT` / `UNAVAILABLE` | `REMEDIATE`（自动静音）+ `ESCALATE` |
| 关联爆发 (correlated burst) | 多策略因同一上游事件同时 firing | `FAILED_PRECONDITION` | `REMEDIATE`（分组）+ `ESCALATE` |
| 抑制窗口内重复 | 已知维护/发布窗口内的预期告警 | `FAILED_PRECONDITION` | `REMEDIATE`（抑制窗口） |

> **激活边界：** 降噪只作用于「告警呈现层」。把瞬时抖动当作根因修复是误用——瞬时告警若持续，应转交资源 owner skill（见 [跨域关联](#跨域关联-cross-skill)）。

## 检测 (Detection)

### 检测 1 — 重复/相似 incident 去重（gcloud monitoring）

```bash
# 按 policy + 条件指纹聚合，找出高频重复
gcloud monitoring policies list-incidents \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --filter="state=OPEN" --format="json" | jq -r '
    group_by(.alertPolicy.name)[] 
    | {policy: .[0].alertPolicy.name, count: length}
    | select(.count >= 5)'
```

### 检测 2 — 瞬时告警（短生命周期 auto-recover）

```bash
# 找 open→close 间隔 <60s 的 incident（典型瞬时抖动）
gcloud monitoring policies list-incidents \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --filter="state=CLOSED" --format="json" | jq -r '
    .[] | select(
      ((.metadata.endTime | fromdateiso8601) - (.metadata.startTime | fromdateiso8601)) < 60
    ) | {name: .alertPolicy.name, life_sec: (...) }'
```

### 检测 3 — 关联爆发（同上游事件多策略）

```bash
# 同一时间窗内多策略 firing，疑似同源
gcloud monitoring policies list-incidents \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --filter="state=OPEN" --format="json" | jq -r '
    group_by(.metadata.startTime[:16])[] 
    | {window: .[0].metadata.startTime[:16], policies: ([.[].alertPolicy.name] | unique | length)}
    | select(.policies >= 3)'
```

### 检测 4 — 抑制窗口命中（日志/标注查询）

```bash
# 查维护窗口标注，确认告警落在已知抑制窗口内
gcloud logging read \
  "resource.type=monitoring_policy AND jsonPayload.maintenance_window=true" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --freshness=6h --format="json"
```

## 自愈动作 (Self-Healing Actions)

### 动作 A — 自动静音瞬时告警（REMEDIATE，带门禁）

**Dry-run：**

```bash
# 预览将被静音的瞬时策略
gcloud monitoring policies describe "{{user.alert_policy_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{name, displayName, enabled}'
echo "[DRY-RUN] Would auto-mute transient policy {{user.alert_policy_id}} for 15m (no mutation)"
```

**Apply（幂等）：** 重复 `enabled=false` 在已禁用策略上是 no-op。

```bash
# 人工复核门禁通过后执行；短时窗口后自动 un-silence
gcloud monitoring policies update "{{user.alert_policy_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --no-enabled
```

**幂等性说明：** `enabled=false` 可安全重放，终态一致（`idempotent_safe=true`，见 taxonomy）。

**人工复核门禁：** 生产瞬时告警静音一律 HALT 于人工复核门禁；静音窗口须记录并到期自动 un-silence。

### 动作 B — 抑制窗口自动 mute（REMEDIATE）

**Dry-run：**

```bash
# 预览维护窗口内的待抑制策略清单
gcloud monitoring policies list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" \
  | jq -r '.[] | select(.displayName | test("{{user.maintenance_match}}")) | .name'
echo "[DRY-RUN] Would mute N policies for maintenance window (no mutation)"
```

**Apply（幂等）：** 维护窗口结束后批量 un-silence。

```bash
# 窗口开始：批量静音（覆盖式，重复执行终态一致）
for p in $(gcloud monitoring policies list --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq -r '.[] | select(.displayName | test("{{user.maintenance_match}}")) | .name'); do
  gcloud monitoring policies update "$p" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --no-enabled
done
```

**幂等性说明：** 对已在窗口内的策略重复静音为 no-op；un-silence 对未静音策略也是 no-op（`idempotent_safe=true`）。

**人工复核门禁：** 批量静音影响多个策略，须人工确认维护窗口真实有效（防误静音盲区）。

### 动作 C — 分组/去重调优（REMEDIATE，低风险）

**Dry-run：**

```bash
# 预览聚合配置改动（仅展示，不改阈值）
gcloud monitoring policies describe "{{user.alert_policy_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" \
  | jq '{displayName, alertStrategy}'
echo "[DRY-RUN] Would set notification_rate_limit / grouping on policy"
```

**Apply：** 设置 `alertStrategy.notificationRateLimit` 合并通知，降低重复推送。

```bash
gcloud alpha monitoring policies update "{{user.alert_policy_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --policy='{ "alertStrategy": { "notificationRateLimit": { "period": "300s" } } }'
```

**幂等性说明：** 覆盖式更新，重复执行终态一致（`idempotent_safe=true`）。

**人工复核门禁：** 仅调节通知频率，低风险；但改 alertStrategy 仍建议变更记录。

### 动作门禁总表

| 动作 | Recovery | 幂等 | 门禁级别 |
|------|----------|------|----------|
| A 自动静音瞬时 | `REMEDIATE` | true | HALT（人工复核） |
| B 抑制窗口 mute | `REMEDIATE` | true | HALT（确认窗口） |
| C 分组/去重调优 | `REMEDIATE` | true | 变更记录 |

## GCL 连接段 (GCL Connection)

降噪自愈同样纳入 GCL Runner 闭环：

- **调度执行**：`gcp-gcl-runner-ops/scripts/gcl_runner_enhanced.py` 周期扫描重复/瞬时 incident，执行前抓 `StateSnapshot`（各策略 enabled 状态、静音窗口），`DegradationDetector` 检测降噪是否造成真实告警被吞（如静音窗口过长导致真故障漏报）。
- **失败回流**：自动静音若误伤、抑制窗口误启、或门禁未过，结论经 `gcp-gcl-runner-ops/trace_feedback.py` 回流到 GCL 评分，形成检测→降噪→反馈闭环（同 [docs/cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md) 的「闭环反馈」）。
- **证据留存**：trace 含 `muted_policies` / `suppression_window` / `incident_count` / `gate_passed`。

## Error Taxonomy 引用

Recovery Action Vocabulary 对齐 [docs/error-taxonomy.md](../../../docs/error-taxonomy.md)：

- `HALT` — 生产策略静音、批量静音、改 alertStrategy 决策交人工/门禁。
- `REMEDIATE` — 自动静音、抑制窗口 mute、分组/去重调优（安全可重放）。
- `ESCALATE` — 瞬时告警持续化（不再是瞬时）时提工单并转交资源 owner。
- `RETRY` — 降噪计算因 `RATE_LIMITED` 失败时带退避重试。

`idempotent_safe` 约定同 taxonomy（详见 [self-healing-runbook.md](self-healing-runbook.md)）。

## 跨域关联 (Cross-Skill)

降噪只处理「呈现层」；瞬时告警背后的根因需转交：

```
瞬时/重复告警 (monitoring)
   ├─ VM 短时超时 ────────► gcp-gce-ops (restart/resize runbook)
   ├─ GKE 节点抖动 ───────► gcp-gke-ops (drain/scale runbook)
   ├─ DB 连接闪断 ────────► gcp-cloudsql-ops (failover runbook)
   └─ 网络瞬时丢包 ──────► gcp-vpc-ops (aiops-network-anomaly.md)
```

> 跨域 blast-radius 描述不在此展开。详见 docs/cross-skill-blast-radius.md。

## See Also

- [Self-Healing Runbook](self-healing-runbook.md) — 监控面自愈总纲与门禁
- [Alert Anomaly Runbook](aiops-alert-anomaly.md) — 告警风暴/抖动检测细节
- [Error Taxonomy (repo-wide)](../../../docs/error-taxonomy.md) — Recovery Action Vocabulary
- [Cross-Skill Blast Radius](../../../docs/cross-skill-blast-radius.md) — 跨域关联与爆炸半径
- [GCL Runner Enhanced](../../../gcp-gcl-runner-ops/scripts/gcl_runner_enhanced.py)
- [GCL Trace Feedback](../../../gcp-gcl-runner-ops/trace_feedback.py)
- [Cloud Monitoring Docs](https://cloud.google.com/monitoring/docs)
