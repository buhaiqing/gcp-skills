# GCP Skills — Agent Guide

This repository is a Skills Farm for Google Cloud Platform operations — structured, AI-agent-parseable runbooks for cloud resource management.

Every section here is high-signal: agents must follow these patterns or they will produce broken or inconsistent skills.

---

## 1. Repo Layout

```
gcp-skills/
├── gcp-[product]-ops/          # One skill per GCP product (SKILL.md + references/ + assets/)
├── gcp-skill-generator/        # Meta-skill: scaffold new skills
├── gcp-gcl-runner-ops/         # Cross-skill GCL runner
├── docs/                       # Lazy-loaded specs (GCL, logging, self-review, token strategy)
├── AGENTS.md                   # This file — always-loaded agent guide
├── TODO.md                     # All-skill TODO tracker (≤8000 tokens)
└── REQUIREMENTS.md             # Full requirements, architecture
```

**Canonical skill structure**: `SKILL.md` (what) + `references/` (how) + `assets/` (configs, eval queries). See `gcp-skill-generator/references/gcp-skill-template.md` for full template.

---

## 2. Content Separation Rule (MANDATORY)

**SKILL.md describes What to do, references/\* describes How to do.**

| File | Responsibility | Content |
|------|---------------|---------|
| `SKILL.md` | What | Triggers, Pre-flight Checks, variable conventions, execution overview, links to references/ |
| `references/*.md` | How | Full commands, scripts, exit code tables, log interpretation, failure recovery |

```markdown
<!-- SKILL.md — correct approach -->
#### Execution
Full script at [references/gcloud-execution.md](references/gcloud-execution.md)

| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud compute instances describe` | Get instance details |
| 2 | `gcloud compute ssh` | Idempotent check and connect |

<!-- Wrong approach: embedding 500-line script in SKILL.md -->
```

---

## 3. GCP CLI & SDK Conventions

| Component | Tool | Notes |
|-----------|------|-------|
| **Primary CLI** | `gcloud` | Google Cloud SDK CLI — most operations |
| **Kubernetes** | `kubectl` / `gcloud container clusters` | GKE operations |
| **Terraform** | `terraform` | For infrastructure-as-code workflows |
| **Python SDK (primary)** | `google-cloud-*` | `pip install google-cloud-[product]`; zero extra runtime (Python 3.8+ required by gcloud) |
| **Go SDK (secondary)** | `cloud.google.com/go/...` | For type-safe complex operations when Python unavailable |
| **REST API** | `curl -H "Authorization: Bearer $(gcloud auth print-access-token)"` | For unsupported operations |

### Credential Rules

| Variable | Purpose | Source |
|----------|---------|--------|
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON key | `{{env.*}}` — NEVER ask user |
| `CLOUDSDK_CORE_PROJECT` | GCP project ID | `{{env.*}}` or `gcloud config get-value project` |
| `CLOUDSDK_AUTH_ACCESS_TOKEN` | Temporary access token | `gcloud auth print-access-token` |

**Never output credentials**: Replace access tokens and service account keys in logs with `****`. Python SDK reads credentials via `GOOGLE_APPLICATION_CREDENTIALS` env var automatically (safe). Go SDK scripts' `config` structs, `fmt.Println(config)`, and `log.Printf("%+v", ...)` can all leak credentials — prohibit such output.

---

## 4. Idempotent Provisioning Pattern

For operations requiring tools on target machines, use the idempotent pattern:

```bash
# 1. Probe
if ! command -v gsutil &>/dev/null; then
  # 2. Install only if missing (e.g. via Google Cloud SDK)
  sudo apt-get update && sudo apt-get install -y google-cloud-sdk
