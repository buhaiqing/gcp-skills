# GCP Skills — Agent Guide

This repository is a Skills Farm for Google Cloud Platform operations — structured, AI-agent-parseable runbooks for cloud resource management.

Every section here is high-signal: agents must follow these patterns or they will produce broken or inconsistent skills.

---

## 1. Repo Layout

```
gcp-skills/
├── gcp-[product]-ops/                # One directory per GCP product
│   ├── SKILL.md                      # What to do (triggers, pre-flight, variables, execution overview)
│   ├── references/                   # How to do (detailed CLI/SDK scripts, troubleshooting, monitoring)
│   │   ├── rubric.md                 # MANDATORY (per skill) when skill is GCL `required`/`recommended` — see §12.3
│   │   └── prompt-templates.md       # MANDATORY (per skill) when skill is GCL `required`/`recommended` — see §12.7
│   ├── assets/                       # Example configs, eval queries
│   │   └── code-snippets/            # SDK-only skills: standalone `python3 run`-able scripts (Go as secondary)
│   └── scripts/                      # (rare — only for complex multi-step operations)
├── gcp-skill-generator/              # Meta-skill: generate new skills from GCP API specs / gcloud reference
│   └── references/
│       ├── gcl-rollout-spec.md       # §12.11 Phase 2 — how to generate GCL files for a new skill
│       └── gcl-orchestrator-agent.md # §12.11 Phase 2 — pi-subagents agent wrapping gcl_runner.py
├── gcp-gcl-runner-ops/               # §12.11 Phase 2 — cross-skill GCL runner (shared skill)
│   └── scripts/
│       ├── gcl_runner.py             # Python 3.10+ standalone CLI; zero external deps
│       ├── gcl_runner_test.py        # unittest suite
│       └── README.md                 # usage guide
├── audit-results/                    # §12.6 — GCL trace storage (GITIGNORED; ephemeral)
├── gcp-jit-setup.sh                  # JIT Python/Go SDK bootstrap (single script)
├── REQUIREMENTS.md                   # Full requirements, architecture, technical specs
├── .env.example                      # Template for GOOGLE_APPLICATION_CREDENTIALS / CLOUDSDK_AUTH vars
├── docker-compose.yaml               # Docker sandbox profiles (dev/runtime/interactive)
└── Dockerfile                        # Go 1.24 + Python 3.10 base image
```

**Canonical skill directory structure** (from `gcp-skill-generator`):

```
gcp-[product]-ops/
├── SKILL.md
├── references/
│   ├── core-concepts.md                    # Architecture, limits, quotas, dependencies
│   ├── api-sdk-usage.md                    # Operation map, request/response, pagination
│   ├── gcloud-usage.md                     # `gcloud` CLI command map (omit for sdk-only)
│   ├── troubleshooting.md                  # Error codes (≥10), diagnostics, recovery
│   ├── integration.md                      # Go bootstrap, env vars, credential rules
│   ├── monitoring.md                       # Cloud Monitoring metrics, dashboards, alerts (if applicable)
│   ├── well-architected-assessment.md      # MANDATORY — five-pillar assessment (Google Cloud Architecture Framework)
│   ├── idempotency-checklist.md            # If retries/automation required
│   └── advanced/                           # Optional — lazy-loaded by Advanced Analytics section
│       ├── aiops-*.md                      #   AIOps: anomaly detection, prediction, auto-remediation
│       ├── finops-*.md                     #   FinOps: cost analysis, optimization
│       └── sql-execution.md                #   Security-Sensitive: SQL file execution (requires user confirmation)
├── assets/
│   ├── example-config.yaml
│   └── eval_queries.json                   # MANDATORY — trigger accuracy eval queries
└── scripts/                                # Optional — only for complex multi-step operations
```

**`advanced/` linking rule**: Files in `advanced/` referencing sibling files in `references/` MUST use `../` relative paths (e.g. `[gcloud Usage](../gcloud-usage.md)`).

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

## 3. Operation Design Pattern

Every operation MUST include these sections (in order):

