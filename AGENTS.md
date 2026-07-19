# GCP Skills — Agent Guide

Skills Farm for Google Cloud Platform operations — structured, AI-agent-parseable runbooks. Every section is high-signal; agents must follow these patterns.

---

## 0. Shared Common Blocks (MANDATORY — referenced by all skills)

The following blocks are defined **once here** (AGENTS.md is always-loaded, zero extra cost). Every `gcp-*-ops` SKILL.md / `references/*.md` MUST reference this section instead of inlining a copy. If you find a skill duplicating any block below, replace it with a one-line pointer: `> See AGENTS.md §0.{n}`.

### §0.1 Credential Masking (Security — MANDATORY)

**NEVER** log, print, or expose service account key content, `GOOGLE_APPLICATION_CREDENTIALS` path content, or any credential field value in console output, debug/error messages, or logs. Replace with `****`.

| Context | Safe | Unsafe |
|---------|------|--------|
| Console | `GOOGLE_APPLICATION_CREDENTIALS=<masked>` | `{"private_key": "-----BEGIN...` |
| Error msg | `Error: API call failed (credential omitted)` | actual SA key content |
| Log file | `[INFO] SA=***` | `SA key: {"private_key":"...` |
| Verify | `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA exists"` | `cat $GOOGLE_APPLICATION_CREDENTIALS` |
| Go SDK | `option.WithCredentialsFile(os.Getenv("..."))` | `fmt.Printf("Config: %+v", config)` / `log.Printf("%+v", ...)` |

Credential verification checks **existence only**, never echoes value. Violation → skill blocked from merge as a security incident.

### §0.2 Go JIT Bootstrap (fallback when CLI does not cover an operation)

Only run if `gcloud` lacks the operation AND Python 3.8+ is unavailable. JIT-download Go 1.24+, scripts compatible with Go 1.21+.

```bash
if ! command -v go &>/dev/null; then
  OS=$(uname -s | tr '[:upper:]' '[:lower:]'); ARCH=$(uname -m)
  [ "$ARCH" = "x86_64" ] && ARCH="amd64"; [ "$ARCH" = "aarch64" ] && ARCH="arm64"
  mkdir -p /tmp/go-runtime
  curl -fsSL "https://go.dev/dl/go1.24.0.${OS}-${ARCH}.tar.gz" | tar -xz -C /tmp/go-runtime
  export PATH="/tmp/go-runtime/go/bin:$PATH" GOPATH=/tmp/go-workspace GOCACHE=/tmp/go-cache GOMODCACHE=/tmp/go-modcache GOPROXY="https://proxy.golang.org,direct"
fi
go version
```

Then: `mkdir -p /tmp/gcp-sdk-workspace && cd $_ && go mod init sdk-script && go get cloud.google.com/go/[product]/apiv1 && go run ./main.go`. Always read creds via `os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")` — never hardcode.

### §0.3 gcloud Execution Conventions

- ALWAYS `--format=json` for machine parsing; extract fields with `jq`.
- Project via `CLOUDSDK_CORE_PROJECT` env or `gcloud config set project`; credentials via `GOOGLE_APPLICATION_CREDENTIALS`.
- Long-running ops: use `gcloud` built-in polling (returns on completion) or poll `describe` until terminal state.
- REST API is canonical for field names/enums; map to `gcloud` / SDK per operation.

---

## 1. Repo Layout

```
gcp-skills/
├── gcp-[product]-ops/   # One skill per GCP product (SKILL.md + references/ + assets/)
├── gcp-skill-generator/ # Meta-skill: scaffold new skills
├── gcp-gcl-runner-ops/  # Cross-skill GCL runner
├── docs/                # Lazy-loaded specs (GCL, logging, self-review, token strategy)
├── AGENTS.md            # This file — always-loaded
├── TODO.md              # All-skill TODO tracker
└── REQUIREMENTS.md      # Full requirements, architecture
```

Canonical skill structure: `SKILL.md` (what) + `references/` (how) + `assets/`. Full template at `gcp-skill-generator/references/gcp-skill-template.md`.

---

## 2. Content Separation (MANDATORY)

**SKILL.md = What; references/ = How.** SKILL.md holds triggers, pre-flight, variable conventions, execution *overview* (step table + link to references), NOT full scripts.

