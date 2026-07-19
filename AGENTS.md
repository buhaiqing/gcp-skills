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