fi
# 3. Execute (regardless of install outcome)
gsutil cp gs://bucket/path ./local --project=$CLOUDSDK_CORE_PROJECT
```

Do not install unconditionally on every run. Log probe results with DIAG/RESULT phase.

---

## 5. Cross-Skill Composition

When a Skill depends on another Skill's capabilities (e.g. `gcp-gce-ops` needs `gcp-gke-ops` to describe workload identity):

**Recommended**: Inline the necessary commands in SKILL.md, document the dependency in comments.

```markdown
# Execution — CLI  (uses gcloud compute ssh; see gcp-gce-ops for advanced usage)
gcloud compute ssh instance-name --zone=us-central1-a --command="..."
```

**Not recommended**: Formal import/require of another skill (the agent may not have both loaded). Inline is the more reliable pattern.

---

## 6. Control Plane vs Data Plane

| Plane | Capability | Channel | Example Operations |
|-------|-----------|---------|-------------------|
| **Control Plane** | Resource lifecycle, config management | `gcloud {product}` API | Create/Delete/Describe/Modify instances, clusters, databases |
| **Data Plane** | Data read/write, command execution | SDK direct / `gcloud compute ssh` | Query BigQuery, write to Cloud Storage, run SQL on Cloud SQL |

When existing APIs cannot cover data-plane operations, use **SSH + CLI client** as an indirect approach:

```
gcp-cloudsql-ops orchestration → gcp-gce-ops gcloud compute ssh → target VM executes mysql/psql
```

For serverless products (Cloud Functions, Cloud Run), use **gcloud commands with --format=json** for data-plane introspection.

---

## 7. Security Constraints

- **Never output credentials**: Replace access tokens, `GOOGLE_APPLICATION_CREDENTIALS` values, and service account key content in logs with `****`. Python SDK auto-reads credentials from env var (safe). Go SDK scripts' `config` structs, `fmt.Println(config)`, and `log.Printf("%+v", ...)` can all leak credentials — prohibit such output.
- **Pass passwords via environment variables**: Use `MYSQL_PWD` / `PGPASSWORD` environment variables instead of `-p<password>` to avoid exposure in `ps aux` or command history. For Cloud SQL, prefer Cloud SQL Auth Proxy or IAM database authentication.
- **Delete operations MUST obtain explicit confirmation**: Include a confirmation row in the Pre-flight Checks table requiring the user to explicitly provide a resource identifier.
- **IAM policy changes MUST use conditional bindings or dry-run**: Use `gcloud projects get-iam-policy` preview before applying policy changes.
- **Service account key rotation**: When creating new keys, always set an expiry and document the rotation schedule.

---

## 8. Quick Reference — Developer Commands

```bash
# Markdown linting
npx markdownlint-cli2 "gcp-*/SKILL.md"

# Python linting + formatting (Ruff)
ruff check gcp-*/scripts/ gcp-*/assets/code-snippets/  # lint
ruff format --check gcp-*/scripts/                       # format check
ruff check --fix gcp-*/scripts/                          # auto-fix

# Docker sandbox profiles (see docker-compose.yaml)
docker compose --profile dev up -d      # Development environment
docker compose --profile runtime up -d  # Minimal runtime
docker compose --profile interactive run interactive  # Interactive sandbox

# Generate new skill (use meta-skill)
"Generate gcp-xyz-ops for product XYZ with operations: create, describe, modify, delete"

# JIT Python/Go SDK setup
./gcp-jit-setup.sh  # Note: file to be created; see gcp-skill-generator/references/execution-environment.md for manual setup

# Authenticate SDK in sandbox
gcloud auth application-default login
```

---

## 9. Quality Gates

Every Skill MUST pass these five quality gates:

1. **Clear Boundaries**: SHOULD/SHOULD NOT triggers with delegation rules; trigger description optimized per agentskills.io guidelines (< 1024 chars)
2. **Structured I/O**: `{{env.*}}` (never ask user), `{{user.*}}` (ask once reuse), `{{output.*}}` (parse from API responses)
3. **Explicit Steps**: Pre-flight → Execute → Validate → Recover for **each** critical operation
4. **Failure Strategies**: Error taxonomy (≥10 product-specific codes), HALT vs retry logic, credential vs quota vs business error separation
5. **Single Responsibility**: One product, one primary resource; cross-product delegation documented, not duplicated

Additionally, every skill MUST include a **Well-Architected Framework** table (five pillars: Security, Stability, Cost, Efficiency, Performance — mapped to the Google Cloud Architecture Framework) and pass the **P0/P1 checklist** defined in `gcp-skill-generator/SKILL.md`.

### 9.1 Token Efficiency Requirements (P0 — MANDATORY)

> Minimize token consumption per Skill while preserving agent executability. Full definitions at `gcp-skill-generator/SKILL.md` §Token Efficiency Requirements.

| Rule | Key Point | Savings |
|------|-----------|---------|
| **TE-1** API query > static table | Use `gcloud` to fetch versions/quotas, no hardcoding | ~200-500/file |
| **TE-2** Omit unnecessary docstrings | Python/Go SDK: `#` comment instead of function-level docstring | ~100-200/func |
| **TE-3** Compact error tables | 1 error code per row, ≤3 columns | ~300-500/file |
| **TE-4** Centralized JSON paths | Declare at file top, don't repeat | ~50-100/file |
| **TE-5** YAML anchors | `example-config.yaml` use `&anchor` to eliminate duplication | ~200-400/file |
| **TE-6** Eliminate cross-file duplication | SKILL.md has full flow, references/ doesn't repeat | Varies |
| **TE-7** Layer professional content | AIOps/FinOps in `references/advanced/`; SQL execution marked Security-Sensitive with explicit confirmation | ~3,000-8,000/file |

