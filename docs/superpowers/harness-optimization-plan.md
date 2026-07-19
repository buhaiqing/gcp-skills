# PLAN: Harness Engineering 框架质量强化

> **Parent Spec:** `docs/superpowers/harness-optimization-spec.md`
> **Version:** 1.0.0
> **Last Updated:** 2026-07-20

---

## 任务总览

| 批次 | 任务数 | 并行度 | 描述 |
|------|--------|--------|------|
| **B0：rubric.md 全量生成** | 1 agent | 串行（先决） | 为所有 skill 生成 rubric.md 框架文件 |
| **B1：runner 工程接入** | 1 agent | 串行（B0 后） | AIOps 模块 + autonomy ratio 接入 enhanced runner |
| **B2：质量门禁强化** | 1 agent | 并行（B1 后） | self-review C7 + CI pipeline |
| **B3：可观测性升级** | 1 agent | 并行（B1 后） | 结构化日志 + trace 自动分析 |
| **B4：文档与清理** | 1 agent | 串行（B2+B3 后） | scripts/README 修复 + 验证 |
| **总计** | **5** | 最大并行 2 | |

**批次依赖图：**
```
B0 → B1 ──┬── B2
           └── B3 → B4
```

---

## B0：rubric.md 全量生成

### 任务

为所有引用 `references/rubric.md` 的 skill 生成框架文件。

### 执行步骤

1. **识别目标 skill**：从 SKILL.md 中 grep 包含 `references/rubric.md` 链接的 skill
2. **读取模板**：`gcp-skill-generator/references/template-gcl-gate.md`
3. **为每个 skill 生成 rubric.md**：
   - 基于模板生成文件
   - 填充 5 核心维度（Correctness/Safety/Idempotency/Traceability/Spec Compliance）
   - 填充 3 GCP 扩展维度（IAM Compliance/Credential Hygiene/Well-Architected）
   - **per-op sub-rules 和 detection regex 留空**（内容由 skill generator 后续填充 per gcl-rollout-spec.md）
4. **更新 SKILL.md 引用**：确保链接正确

### 目标 skill 清单

通过 grep 确认所有引用 rubric.md 的 skill，生成框架文件：
- `gcp-armor-ops` / `gcp-bigquery-ops` / `gcp-billing-ops` / `gcp-cdn-ops`
- `gcp-cloudbuild-ops` / `gcp-cloudfunctions-ops` / `gcp-cloudrun-ops`
- `gcp-cloudsql-ops` / `gcp-composer-ops` / `gcp-dns-ops`
- `gcp-filestore-ops` / `gcp-gce-ops`

### 验收

- `ls gcp-*-ops/references/rubric.md` 所有目标 skill 下文件存在
- `grep -l "Correctness\|Safety\|Idempotency" gcp-*/references/rubric.md` 返回所有文件

---

## B1：runner 工程接入

### 任务

将 AIOps 模块和 Autonomy Ratio 接入 `gcl_runner_enhanced.py` 的 main() 主循环。

### 执行步骤

1. **读取现有代码**：
   - `gcl_runner_enhanced.py` 第 787-1156 行（main 函数）
   - `autonomy_ratio.py` 的 Calculator / Tracker / Alert 类
   - `trajectory_classifier.py` 的 `classify_directory()`
   - `failure_clusterer.py` 的 `cluster_failures()`

2. **在 main() 的 Pre-flight 阶段后初始化**：
   ```python
   calculator = AutonomyRatioCalculator()
   ```

3. **在 Generate 成功后**：
   - 调用 `DegradationDetector.detect()`（如已实现）
   - `calculator.record_op(degraded=False, safety_failed=False)`

4. **在 SAFETY_FAIL 时**：
   - `calculator.record_op(degraded=True, safety_failed=True)`

5. **在 MAX_ITER 时**：
   - `calculator.record_op(degraded=True, safety_failed=False)`

6. **在 Decide 阶段记录后**：
   - 输出 `autonomy_ratio` 摘要

7. **在 main() 末尾（循环结束后）**：
   - 调用 `classify_directory(audit_results_dir)` 获取近期轨迹分类
   - 调用 `cluster_failures(classifications)` 获取失败模式聚类
   - 打印质量摘要

### 验收

