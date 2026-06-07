# AIOps Best Practices — GCP Skill Generator

> **Purpose:** 定义所有具备监控/告警/诊断能力的 `gcp-[product]-ops` Skill 必须遵循的 AIOps 最佳实践规范。
> **Version:** 1.0.0
> **Last Updated:** 2026-06-07
> **Status:** MANDATORY — 所有涉及 Cloud Monitoring 告警和诊断的 Skill 必须实现本规范中的相关模式

---

## 目录

1. [核心原则](#1-核心原则)
2. [多指标关联巡检规范](#2-多指标关联巡检规范)
3. [跨 Skill 委托矩阵规范](#3-跨-skill-委托矩阵规范)
4. [诊断报告 Schema](#4-诊断报告-schema)

---

## 1. 核心原则

### 1.1 能力成熟度模型

| 等级 | 名称 | 特征 |
|------|------|------|
| L1 | 基础监控 | 单指标查询、静态阈值告警（Cloud Monitoring） |
| L2 | 关联分析 | 多指标联合巡检、复合异常模式 |
| L3 | 智能诊断 | 跨 Skill 委托、AI 诊断联动、决策树 |
| L4 | 主动预防 | 主动巡检、趋势预测、知识库匹配 |
| L5 | 自治修复 | 自动修复、自学习、闭环优化 |

### 1.2 AIOps 五步闭环

```
[发现异常] → [验证确认] → [关联分析] → [根因定位] → [修复建议]
     ↑                                                      |
     └──────────────── 反馈优化 ─────────────────────────────┘
```

---

## 2. 多指标关联巡检规范

### Cloud Monitoring 指标查询

```bash
# 查询 CPU 利用率（最近 1 小时）
gcloud monitoring metrics list \
  --filter="metric.type = 'compute.googleapis.com/instance/cpu/utilization'" \
  --format="json" | jq -r '.metrics[0].point'
```

### 巡检模板

```markdown
### 例行巡检

| 检查项 | 指标 | 阈值 | 异常处理 |
|--------|------|------|----------|
| CPU | compute.googleapis.com/instance/cpu/utilization | > 80% | 检查进程、建议扩容 |
| 内存 | agent.googleapis.com/memory/percent_used | > 90% | 检查内存泄漏 |
| 磁盘 | compute.googleapis.com/instance/disk/utilization | > 85% | 清理或扩容磁盘 |
```

---

## 3. 跨 Skill 委托矩阵

| 诊断需求 | 主 Skill | 委托 Skill |
|----------|----------|-----------|
| VM CPU 高 | `gcp-gce-ops` | `gcp-monitoring-ops` 查询指标 |
| 数据库连接慢 | `gcp-cloudsql-ops` | `gcp-gce-ops` 检查 VM 网络 |
| 网络延迟 | `gcp-vpc-ops` | `gcp-gce-ops` 检查 VM 拓扑 |

---

## 4. 诊断报告 Schema

```json
{
  "product": "compute",
  "resource": "projects/my-project/zones/us-central1-a/instances/instance-1",
  "time": "2026-06-07T10:00:00Z",
  "severity": "WARNING",
  "metrics": {
    "cpu_utilization": 0.85,
    "memory_utilization": 0.92
  },
  "anomaly": "High memory usage (>90%)",
  "possible_causes": ["Memory leak", "Insufficient memory allocation"],
  "recommendations": [
    "Restart the instance",
    "Upgrade to a larger machine type",
    "Investigate application memory usage"
  ],
  "delegated_skills": ["gcp-gce-ops"]
}
```