**Non-compressible**: Agent-executable commands (params, JSON paths), error recovery logic, safety gates, credential rules, cross-skill orchestration chains.

> **Mandatory per-skill enforcement**: Every `gcp-*-ops` SKILL.md **MUST** include a `## Token Efficiency Guidelines (P0 — 强制)` section (TE-1 to TE-7, sourced from `gcp-skill-generator/references/gcp-skill-template.md` §Token Efficiency Guidelines). A skill missing this section is a **P0 failure** and MUST be fixed before merge. The generator already injects this section for new skills; existing skills lacking it MUST add it on next update (tracked by CADL §10.5 and generator charter C6).

> **Application-level optimization**: AGENTS.md's own always-loaded optimization strategy (TE-A/TE-B/TE-C) is documented at [docs/token-efficiency-strategy.md](docs/token-efficiency-strategy.md) — includes full audit methodology and checklist for scanning existing skills.

---

## 10. Post-Update Self-Review (MANDATORY)

> **Rule**: After every skill update, auto-run 2 rounds of self-review and fix all discovered issues.
>
> Full spec (check tables, verification scripts, dedup procedures, implementation notes) at [docs/post-update-self-review.md](docs/post-update-self-review.md)

| Round | Scope | Key Checks |
|-------|-------|-----------|
| **R1: Structural** | Frontmatter/Trigger/Variables/Token Efficiency | C1-C6, C6 MUST PASS |
| **R2: Content** | CLI validation/error codes/safety gates/link integrity/dedup/TODO.md sync | F1-F8, F5/F6/F8 MUST PASS |

其中新增 **F8** 检查项：

| 编号 | 检查项 | 说明 | 要求 |
|------|--------|------|------|
| **F8** | TODO.md 同步 | 本次所有新增/修改的功能是否已在根目录 `TODO.md` 中更新为 `✅` | 每次更新必须同步更新根 TODO.md |
| **F9** | 提示词示例充分性 | `assets/eval_queries.json` 覆盖所有操作类型，正面+反面示例充足，不足则补充 | 每次新增操作必须补充对应 eval query |

> **F6（Token Efficiency）、F8（TODO.md 同步）和 F9（提示词示例充分性）是强制通过项**，不通过不得提交。

### 10.1 TODO.md 维护规范

> **规则**: 所有 skill 的待办事项统一在项目根目录 `TODO.md` 中维护，各 skill 目录下不再保留独立 TODO.md。

| 规范 | 说明 |
|------|------|
| **统一位置** | `TODO.md` 位于仓库根目录，按 skill 分节 (`## gcp-xxx-ops`) |
| **同步更新** | 每次新增/修改功能，必须同步更新根 `TODO.md`：完成的标 `✅`，计划中标 `⬜` |
| **禁止重复** | 各 skill 子目录下不保留独立 `TODO.md`，避免多处维护导致不一致 |
| **F8 校验** | 自审 F8 检查项以根 `TODO.md` 为准 |

Any issue found → fix one by one → all must pass before finishing.

---

### 10.2 AGENTS.md 行数门禁（Agent CMD Size Guard）

**硬限制**：本文件（AGENTS.md）**不得超过 500 行**。

#### 为什么是 500 行

