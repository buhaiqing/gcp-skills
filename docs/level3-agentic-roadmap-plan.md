# PLAN: GCP-Skills Level 3 Agentic 成熟度达标执行计划

> **Purpose:** 将 Level 3 达标拆解为可执行的任务清单，包含依赖关系、验收标准和执行顺序。
> **Parent Spec:** `docs/level3-agentic-roadmap-spec.md`
> **Version:** 1.0.0
> **Last Updated:** 2026-07-18

---

## 任务总览

| 阶段 | 任务数 | 周期 | 核心内容 |
|------|--------|------|---------|
| **Phase 0: Foundation** | 6 | Week 1-2 | Schema 设计 + BigQuery 搭建 + Runner 骨架 |
| **Phase 1: Core** | 8 | Week 3-6 | Enhanced GCL Runner 完整实现 + Trace Collector |
| **Phase 2: Observability** | 7 | Week 7-10 | Dashboard + Alert Policies |
| **Phase 3: Validation** | 5 | Week 11-12 | 端到端测试 + 文档 |
| **总计** | **26** | **12 周** | |

---

## Phase 0: Foundation（Week 1-2）

### P0-1: 基础设施搭建

| Task | 描述 | 依赖 | 验收 |
|------|------|------|------|
| P0-1.1 | 设计 GCL trace schema（skill, op, result, latency, safety_score, autonomy_decisions, error_type） | — | Schema 评审通过 |
| P0-1.2 | 创建 BigQuery dataset `gcp_skills_gcl_audit` | P0-1.1 | Dataset 创建完成 |
| P0-1.3 | 创建 BigQuery table `gcl_traces` with schema | P0-1.2 | Table 创建 + 分区策略确定 |
| P0-1.4 | 设计 Enhanced GCL Runner 架构（自动重试 + Safety 强制终止 + 轨迹上传） | P0-1.3 | 架构设计文档评审通过 |
| P0-1.5 | 实现 Enhanced GCL Runner 骨架（CLI 接口保持兼容） | P0-1.4 | `--help` 输出正常 |

### P0-2: Cloud Logging 集成设计

| Task | 描述 | 依赖 | 验收 |
|------|------|------|------|
| P0-2.1 | 设计 GCL 日志结构化格式（JSON log entry） | P0-1.5 | 日志格式规范评审通过 |
| P0-2.2 | 设计日志过滤器（log metric for error rate） | P0-2.1 | 过滤器配置评审通过 |

---

## Phase 1: Core（Week 3-6）

### P1-1: Enhanced GCL Runner 完整实现

| Task | 描述 | 依赖 | 验收 |
|------|------|------|------|
| P1-1.1 | 实现 EGR-1：自动重试逻辑（指数退避） | P0-1.5 | max_iter 内自动重试，退出码正确 |
| P1-1.2 | 实现 EGR-2：Safety=0 强制终止 | P1-1.1 | Safety=0 立即终止，不重试 |
| P1-1.3 | 实现 EGR-3：轨迹自动上传 BigQuery | P1-1.2 | 100% 轨迹上传成功 |
| P1-1.4 | 实现 EGR-4：同类失败 > 3 次自动降级 + 告警 | P1-1.3 | 降级触发，日志可见 |
| P1-1.5 | 实现 EGR-5：执行前后资源状态快照对比 | P1-1.4 | diff 可报告 |

### P1-2: Trace Collector

| Task | 描述 | 依赖 | 验收 |
|------|------|------|------|
| P1-2.1 | 实现 TC-1：BigQuery streaming insert | P1-1.3 | 轨迹实时写入 |
| P1-2.2 | 实现 TC-4：Cloud Logging 集成（GCL 日志结构化） | P1-1.4 | 日志可查询 |
| P1-2.3 | 实现 Autonomy Ratio 计算逻辑 | P1-2.2 | 指标可输出 |

### P1-3: GCL Runner 增强版 CLI

