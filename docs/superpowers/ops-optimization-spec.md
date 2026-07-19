# SPEC: AIOps + FinOps + SecOps 三维批判性审计与优化

> **Purpose:** 从 AIOps（智能运维）、FinOps（云成本优化）、SecOps（安全运维）三个视角，对 gcp-skills 仓库进行批判性反思审计，识别值得优化的高价值改进点。
> **Parent Context:** 承接 Level 4 Agentic Roadmap（`docs/level4-agentic-roadmap-spec.md`）与 AIOps 自愈补全（`docs/superpowers/aiops-selfhealing-spec.md`）。
> **Version:** 1.0.0
> **Last Updated:** 2026-07-19

---

## 1. 背景与动机

### 1.1 当前成熟度快照

| 维度 | 覆盖率 | 证据 |
|------|--------|------|
| **AIOps** | 25 skill 中 12 个有 advanced/aiops 文档（48%） | monitoring/logging/securitycenter/armor/cloudsql/gke/pubsub/bigquery/vpc/billing/cloudbuild/terraform |
| **FinOps** | 25 skill 中 7 个有 advanced/finops 文档（28%） | bigquery/billing/cloudbuild/gcs/iam/pubsub/terraform |
| **SecOps** | 25 skill 中 4 个有安全专项文档（16%） | iam/kms/secretmanager/securitycenter（armor 有 WAF 但非独立安全文档） |
| **GCL 覆盖** | 25 skill 中 6 个有 rubric.md + prompt-templates.md（24%） | armor/bigquery/billing/cloudbuild/gke/securitycenter |
| **Token Efficiency** | 25 skill 中 10 个有 TE 合规标记（40%） | armor/billing/cloudbuild/composer/gke/iam/pubsub/securitycenter/terraform + AGENTS.md |

### 1.2 批判性反思：为什么需要这次审计

| 反思维度 | 当前盲点 |
|---------|---------|
| **AIOps** | 13 个 skill（cloudfunctions/cloudrun/dns/filestore/gce/kms/lb/memorystore/secretmanager/vpc/cdn）无自愈能力；GCL 闭环仅覆盖 24% 的 skill；跨域 blast-radius 关联已建但利用率低 |
| **FinOps** | 仅 28% 的 skill 有成本分析；无统一的成本预估门禁（执行前不知道要花多少钱）；committed-use/rightsizing 建议分散在少数 skill 中 |
| **SecOps** | 11 个 skill 有 DELETE 操作但仅 4 个有安全文档；凭证遮蔽规则（AGENTS.md §0.1）执行无自动化验证；CIS Benchmark 对齐未覆盖 |
| **交叉维度** | AIOps 的异常检测与 SecOps 的威胁检测未联动；FinOps 的成本异常与 AIOps 的告警未关联；三维度无统一仪表板 |

---

## 2. 目标（Goal）

### 2.1 核心目标

对 25 个 gcp-*-ops skill 逐一审计，从三维度产出：

1. **缺口清单**：每个 skill 在 AIOps / FinOps / SecOps 各缺什么（引用具体文件和行号）
2. **优先级矩阵**：P0（安全/数据风险）→ P1（成本浪费/运维盲区）→ P2（效率提升）
3. **落地方案**：每个优化点的最小可行改进（MVI），含具体文件路径和内容骨架
4. **交叉维度联动**：识别三维度间的协同优化机会（如 AIOps 异常 → FinOps 成本告警 → SecOps 安全事件）

### 2.2 成功标准

| # | 标准 | 验收方式 |
|---|------|---------|
| AC-1 | 每个 skill 的三维度缺口清单完整 | 25 skill × 3 维度 = 75 个审计单元，每个有结论 |
| AC-2 | 优先级矩阵覆盖所有 P0 项 | P0 项有 100% 的 MVI 方案 |
| AC-3 | 交叉维度联动 ≥ 5 条 | 如 LB→GCE→VPC 的 AIOps+FinOps+SecOps 联动链路 |
| AC-4 | 所有优化点引用具体文件路径 | 无空泛建议，每个建议有 `file:line` 锚点 |

---

## 3. 审计框架（三维度定义）

### 3.1 AIOps 维度