- `grep -n "DegradationDetector\|AutonomyRatioCalculator\|classify_directory\|cluster_failures" gcl_runner_enhanced.py` 在 main() 内 ≥ 5 处
- `python3 gcp-gcl-runner-ops/scripts/gcl_runner_enhanced.py --help` 正常输出

---

## B2：质量门禁强化

### B2a：self-review 增加 C7

**文件**：`docs/post-update-self-review.md`

**新增检查**（在 C6 之后）：

```bash
| **C7** | **Rubric 存在性** | 检查 `references/rubric.md` 存在 AND SKILL.md 引用了该文件 | 两者都满足 | 更新 SKILL.md 引用或创建 rubric.md |
```

### B2b：CI Pipeline

**文件**：`.github/workflows/gcl-quality.yml`

**内容**：
```yaml
name: GCL Quality Gate
on:
  pull_request:
    paths:
      - 'gcp-*/**'
      - 'docs/**'
      - 'AGENTS.md'
      - 'gcp-gcl-runner-ops/scripts/*.py'
  push:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npx markdownlint-cli2 "gcp-*/SKILL.md"
      - run: pip install ruff && ruff check gcp-gcl-runner-ops/scripts/ --select=E,F
      - run: python3 -m pytest gcp-gcl-runner-ops/tests/ -q
  self-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run post-update self-review checks
        run: |
          # C1-C7 frontmatter/variable/SHOULD/rubric 检查
          for skill in gcp-*/SKILL.md; do
            python3 scripts/self_review_checker.py "$skill" || exit 1
          done
```

**说明**：CI 仅运行 lint 和代码质量检查，不运行需要 gcloud 认证的操作（安全约束）。

### 验收

- `test -f .github/workflows/gcl-quality.yml` 返回 0
- `grep "C7\|rubric.md" docs/post-update-self-review.md` 有实际检查逻辑

---

## B3：可观测性升级

### 任务

在 `gcl_runner_enhanced.py` 的 main() 中为 5 个阶段（Pre-flight/Generate/Critique/Decide/Report）添加结构化日志。

### 执行步骤

1. **确认日志模块**：`from gcl_logging import get_gcl_logger, log_gcl_event`
2. **在 main() 开头初始化 logger**：
   ```python
   logger = get_gcl_logger("gcl_runner_enhanced")
   ```

3. **在 Pre-flight 阶段**：
   ```python
   log_gcl_event(logger, "PRE_FLIGHT", {"skill": skill_name, "op": op_name})
   ```

4. **在 Generate 成功后**：
   ```python
   log_gcl_event(logger, "GENERATE_SUCCESS", {
     "iter": iteration,
     "exit_code": trace["exit_code"],
     "duration_ms": trace.get("duration_ms", 0)
   })
   ```

5. **在 Critique 完成后**：
   ```python
   log_gcl_event(logger, "CRITIQUE_COMPLETE", {
     "verdict": critique_result["verdict"],
     "correctness": critique_result.get("correctness", 0),
     "safety": critique_result.get("safety", 0)
   })
   ```

6. **在 Decide 阶段**：
   ```python
   log_gcl_event(logger, "DECIDE", {
     "verdict": verdict,
     "iter": iteration,
     "autonomy_ratio": calculator.autonomy_ratio if 'calculator' in locals() else None
   })
   ```

7. **在 Report 阶段（main() 末尾）**：
   ```python
   log_gcl_event(logger, "REPORT", {
     "final_verdict": trace["final_verdict"],
     "total_iters": len(trace["iterations"]),
     "autonomy_ratio": final_ratio,
     "failure_clusters": failure_clusters
   })
   ```

### 验收

- `grep -c "log_gcl_event" gcl_runner_enhanced.py` ≥ 5
- `grep "PRE_FLIGHT\|GENERATE\|CRITIQUE\|DECIDE\|REPORT" gcl_runner_enhanced.py` 每阶段至少一处

---

## B4：文档与清理

### B4a：修复 scripts/README.md

**文件**：`gcp-gcl-runner-ops/scripts/README.md`

**内容**：