| Task | 描述 | 依赖 | 验收 |
|------|------|------|------|
| P1-3.1 | 实现 `--dry-run` 模式（不执行，只生成轨迹） | P1-2.3 | dry-run 轨迹生成 |
| P1-3.2 | 实现 `--trace-only` 模式（执行但不等待结果） | P1-3.1 | 异步轨迹收集 |
| P1-3.3 | 端到端测试：Enhanced GCL Runner vs 现有 GCL Runner 结果一致性 | P1-3.2 | 一致性 ≥ 99% |

---

## Phase 2: Observability（Week 7-10）

### P2-1: Grafana Dashboard

| Task | 描述 | 依赖 | 验收 |
|------|------|------|------|
| P2-1.1 | 部署 Grafana（使用 Grafana Cloud 或自托管） | P1-3.3 | Grafana 可访问 |
| P2-1.2 | 配置 BigQuery DataSource | P2-1.1 | BigQuery 连接正常 |
| P2-1.3 | 实现 OD-1：GCL 成功率趋势图 | P2-1.2 | 图表可显示 |
| P2-1.4 | 实现 OD-2：Autonomy Ratio 实时显示 | P2-1.3 | 指标实时更新 |
| P2-1.5 | 实现 OD-3：执行延迟分布图 | P2-1.4 | P50/P95/P99 显示 |
| P2-1.6 | 实现 OD-4：Skill 执行频率排名 | P2-1.5 | Top 10 Skill 显示 |
| P2-1.7 | 实现 OD-5：Safety=0 事件记录 | P2-1.6 | 事件列表可查 |

### P2-2: Alert Policies

| Task | 描述 | 依赖 | 验收 |
|------|------|------|------|
| P2-2.1 | 实现 AP-1：GCL 成功率 < 90% 告警 | P2-1.7 | Alert 可触发 |
| P2-2.2 | 实现 AP-2：Safety=0 事件告警 | P2-2.1 | Alert 可触发 |
| P2-2.3 | 实现 AP-3：Autonomy Ratio > 90% 告警 | P2-2.2 | Alert 可触发 |
| P2-2.4 | 实现 AP-4：执行延迟 P95 > 60s 告警 | P2-2.3 | Alert 可触发 |
| P2-2.5 | 实现 AP-5：同类失败 > 3 次自动降级 | P2-2.4 | 降级 + Alert 同时触发 |

### P2-3: IaC 部署

| Task | 描述 | 依赖 | 验收 |
|------|------|------|------|
| P2-3.1 | Terraform 化：BigQuery dataset + table | P2-2.5 | Terraform apply 成功 |
| P2-3.2 | Terraform 化：Cloud Monitoring Alert Policies | P2-3.1 | Terraform apply 成功 |
| P2-3.3 | Terraform 化：Grafana 部署配置 | P2-3.2 | 配置版本化 |

---

## Phase 3: Validation（Week 11-12）

### P3-1: 端到端测试

| Task | 描述 | 依赖 | 验收 |
|------|------|------|------|
| P3-1.1 | 影子模式：Enhanced GCL Runner 与现有 Runner 并行运行 | P2-3.3 | 结果一致性 ≥ 99% |
| P3-1.2 | 负载测试：连续 100 次 GCL 执行轨迹采集验证 | P3-1.1 | 轨迹完整率 100% |
| P3-1.3 | Dashboard 验证：所有图表数据正确显示 | P3-1.2 | 图表数据与 BigQuery 一致 |

### P3-2: 文档完善

| Task | 描述 | 依赖 | 验收 |
|------|------|------|------|
| P3-2.1 | 编写 Enhanced GCL Runner 使用手册 | P3-1.3 | 手册评审通过 |
| P3-2.2 | 更新 AGENTS.md：新增 Level 3 架构说明 | P3-2.1 | AGENTS.md 更新 |
| P3-2.3 | 团队培训 | P3-2.2 | 培训覆盖率 100% |

---

## 验收检查清单

### AC-1: GCL 执行轨迹自动采集率 100%

