# AIOps Query Insights — Google Cloud SQL

> Provides database administrators with a guide to implementing AIOps-driven anomaly detection for Cloud SQL — query performance monitoring, storage growth prediction, connection pool anomalies, and automated remediation.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Query Performance Anomalies](#query-performance-anomalies)
5. [Storage Growth Prediction](#storage-growth-prediction)
6. [Connection Pool Monitoring](#connection-pool-monitoring)
7. [Real-Time Alerting](#real-time-alerting)
8. [Automated Remediation](#automated-remediation)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)
11. [See Also](#see-also)

## Overview

AIOps for Cloud SQL detects performance anomalies and predicts resource exhaustion. With Cloud SQL Insights and Cloud Monitoring, you can:

- Detect slow query patterns (performance regression)
- Monitor storage growth (quota management)
- Track connection pool exhaustion (availability)
- Identify lock contention issues (concurrency)
- Automate performance remediation

### Detection Capabilities

| Anomaly Type | Detection Method | Severity |
|--------------|-----------------|----------|
| Slow query increase | Time-series analysis | High |
| Storage growth spike | Linear regression | Medium |
| Connection pool exhaustion | Threshold monitoring | Critical |
| Lock contention | Wait event analysis | High |
| Replication lag | Metric deviation | Critical |

## Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                          Database Monitoring                            │
│                                                                          │
│  Cloud SQL Instance                                                      │
│  ┌────────────────┐    ┌────────────────┐    ┌──────────────────────┐   │
│  │ Query Load     │───►│ Cloud SQL      │───►│ Cloud Monitoring    │   │
│  │ (Connections)  │    │ Insights       │    │ (Metrics)           │   │
│  └────────────────┘    └────────────────┘    └──────────────────────┘   │
│                                                       │                  │
│              ┌────────────────────────────────────────┤                  │
│              │                     │                   │                 │
│       ┌──────▼──────┐      ┌──────▼──────┐     ┌──────▼──────┐        │
│       │ Query       │      │ Storage     │     │ Alert       │        │
│       │ Analysis    │      │ Prediction  │     │ Policy      │        │
│       └─────────────┘      └──────┬──────┘     └─────────────┘        │
│                                   │                                     │
│                          ┌────────▼────────┐                           │
│                          │ Automated       │                           │
│                          │ Remediation     │                           │
│                          └─────────────────┘                           │
└────────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

```bash
# 1. Enable required APIs
gcloud services enable sqladmin.googleapis.com
gcloud services enable monitoring.googleapis.com
gcloud services enable cloudsql.googleapis.com

# 2. Set project
export CLOUDSDK_CORE_PROJECT=my-cloudsql-project

# 3. Verify Cloud SQL access
gcloud sql instances list --format="table(name,databaseVersion,region)"
```

## Query Performance Anomalies

### Slow Query Detection

```bash
# Find slow queries using Cloud SQL Insights
# NOTE: operationType is NOT a valid server-side --filter field for
# `gcloud sql operations list`; the filter would silently return nothing.
# List all operations and filter client-side with jq on the real JSON field.
gcloud sql operations list \
  --instance=my-instance \
  --format="json" | \
  jq -r '.[] | select(.operationType == "QUERY") | [.name, .user, .startTime, .duration] | @tsv'
```

### Query Performance Analysis

```bash
# Analyze query performance
# NOTE: operationType is filtered client-side (not a valid --filter field).
gcloud sql operations list \
  --instance=my-instance \
  --format="json" | \
  jq '.[] | select(.operationType == "QUERY" and .duration > 300) | {id, user, query, duration}'
```

### Performance Regression Detection

```bash
# Detect performance regression (queries getting slower)
# NOTE: operationType is filtered client-side (not a valid --filter field).
gcloud sql operations list \
  --instance=my-instance \
  --format="json" | \
  jq '[.[] | select(.operationType == "QUERY")] | group_by(.startTime[:10]) | map({day: .[0].startTime[:10], avgDuration: (map(.duration) | add / length)})' | \
  jq '.[] | select(.avgDuration > 60)'
```

## Storage Growth Prediction

### Storage Usage Analysis

```bash
# Analyze storage growth
gcloud sql instances describe my-instance \
  --format="json" | jq '.diskUsageBytes, .diskQuota'

# Calculate growth rate
echo "Current: $(gcloud sql instances describe my-instance --format="value(diskUsageBytes)") bytes"
echo "Quota: $(gcloud sql instances describe my-instance --format="value(diskQuota)") bytes"
```

### Growth Prediction

```bash
# Predict storage growth (linear regression)
# NOTE: `gcloud sql operations list` has NO valid server-side filter for the
# storage operation type, nor a valid date-comparison filter expression — those
# silently return nothing. Historical point-in-time disk usage is NOT available
# via `gcloud sql instances describe` (it only reports the CURRENT usage). For
# real trending, export disk metrics from Cloud Monitoring
# (cloudsql.googleapis.com/database/disk/usage) to BigQuery and run the
# regression there. Below is a CURRENT-USAGE snapshot plus the regression
# helper, kept honest about its single-point limitation.
cat << 'EOF' > predict_storage.sh
#!/bin/bash
INSTANCE=$1

# Current disk usage snapshot (single point-in-time; not historical trend)
USAGE=$(gcloud sql instances describe "$INSTANCE" --format="value(diskUsageBytes)")
QUOTA=$(gcloud sql instances describe "$INSTANCE" --format="value(diskQuota)")
echo "Current usage: $USAGE bytes"
echo "Quota:         $QUOTA bytes"
echo "Used pct:      $(awk "BEGIN { printf \"%.1f\", ($USAGE*100)/$QUOTA }")%"

# For historical trend + linear regression, query exported Cloud Monitoring
# metrics instead of operations list. Example (requires metrics export to bq):
#   bq query --use_legacy_sql=false \
#     "SELECT timestamp, value FROM \`project.dataset.cloudsql_disk_usage\`
#      WHERE instance='$INSTANCE' ORDER BY timestamp"
# Then fit slope/intercept over the returned (x=day_index, y=bytes) series.
EOF
chmod +x predict_storage.sh
./predict_storage.sh my-instance
```

## Connection Pool Monitoring

### Connection Analysis

```bash
# Monitor active connections
# NOTE: operationType is filtered client-side (not a valid --filter field).
gcloud sql operations list \
  --instance=my-instance \
  --format="json" | \
  jq -r '.[] | select(.operationType == "CONNECT") | [.user, .clientAddr, .startTime] | @tsv'

# Count connections by user
gcloud sql operations list \
  --instance=my-instance \
  --format="json" | \
  jq '[.[] | select(.operationType == "CONNECT")] | group_by(.user) | map({user: .[0].user, count: length})'
```

### Connection Pool Exhaustion Detection

```bash
# Detect connection pool exhaustion
# NOTE: operationType is filtered client-side (not a valid --filter field).
gcloud sql operations list \
  --instance=my-instance \
  --format="json" | \
  jq '[.[] | select(.operationType == "CONNECT" and .status == "REJECTED")] | length' | \
  xargs -I {} echo "Rejected connections: {}"
```

## Real-Time Alerting

### Storage Alert Setup

```bash
# Create storage usage alert
gcloud alpha monitoring policies create \
  --notification-channels="projects/$CLOUDSDK_CORE_PROJECT/notificationChannels/123456789" \
  --display-name="Cloud SQL Storage High" \
  --condition-display-name="Storage > 80%" \
  --condition-filter='metric.type="cloudsql.googleapis.com/database/disk/usage" resource.type="cloudsql_database"' \
  --condition-threshold-value=0.8 \
  --condition-threshold-duration=300s \
  --condition-threshold-comparison=COMPARISON_GT
```

### Connection Alert Setup

```bash
# Create connection alert
gcloud alpha monitoring policies create \
  --notification-channels="projects/$CLOUDSDK_CORE_PROJECT/notificationChannels/123456789" \
  --display-name="Cloud SQL Connections High" \
  --condition-display-name="Connections > 90%" \
  --condition-filter='metric.type="cloudsql.googleapis.com/database/connection_count" resource.type="cloudsql_database"' \
  --condition-threshold-value=0.9 \
  --condition-threshold-duration=300s \
  --condition-threshold-comparison=COMPARISON_GT
```

## Automated Remediation

### Auto-Scale Storage

```bash
#!/bin/bash
# auto-scale-storage.sh

INSTANCE=$1
CURRENT_SIZE=$(gcloud sql instances describe $INSTANCE --format="value(diskSize)")
USAGE=$(gcloud sql instances describe $INSTANCE --format="value(diskUsage)")
USAGE_PCT=$((USAGE * 100 / CURRENT_SIZE))

if [ $USAGE_PCT -gt 80 ]; then
  NEW_SIZE=$((CURRENT_SIZE + 50))
  echo "Scaling storage: ${CURRENT_SIZE}GB -> ${NEW_SIZE}GB"
  gcloud sql instances patch $INSTANCE --database-version=MYSQL_8_0 --storage-size=${NEW_SIZE}GB
fi
```

### Auto-Kill Long Queries

```bash
#!/bin/bash
# auto-kill-long-queries.sh

INSTANCE=$1
# NOTE: operationType is filtered client-side (not a valid --filter field).
gcloud sql operations list --instance=$INSTANCE \
  --format="json" | \
  jq -r '.[] | select(.operationType == "QUERY" and .duration > 300) | .id' | \
  while read -r op_id; do
    echo "Killing long query: $op_id"
    gcloud sql operations cancel $INSTANCE $op_id
  done
```

## Best Practices

1. **Enable Cloud SQL Insights**: Use Query Insights for performance monitoring
2. **Set Connection Limits**: Configure max connections appropriately
3. **Monitor Storage Growth**: Set up alerts for storage thresholds
4. **Use Read Replicas**: Distribute read load across replicas
5. **Optimize Queries**: Use query analysis to identify slow queries
6. **Regular Backups**: Implement automated backup schedules
7. **Index Optimization**: Regularly review and optimize indexes

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| High CPU usage | Slow queries, missing indexes | Optimize queries, add indexes |
| Storage full | Uncontrolled growth | Scale storage, implement cleanup |
| Connection exhaustion | Too many clients | Increase max_connections, use pooling |
| Replication lag | Heavy writes | Optimize writes, use batch operations |

### Debug Queries

```bash
# Check instance status
gcloud sql instances describe my-instance --format="table(name,state,backendType)"

# List recent operations
gcloud sql operations list --instance=my-instance --limit=10

# Check storage usage
gcloud sql instances describe my-instance --format="value(diskUsage,diskQuota)"
```

## Self-Healing Playbook

> 自愈闭环：detection → DRY-RUN preview → 门禁 → 幂等 apply。所有自愈动作**默认 dry-run**，需人工复核门禁放行后才执行真实变更。failover / 实例重启 / promote-replica 等破坏性动作标 **HALT**，禁止自动执行。
>
> 凭证遮蔽遵循 AGENTS.md §0.1：任何命令输出中的 SA key、密码、token 一律替换为 `****`，仅校验存在性（`test -f "$GOOGLE_APPLICATION_CREDENTIALS"`），绝不 `cat` 或打印内容。
>
> 错误分类与跨 skill 影响面评估见 [docs/error-taxonomy.md](../../../docs/error-taxonomy.md) 与 [docs/cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md)。闭环反馈模式参考 [gcp-gcl-runner-ops/trace_feedback.py](../../../gcp-gcl-runner-ops/trace_feedback.py)。

### 通用执行框架

每个自愈场景统一遵循四阶段，门禁未通过则停止并升级人工：

```
1. DETECTION   — 基于 Cloud Monitoring 指标 / Query Insights 判定异常
2. DRY-RUN     — 打印将执行的变更（preview），不触碰资源
3. GATE        — 人工复核门禁：HALT 类动作一律拦截；非 HALT 类需确认
4. APPLY       — 幂等执行：重复运行结果一致，可安全重试
```

| 动作类别 | 风险 | 门禁 |
|----------|------|------|
| 连接池参数调整（max_connections / 连接超时） | Medium | 人工确认后 apply |
| 高 QPS 落盘：kill 长事务 / 限流 | Medium | 人工确认后 apply |
| 副本延迟：重连 / 重建副本 | High | HALT — 人工介入 |
| 实例重启 / failover / promote-replica | **High** | **HALT — 禁止自动** |

### Scenario 1: 连接池耗尽 (Connection Pool Exhaustion)

**Detection**
```bash
# 连接数逼近上限（>90%）
gcloud sql instances describe "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" \
  | jq '{maxConnections: .settings.userLabels.max_connections, current: .currentDiskSize}'
gcloud monitoring time-series list \
  --filter='metric.type="cloudsql.googleapis.com/database/connection_count" AND resource.labels.instance_name="{{user.instance_name}}"' \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"
```

**DRY-RUN preview** — 仅打印计划调整，不执行：
```bash
echo "[DRY-RUN] Would raise max_connections flag on {{user.instance_name}} (current -> +50)"
echo "[DRY-RUN] Would advise app-side pool shrink / connection timeout reduction"
```

**Gate** — 非 HALT，需人工确认后放行。

**Idempotent apply**
```bash
# 幂等：patch 设置目标值，重复执行结果一致
gcloud sql instances patch "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --database-flags max_connections={{user.new_max_connections}} --format=json
# 验证
gcloud sql instances describe "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="value(settings.databaseFlags)"
```

### Scenario 2: 高 QPS 落盘 (High QPS Disk Spill)

**Detection**
```bash
# 识别落盘长事务 / 慢查询（duration > 300s）
# NOTE: operationType 不是 `gcloud sql operations list` 的有效 server-side
# --filter 字段，改为客户端 jq 过滤。
gcloud sql operations list --instance="{{user.instance_name}}" \
  --format="json" \
  | jq '.[] | select(.operationType == "QUERY" and .duration > 300) | {id, user, startTime, duration}'
```

**DRY-RUN preview** — 列出将被取消的操作，不实际取消：
```bash
gcloud sql operations list --instance="{{user.instance_name}}" \
  --format="json" \
  | jq -r '.[] | select(.operationType == "QUERY" and .duration > 300) | "[DRY-RUN] Would cancel op: \(.id) user=\(.user) duration=\(.duration)"'
```

**Gate** — 非 HALT，需人工确认后放行（取消查询可能中断在途业务）。

**Idempotent apply**
```bash
# 幂等：已取消的操作再次 cancel 返回 NOT_FOUND，无副作用
gcloud sql operations list --instance="{{user.instance_name}}" \
  --format="json" \
  | jq -r '.[] | select(.operationType == "QUERY" and .duration > 300) | .id' \
  | while read -r op_id; do
      gcloud sql operations cancel "{{user.instance_name}}" "$op_id" \
        --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json || true
    done
```

### Scenario 3: 副本延迟 (Replica Lag)

**Detection**
```bash
gcloud monitoring time-series list \
  --filter='metric.type="cloudsql.googleapis.com/database/replication/seconds_behind_master" AND resource.labels.instance_name="{{user.replica_name}}"' \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"
```

**DRY-RUN preview**
```bash
echo "[DRY-RUN] Replica lag detected on {{user.replica_name}}; HALT — no auto action"
echo "[DRY-RUN] Suggested manual steps: verify replica health, check write load, consider rebuild replica"
```

**Gate** — **HALT**：副本延迟自愈（重连 / 重建副本 / promote）一律拦截，升级人工处理。禁止自动 failover 或重启。

### 闭环反馈 (Closed-Loop Feedback)

自愈执行结果应回写 GCL 反馈链路，供 Critic 评估有效性：
```bash
# 可选：将自愈结果上报 GCL 反馈（详见 gcp-gcl-runner-ops/trace_feedback.py）
python3 ../../../gcp-gcl-runner-ops/trace_feedback.py \
  --skill gcp-cloudsql-ops --scenario connection-pool --outcome "{{user.outcome}}"
```
> 凭证遮蔽：上述脚本读取 `GOOGLE_APPLICATION_CREDENTIALS` 环境变量，输出中 SA 路径与 token 一律 `****`，不打印明文。

## See Also

- [Cloud SQL Monitoring](../monitoring.md)
- [Cloud SQL Core Concepts](../core-concepts.md)
- [Troubleshooting](../troubleshooting.md)
- [Error Taxonomy](../../../docs/error-taxonomy.md)
- [Cross-Skill Blast Radius](../../../docs/cross-skill-blast-radius.md)
- [GCL Runner — trace_feedback](../../../gcp-gcl-runner-ops/trace_feedback.py)
- [Google Cloud Architecture Framework — Performance](https://cloud.google.com/architecture/framework/performance)
