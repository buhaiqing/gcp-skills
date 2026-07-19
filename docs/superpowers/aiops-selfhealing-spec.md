# AIOps 自愈 Runbook 补全 — Specification (Spec)

> 本文档定义「维度二/三/四 AIOps 自愈能力补全」的目标、边界、约束与验收标准。
> 承接上一轮已建资产（见 §3）。先于 plan 与 implementation 存在，作为唯一事实来源。

---

## 1. 背景与动机

上一轮已完成 AIOps **根因层**三项 P0 修复：
- P0-2 统一错误分类 `docs/error-taxonomy.md`
- P0-3 闭环反馈 `gcp-gcl-runner-ops/trace_feedback.py`
- P0-1 GCL 孤儿模块接入 `gcl_runner_enhanced.py`

本轮目标是补齐**能力层**：让各 skill 从「配置手册」升级为「可自治运维」——即具备自愈 runbook、连接 GCL 知识/自纠闭环、并能跨域关联。

当前现状（已核查，证据见 plan 附录）：
- 维度二（4 skill）：monitoring/logging 零自愈；securitycenter/armor 有片段但未主线化；4 个 skill 均无 GCL 连接；SLO/降噪/跨信号全缺
- 维度三（7 skill）：cloudsql/gke/pubsub/bigquery 有孤立 aiops 文档但 SKILL.md 未引用、脚本仅伪代码；cloudrun/composer/memorystore 缺 aiops 文档
- 维度四（14 skill）：cdn README 引用 4 个不存在文件；7 个 skill 无 advanced 目录；全仓库无跨域 blast-radius 关联文档

---

## 2. 目标（Goal）

1. 为缺失/孤立的 AIOps 能力补齐 `references/advanced/aiops-*.md` 自愈 runbook
2. 每个 runbook 必须**引用**上一轮资产（error-taxonomy 的恢复动作词汇、GCL 接线），不重建
3. 修复 cdn 失效引用（创建缺失文件或修正 README）
4. 新建全局跨域 blast-radius 关联文档 `docs/cross-skill-blast-radius.md`
5. 所有自愈路径必须带 dry-run / 幂等 / 人工复核门禁，沿用 GCL StateSnapshot 语义

---

## 3. 已建资产（必须引用，禁止重建）

| 资产 | 位置 | 本轮如何使用 |
|---|---|---|
| 统一错误分类 | `docs/error-taxonomy.md` | runbook 的 Recovery 动作（HALT/RETRY/REMEDIATE/ESCALATE）对齐其 Recovery Action Vocabulary；错误码映射其根因维度 |
| 闭环反馈 | `gcp-gcl-runner-ops/trace_feedback.py` | runbook 末尾注明「失败模式经 GCL trace 回流」 |
| GCL 接线 | `gcp-gcl-runner-ops/scripts/gcl_runner_enhanced.py` | runbook 注明自愈执行可经 GCL runner 调度（StateSnapshot 前后比对、DegradationDetector） |
| 诊断日志标准 | `docs/diagnostic-logging-standard.md` | runbook 日志格式遵循 `[HH:MM:SS] [PHASE] key=value` |
| 增强自愈框架 | `gcp-skill-generator/references/enhanced-self-healing-framework.md` | 作为 GCL 知识连接段的参考模式 |

---

## 4. 范围边界（Scope）

### In Scope（本轮做）
- 维度二：monitoring / logging / securitycenter / armor 各补 `self-healing-runbook.md` + GCL 连接段；monitoring 补 `slo-error-budget.md` + `alert-noise-reduction.md`；logging 补 `log-anomaly-detection.md`
- 维度三：memorystore / cloudrun / composer 新建 `aiops-*-anomaly.md`；cloudsql / gke / pubsub / bigquery 补「Automated Remediation」段并引用既有 aiops 文档
- 维度四：修复 cdn 失效引用；新建 `docs/cross-skill-blast-radius.md`；为 7 个缺 advanced 目录的 infra skill 补最小 aiops 关联段（仅 monitoring 关联维度，不展开完整 runbook）

### Out of Scope（本轮不做，避免范围蔓延）
- 不写真实可执行 `auto-*.sh` 脚本文件（仅 markdown 伪代码 + 门禁说明），落地脚本是独立任务
- 不改造 GCL runner 架构（上一轮已完成）
- 不补维度二/三/四 skill 的 SKILL.md 触发词（那是 trigger_audit 预存失败，独立任务）
- 不创建 `remediation_adapter.py`（执行流接线，独立任务，需先定义 runner 的 knowledge 概念）
- 不修其他预存测试失败

---

## 5. 约束（Mandatory Constraints）

1. **引用不重建**：所有 runbook 必须链接 `docs/error-taxonomy.md`，Recovery 动作词汇对齐，禁止在 runbook 内重定义错误码表
2. **安全门禁**：每个自愈路径必须声明 dry-run 步骤 + 幂等性说明 + required 级人工复核；破坏性操作（delete/resize/unlink）必须标 `HALT` 或 `REMEDIATE with --confirm`
3. **凭证遮蔽**：任何日志/脚本示例不得暴露 SA key 内容，遵循 AGENTS.md §0.1
4. **最小侵入**：只新增 `references/advanced/` 文档与 SKILL.md 的引用段，不改现有 troubleshooting 的命令逻辑
5. **风格一致**：文档结构对齐现有 aiops-*.md（如 `gcp-vpc-ops/references/advanced/aiops-network-anomaly.md`），中文正文 + 英文代码
6. **不 commit**：子 agent 在 worktree 内完成，由主 agent 审查后统一合并

---

## 6. 验收标准（Acceptance Criteria）

- [ ] 每个新建/补全的 aiops 文档都包含：触发条件、检测（含指标/日志查询）、自愈动作（含 dry-run + 幂等 + 门禁）、GCL 连接段、error-taxonomy 引用
- [ ] cdn README 引用的 4 个文件全部存在，或 README 已修正为有效引用
- [ ] `docs/cross-skill-blast-radius.md` 存在，覆盖 ≥3 条跨域链路（如 LB→GCE→VPC、CDN→DNS→GCS、IAM→多产品）
- [ ] 所有新增文档通过 markdownlint（`npx markdownlint-cli2 "gcp-*/SKILL.md"` 及相关 md）
- [ ] 现有测试套件失败数不增加（基线 16 failed，预存，非本轮引入）
- [ ] 不破坏既有 aiops 文档的链接完整性