| Checkpoint | 验证方式 | 目标值 |
|-----------|---------|--------|
| P1-1.3 轨迹上传 | BigQuery 查询轨迹数 / 总执行数 | 100% |
| P3-1.2 负载测试 | 轨迹完整率 | 100% |

### AC-2: GCL 成功率可视化 Dashboard 可用

| Checkpoint | 验证方式 | 目标值 |
|-----------|---------|--------|
| P2-1.3 成功率趋势图 | Dashboard 访问 + 数据正确 | ✅ |
| P3-1.3 Dashboard 验证 | 与 BigQuery 一致 | ✅ |

### AC-3: Autonomy Ratio ≥ 60%

| Checkpoint | 验证方式 | 目标值 |
|-----------|---------|--------|
| P1-2.3 Autonomy Ratio 计算 | Dashboard 显示 | ≥ 60% |
| P3-1.1 影子模式 | 实际 Ratio | ≥ 60% |

### AC-4: Safety=0 强制终止率 100%

| Checkpoint | 验证方式 | 目标值 |
|-----------|---------|--------|
| P1-1.2 Safety=0 强制终止 | 日志验证 | 100% |
| P2-2.2 Safety=0 告警 | Alert 触发验证 | ✅ |

### AC-5: 告警规则覆盖 ≥ 5 种失败模式

| Checkpoint | 验证方式 | 目标值 |
|-----------|---------|--------|
| P2-2.1 ~ P2-2.5 | Alert Policy 数量 | ≥ 5 |

### AC-6: Enhanced GCL Runner 生产可用

| Checkpoint | 验证方式 | 目标值 |
|-----------|---------|--------|
| P1-3.3 一致性测试 | Enhanced vs 现有 Runner | 一致性 ≥ 99% |
| P3-1.1 影子模式 | 生产等价验证 | ✅ |

---

## 依赖关系图

```
Week 1-2 (Phase 0: Foundation)
─────────────────────────────────────────────────────────────
P0-1.1 ─▶ P0-1.2 ─▶ P0-1.3 ─▶ P0-1.4 ─▶ P0-1.5
                                    │
P0-2.1 ─▶ P0-2.2 ──────────────────┘
                    │
Week 3-6 (Phase 1: Core)
─────────────────────────────────────────────────────────────
                    │
                    ▼
P1-1.1 ─▶ P1-1.2 ─▶ P1-1.3 ─▶ P1-1.4 ─▶ P1-1.5 ─▶ P1-2.1 ─▶ P1-2.2 ─▶ P1-3.1 ─▶ P1-3.2 ─▶ P1-3.3
                                                                                                    │
Week 7-10 (Phase 2: Observability)                                                               │
────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                                                                    │
P2-1.1 ─▶ P2-1.2 ─▶ P2-1.3 ─▶ P2-1.4 ─▶ P2-1.5 ─▶ P2-1.6 ─▶ P2-1.7 ─▶ P2-2.1 ─▶ P2-2.2 ─▶ P2-2.3 ─▶ P2-2.4 ─▶ P2-2.5 ─▶ P2-3.1 ─▶ P2-3.2 ─▶ P2-3.3
                                                                                                                                                                  │
Week 11-12 (Phase 3: Validation)                                                                                                                                │
───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                                                                                                                                  │
P3-1.1 ─▶ P3-1.2 ─▶ P3-1.3 ─▶ P3-2.1 ─▶ P3-2.2 ─▶ P3-2.3
```

---

## 关键里程碑

| 里程碑 | 时间 | 交付物 |
|--------|------|--------|
| M1: Foundation | Week 2 | BigQuery 搭建完成 + Runner 骨架 |
| M2: Core Complete | Week 6 | Enhanced GCL Runner 生产可用 |
| M3: Observability Live | Week 10 | Dashboard + Alert Policies 上线 |
| M4: Level 3 Complete | Week 12 | 端到端验证通过 |

---

### PLAN Version 1.0.0 — 2026-07-18