### Pre-flight Checks
```markdown
| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| {precondition} | {verification command} | {normal value} | HALT — {human action} |
```

### Variable Convention
```markdown
| Variable | Meaning | Source |
|----------|---------|--------|
| `{{user.xxx}}` | User input | Ask once, reuse |
| `{{env.xxx}}` | Environment variable | NEVER ask user, HALT if missing |
| `{{output.xxx}}` | Previous step output | Parse from API response |
```

### Execution → Post-execution Validation → Failure Recovery

Every CLI script MUST include **structured diagnostic logs** (format at [Diagnostic Logging Standard](docs/diagnostic-logging-standard.md)).

All remote scripts use `[HH:MM:SS] [PHASE] key=value` format with phases `DIAG`/`INSTALL`/`EXEC`/`RESULT`/`WARN`/`ERROR`/`SUMMARY`. Errors use `[ERROR] TYPE={category} FIX={action}`. Full spec at [docs/diagnostic-logging-standard.md](docs/diagnostic-logging-standard.md).

---

## 4. GCP CLI & SDK Conventions

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

## 5. Idempotent Provisioning Pattern

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

## 6. Cross-Skill Composition

When a Skill depends on another Skill's capabilities (e.g. `gcp-gce-ops` needs `gcp-gke-ops` to describe workload identity):

**Recommended**: Inline the necessary commands in SKILL.md, document the dependency in comments.

```markdown
# Execution — CLI  (uses gcloud compute ssh; see gcp-gce-ops for advanced usage)
gcloud compute ssh instance-name --zone=us-central1-a --command="..."
```

**Not recommended**: Formal import/require of another skill (the agent may not have both loaded). Inline is the more reliable pattern.

---

## 7. Control Plane vs Data Plane

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

## 8. Security Constraints

- **Never output credentials**: Replace access tokens, `GOOGLE_APPLICATION_CREDENTIALS` values, and service account key content in logs with `****`. Python SDK auto-reads credentials from env var (safe). Go SDK scripts' `config` structs, `fmt.Println(config)`, and `log.Printf("%+v", ...)` can all leak credentials — prohibit such output.
- **Pass passwords via environment variables**: Use `MYSQL_PWD` / `PGPASSWORD` environment variables instead of `-p<password>` to avoid exposure in `ps aux` or command history. For Cloud SQL, prefer Cloud SQL Auth Proxy or IAM database authentication.
- **Delete operations MUST obtain explicit confirmation**: Include a confirmation row in the Pre-flight Checks table requiring the user to explicitly provide a resource identifier.
- **IAM policy changes MUST use conditional bindings or dry-run**: Use `gcloud projects get-iam-policy` preview before applying policy changes.
- **Service account key rotation**: When creating new keys, always set an expiry and document the rotation schedule.

---

## 9. Quick Reference — Developer Commands

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

## 10. Quality Gates

Every Skill MUST pass these five quality gates:

1. **Clear Boundaries**: SHOULD/SHOULD NOT triggers with delegation rules; trigger description optimized per agentskills.io guidelines (< 1024 chars)
2. **Structured I/O**: `{{env.*}}` (never ask user), `{{user.*}}` (ask once reuse), `{{output.*}}` (parse from API responses)
3. **Explicit Steps**: Pre-flight → Execute → Validate → Recover for **each** critical operation
4. **Failure Strategies**: Error taxonomy (≥10 product-specific codes), HALT vs retry logic, credential vs quota vs business error separation
5. **Single Responsibility**: One product, one primary resource; cross-product delegation documented, not duplicated

Additionally, every skill MUST include a **Well-Architected Framework** table (five pillars: Security, Stability, Cost, Efficiency, Performance — mapped to the Google Cloud Architecture Framework) and pass the **P0/P1 checklist** defined in `gcp-skill-generator/SKILL.md`.

### 10.1 Token Efficiency Requirements (P0 — MANDATORY)

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

> **Application-level optimization**: AGENTS.md's own always-loaded optimization strategy (TE-A/TE-B/TE-C) is documented at [docs/token-efficiency-strategy.md](docs/token-efficiency-strategy.md) — includes full audit methodology and checklist for scanning existing skills.