| 子维度 | 定义 | 当前覆盖基线 |
|--------|------|-------------|
| **异常检测** | 指标/日志/ traces 异常自动识别 | monitoring/logging 有 runbook；其余 skill 无 |
| **自愈能力** | 检测→诊断→修复→验证闭环 | 仅 4 个 skill 有 self-healing-runbook.md |
| **GCL 闭环** | 执行轨迹→反馈→rubric 优化 | 6/25 skill 有 rubric（24%） |
| **告警治理** | 告警降噪、SLO/error-budget | 仅 monitoring 有 alert-noise-reduction.md + slo-error-budget.md |
| **跨域关联** | 产品间故障传播分析 | docs/cross-skill-blast-radius.md 已建但利用率低 |

### 3.2 FinOps 维度

| 子维度 | 定义 | 当前覆盖基线 |
|--------|------|-------------|
| **成本预估** | 执行前预估操作成本 | 无 skill 有此能力 |
| **成本分析** | 资源使用→成本映射 | 7/25 skill 有 finops 文档（28%） |
| **优化建议** | rightsizing/commitment/storage class | 分散在 billing/bigquery/gcs 中 |
| **预算管控** | 预算告警、成本分配标签 | billing-ops 有但其他 skill 未集成 |
| **Idle 检测** | 空闲资源识别 | 无统一模式 |

### 3.3 SecOps 维度

| 子维度 | 定义 | 当前覆盖基线 |
|--------|------|-------------|
| **凭证安全** | SA key 管理、最小权限 | iam/kms/secretmanager 有；其余依赖 AGENTS.md §0.1 |
| **破坏性操作门禁** | DELETE 前确认 + 审计日志 | 大部分 skill 有确认步骤，但无审计日志联动 |
| **合规对齐** | CIS Benchmark / Org Policy | 仅 securitycenter 有 SCC Enterprise 文档 |
| **数据安全** | 加密(TLS/CMEK)、脱敏 | kms/secretmanager 有；cloudsql 有 SSL 但非安全专项 |
| **事件响应** | 安全事件检测→响应→恢复 | securitycenter 有 event-threat-detection；其余无 |

---

## 4. 已建资产（必须引用）

| 资产 | 位置 | 本轮使用方式 |
|------|------|-------------|
| 错误分类 | `docs/error-taxonomy.md` | AIOps 检测逻辑对齐错误码 |
| 跨域爆炸半径 | `docs/cross-skill-blast-radius.md` | AIOps 跨域关联的锚点 |
| 诊断日志标准 | `docs/diagnostic-logging-standard.md` | 所有审计文档日志格式 |
| Token Efficiency | `docs/token-efficiency-strategy.md` | 审计文档的 TE 合规基准 |
| 自愈框架 | `gcp-skill-generator/references/enhanced-self-healing-framework.md` | AIOps 自愈 runbook 参考模式 |
| GCL 规范 | `docs/gcl-spec.md` | GCL 闭环审计基准 |
| Level 4 Roadmap | `docs/level4-agentic-roadmap-spec.md` | 本审计作为 L4 的Gap Analysis 输入 |

---

## 5. 范围边界

### In Scope
- 25 个 gcp-*-ops skill 的三维度审计
- 每个 skill 的缺口清单 + 优先级 + MVI 方案
- 三维度交叉联动分析（≥5 条联动链路）
- 全局优化路线图（Phase 1/2/3 优先级排序）

### Out of Scope
- 不执行实际代码修改（仅产出 spec + plan）
- 不审计 gcp-gcl-runner-ops 和 gcp-skill-generator（基础设施，非产品 skill）
- 不重写现有 advanced/ 文档（仅识别缺口）
- 不创建新的 GCP 产品 skill

---

## 6. 约束

1. **证据驱动**：每个缺口必须引用 `file:line`，不可空泛描述
2. **最小侵入**：MVI 方案优先引用现有资产，不重建
3. **安全优先**：P0 安全项优先于 P1 成本项
4. **Token 感知**：优化方案必须考虑 Token Efficiency（TE-1..TE-8）
5. **GCL 对齐**：AIOps 优化必须考虑 GCL 闭环集成

---

## 7. 交付物

| 交付物 | 格式 | 位置 |
|--------|------|------|
| 三维度审计报告 | Markdown | `docs/superpowers/ops-audit-report.md` |
| 优先级矩阵 | 表格 | 嵌入审计报告 |
| 优化路线图 | 分阶段计划 | `docs/superpowers/ops-optimization-plan.md` |
| 联动链路图 | Mermaid | 嵌入审计报告 |

---

## Version History

### SPEC Version 1.0.0 — 2026-07-19
- 初始版本：定义审计框架、目标、约束
