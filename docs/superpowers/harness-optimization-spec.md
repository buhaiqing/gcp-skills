# SPEC: Harness Engineering 框架质量强化

> **Purpose:** 修复 GCL 框架的 P0/P1 工程缺陷，使框架从"文档完备但工程残缺"状态升级为可执行、可观测、可迭代的质量门禁系统。
> **Parent Context:** 承接 `docs/superpowers/ops-optimization-spec.md` 三维审计结果，本轮聚焦框架基础设施自身。
> **Version:** 1.0.0
> **Created:** 2026-07-20

---

## 1. 背景与动机

### 1.1 当前状态快照

| 资产 | 状态 | 证据 |
|------|------|------|
| `references/rubric.md` | **0/25 skill 存在** | grep 结果：所有 skill SKILL.md 引用但文件不存在 |
| AIOps 模块（self_correction_mechanism / knowledge_query / knowledge_auto_update） | **导入但未调用** | `gcl_runner_enhanced.py` 第 52-59 行 import，第 787-1156 行 main() 从未调用 |
| Autonomy Ratio 模块 | **导入但未调用** | `autonomy_ratio.py` 有 Calculator+Tracker+Alert，enhanced runner 从未调用 |
| post-update self-review | **缺少 rubric 存在性检查** | `docs/post-update-self-review.md` C1-C6 + F1-F8 无一项检查 rubric.md 是否存在 |
| CI/CD 门禁 | **不存在** | repo 根目录无 GitHub Actions / CI 配置 |
| trace_feedback.py | **手动工具，未接入循环** | 仅作 `python3 trace_feedback.py` 手动触发，从未在 GCL SAFETY_FAIL 后自动触发 |
| GCL Phase 3（LLM-based Critic） | **悬空** | `docs/gcl-spec.md` Rollout Roadmap Phase 3 为 "Planned" |

### 1.2 为什么需要这次修复

| 反思维度 | 当前工程缺陷 |
|---------|------------|
| **可用性** | rubric.md 缺失 → GCL Critic 无评分依据 → GCL 降级为纯执行记录器 |
| **完整性** | AIOps 模块导入不调用 → 自愈/知识闭环从未触发 → 标注 "wired" 实为死代码 |
| **质量门禁** | self-review 缺少 rubric 检查 → rubric 缺失也能通过 review → merge 后 GCL 不可用 |
| **可观测性** | 无 CI、无 trace_feedback 接入循环 → GCL 运行数据无消费者 → 无法基于真实数据改进 |
| **可迭代性** | Phase 3 LLM Critic 悬空 → 机械 Critic 无法理解语义 → Safety=0 的误判无法纠正 |
| **可见性** | gcl_runner vs enhanced 职责不清 → 开发者不知用哪个 → 工程决策混乱 |

---

## 2. 目标（Goal）

### 2.1 核心目标

将 GCL 框架从"文档完备但工程残缺"修复为"文档与工程同步可执行"：

1. **rubric.md 全量生成**：为所有引用 rubric.md 的 skill 生成真实可用的 rubric 文件
2. **AIOps 模块接入**：将 self_correction_mechanism / knowledge_query / autonomy_ratio 接入 enhanced runner 主循环
3. **质量门禁闭环**：self-review 增加 rubric 检查，CI/CD 自动执行 lint/self-review
4. **可观测性升级**：structured logging + unified metrics + trace 上报

### 2.2 成功标准

| # | 标准 | 验收方式 |
|---|------|---------|
| AC-1 | rubric.md 在所有引用它的 skill 下存在 | `ls gcp-*-ops/references/rubric.md` 覆盖 100% 引用它的 skill |
| AC-2 | AIOps 模块在 enhanced runner 中被调用 | `grep -c "DegradationDetector\|KnowledgeQueryAPI\|AutonomyRatioCalculator" gcl_runner_enhanced.py` 在 main() 内 ≥ 3 处 |
| AC-3 | self-review 有 rubric 存在性检查 | `grep "rubric.md" docs/post-update-self-review.md` 有实际检查命令 |
| AC-4 | CI pipeline 执行 lint + self-review | `.github/workflows/gcl-quality.yml` 存在且 PR 时自动运行 |
| AC-5 | 结构化日志覆盖 GCL 所有阶段 | `grep "GCL_LOGGER\|log_gcl_event" gcl_runner_enhanced.py` 在 main() 内 ≥ 5 处 |
| AC-6 | 无新增测试失败 | `python3 -m pytest gcp-gcl-runner-ops/tests/ -q` 失败数 ≤ 0 |