---

## 11. Post-Update Self-Review (MANDATORY)

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

### 11.1 TODO.md 维护规范

> **规则**: 所有 skill 的待办事项统一在项目根目录 `TODO.md` 中维护，各 skill 目录下不再保留独立 TODO.md。

| 规范 | 说明 |
|------|------|
| **统一位置** | `TODO.md` 位于仓库根目录，按 skill 分节 (`## gcp-xxx-ops`) |
| **同步更新** | 每次新增/修改功能，必须同步更新根 `TODO.md`：完成的标 `✅`，计划中标 `⬜` |
| **禁止重复** | 各 skill 子目录下不保留独立 `TODO.md`，避免多处维护导致不一致 |
| **F8 校验** | 自审 F8 检查项以根 `TODO.md` 为准 |

Any issue found → fix one by one → all must pass before finishing.

---

## Key References

| Document | Description |
|----------|-------------|
| `README.md` | Project overview, CLI setup, credential configuration |
| `REQUIREMENTS.md` | Skill requirements, architecture, technical specs |
| `TODO.md` | **All-skill TODO tracker** — unified tracking across all skills, synced on every update |
| `gcp-skill-generator/SKILL.md` | **Meta Skill generator** — full workflow, P0/P1 checklist, Token Efficiency rules |
| `gcp-skill-generator/references/governance-and-adversarial-review.md` | Governance & adversarial review — 24+ pre-merge security/resilience/UX scenarios |
| `gcp-skill-generator/references/gcp-skill-template.md` | Canonical SKILL.md template |
| `gcp-skill-generator/references/aiops-best-practices.md` | Multi-round self-review & critical reflection for fault diagnosis |
| `gcp-skill-generator/references/execution-environment.md` | CLI installation (`gcloud` SDK), Go JIT bootstrap, credential configuration |
| `gcp-skill-generator/references/user-experience-spec.md` | UX compliance requirements for all skills |
| [`docs/gcl-spec.md`](docs/gcl-spec.md) | **GCL full spec** — roles, rubric, loop flow, trace schema, prompt templates, anti-patterns, rollout roadmap, skill classification table |
| [`docs/post-update-self-review.md`](docs/post-update-self-review.md) | **Post-update self-review spec** — check tables, verification scripts, dedup procedures |
| [`docs/diagnostic-logging-standard.md`](docs/diagnostic-logging-standard.md) | **Diagnostic logging standard** — log format, phase prefixes, error types, exit codes |
| [`docs/token-efficiency-strategy.md`](docs/token-efficiency-strategy.md) | **Token efficiency optimization strategy** — always-loaded vs lazy-loaded methodology, audit checklist, use cases |
| `CLAUDE.md` | Entry point (content: `@AGENTS.md`) |

> **When specs conflict, `gcp-skill-generator/SKILL.md` and its `references/` are the authoritative source.** AGENTS.md is a summary of these specs, not a replacement.

---

## 12. Generator-Critic-Loop (GCL) — Adversarial Quality Gate

> **Full spec**: [`docs/gcl-spec.md`](docs/gcl-spec.md)

**Core concept**: Enforce a Generator ↔ Critic adversarial loop on every cloud operation, scored against a quantified rubric. Complements [Post-Update Self-Review](docs/post-update-self-review.md) — §11 reviews skill authoring quality, §12 reviews runtime execution quality.

### Roles

| Role | Responsibility | Banned |
|------|---------------|--------|
| **Generator (G)** | Execute the cloud operation | Modify rubric, self-score |
| **Hallucination Detector (H)** | Pre-execution structural validity check | Execute API calls, mutate G's output |
| **Critic (C)** | Independently audit G's output; verify factual accuracy and freshness | Call `gcloud`/SDK, mutate resources |
| **Orchestrator (O)** | Loop control, termination decision | Execute or score |

