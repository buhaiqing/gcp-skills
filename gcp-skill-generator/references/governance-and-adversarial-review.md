# Governance & Adversarial Review

> **Purpose:** Provides a minimal adversarial review framework for generated skills, catching destructive-action shortcuts, credential leaks, API hallucination, and UX gaps **before** merge. All generated skills MUST pass this review.
> **Version:** 1.0.0
> **Last Updated:** 2026-06-07
> **Status:** MANDATORY — no skill may be merged without passing this review

---

## 0. Charter (不可违背的基本原则)

> **地位：宪章条款 — 所有生成的 SKILL.md 必须遵守，否则视为无效技能。**
> **自解机制：Agent 在生成完成后自动执行合规检查，不符合则自动触发修复。**

以下 6 条为不可违背的基本原则（INVIOLABLE PRINCIPLES）：

| # | 原则 | 检查方法 | 违背后果 |
|---|------|----------|----------|
| **C1** | **YAML Frontmatter 存在且格式正确** | 文件开头必须是 `---`，包含 `name`、`description`、`license`、`compatibility`、`metadata` 字段 | **自动修复** — Agent 必须添加完整 frontmatter |
| **C2** | **SHOULD/SHOULD NOT Use 章节存在** | 搜索 `### SHOULD Use` 和 `### SHOULD NOT Use` | **自动修复** — Agent 必须添加触发条件章节 |
| **C3** | **Five Core Standards 表格存在** | 搜索 `## Five Core Standards` 表格 | **自动修复** — Agent 必须添加质量门表格 |
| **C4** | **Well-Architected Framework 表格存在** | 搜索 `Google Cloud Architecture Framework` 或 `Well-Architected Framework Integration` | **自动修复** — Agent 必须添加五支柱表格 |
| **C5** | **Variables 章节存在** | 搜索 `## Variables` 表格 | **自动修复** — Agent 必须添加占位符表格 |
| **C6** | **Token Efficiency 6 条规则落实** | 检查 TE-1~TE-6 每条已应用 | **自动修复** — Agent 必须按 Token Efficiency Requirements 逐条修复 |

> **自解规则**：如果任何 C1-C6 不满足，Agent 必须：
> 1. 立即停止，报告违规项
> 2. 自动修复缺失章节（使用模板内容填充）
> 3. 重新执行合规检查
> 4. 循环直到全部通过

---

## 1. Review Process

### 1.1 Review Stages

Every generated skill MUST pass three review stages before merge:

| Stage | Focus | Reviewer | Artifact |
|-------|-------|----------|----------|
| **Stage 1: Technical Review** | API fidelity, gcloud accuracy, security | AI Agent / Senior Engineer | Technical sign-off |
| **Stage 2: UX Review** | Onboarding, interaction, feedback, error handling | UX Reviewer / Product Owner | UX checklist completion |
| **Stage 3: Adversarial Review** | Destructive gates, credential safety, resilience | Security / SRE | Adversarial report |

### 1.2 Review Triggers

Review is REQUIRED when:
- New `gcp-[product]-ops` skill is generated
- Existing skill undergoes material update (new operations, API version bump)

---

## 2. Adversarial Review Scenarios

### 2.1 Destructive Action Bypass

| Scenario | Attack Vector | Expected Defense |
|----------|--------------|------------------|
| A1 | Agent executes delete without user confirmation | Pre-flight requires explicit user confirmation with resource name/ID |
| A2 | Agent uses `--quiet` to bypass gcloud prompts | Safety gate must be in SKILL.md PRE-command, not relying on `--quiet` |
| A3 | Agent modifies resource with no backup check | Pre-flight checks backup status before modify operations |
| A4 | Batch delete without per-resource confirmation | Each resource in batch must be confirmed or filtered |

### 2.2 Credential Leak

| Scenario | Attack Vector | Expected Defense |
|----------|--------------|------------------|
| B1 | Agent outputs SA key content in error logs | All credential values masked with `<masked>` or `***` |
| B2 | Agent `cat`s credential file for verification | Verification checks existence only: `test -f "$GOOGLE_APPLICATION_CREDENTIALS"` |
| B3 | Agent prints `config` struct in Go SDK | `fmt.Printf("%+v", config)` banned; env read only |
| B4 | Agent writes credential to file or debug log | No file output of credential values |

### 2.3 API Hallucination

| Scenario | Attack Vector | Expected Defense |
|----------|--------------|------------------|
| C1 | Agent invents gcloud command flag | Every flag must be traceable to `gcloud --help` or official reference |
| C2 | Agent invents JSON response path | JSON paths must match real `--format=json` output |
| C3 | Agent invents REST API endpoint | Endpoint must be from official discovery doc |
| C4 | Agent uses wrong IAM permission name | Permission names from official IAM docs only |

### 2.4 Resilience Gaps

| Scenario | Attack Vector | Expected Defense |
|----------|--------------|------------------|
| D1 | No retry on UNAVAILABLE/503 | Retry with exponential backoff (max 3) |
| D2 | No HALT on QUOTA_EXCEEDED | HALT and advise quota increase |
| D3 | No timeout on long-running operations | Max wait documented (default: 300s) |
| D4 | No fallback when CLI unavailable | Document JIT Go SDK fallback path |

---

## 3. Governance Checklist

Before merge, verify:

### Security
- [ ] All credential values masked in output/errors/logs
- [ ] Service account key content never displayed
- [ ] `--quiet` only used AFTER safety gate
- [ ] Delete/stop operations have explicit user confirmation
- [ ] IAM minimum permissions documented

### API Accuracy
- [ ] gcloud commands verified against `--help` output
- [ ] REST API paths verified against discovery docs
- [ ] JSON response paths match real API output
- [ ] Error codes documented with grpc/HTTP mapping

### UX
- [ ] Quick Start section present
- [ ] Error messages follow `[ERROR] code → summary → fix → next` format
- [ ] Common operations require ≤ 3 prompts
- [ ] Progress feedback for operations > 5s

### Resilience
- [ ] Retry logic documented for transient errors
- [ ] HALT conditions documented for business errors
- [ ] Fallback paths documented (CLI → SDK)
- [ ] Timeouts documented