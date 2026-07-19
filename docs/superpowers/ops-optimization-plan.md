# PLAN: AIOps + FinOps + SecOps 三维审计执行计划

> **Parent Spec:** `docs/superpowers/ops-optimization-spec.md`
> **Version:** 1.0.0
> **Last Updated:** 2026-07-19

---

## 任务总览

| 阶段 | 任务数 | 并行度 | 描述 |
|------|--------|--------|------|
| **Wave 1: AIOps 审计** | 5 | 5 agent 并行 | 按产品域分组审计 AIOps 覆盖 |
| **Wave 2: FinOps 审计** | 3 | 3 agent 并行 | 按成本影响分组审计 FinOps 覆盖 |
| **Wave 3: SecOps 审计** | 3 | 3 agent 并行 | 按安全风险分组审计 SecOps 覆盖 |
| **Wave 4: 交叉维度联动** | 1 | 1 agent | 聚合三维度结果，识别联动机会 |
| **Wave 5: 路线图产出** | 1 | 1 agent | 生成优先级矩阵和分阶段路线图 |
| **总计** | **13** | 最大并行 5 | |

---

## Wave 1: AIOps 审计（5 agent 并行）

### 分组策略
按产品域分组，每组覆盖 5 个 skill：

| Agent | 覆盖 Skill | 审计重点 |
|-------|-----------|---------|
| **W1-A: 基础设施域** | gce/dns/lb/cdn/vpc | 异常检测覆盖率、自愈 runbook 存在性、GCL rubric 覆盖 |
| **W1-B: 数据域** | bigquery/cloudsql/pubsub/gcs/filestore | 数据平面异常检测、查询性能监控、存储异常 |
| **W1-C: 计算域** | gke/cloudrun/cloudfunctions/composer | 容器/Serverless 异常检测、自动扩缩容监控 |
| **W1-D: 安全域** | iam/kms/secretmanager/securitycenter/armor | 安全事件检测、威胁告警、合规监控 |
| **W1-E: 运维域** | monitoring/logging/billing/cloudbuild/terraform/memorystore | 运维工具自身的 AIOps 能力、GCL 闭环 |

### 每个 Agent 的审计清单

对每个 skill 执行：

```
□ 1. 读取 SKILL.md → 检查是否有 AIOps 相关触发条件
□ 2. 检查 references/advanced/aiops-*.md 是否存在
□ 3. 检查 references/advanced/self-healing-runbook.md 是否存在
□ 4. 检查是否有 GCL rubric.md + prompt-templates.md
□ 5. 检查 references/monitoring.md 是否有异常检测指标
□ 6. 检查 troubleshooting.md 是否有自动修复路径
□ 7. 输出：每个 skill 的 AIOps 覆盖评分（0-5）+ 具体缺口
```

### 输出格式

```markdown
## [Agent ID] AIOps 审计结果

### [skill-name]
- **覆盖评分**: X/5
- **已有**: [列出已存在的 aiops 文档和能力]
- **缺口**: [列出缺失项，引用 file:line]
- **优先级**: P0/P1/P2
- **MVI**: [最小可行改进方案]
```

---

## Wave 2: FinOps 审计（3 agent 并行）

### 分组策略

| Agent | 覆盖 Skill | 审计重点 |
|-------|-----------|---------|
| **W2-A: 高成本域** | bigquery/cloudsql/gke/composer | 计算/存储密集型产品的成本优化覆盖 |
| **W2-B: 中成本域** | gce/cloudrun/cloudfunctions/vpc/lb/cdn | 网络/计算产品的成本意识 |
| **W2-C: 低成本域 + 工具** | gcs/pubsub/dns/filestore/memorystore/iam/kms/secretmanager/billing/cloudbuild/terraform/monitoring/logging/armor/securitycenter | 存储/工具类产品的成本分析 |

### 每个 Agent 的审计清单

```
□ 1. 检查 references/advanced/finops-*.md 是否存在
□ 2. 检查 SKILL.md 是否有成本预估步骤（执行前告知用户成本）
□ 3. 检查是否有 committed-use / rightsizing 建议
□ 4. 检查是否有 idle 资源检测模式
□ 5. 检查 billing-ops 的成本分析是否可复用到其他 skill
□ 6. 输出：每个 skill 的 FinOps 覆盖评分（0-5）+ 具体缺口
```

### 特别关注

- **成本预估门禁**：所有 CREATE/MODIFY 操作是否在执行前预估成本？
- **billing-ops 复用**：billing-ops 的 finops-cost-analysis.md 是否被其他 skill 引用？
- **存储成本**：GCS/CloudSQL/Filestore 的存储生命周期策略是否文档化？