```markdown
#### Execution
Full script at [references/gcloud-execution.md](references/gcloud-execution.md)
| Step | Action | Description |
|------|--------|-------------|
| 1 | `gcloud compute instances describe` | Get instance details |
```

---

## 3. GCP CLI & SDK Conventions

| Component | Tool | Notes |
|-----------|------|-------|
| Primary CLI | `gcloud` | Most operations |
| Kubernetes | `kubectl` / `gcloud container clusters` | GKE |
| IaC | `terraform` | When IaC workflow required |
| Python SDK (primary) | `google-cloud-*` | `pip install google-cloud-[product]`; auto-reads `GOOGLE_APPLICATION_CREDENTIALS` (safe) |
| Go SDK (secondary) | `cloud.google.com/go/...` | When Python unavailable; follow §0.2 |
| REST API | `curl -H "Authorization: Bearer $(gcloud auth print-access-token)"` | Unsupported ops |

**Credential vars**: `GOOGLE_APPLICATION_CREDENTIALS` (`{{env.*}}`, never ask), `CLOUDSDK_CORE_PROJECT` (`{{env.*}}` or `gcloud config get-value project`), `CLOUDSDK_AUTH_ACCESS_TOKEN` (`gcloud auth print-access-token`). See §0.1 for masking.

---

## 4. Idempotent Provisioning

Probe → install only if missing → execute regardless. Do not install unconditionally. Log probe with DIAG/RESULT phase.

```bash
if ! command -v gsutil &>/dev/null; then sudo apt-get update && sudo apt-get install -y google-cloud-sdk; fi
gsutil cp gs://bucket/path ./local --project=$CLOUDSDK_CORE_PROJECT
```

---

## 5. Cross-Skill Composition

Inline necessary commands + document dependency in comments. Do NOT formally import/require another skill (agent may not have both loaded).

---

## 6. Control Plane vs Data Plane

| Plane | Channel | Example |
|-------|---------|---------|
| Control | `gcloud {product}` API | Create/Delete/Describe/Modify |
| Data | SDK / `gcloud compute ssh` | Query BigQuery, run SQL on Cloud SQL |

APIs can't cover data-plane → SSH + CLI client (e.g. `gcp-cloudsql-ops` → `gcp-gce-ops` ssh → mysql/psql). Serverless → `gcloud --format=json`.

---

## 7. Security Constraints

- **Never output credentials** (§0.1).
- **Passwords via env vars**: `MYSQL_PWD` / `PGPASSWORD`, not `-p<password>`. Prefer Cloud SQL Auth Proxy / IAM DB auth.
- **Delete ops**: explicit confirmation with resource identifier (Pre-flight row).
- **IAM changes**: conditional bindings or `gcloud projects get-iam-policy` dry-run preview.
- **SA key rotation**: set expiry + document schedule.

---

## 8. Developer Commands

```bash
npx markdownlint-cli2 "gcp-*/SKILL.md"          # lint
ruff check --fix gcp-*/scripts/                  # Python lint+fix
docker compose --profile dev up -d               # dev sandbox
"Generate gcp-xyz-ops for product XYZ ..."        # meta-skill
gcloud auth application-default login            # sandbox auth
```

---

## 9. Quality Gates

Every skill MUST pass 5 gates: (1) Clear Boundaries (SHOULD/SHOULD NOT + delegation, trigger <1024 chars); (2) Structured I/O (`{{env.*}}` never ask / `{{user.*}}` ask-once / `{{output.*}}` parse from API); (3) Explicit Steps (Pre-flight → Execute → Validate → Recover per op); (4) Failure Strategies (≥10 product-specific error codes, HALT vs retry); (5) Single Responsibility (one product, cross-product delegation not duplication). Plus a Well-Architected 5-pillar table (Security/Stability/Cost/Efficiency/Performance) and the P0/P1 checklist in `gcp-skill-generator/SKILL.md`.