> **H role**: Added in GCL v1.5.0 (Phase 6). Catches LLM hallucinations in generated commands/JSON **before** execution.
> Full spec at [`docs/gcl-spec.md#14-hallucination-detection-layer-h`](docs/gcl-spec.md#14-hallucination-detection-layer-h).

### Rubric Dimensions (≥5)

| Dimension | Meaning | When Safety=0 |
|-----------|---------|---------------|
| **Correctness** | Resource ID/state/config matches request | — |
| **Safety** | Destructive operations confirmed or protected | **Immediate ABORT** |
| **Idempotency** | Repeating the call has no side effects | — |
| **Traceability** | Output is auditable (command, params, response) | — |
| **Spec Compliance** | Complies with core-concepts.md constraints | — |
| **Factual Accuracy** | Content is complete, up-to-date, and truthful; stale or inaccurate info corrected; uncertain items escalated to human review | Uncertain → HALT and request human review |

### Termination Conditions (first match wins)

| Condition | Action |
|-----------|--------|
| **PASS** | All dimensions pass → return G's result |
| **MAX_ITER** | Reached max_iter → return best-so-far + unresolved issues |
| **SAFETY_FAIL** | Safety=0 → **ABORT**, no partial result |
| **HALLUCINATION_ABORT** | H detected unresolved hallucinations → **ABORT**, return hallucination report (since v1.5.0) |

### Skill Classification (GCL Level + max_iter)

Full 30+ skill table at [docs/gcl-spec.md §8 Per-Skill Defaults](docs/gcl-spec.md#8-per-skill-defaults):

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

| GCP Product | Directory | Operations |
|-------------|-----------|------------|
| Compute Engine | `gcp-gce-ops` | VM lifecycle, disks, snapshots, instance groups |
| Google Kubernetes Engine | `gcp-gke-ops` | Cluster lifecycle, node pools, workloads, IAM |
| Cloud SQL | `gcp-cloudsql-ops` | MySQL/PostgreSQL/SQL Server instances, backups |
| Cloud Storage | `gcp-gcs-ops` | Buckets, objects, lifecycle policies, IAM |
| Cloud Run | `gcp-cloudrun-ops` | Services, revisions, traffic splitting |
| Cloud Functions | `gcp-cloudfunctions-ops` | Functions, triggers, source repos |
| Cloud Build | `gcp-cloudbuild-ops` | Triggers, builds, artifacts |
| Cloud Monitoring | `gcp-monitoring-ops` | Metrics, dashboards, alert policies |
| Cloud Logging | `gcp-logging-ops` | Log buckets, views, log-based metrics |
| Cloud IAM | `gcp-iam-ops` | Roles, policies, service accounts |
| Cloud VPC | `gcp-vpc-ops` | Networks, subnets, firewall rules, VPN |
| Cloud DNS | `gcp-dns-ops` | Zones, records, policies |
| Cloud Load Balancing | `gcp-lb-ops` | Forwarding rules, backend services, health checks |
| Cloud CDN | `gcp-cdn-ops` | Origins, cache policies |
| Cloud Pub/Sub | `gcp-pubsub-ops` | Topics, subscriptions, schemas |
| Cloud BigQuery | `gcp-bigquery-ops` | Datasets, tables, queries, jobs |
| Cloud Spanner | `gcp-spanner-ops` | Instances, databases, backups |
| Cloud Bigtable | `gcp-bigtable-ops` | Instances, clusters, tables |
| Cloud Memorystore (Redis) | `gcp-memorystore-ops` | Redis/Memcached instances |
| Cloud Filestore | `gcp-filestore-ops` | Fileshares, backups |
| Cloud KMS | `gcp-kms-ops` | Key rings, keys, versions |
| Cloud Secret Manager | `gcp-secretmanager-ops` | Secrets, versions, IAM |
| Cloud Deployment Manager | `gcp-deployment-ops` | Deployments, templates |
| Cloud Resource Manager | `gcp-resourcemanager-ops` | Projects, folders, organizations |
| Cloud Billing | `gcp-billing-ops` | Budgets, exports, cost analysis |

For each planned skill, a corresponding `gcp-[product]-ops/` directory should be created following the canonical structure above.