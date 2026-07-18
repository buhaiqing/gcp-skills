# SPEC: GCP-Skills Level 3 Agentic 成熟度达标

> **Purpose:** 定义 gcp-skills 达到 Level 3 — Autonomous Orchestration Layer 所需的具体目标、验收标准和实现路径。
> **Version:** 1.0.0
> **Last Updated:** 2026-07-18

---

## 1. 背景与现状

### 1.1 Level 3 定义（Gartner）

> **Autonomous Orchestration Layer** — Various AI agents act with minimal human intervention based on governance layers managing safety, compliance, and monitoring. Decision-making occurs within defined parameters.

### 1.2 当前 L3 成熟度评估

| 能力维度 | 状态 | 当前差距 |
|---------|------|---------|
| 单任务自动化 | ✅ | — |
| 多 Agent 协调（GCL） | ✅ | — |
| Governance 层 | ✅ | Charter Principles + Adversarial Review 已完善 |
| 最小化人工干预 | ⚠️ | GCL 需人工触发，非全自动循环 |
| 决策在参数内执行 | ✅ | Safety gates 已实现 |
| 实时监控 | ❌ | **核心差距**：无 GCL 执行质量实时监控 |
| 观察仪表板 | ❌ | **核心差距**：无 GCL 质量指标 Dashboard |

### 1.3 差距根因

当前 `gcp-monitoring-ops/references/monitoring.md` 描述的是**如何用 Cloud Monitoring 监控 GCP 资源**（CPU、内存等），而非**监控 GCL 执行质量本身**。

---

## 2. 目标声明

### 2.1 最终目标

gcp-skills 在 **3 个月内** 达到 **Level 3 — Autonomous Orchestration Layer**，核心补齐：

1. **GCL 执行质量实时监控**：GCL 成功率、延迟、Autonomy Ratio 自动采集
2. **GCL 观察仪表板**：质量指标可视化，异常实时告警
3. **增强 GCL 自动循环**：自动重试 + Safety=0 强制终止 + 异常降级

### 2.2 验收标准（Acceptance Criteria）

| # | 标准 | 目标值 | 验证方式 |
|---|------|--------|---------|
| AC-1 | GCL 执行轨迹自动采集率 | 100% | BigQuery 查询轨迹数 / 总执行数 |
| AC-2 | GCL 成功率可视化 | Dashboard 可用 | Dashboard 访问正常 |
| AC-3 | Autonomy Ratio 可计算 | ≥ 60% | Dashboard 显示 |
| AC-4 | Safety=0 强制终止率 | 100% | 日志验证 |
| AC-5 | 告警规则覆盖主要失败模式 | ≥ 5 种 | Alert Policy 数量 |
| AC-6 | GCL Runner 增强版部署 | 生产可用 | 端到端测试通过 |

---

## 3. 核心架构

### 3.1 目标架构