**Token Efficiency (P0 — MANDATORY)**: every `gcp-*-ops` SKILL.md MUST include a `## Token Efficiency Guidelines (P0 — 强制)` section (TE-1..TE-8). Full TE table + audit methodology at [docs/token-efficiency-strategy.md](docs/token-efficiency-strategy.md). Summary: TE-1 API-query>static-tables · TE-2 no docstrings · TE-3 compact error tables (≤3 cols) · TE-4 centralized JSON paths · TE-5 YAML anchors · TE-6 no cross-file dup · TE-7 layer AIOps/FinOps in `references/advanced/` · TE-8 refs depth ≤2. **Non-compressible**: executable commands, error recovery, safety gates, credential rules, orchestration chains.

Full TE-1..TE-8 table (single source of truth — do NOT inline this in `gcp-*-ops/SKILL.md`; use the pointer line instead):

| Rule | Key Point | Application |
|------|-----------|-------------|
| **TE-1** API query > static table | Use `gcloud` to fetch versions/quotas, no hardcoding | Replace hardcoded machine-type/version tables with live queries |
| **TE-2** Omit unnecessary docstrings | Inline comments only, no function-level docstring | Python/Go SDK snippets use `#`/`//` inline comments |
| **TE-3** Compact error tables | 1 error code per row, ≤3 columns | Error taxonomy tables in `references/troubleshooting.md` stay compact |
| **TE-4** Centralized JSON paths | Declare at file top, don't repeat | Resource JSON paths declared once in `variables-and-conventions.md` |
| **TE-5** YAML anchors | `example-config.yaml` use `&anchor` | Reusable config blocks use anchors to eliminate duplication |
| **TE-6** Eliminate cross-file duplication | SKILL.md has full flow, references/ don't repeat | Execution flows live in SKILL.md; references/ link, don't re-narrate |
| **TE-7** Layer professional content | AIOps/FinOps in `references/advanced/`; destructive ops marked Security-Sensitive | Advanced content split out; confirmations gated explicitly |
| **TE-8** Reference depth ≤ 2 layers | `references/` nested max 2 levels; no `references/advanced/deep/` chains | ~100-500/file |

**Non-compressible**: Agent-executable commands (params, JSON paths), error recovery logic, safety gates, credential rules, cross-skill orchestration chains.

---

## 10. Post-Update Self-Review (MANDATORY)

After every skill update, run 2 rounds (R1 Structural: frontmatter/trigger/vars/token-eff; R2 Content: CLI validity/error codes/safety/link integrity/dedup/TODO sync). Full spec at [docs/post-update-self-review.md](docs/post-update-self-review.md). **Mandatory-pass items**: F6 (Token Efficiency), F8 (TODO.md sync), F9 (eval_queries.json coverage). All issues fixed one-by-one before finishing.

**TODO.md rule**: single root `TODO.md`, per-skill sections, no per-skill TODO.md. Sync on every update (✅ done / ⬜ planned).

**AGENTS.md size guard (this file ≤500 lines)**: before adding, `wc -l AGENTS.md`; <400 free, 400-500 trim-first, ≥500 forbidden-add. Trim priority: drop redundant examples → merge similars → demote detail to docs/ → delete obsolete.

---

## 11. Compound-Asset Distillation Loop (CADL)

Any substantial task (multi-step / cross-skill / review-fix loop / repo pitfall found / pre-existing FAIL attributed / user workflow preference) MUST close the loop: **Extract → Locate → Write → Gate → Reuse**. Locate: cross-repo-useful → user-level agent guide; repo-only → this file; skill-specific capability → new skill via generator. Write: executable, grep-existing-first (no dup), gate by `wc -l` (§10). Inject at SKILL.md tail: `> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。`

**Agent-agnostic constraint (MANDATORY)**: no spec/skill/template hardcodes a specific coding-agent product name or path as a dependency. Generalize (e.g. "各 agent 框架的全局 agent 指南") unless framework-specific, then mark "optional / framework-specific".

---

## 12. Generator-Critic-Loop (GCL)

Adversarial gate with three components:

- **Generator**: Executes the operation (subprocess for `gcloud` CLI, SDK fallback).
- **Hallucination Detector**: Pre-checks validity of Generator output before the Critic — blocks fabricated command flags, malformed resource identifiers, and out-of-scope mutations.
- **Critic**: Independently audits (no resource mutation, verifies factual accuracy) against the rubric.

