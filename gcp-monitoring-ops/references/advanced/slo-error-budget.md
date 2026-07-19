# SLO & Error Budget Policy — Google Cloud Monitoring

> 基于 Cloud Monitoring 的 SLO / 错误预算（error budget）治理策略：定义 burn-rate 告警、预算耗尽时的自动 freeze / rollback 触发条件，以及对应的 dry-run 与人工复核门禁。Recovery 词汇对齐 [docs/error-taxonomy.md](../../../docs/error-taxonomy.md)。

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

SLO（Service Level Objective）通过 Error Budget（错误预算）量化可接受的错误量。当预算被快速消耗（高 burn-rate）时，需要提前预警；当预算耗尽时，应触发 **发布冻结 (freeze)** 或 **回滚 (rollback)** 以保护可用性。

本策略只管理「监控侧」的预算计算、burn-rate 告警与 freeze/rollback 信号；真正的回滚/冻结执行由 CI/CD 与资源 owner skill 完成（监控只发信号、不开闸）。

## 触发条件 (Trigger)

| 触发信号 | 判定条件 | 典型 error-taxonomy 维度 | 默认自愈动作 |
|----------|----------|--------------------------|--------------|
| 快速消耗 (fast burn) | 1h burn-rate ≥ 14.4（即 1h 烧掉整月预算） | `UNCLASSIFIED` | `REMEDIATE`（建 burn-rate 告警）+ `ESCALATE` |
| 中速消耗 (slow burn) | 6h burn-rate ≥ 6 | `UNCLASSIFIED` | `REMEDIATE` + `ESCALATE` |
| 预算耗尽 (budget exhausted) | 滚动窗口内错误率超过 1 - SLO 阈值 | `FAILED_PRECONDITION` | `HALT` → `ESCALATE`（发 freeze/rollback 信号） |
| 预算临近耗尽 (near-exhausted) | 剩余预算 < 10% | `FAILED_PRECONDITION` | `REMEDIATE`（提高告警敏感度）+ `ESCALATE` |

> **激活边界：** 监控侧只计算预算、发 burn-rate 告警、并产出 freeze/rollback 建议信号。禁止监控直接执行发布回滚（那是 CI/CD 的职责）——预算耗尽时动作一律标 `HALT` 交人工/CI 决策。

## 检测 (Detection)

### 检测 1 — 多窗口 burn-rate 告警（gcloud monitoring）

Cloud Monitoring 的 SLO + alertPolicy 用多窗口多燃尽率条件表达 fast/slow burn：

```bash
# 创建 fast-burn (1h/14.4, 6h/6) 告警策略
gcloud alpha monitoring policies create \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --policy='{
    "displayName": "SLO Fast Burn Rate",
    "conditions": [{
      "displayName": "fast burn 14.4x/1h and 6x/6h",
      "conditionThreshold": {
        "filter": "select_slo_burn_rate(\"projects/{{env.CLOUDSDK_CORE_PROJECT}}/services/{{user.service_id}}/serviceLevelObjectives/{{user.slo_id}}\", \"14400s\", \"3600s\") > 14.4 OR select_slo_burn_rate(\"projects/{{env.CLOUDSDK_CORE_PROJECT}}/services/{{user.service_id}}/serviceLevelObjectives/{{user.slo_id}}\", \"86400s\", \"21600s\") > 6",
        "comparison": "COMPARISON_GT",
        "duration": "0s",
        "trigger": {"count": 1}
      }
    }],
    "notificationChannels": ["projects/{{env.CLOUDSDK_CORE_PROJECT}}/notificationChannels/{{user.channel_id}}"]
  }'
```

### 检测 2 — 当前错误预算余量（MQL）

```bash
# 估算滚动 30d 窗口的错误率与剩余预算
gcloud monitoring query \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" \
  --query='fetch service_level_objective
  | within 30d
  | condition val() > (1 - 0.99)
  | count()'
```

### 检测 3 — 预算耗尽确认（日志查询）

```bash
# 查 SLO burn 相关 incident 是否已触发
gcloud monitoring policies list-incidents \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --filter="state=OPEN AND alertPolicy.displayName:SLO" \
  --format="json" | jq -r '.[].alertPolicy.name'
```

## 自愈动作 (Self-Healing Actions)

### 动作 A — 建立/提升 burn-rate 告警敏感度（REMEDIATE）

**Dry-run：**

```bash
# 预览将创建的告警策略（不创建）
echo "[DRY-RUN] Would create fast-burn alert for SLO {{user.slo_id}} (no mutation)"
gcloud alpha monitoring policies list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --filter="displayName:SLO" --format="json" | jq -r '.[].displayName'
```

**Apply（幂等）：** 用稳定 `displayName` 创建；已存在则视为 no-op（重复创建会 `ALREADY_EXISTS`，需换名或幂等更新）。