---

## 3. 可观测性集成评估

### 3.1 现状分析

**已有可观测资产：**

| 组件 | 功能 | 接入状态 |
|------|------|---------|
| `autonomy_ratio.py` | 自主决策率追踪 | ❌ 未接入（仅 import） |
| `trajectory_classifier.py` | 轨迹分类（SUCCESS/FAILURE/ANOMALY） | ❌ 未接入（仅手动工具） |
| `failure_clusterer.py` | 失败模式聚类 | ❌ 未接入（仅手动工具） |
| `trace_feedback.py` | 质量闭环报告 | ⚠️ 手动触发，未入循环 |
| `audit-results/gcl-trace-*.json` | GCL 执行轨迹持久化 | ⚠️ 写入了但无消费者 |
| `gcl_runner_enhanced.py` 的 retry 逻辑 | 重试 + 降级检测 | ⚠️ 有代码但 autonomy_ratio 未调用 |

**Langfuse 集成现状：**
- `gcl_runner_enhanced.py` 第 50 行从 `gcl_trace_schema` 导入 trace 类型
- 但整个 runner 中没有 `langfuse` 或任何 LLM tracing 库的 import
- GCL 的 Generator/Critic/H 三个 LLM 调用没有任何 tracing

**结构化日志现状：**
- `gcl_runner_enhanced.py` 第 42 行：`from gcl_logging import get_gcl_logger, log_gcl_event`
- `gcl_logging` 模块存在于 `gcp-gcl-runner-ops/` 但未被调用

### 3.2 评估结论：需要加强

当前可观测性存在三层断链：

```
断链 1: LLM 调用无 tracing
  Generator/Critic/H 的 LLM 调用 → 无 Langfuse trace → 无法分析 token 消耗、延迟、质量

断链 2: 运行时指标无采集
  DegradationDetector / AutonomyRatioCalculator → 未接入 main() → 无实时指标 → 无统一 dashboard

断链 3: 轨迹数据无消费
  audit-results/gcl-trace-*.json → trace_feedback.py 未自动触发 → 质量数据无消费者 → skill 无法基于真实数据迭代
```

### 3.3 强化方案

**最小可行可观测性（不破坏现有架构）：**

| 层级 | 当前 | 目标 | 实现文件 |
|------|------|------|---------|
| Structured Logging | `gcl_logging` 模块存在但未调用 | 在 main() 的 Pre-flight/Generate/Critique/Decide 每阶段调用 `log_gcl_event` | `gcl_runner_enhanced.py` |
| Runtime Metrics | AutonomyRatioCalculator 未接入 | 在 Decide 阶段调用 `calculator.record_op()`，PASS/FAIL 后输出一行摘要 | `gcl_runner_enhanced.py` |
| Trace Collection | `classify_directory()` 手动调用 | 在 main() 循环结束后调用 `classify_directory()` + `cluster_failures()`，自动生成质量报告 | `gcl_runner_enhanced.py` |
| LLM Tracing | 无 | 在 Generator/Critic/H 调用前后加 `log_gcl_event` 事件（暂不引入 Langfuse SDK，避免破坏现有依赖） | `gcl_runner_enhanced.py` |

> **决策：暂不引入 Langfuse SDK**（依赖破坏风险高）。用结构化日志 + 轨迹文件分析替代，等框架稳定后作为 Phase 2 引入。

---

## 4. 范围边界（Scope）