Orchestrator controls loop. Rubric ≥5 dims (Correctness, Safety [=0 → ABORT], Idempotency, Traceability, Spec Compliance, Factual Accuracy). Levels: required (max_iter 2, destructive) / recommended (3, delete/config) / optional (5, read-only). Persist JSON trace to `./audit-results/gcl-trace-*.json` (gitignored). Full spec at [docs/gcl-spec.md](docs/gcl-spec.md).

---

## Appendix A: Product → Directory Mapping

Full mapping at [docs/gcp-product-mapping.md](docs/gcp-product-mapping.md).

---

## 13. Parallel Subagent Dispatch (MANDATORY for batch work)

When a task fans out into multiple independent subagent units (e.g. one skill per worktree, one doc per product), dispatch them **all in parallel** and start consuming results **as soon as each individual unit completes** — do NOT wait for the entire batch to finish before beginning the next batch or follow-up work.

**Rules:**
- Fire all independent `task(run_in_background=true)` calls in one message; do not serialize what can run concurrently.
- On receiving a single `<system-reminder>` for one completed unit, immediately `background_output` that unit and act on it (merge, verify, fix) — do not block on siblings still running.
- New follow-up subagents MAY be dispatched the moment a prerequisite unit lands, without waiting for the rest of its batch.
- Only serialize when a later step has a hard dependency on an earlier unit's output (e.g. a shared cross-cutting doc that other units reference must merge FIRST so their links resolve).
- Exception: if there is genuinely no pending/queued work, end the turn and wait for the ALL-COMPLETE notification.

**Anti-pattern (forbidden):** holding completed work idle while polling for a full batch to close, then starting the next batch all at once. That wastes wall-clock time with no token benefit.

---

## 14. GCL Runner 可复用工程资产（CADL）

> 本节沉淀自 `harness-optimization` sprint（2026-07-20）的工程实践，可直接复制到任何 GCL runner 项目。

### §14.1 结构化日志模板（零依赖）

在 `gcl_runner_enhanced.py` main() 的每个 phase 边界调用，14 处已验证：

```python
from gcl_logging import get_gcl_logger, log_gcl_event

runner_logger = get_gcl_logger("gcl-runner", use_cloud_logging=False)

# Phase 0: Pre-flight
log_gcl_event(runner_logger, "PRE_FLIGHT", severity="INFO", skill=args.skill,
              op=args.op, result="PRE_FLIGHT_COMPLETE", extra={"env": args.environment})

# Phase 1: Generate（每轮循环）
log_gcl_event(runner_logger, f"[ITER {i}] Generate complete", severity="INFO",
              skill=args.skill, op=args.op, result="GENERATE_SUCCESS",
              extra={"iteration": i, "exit_code": gen_trace.get("exit_code", -1),
                     "duration_ms": gen_trace.get("duration_ms", 0)})

# Phase 1: Critique（每轮循环）
log_gcl_event(runner_logger, f"[ITER {i}] Critique complete", severity="INFO",
              skill=args.skill, op=args.op, result="CRITIQUE_COMPLETE",
              extra={"iteration": i, "correctness": crit.get("correctness", 0.0),
                     "safety": crit.get("safety", 0.0)})

# Phase 2: Decide（每轮循环）
log_gcl_event(runner_logger, f"[ITER {i}] Decide: {verdict}",
              severity="WARNING" if verdict in ("SAFETY_FAIL", "MAX_ITER") else "INFO",
              skill=args.skill, op=args.op, result=f"DECIDE_{verdict}",
              extra={"iteration": i, "verdict": verdict,
                     "autonomy_ratio_preview": calculate_autonomy_ratio(...)})

# Phase 4: Report（main() 末尾）
log_gcl_event(runner_logger, f"GCL run complete: {trace.result.value}",
              severity="INFO", skill=args.skill, op=args.op,
              result=f"REPORT_{trace.result.value}",
              extra={"trace_id": trace.trace_id, "final_verdict": trace.result.value,
                     "total_iters": trace.iterations_count,
                     "autonomy_ratio": round(trace.autonomy_ratio, 3),
                     "safety_score": round(trace.safety_score, 3),
                     "latency_ms": trace.latency_ms})
```

**字段规范**：`severity` in {INFO, WARNING, ERROR}，`result` = `PHASE_VERDICT` 格式，`extra` = 任意 JSON-serializable dict。