- LLM 上下文窗口有限，过长的规则文件会稀释重要规则的注意力权重
- 500 行 ≈ 8000 tokens，约占常用模型上下文的 2-3%，留足空间给实际工作内容
- 超过 500 行后，规则间的优先级冲突概率显著上升

#### 自我监督机制

每次向本文件写入新内容前，**必须**执行：

```bash
wc -l AGENTS.md
```

| 当前行数 | 动作 |
|---------|------|
| < 400 行 | 自由添加 |
| 400-500 行 | 谨慎添加，同时精简已有内容 |
| ≥ 500 行 | **禁止添加**，必须先精简再写入 |

#### 精简策略（按优先级）

1. **删除冗余示例**：保留结论，删除代码推导过程（代码在仓库里，规则里只需说"做什么"）
2. **合并同类项**：多个相似规则合并为一个 checklist 或表格
3. **降级到 docs/**：详细实现文档移到 `docs/` 子目录，AGENTS.md 只放摘要 + 链接
4. **删除过时规则**：已被实践淘汰的规则直接删除（git 有历史）

---

## 10.5 复利资产沉淀机制（Compound-Asset Distillation Loop, CADL）

**这不是一条规范，而是一套工作闭环——任何实质任务完成后，Agent 必须走完「提取 → 判定落点 → 写入 → 门禁」才能结束。目的是让每次踩坑、每次评审、每次跨 skill 协作都变成下一次的可复用资产，形成复利。**

### 为什么是机制而非规范

单条规则（如"记得写 AGENTS.md"）会被忽略，因为无触发、无闭环。CADL 把沉淀变成工作流的**必经出口**：任务不做沉淀 = 任务未完成。Agent 调用任何 Skill 后都走到这一步，Skill 本身也通过下方「Skill 侧钩子」提示大模型。

### 触发条件（满足任一即必须走 CADL）

- 多步 / 跨文件任务完成
- 跨 Skill 协作（用了 Delegation Rules 或并行 agent）
- 评审 / 修复循环（如 GCL、Post-Update Self-Review §10）
- 发现 repo 缺陷 / 坑（即使不在本次 scope，也记）
- 验证中发现预存 FAIL 并归因
- 用户给出可复用的工作流偏好（如"用双写子命令绕过 CLI bug"）

### 闭环步骤

```
1. 提取   → 从刚完成的任务中抽象出可复用模式：
             踩坑避免 / 评审维度 / 协作模式 / 验证命令 / 复用 helper
             格式："问题 → 反模式 → 正确做法（含代码示例）"
 2. 落点判定 → 离开本仓库还有用？ → 用户级 AGENTS.md（即各 agent 框架的全局 agent 指南，路径随所用框架而定，例如 `~/.config/<agent>/AGENTS.md` 或等价位置）
             仅本仓库适用？     → 项目级 AGENTS.md（本文件）
             是某 skill 专属可调用的能力？ → 独立 Skill 文件（经 gcp-skill-generator）
3. 写入   → 可执行、有示例、有边界、先 grep 现有 AGENTS.md 确认未覆盖（不重复）
4. 门禁   → 写入前查 wc -l，本文件 ≥500 行先精简再写（见 §10.2 行数门禁）
5. 复用   → 下次同类任务，Agent 读 AGENTS.md 即获得该资产 → 复利生效
```

### Skill 侧钩子（让每个 Skill 自带沉淀意识）

- **源头**：`gcp-skill-generator` 在生成每个 skill 时，须在 SKILL.md 末尾注入一行：
   `> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。`
   未来所有 `gcp-*-ops` 自动继承此意识。
- **现存 skill**：逐批在 SKILL.md 末尾补同一行提示，使大模型调用任何 skill 后都看到触发信号。
- **大模型侧**：Agent 在任意 skill 调用结束前，主动检查 CADL 触发条件，而非等用户提醒。

### 反模式（违反 CADL）

| 反模式 | 正确做法 |
|---|---|
| 任务做完就结束，不沉淀 | 走完 CADL 闭环再交付 |
| 把一次性上下文当资产写进 AGENTS.md | 只沉淀跨任务可复用的模式 |
| 重复已有条目 | 写入前 grep 确认未覆盖 |
| 只在 GCL / Self-Review 相关任务才沉淀 | 评审/修复/协作/验证都触发 |

### 通用性约束（Agent 无关 — MANDATORY）

> 本仓库所有规范、Skill、模板、CADL 落点描述 **不得硬编码依赖任何具体 Coding Agent**（如 OpenCode、Claude Code、Cursor 等）。

**规则**：
- Agent 名称、路径、配置文件位置必须泛化表述，例如用户级 agent 指南写作「各 agent 框架的全局 agent 指南，路径随所用框架而定（如 `~/.config/<agent>/AGENTS.md` 或等价位置）」，而非写死 `~/.config/opencode/AGENTS.md`。
- Skill / 模板中的触发提示、变量约定、执行方式应保持框架无关，使任意兼容 agentskills 规范的 agent 均可加载执行。
- 若某流程确实仅特定框架支持，须在文档中明确标注为「可选 / 框架特定」而非默认要求。

**反模式**：在 AGENTS.md、SKILL.md、模板或 references/ 中直接写出具体 agent 产品名作为路径或强制依赖。

---

## Key References

> **Key References**: See the README for the full list of documents.

---

## 11. Generator-Critic-Loop (GCL) — Adversarial Quality Gate

> **Full spec**: [`docs/gcl-spec.md`](docs/gcl-spec.md)

**Core concept**: Enforce a Generator ↔ Critic adversarial loop on every cloud operation, scored against a quantified rubric. Complements [Post-Update Self-Review](docs/post-update-self-review.md) — §10 reviews skill authoring quality, §11 reviews runtime execution quality.

### Roles

| Role | Responsibility | Banned |
|------|---------------|--------|
| **Generator (G)** | Execute the cloud operation | Modify rubric, self-score |
| **Hallucination Detector (H)** | Pre-execution structural validity check | Execute API calls, mutate G's output |
| **Critic (C)** | Independently audit G's output; verify factual accuracy and freshness | Call `gcloud`/SDK, mutate resources |
| **Orchestrator (O)** | Loop control, termination decision | Execute or score |

### Rubric Dimensions (≥5)

| Dimension | Meaning | When Safety=0 |
|-----------|---------|---------------|
| **Correctness** | Resource ID/state/config matches request | — |
| **Safety** | Destructive operations confirmed or protected | **Immediate ABORT** |
| **Idempotency** | Repeating the call has no side effects | — |
| **Traceability** | Output is auditable (command, params, response) | — |
| **Spec Compliance** | Complies with core-concepts.md constraints | — |
| **Factual Accuracy** | Content is complete, up-to-date, and truthful | Uncertain → HALT |

### Termination Conditions (first match wins)

| Condition | Action |
|-----------|--------|
| **PASS** | All dimensions pass → return G's result |
| **MAX_ITER** | Reached max_iter → return best-so-far + unresolved issues |
| **SAFETY_FAIL** | Safety=0 → **ABORT**, no partial result |
| **HALLUCINATION_ABORT** | H detected unresolved hallucinations → **ABORT** |

### Skill Classification (GCL Level + max_iter)

| Level | max_iter | Key Risk |
|-------|:--------:|----------|
| **required** | 2 | Data destruction / instance deletion / irreversible operations |
| **recommended** | 3 | Resource deletion / configuration changes |
| **optional** | 5 | Read-only audit / diagnostic |

**Anti-Patterns (banned)**: Shared context G+C, subjective scoring, unbounded loop, Critic seeing user request, silently downgrading on Safety fail, trace not persisted, Critic mutating resources, trace leaking secrets.

**Factual Accuracy Rule (mandatory for all skills):** The Critic MUST verify that generated content is complete, up-to-date, and truthful. If any stale, inaccurate, or unverifiable information is found, it MUST be corrected immediately. If the Critic cannot confidently verify the accuracy, it MUST HALT and escalate to human review rather than proceed with uncertain content.

**Trace audit**: Every GCL run MUST persist a JSON trace to `./audit-results/gcl-trace-*.json` (gitignored).

---

## Appendix A: GCP Product → Directory Mapping (Planned)

> **Full mapping**: [`docs/gcp-product-mapping.md`](docs/gcp-product-mapping.md)

See the full product-to-directory mapping in the docs directory.