```
┌──────────────────────────────────────────────────────────────┐
│                     Level 3 Architecture                      │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐    ┌──────────────────────────┐              │
│  │ GCL Runner │───▶│   Trace Collector       │              │
│  │ (Enhanced) │    │   (BigQuery + Logging)   │              │
│  └─────────────┘    └──────────┬───────────────┘              │
│                                  │                              │
│                                  ▼                              │
│                      ┌────────────────────────┐                │
│                      │   Observability        │                │
│                      │   Dashboard            │                │
│                      │   (Grafana)            │                │
│                      └──────────┬─────────────┘                │
│                                 │                               │
│                                 ▼                               │
│                      ┌────────────────────────┐                 │
│                      │   Alert Policies      │                 │
│                      │   (Cloud Monitoring)  │                 │
│                      └────────────────────────┘                │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

### 3.2 组件清单

| 组件 | 职责 | 技术选型 |
|------|------|---------|
| Enhanced GCL Runner | 自动重试 + Safety=0 强制终止 + 轨迹上传 | Python (复用现有 gcl_runner.py) |
| Trace Collector | 收集 GCL 执行轨迹到 BigQuery | BigQuery + Cloud Logging |
| Observability Dashboard | GCL 质量指标可视化 | Grafana + Cloud Monitoring |
| Alert Policies | GCL 失败模式告警 | Cloud Monitoring Alerts |

---

## 4. 详细需求

### 4.1 Enhanced GCL Runner

| 需求 | 描述 | 优先级 |
|------|------|--------|
| EGR-1 | 自动重试：GCL loop 自动重试直到通过或达到 max_iter | P0 |
| EGR-2 | Safety=0 强制终止：Safety 检查失败立即停止，不重试 | P0 |
| EGR-3 | 轨迹自动上传：每次执行后自动上传轨迹到 BigQuery | P0 |
| EGR-4 | 异常降级：同类失败超过 3 次自动降级并告警 | P1 |
| EGR-5 | 状态前后对比：执行前后资源状态快照对比 | P1 |

### 4.2 Trace Collector

| 需求 | 描述 | 优先级 |
|------|------|--------|
| TC-1 | BigQuery dataset `gcp_skills_gcl_audit` 创建 | P0 |
| TC-2 | GCL trace schema 设计（skill, op, result, latency, safety_score, autonomy_decisions） | P0 |
| TC-3 | 轨迹自动写入 BigQuery | P0 |
| TC-4 | Cloud Logging 集成：GCL 日志结构化 | P1 |

### 4.3 Observability Dashboard

| 需求 | 描述 | 优先级 |
|------|------|--------|
| OD-1 | GCL 成功率趋势图 | P0 |
| OD-2 | Autonomy Ratio 实时显示 | P0 |
| OD-3 | 执行延迟分布图 | P1 |
| OD-4 | Skill 执行频率排名 | P1 |
| OD-5 | Safety=0 事件记录 | P1 |

### 4.4 Alert Policies

| 需求 | 描述 | 优先级 |
|------|------|--------|
| AP-1 | GCL 成功率 < 90% 告警 | P0 |
| AP-2 | Safety=0 事件告警 | P0 |
| AP-3 | Autonomy Ratio > 90% 告警（人工介入阈值） | P0 |
| AP-4 | 执行延迟 P95 > 60s 告警 | P1 |
| AP-5 | 同类失败 > 3 次自动降级 | P1 |

---

## 5. 技术实现路径

### 5.1 Phase 0: Foundation（Week 1-2）

1. 设计 GCL trace schema
2. 创建 BigQuery dataset
3. 实现 Enhanced GCL Runner 骨架

### 5.2 Phase 1: Core（Week 3-6）

1. Enhanced GCL Runner 完整实现（EGR-1 ~ EGR-5）
2. Trace Collector 实现（TC-1 ~ TC-3）
3. Cloud Logging 集成

### 5.3 Phase 2: Observability（Week 7-10）

1. Grafana Dashboard 部署
2. Alert Policies 配置（AP-1 ~ AP-5）
3. Dashboard 自动化部署（IaC）

### 5.4 Phase 3: Validation（Week 11-12）

1. 端到端测试
2. 影子模式验证
3. 文档完善

---

## 6. 约束条件

| 约束 | 描述 |
|------|------|
| C-1 | 不破坏现有 GCL 向后兼容性 |
| C-2 | Safety=0 必须强制人工介入 |
| C-3 | 所有轨迹必须持久化存储 |
| C-4 | 监控不影响 GCL 执行性能 |

---

## 7. 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| R-1: 轨迹上传失败导致执行延迟 | 中 | 本地缓存 + 异步上传 |
| R-2: Dashboard 查询性能差 | 中 | BigQuery 合理分区 |
| R-3: 告警风暴 | 低 | 告警抑制规则 |

---

## 8. 与 Level 4 的关系

Level 3 是 Level 4 的**基础设施**：

| Level 3 组件 | Level 4 复用 |
|-------------|-------------|
| Enhanced GCL Runner | Autonomy Loop |
| Trace Collector | Learning Engine 数据源 |
| Grafana Dashboard | Observability Dashboard |
| BigQuery dataset | Knowledge Graph 存储 |

完成 Level 3 后，Level 4 的 Learning Engine 和 Knowledge Graph 可直接基于现有基础设施构建。

---

### SPEC Version 1.0.0 — 2026-07-18