```bash
# 提升敏感度：预算 <10% 时收紧窗口（覆盖式更新，终态一致）
gcloud alpha monitoring policies update "{{user.burn_policy_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --policy='{ "displayName": "SLO Near-Exhausted", "conditions": [ /* tightened window */ ] }'
```

**幂等性说明：** 覆盖式更新告警策略终态一致；新建带唯一名的策略若已存在则 `HALT` 提示换名（`idempotent_safe=true` for update, false for create）。

**人工复核门禁：** 提升敏感度仅影响告警频率，低风险；但改阈值仍需变更记录。

### 动作 B — 预算耗尽 → 发布冻结信号（HALT → ESCALATE）

**Dry-run / 信号产出：**

```bash
# 产出 freeze 建议信号（不执行冻结，冻结由 CI/CD 开闸）
echo "[DRY-RUN] Would emit freeze signal: budget_exhausted=true slo={{user.slo_id}}"
```

**Apply：** 监控写入一条信号事件并 `ESCALATE` 工单；**不**自动冻结/回滚发布。

```bash
# 1) 记录预算耗尽事件到日志（供 CI/CD / 人审消费）
gcloud logging write monitoring-slo-policy \
  '{"event":"error_budget_exhausted","slo":"{{user.slo_id}}","action":"freeze_signal"}' \
  --severity=WARNING --project="{{env.CLOUDSDK_CORE_PROJECT}}"
# 2) ESCALATE：提工单通知 release owner（不自动改发布系统）
```

**幂等性说明：** 写日志事件可重复（每条独立记录）；工单创建须按 SLO+窗口去重（`idempotent_safe=true`）。

**人工复核门禁：** 冻结/回滚是破坏性发布决策，一律 `HALT` 于人工/CI 决策门禁——监控只发信号，不开闸。

### 动作门禁总表

| 动作 | Recovery | 幂等 | 门禁级别 |
|------|----------|------|----------|
| A 建/提 burn-rate 告警 | `REMEDIATE` | true (update) | 变更记录 |
| B 预算耗尽发 freeze 信号 | `HALT`→`ESCALATE` | true (去重) | HALT（发布决策） |

## GCL 连接段 (GCL Connection)

SLO / 错误预算治理可纳入 GCL Runner 闭环：

- **调度执行**：`gcp-gcl-runner-ops/scripts/gcl_runner_enhanced.py` 周期计算预算余量并比对 `StateSnapshot`（上周期预算、当前 burn-rate）。`DegradationDetector` 检测 freeze 信号是否误触发（如 SLO 定义漂移导致假耗尽）。
- **失败回流**：预算计算异常、freeze 信号未被 CI 消费、或 burn-rate 告警误报，结论经 `gcp-gcl-runner-ops/trace_feedback.py` 回流到 GCL 评分，形成检测→信号→反馈闭环（同 [docs/cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md) 的「闭环反馈」）。
- **证据留存**：trace 含 `slo_id` / `burn_rate` / `budget_remaining` / `signal_emitted` / `gate_passed`。

## Error Taxonomy 引用

Recovery Action Vocabulary 对齐 [docs/error-taxonomy.md](../../../docs/error-taxonomy.md)：

- `HALT` — 预算耗尽后的冻结/回滚决策，交人工/CI，监控不开闸。
- `REMEDIATE` — 建立/提升 burn-rate 告警敏感度（安全可重放）。
- `ESCALATE` — 预算耗尽提工单、通知 release owner。
- `RETRY` — 预算计算因 `RATE_LIMITED` / 临时错误失败时带退避重试。

`idempotent_safe` 约定同 taxonomy（详见 [self-healing-runbook.md](self-healing-runbook.md)）。

## 跨域关联 (Cross-Skill)

SLO 预算耗尽信号需要跨域执行方接手：

```
SLO 预算耗尽 (monitoring)
   ├─ 发布冻结 ───────────► CI/CD pipeline (gate on freeze signal)
   ├─ 服务回滚 ───────────► gcp-gke-ops / gcp-gce-ops (rollback runbook)
   └─ 根因定位 ───────────► 资源 owner skill (按异常类型委托)
```

> 跨域 blast-radius 描述不在此展开。详见 docs/cross-skill-blast-radius.md。

## See Also

- [Self-Healing Runbook](self-healing-runbook.md) — 监控面自愈动作与门禁
- [Error Taxonomy (repo-wide)](../../../docs/error-taxonomy.md) — Recovery Action Vocabulary
- [Cross-Skill Blast Radius](../../../docs/cross-skill-blast-radius.md) — 跨域关联与爆炸半径
- [GCL Runner Enhanced](../../../gcp-gcl-runner-ops/scripts/gcl_runner_enhanced.py)
- [GCL Trace Feedback](../../../gcp-gcl-runner-ops/trace_feedback.py)
- [Cloud Monitoring SLO Docs](https://cloud.google.com/monitoring/service-level-objectives)