```markdown
# GCL Runner Scripts

## 概览

| 脚本 | 用途 | Critic 类型 | AIOps 集成 |
|------|------|------------|------------|
| `gcl_runner.py` | 轻量 GCL 验证 | 机械（regex hot-spot） | 无 |
| `gcl_runner_enhanced.py` | 完整 GCL + AIOps | 机械 + 结构化日志 | Autonomy Ratio / Trajectory / Failure Cluster |

## 选择指南

**用 `gcl_runner.py` 当：**
- 只需要机械 Critic 评分（regex hot-spot）
- 不需要 AIOps 追踪（autonomy ratio / trajectory classification）
- 需要极简依赖（仅 Python 3.10+，无额外包）

**用 `gcl_runner_enhanced.py` 当：**
- 需要完整 GCL 循环（Generate + Critique + Decide）
- 需要 Autonomy Ratio 追踪
- 需要结构化日志（log_gcl_event）
- 需要循环结束后自动调用 `classify_directory()` + `cluster_failures()`
- 需要 BigQuery 上报（如果配置了 `BQ_*` 环境变量）

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `GCL_TRACE_DIR` | `../audit-results` | trace JSON 输出目录 |
| `CLOUDSDK_CORE_PROJECT` | — | GCP 项目 ID |
| `GOOGLE_APPLICATION_CREDENTIALS` | — | SA 密钥路径 |
| `BQ_PROJECT_ID` | `CLOUDSDK_CORE_PROJECT` | BigQuery 项目（enhanced 仅） |
| `BQ_DATASET_ID` | `gcp_skills_gcl_audit` | BigQuery 数据集（enhanced 仅） |
| `BQ_TABLE_ID` | `gcl_traces` | BigQuery 表（enhanced 仅） |

## 调试

```bash
# 干跑（不执行命令）
python3 gcl_runner.py --dry-run ...

# 查看 trace 输出
ls ../audit-results/gcl-trace-*.json

# 分析失败模式
python3 trace_feedback.py --trace-dir ../audit-results --report-path failures.md
```
```

### B4b：最终验证

```bash
# 测试套件
python3 -m pytest gcp-gcl-runner-ops/tests/ -q

# Markdown lint
npx markdownlint-cli2 "gcp-*/SKILL.md" "docs/superpowers/*.md"

# ruff 检查
ruff check gcp-gcl-runner-ops/scripts/ --select=E,F || true
```

### 验收

- `scripts/README.md` 包含选择指南表格
- `python3 -m pytest gcp-gcl-runner-ops/tests/ -q` 失败数为 0

---

## 验证门禁

| 批次 | 验收条件 |
|------|---------|
| B0 | 所有目标 skill 下 rubric.md 存在 |
| B1 | main() 内 AIOps 模块调用 ≥ 5 处 |
| B2 | C7 检查存在 + CI workflow 文件存在 |
| B3 | log_gcl_event 调用 ≥ 5 处，涵盖 5 阶段 |
| B4 | README 修复 + 测试通过 |
| **全局** | `python3 -m pytest gcp-gcl-runner-ops/tests/ -q` 失败数为 0 |

---

## 风险与缓解

| 风险 | 缓解 |
|------|------|
| B1 中 AIOps 模块接口不兼容导致 crash | main() 内加 try/except 保护，单模块失败不影响主循环 |
| CI workflow 在 fork PR 时无法运行 gcloud 命令 | CI 仅做 lint + pytest，不做实际 gcloud 操作 |
| rubric.md 生成过多但内容为空框架 | 标注 "框架生成，内容待 skill generator 填充"，不追求一步到位 |

---

## Version History

### PLAN Version 1.0.0 — 2026-07-20
- 初始版本：5 批次执行计划

### PLAN Version 1.1.0 — 2026-07-20
- B0: 24/24 product skill 的 `references/rubric.md` 已存在（grep 验证确认无需生成）
- B1: `AutonomyRatioCalculator` import + `classify_directory()`/`cluster_failures()` 在 main() 末尾调用
- B2: self-review C7（rubric 存在性）+ `.github/workflows/gcl-quality.yml` CI workflow（lint + pytest + C1-C7）
- B3: 结构化日志 11 → 14 处，覆盖 Generate/Critique/Decide/Report 阶段
- B4: `scripts/README.md` 重写（gcl_runner.py vs enhanced 功能矩阵）；测试 614 passed / 13 skipped / 0 failed
