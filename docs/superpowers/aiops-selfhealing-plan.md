# AIOps 自愈 Runbook 补全 — Implementation Plan

> 基于 `.omo/plans/aiops-selfhealing-spec.md`。所有工作通过 Git Worktree + 子 agent 并行完成。
> 主 agent 审查每个 worktree 后合并。

---

## 批次划分（Batch Strategy）

按「依赖关系」而非「skill 数量」分批。全局件先单独做（串行），skill 级文档可高度并行（每个 skill 互不依赖）。

| 批次 | 内容 | 并行度 | Worktree 分支 |
|---|---|---|---|
| **B0（全局件，先串行）** | `docs/cross-skill-blast-radius.md` | 1 agent | feature/aiops-blast-radius |
| **B1（维度四修复）** | cdn 失效引用修复 | 1 agent | feature/aiops-cdn-fix |
| **B2（维度二）** | monitoring/logging/securitycenter/armor 自愈 runbook | 4 agent 并行 | feature/aiops-dim2-{skill} |
| **B3（维度三-缺口）** | memorystore/cloudrun/composer 新建 aiops 文档 | 3 agent 并行 | feature/aiops-dim3-{skill} |
| **B4（维度三-既有）** | cloudsql/gke/pubsub/bigquery 补 Automated Remediation 段 | 4 agent 并行 | feature/aiops-dim3-{skill} |
| **B5（维度四-补空）** | 7 个缺 advanced 目录的 infra skill 补最小 aiops 关联段 | 7 agent 并行（或 2 批） | feature/aiops-dim4-{skill} |

B0 必须先完成（其他批次的 runbook 需要引用 blast-radius 文档作为跨域关联锚点）。B1-B5 之间无依赖，可并行启动。

---

## 各批次任务卡（Task Cards）

### B0 — `docs/cross-skill-blast-radius.md`
- 读取 vpc/iam/billing/cloudbuild/gcs 的 aiops 文档作为锚点（explore 已列清单）
- 覆盖 ≥3 条跨域链路：LB→GCE→VPC、CDN→DNS→GCS、IAM→多产品依赖
- 每条链路：上游变更如何影响下游、关联告警规则示例、blast radius 边界、降级顺序
- 遵循 `docs/` 现有文档风格（参考 token-efficiency-strategy.md）

### B1 — cdn 失效引用修复
- 选项 A：创建 `gcp-cdn-ops/references/advanced/` 下 4 个缺失文件（aiops-cdn-anomaly-detection.md / aiops-cdn-prediction.md / aiops-cdn-auto-remediation.md / finops-cdn-cost-analysis.md），内容对齐其他 cdn aiops 风格
- 选项 B：若内容无法合理生成，修正 README.md 引用为有效文件
- 优先选项 A（保持 README 完整性）

### B2 — 维度二（4 skill 并行）
每个 agent 在独立 worktree：
- 新建 `references/advanced/self-healing-runbook.md`（monitoring/logging/securitycenter/armor）
- monitoring 额外：`slo-error-budget.md` + `alert-noise-reduction.md`
- logging 额外：`log-anomaly-detection.md`
- 每个 runbook：触发条件 → 检测（指标/日志查询）→ 自愈动作（dry-run+幂等+门禁）→ **GCL 连接段**（引用 gcl_runner_enhanced + trace_feedback）→ **error-taxonomy 引用**
- securitycenter/armor 把既有 advanced 片段（auto-mute / adaptive-protection）主线化为 runbook

### B3 — 维度三缺口（3 skill 并行）
- memorystore：新建 `references/advanced/aiops-memorystore-anomaly.md`（auto-failover-redis / auto-scale-replica 伪代码）+ `references/idempotency-checklist.md`
- cloudrun：新建 `references/advanced/` + `aiops-cloudrun-anomaly.md`（auto-rollout-rollback / auto-scale-revision）+ `references/idempotency-checklist.md`
- composer：在现有 advanced/ 补 `aiops-composer-anomaly.md`（auto-pause-dag / auto-clear-stuck-task）+ `references/idempotency-checklist.md`
- 均含 GCL 连接段 + error-taxonomy 引用

### B4 — 维度三既有（4 skill 并行）
- cloudsql/gke/pubsub/bigquery：在 SKILL.md 或 troubleshooting.md 增加「Automated Remediation」段，链接既有 aiops 文档，声明脚本伪代码的 dry-run/幂等/门禁；补 GCL 连接段 + error-taxonomy 引用
- 不改既有 aiops 文档内容（仅新增引用段）

### B5 — 维度四补空（7 skill 并行）
- cloudfunctions/lb/dns/gce/kms/secretmanager/filestore：新建 `references/advanced/aiops-{product}-anomaly.md`（最小版，聚焦 monitoring 关联异常检测 + 跨域依赖指针到 blast-radius 文档）
- 不展开完整自愈 runbook（避免与 B2/B3 重复），仅建立 advanced 目录 + 最小 aiops 锚点

---

## 验证门禁（Verification Gates）

每个 worktree 完成前必须：
1. `npx markdownlint-cli2 "gcp-<skill>-ops/**/*.md"` 零 error（或仅既有 warning）
2. 新增文档含 error-taxonomy 引用链接且目标存在
3. 不破坏既有链接（grep 确认无新增死链）
4. 子 agent 简报：创建了什么、引用了哪些资产、markdownlint 结果

主 agent 合并前：
1. 抽查每个 worktree 的 diff（`git diff --stat`）
2. 跑 `gcp-gcl-runner-ops` 测试确认 16 failed 基线不增加
3. 合并后 `git worktree remove`

---

## 风险与缓解

| 风险 | 缓解 |
|---|---|
| runbook 写得太泛、无门禁 | spec §5 强制 dry-run+幂等+人工门禁；主 agent 抽查 |
| 与既有 troubleshooting 重复 | 只新增 advanced/ 文档 + 引用段，不改 troubleshooting 命令 |
| 跨域文档臆造依赖 | B0 仅基于已核查的 10 个 aiops 文档锚点，不虚构链路 |
| 范围蔓延 | Out of Scope 明确排除真实脚本/remediation_adapter/触发词修复 |
| worktree 冲突 | 每个 skill 独立分支，B5 的 7 个 skill 互不重叠 |