### In Scope（本轮做）
- 为所有引用 rubric.md 的 skill 生成 `references/rubric.md`
- 将 DegradationDetector / KnowledgeQueryAPI / AutonomyRatioCalculator 接入 enhanced runner
- post-update self-review 增加 rubric 存在性检查（C7）
- 新增 `.github/workflows/gcl-quality.yml` CI pipeline
- 结构化日志覆盖 GCL 5 阶段（Pre-flight/Generate/Critique/Decide/Report）
- main() 循环结束后自动调用 `classify_directory()` + `cluster_failures()`
- 修复 `scripts/README.md` 说明 gcl_runner.py vs gcl_runner_enhanced.py 职责

### Out of Scope（本轮不做）
- Phase 3 LLM-based Critic 实现（独立大任务，留作 Phase 2）
- 引入 Langfuse SDK（等框架稳定后作为独立任务）
- rubric.md 的 per-op sub-rules 内容填充（那是 skill generator 的职责，本轮只生成框架文件）
- gcp-skill-generator 自身的优化（独立任务）
- GitHub Actions 以外的 CI 系统

---

## 5. 已建资产（必须引用）

| 资产 | 位置 | 本轮使用方式 |
|------|------|-------------|
| rubric.md 模板 | `gcp-skill-generator/references/template-gcl-gate.md` | 生成各 skill rubric.md 的格式模板 |
| GCL spec | `docs/gcl-spec.md` | rubric 维度和权重定义 |
| GCL rollout spec | `gcp-skill-generator/references/gcl-rollout-spec.md` | rubric 结构（5 核心 + 3 GCP 扩展）|
| post-update self-review | `docs/post-update-self-review.md` | 新增 C7 检查的检查逻辑 |
| autonomy_ratio.py | `gcp-gcl-runner-ops/autonomy_ratio.py` | 接入 main() 的 Calculator + Alert |
| trajectory_classifier.py | `gcp-gcl-runner-ops/trajectory_classifier.py` | 接入 main() 末尾的 `classify_directory()` |
| failure_clusterer.py | `gcp-gcl-runner-ops/failure_clusterer.py` | 接入 main() 末尾的 `cluster_failures()` |
| gcl_logging | `gcp-gcl-runner-ops/gcl_logging.py` | 在各阶段调用的结构化日志 |
| GCL trace schema | `gcp-gcl-runner-ops/gcl_trace_schema.py` | Trace 数据结构和 Environment 枚举 |

---

## 6. 约束（Constraints）

1. **不破坏现有接口**：`gcl_runner.py`（标准版）的 CLI 接口不变，enhanced 版仅新增调用
2. **零新增测试失败**：现有测试套件失败数必须维持 0
3. **Token Efficiency 遵循**：TE-1..TE-8 规则继续适用，rubric.md 内容紧凑（≤ 500 行/文件）
4. **结构化日志不过度**：每阶段一条关键事件日志，不逐行打印
5. **Git 安全**：CI workflow 不在 pull_request 上运行需要 secret 的操作（gcloud 认证仅在 merge 时）
6. **框架无关**：所有改动不硬编码 "Claude Code" / "Cursor" 等 agent 产品名

---

## 7. 验收标准（Acceptance Criteria）

- [ ] 所有引用 `references/rubric.md` 的 skill 下该文件存在（可为空框架，内容由 skill generator 后续填充）
- [ ] `gcl_runner_enhanced.py` main() 内对 DegradationDetector / KnowledgeQueryAPI / AutonomyRatioCalculator 的调用 ≥ 5 处
- [ ] `docs/post-update-self-review.md` 包含 C7 rubric 存在性检查
- [ ] `.github/workflows/gcl-quality.yml` 存在，PR 时执行 `markdownlint` + `ruff` + self-review 检查
- [ ] `gcl_runner_enhanced.py` 在 Pre-flight/Generate/Critique/Decide/Report 每阶段有 `log_gcl_event` 调用
- [ ] main() 末尾调用 `classify_directory()` 和 `cluster_failures()`，输出质量摘要
- [ ] `scripts/README.md` 明确 gcl_runner.py（轻量/机械 Critic）和 gcl_runner_enhanced.py（AIOps/追踪）的适用场景
- [ ] `python3 -m pytest gcp-gcl-runner-ops/tests/ -q` 失败数为 0

---

## Version History

### SPEC Version 1.0.0 — 2026-07-20
- 初始版本：定义框架质量修复目标、范围、约束