---

## Wave 3: SecOps 审计（3 agent 并行）

### 分组策略

| Agent | 覆盖 Skill | 审计重点 |
|-------|-----------|---------|
| **W3-A: 数据安全域** | bigquery/cloudsql/gcs/filestore | 数据加密、访问控制、审计日志 |
| **W3-B: 身份与访问域** | iam/kms/secretmanager/gke | 凭证管理、最小权限、Workload Identity |
| **W3-C: 网络与边界域** | vpc/lb/cdn/armor/dns/gce/cloudrun/cloudfunctions/composer/monitoring/logging/billing/cloudbuild/terraform/memorystore/securitycenter | 网络安全、WAF、DDoS、操作审计 |

### 每个 Agent 的审计清单

```
□ 1. 检查 DELETE 操作是否有安全门禁（确认 + 审计日志）
□ 2. 检查凭证处理是否遵循 AGENTS.md §0.1（遮蔽）
□ 3. 检查是否有最小 IAM 权限文档
□ 4. 检查是否有加密（TLS/CMEK）文档
□ 5. 检查 troubleshooting.md 是否有安全相关错误码
□ 6. 输出：每个 skill 的 SecOps 覆盖评分（0-5）+ 具体缺口
```

### 特别关注

- **凭证遮蔽自动化**：AGENTS.md §0.1 的遮蔽规则是否有自动化验证？
- **CIS Benchmark**：哪些 skill 的操作对应 CIS GCP Benchmark 控制项？
- **审计日志**：哪些 skill 的操作应该记录到 Cloud Audit Logs？

---

## Wave 4: 交叉维度联动（1 agent）

### 任务

聚合 Wave 1-3 的结果，识别三维度间的协同优化机会：

```
□ 1. 读取 Wave 1-3 的所有审计结果
□ 2. 识别 ≥5 条交叉维度联动链路，格式：
   - 链路名称（如 "LB→GCE→VPC AIOps+FinOps+SecOps 联动"）
   - AIOps 维度：异常检测 → 自动响应
   - FinOps 维度：成本影响评估
   - SecOps 维度：安全事件关联
   - 统一仪表板需求
□ 3. 识别 ≥3 个"一石三鸟"优化点（一个改进同时覆盖三维度）
□ 4. 输出：联动分析报告
```

### 示例联动链路

| 链路 | AIOps | FinOps | SecOps |
|------|-------|--------|--------|
| LB→GCE→VPC | 后端健康异常检测 | 流量激增导致成本飙升 | DDoS 攻击检测 |
| CloudSQL→GCS | 查询性能异常 | 存储成本分析 | 数据泄露检测 |
| IAM→多产品 | 权限变更异常 | 权限膨胀成本 | 最小权限违规 |

---

## Wave 5: 路线图产出（1 agent）

### 任务

基于 Wave 1-4 的所有结果，产出最终交付物：

```
□ 1. 生成三维度审计报告（docs/superpowers/ops-audit-report.md）
   - 每个 skill 的三维度评分矩阵
   - 所有缺口的优先级排序
   - 联动链路图（Mermaid）
□ 2. 生成优化路线图（更新 docs/superpowers/ops-optimization-plan.md）
   - Phase 1（立即）：所有 P0 安全项
   - Phase 2（短期）：P1 成本/运维项
   - Phase 3（中期）：P2 效率提升项
   - 每个 Phase 的任务卡 + 验收标准
□ 3. 更新 TODO.md 的 Cross-Skill 段
```

---

## 验证门禁

### Wave 1-3 验证
- 每个 agent 的输出包含 ≥5 个 skill 的审计结果
- 每个缺口有 `file:line` 引用
- 优先级标记（P0/P1/P2）有理由

### Wave 4 验证
- ≥5 条联动链路
- 每条链路覆盖三维度
- ≥3 个"一石三鸟"优化点

### Wave 5 验证
- 审计报告覆盖 25 skill × 3 维度 = 75 个审计单元
- 路线图有明确的 Phase 分期
- TODO.md 已同步

---

## 风险与缓解

| 风险 | 缓解 |
|------|------|
| 审计结果过于泛化 | 强制 `file:line` 引用，无引用视为无效 |
| 遗漏 skill | 按分组清单逐条勾选，不允许跳过 |
| 联动链路臆造 | 仅基于已审计的缺口识别联动，不虚构 |
| 路线图过于宏大 | P0 项必须在 1 周内可执行 |

---

## Version History

### PLAN Version 1.0.0 — 2026-07-19
- 初始版本：5 Wave 执行计划