### §14.2 Trace 自动分析（main() 末尾注入）

在 main() 循环结束后、BigQuery 上报前插入，无需新依赖：

```python
trace_dir = args.output_dir or TRACE_DIR
try:
    classifications = classify_directory(trace_dir)
    failures = [c for c in classifications if c.category.value != "SUCCESS"]
    failure_clusters = cluster_failures(classifications) if failures else []
    if failure_clusters:
        print(f"[ANALYSIS] {len(failure_clusters)} failure cluster(s):")
        for cl in failure_clusters[:5]:
            print(f"  [{cl.category.value}] {cl.label}: {cl.count}x")
except Exception as exc:
    print(f"[WARN] trace analysis skipped: {exc}", file=sys.stderr)
```

**要求**：`from trajectory_classifier import classify_directory; from failure_clusterer import cluster_failures`

### §14.3 CI Quality Gate（GitHub Actions）

`.github/workflows/gcl-quality.yml` — PR 时触发，不在 fork PR 上运行 gcloud 认证：

```yaml
name: GCL Quality Gate
on:
  pull_request:
    paths: ['gcp-*/**', 'docs/**', 'AGENTS.md', 'gcp-gcl-runner-ops/**', '.github/workflows/**']
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm install -g markdownlint-cli2 && npx markdownlint-cli2 "gcp-*/SKILL.md"
      - run: pip install ruff && ruff check gcp-gcl-runner-ops/scripts/ --select=E,F
  tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install pytest pytest-asyncio pyyaml && cd gcp-gcl-runner-ops && python3 -m pytest tests/ -q
  self-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: |
          for skill in gcp-*/SKILL.md; do
            dir=$(dirname "$skill")
            head -3 "$skill" | grep -q "^---" || { echo "[C1 FAIL] $skill"; exit 1; }
            grep -q "SHOULD Use\|SHOULD NOT Use" "$skill" || { echo "[C2 FAIL] $dir"; exit 1; }
            grep -q "Five Core Standards" "$skill" || { echo "[C3 FAIL] $dir"; exit 1; }
            grep -q "Well-Architected\|Architecture Framework" "$skill" || { echo "[C4 FAIL] $dir"; exit 1; }
            grep -q "^## Variables" "$skill" || { echo "[C5 FAIL] $dir"; exit 1; }
            if grep -q "references/rubric.md" "$skill" && [ ! -f "$dir/references/rubric.md" ]; then
              echo "[C7 FAIL] $dir"; exit 1
            fi
          done
```

### §14.4 self-review C7 增补

在 `docs/post-update-self-review.md` 的 R1 检查表末尾添加：

```markdown
| **C7** | **Rubric 存在性** | `grep -q "references/rubric.md" SKILL.md && test -f "references/rubric.md"` | Both true: SKILL.md references AND file exists | Add rubric.md link or create the file |
```

同步更新验证脚本：`for check in C1 C2 C3 C4 C5 C6 C7`。

### §14.5 AIOps 模块接入检查单

增强 runner 的 AIOps 接入验证命令：

```bash
# 验证 AIOps 模块已接入 main()（≥8 处）
grep -c "DegradationDetector\|KnowledgeQueryAPI\|AutonomyRatioCalculator\|AutonomyRatioTracker\|AutonomyRatioAlert\|classify_directory\|cluster_failures" gcl_runner_enhanced.py

# 验证结构化日志覆盖（≥14 处）
grep -c "log_gcl_event(" gcl_runner_enhanced.py

# 验证测试基线未回归
python3 -m pytest gcp-gcl-runner-ops/tests/ -q
# 必须: 614 passed, 13 skipped, 0 failed
```

### §14.6 快速验证命令集（每次提交前必跑）

```bash
# 1. 测试基线
python3 -m pytest gcp-gcl-runner-ops/tests/ -q

# 2. ruff lint（scripts）
ruff check gcp-gcl-runner-ops/scripts/ --select=E,F || true

# 3. rubric 覆盖（所有 skill）
ls gcp-*-ops/references/rubric.md 2>/dev/null | wc -l
# 期望: 24

# 4. 结构化日志密度
grep -c "log_gcl_event(" gcp-gcl-runner-ops/scripts/gcl_runner_enhanced.py
# 期望: ≥14
```
