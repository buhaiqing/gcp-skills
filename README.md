# GCP Skills

> Agent-parsable operational runbooks for Google Cloud Platform — structured, AI-agent-executable skills for cloud resource management.

[**中文版**](README_CN.md)

---

## Overview

`gcp-skills` is a **Skills Farm** — a collection of production-grade operational runbooks designed for AI agents to manage Google Cloud resources. Each skill is a self-contained directory that tells the agent **when** to act, **what** to check before acting, **how** to execute via `gcloud` CLI or SDK, and **how** to recover from failures.

Built on the [Agent Skill OpenSpec](https://agentskills.io/specification) and following the guidelines in [`AGENTS.md`](AGENTS.md), this repository enforces strict quality gates including token efficiency, credential safety, and the **Generator-Critic-Loop (GCL)** adversarial quality gate.

---

## Repository Structure

```
gcp-skills/
├── gcp-[product]-ops/          # One directory per GCP product skill
│   ├── SKILL.md                # Entry point: triggers, variables, execution overview
│   ├── references/             # Depth: commands, error codes, monitoring, assessment
│   │   ├── core-concepts.md
│   │   ├── api-sdk-usage.md
│   │   ├── gcloud-usage.md
│   │   ├── troubleshooting.md
│   │   ├── monitoring.md
│   │   ├── integration.md
│   │   ├── well-architected-assessment.md
│   │   ├── idempotency-checklist.md
│   │   ├── rubric.md               # GCL scoring rubric (required/recommended skills)
│   │   └── prompt-templates.md     # GCL generator + critic templates (required/recommended)
│   └── assets/
│       ├── example-config.yaml
│       └── eval_queries.json
├── gcp-skill-generator/         # Meta-skill: scaffolds new skills from GCP API specs
│   └── references/
│       ├── gcp-skill-template.md
│       ├── gcl-rollout-spec.md
│       └── ...
├── gcp-gcl-runner-ops/          # Cross-skill GCL execution runner (Phase 2)
│   └── scripts/
│       ├── gcl_runner.py
│       ├── gcl_runner_test.py
│       └── README.md
├── AGENTS.md                    # Master specification — read this first
├── REQUIREMENTS.md              # Full requirements and architecture
├── README.md                    # This file
├── README_CN.md                 # Chinese version
├── .env.example
├── docker-compose.yaml
└── Dockerfile
```

### Canonical Skill Directory

```
gcp-[product]-ops/
├── SKILL.md
├── references/
│   ├── core-concepts.md
│   ├── api-sdk-usage.md
│   ├── gcloud-usage.md              # Omit for sdk-only skills
│   ├── troubleshooting.md
│   ├── integration.md
│   ├── monitoring.md
│   ├── well-architected-assessment.md  # MANDATORY
│   ├── idempotency-checklist.md
│   ├── rubric.md                       # GCL: required/recommended
│   └── prompt-templates.md            # GCL: required/recommended
├── assets/
│   ├── example-config.yaml
│   └── eval_queries.json
└── scripts/                            # Optional
```

---

## Available Skills

| Skill Directory | Product | Status |
|----------------|---------|--------|
| [`gcp-gce-ops`](gcp-gce-ops/SKILL.md) | Compute Engine (VM instances, disks, snapshots, MIGs) | ✅ Released |
| [`gcp-lb-ops`](gcp-lb-ops/SKILL.md) | Cloud Load Balancing (forwarding rules, backend services, URL maps, NEGs, SSL certs) | ✅ Released |
| [`gcp-logging-ops`](gcp-logging-ops/SKILL.md) | Cloud Logging (log buckets, views, sinks, metrics, exclusions) | ✅ Released |
| [`gcp-kms-ops`](gcp-kms-ops/SKILL.md) | Cloud KMS (key rings, crypto keys, versions, encrypt/decrypt) | ✅ Released |
| [`gcp-memorystore-ops`](gcp-memorystore-ops/SKILL.md) | Memorystore for Redis (instances, scaling, export/import, failover) | ✅ Released |
| [`gcp-cloudbuild-ops`](gcp-cloudbuild-ops/SKILL.md) | Cloud Build (builds, triggers, private worker pools, diagnostics) | ✅ Released |
| [`gcp-billing-ops`](gcp-billing-ops/SKILL.md) | Cloud Billing (billing accounts, budgets, exports, project links, pricing) | ✅ Released |
| `gcp-vpc-ops` | VPC (networks, subnets, firewall rules, VPN, Cloud NAT) | In development |
| `gcp-gke-ops` | Google Kubernetes Engine | Planned |
| `gcp-cloudsql-ops` | Cloud SQL | Planned |
| `gcp-gcs-ops` | Cloud Storage | Planned |
| `gcp-iam-ops` | IAM | Planned |
| `gcp-dns-ops` | Cloud DNS | Planned |

See [AGENTS.md Appendix A](AGENTS.md#appendix-a-gcp-product--directory-mapping-planned) for the full roadmap.

---

## Quick Start

### Prerequisites

```bash
# 1. gcloud CLI
gcloud version

# 2. Service account key
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# 3. Set project
export CLOUDSDK_CORE_PROJECT=my-gcp-project

# 4. Verify
gcloud auth application-default print-access-token --quiet &>/dev/null && echo "✅ Auth OK"
```

### Using a Skill

Skills are loaded automatically by compatible AI agent runtimes (Claude Code, Cursor, Harness AI Agent, etc.). The agent reads `SKILL.md` frontmatter `description` to match user requests.

**Example:**
```
User: "Create a VM instance in us-central1-a"
Agent loads gcp-gce-ops → executes gcloud compute instances create with pre-flight checks → validates → reports result
```

### Running Eval Queries

Each skill ships with `assets/eval_queries.json` — ~20 test queries to verify trigger accuracy:

```bash
# Example evaluation (manual)
cat gcp-gce-ops/assets/eval_queries.json | python3 -m json.tool
```

---

## Quality Gates

### Five Core Standards

| # | Standard | Description |
|---|----------|-------------|
| 1 | **Clear Boundaries** | Precise SHOULD/SHOULD NOT triggers with delegation rules |
| 2 | **Structured I/O** | `{{env.*}}` (never ask), `{{user.*}}` (ask once), `{{output.*}}` (from API) |
| 3 | **Explicit Steps** | Pre-flight → Execute → Validate → Recover for every operation |
| 4 | **Failure Strategies** | ≥10 product-specific error codes; HALT vs retry separation |
| 5 | **Single Responsibility** | One product, one resource model; cross-product delegation, not duplication |

### Generator-Critic-Loop (GCL)

The **GCL** adversarial quality gate enforces runtime execution quality. Each destructive operation is scored against a quantified rubric by an independent Critic, preventing silent failures.

| Level | max_iter | Key Risk |
|-------|:--------:|----------|
| **required** | 2 | Data destruction, irreversible ops, production traffic impact |
| **recommended** | 3 | Resource deletion, configuration changes |
| **optional** | 5 | Read-only audit, diagnostics |

### Post-Update Self-Review

Every skill update triggers a mandatory 2-round self-review:
- **R1**: Structural compliance (frontmatter, triggers, variables, token efficiency)
- **R2**: Content validation (link integrity, deduplication, error codes, TODO.md sync)

See [`AGENTS.md §11`](AGENTS.md#11-post-update-self-review-mandatory) and [`docs/post-update-self-review.md`](docs/post-update-self-review.md).

---

## Token Efficiency

Skills follow 8 rules (TE-1 to TE-8) to minimize token consumption while preserving agent executability:

| Rule | Key Point | Savings |
|------|-----------|---------|
| **TE-1** | API queries > static tables | ~200-500/file |
| **TE-2** | Omit unnecessary docstrings | ~100-200/func |
| **TE-3** | Compact error tables (≤3 columns) | ~300-500/file |
| **TE-4** | Centralized JSON paths | ~50-100/file |
| **TE-5** | YAML anchors | ~200-400/file |
| **TE-6** | Eliminate cross-file duplication | Varies |
| **TE-7** | Layer professional content in `advanced/` | ~3,000-8,000/file |
| **TE-8** | Reference depth ≤ 2 layers | ~100-500/file |

---

## Development

### Creating a New Skill

Use the [`gcp-skill-generator`](gcp-skill-generator/SKILL.md) meta-skill:

```
"Generate gcp-gke-ops for Google Kubernetes Engine with operations: create, describe, modify, delete"
```

The generator scaffolds the directory, populates all reference files, and validates against the P0/P1 checklist.

### Quality Checklist (P0 — Must Pass)

- [ ] Trigger & Scope with SHOULD/SHOULD NOT
- [ ] Variables: `{{env.*}}` vs `{{user.*}}` — no secret literals
- [ ] Pre-flight → Execute → Validate → Recover for each operation
- [ ] Error taxonomy with ≥10 codes, HALT vs retry
- [ ] Safety gates for all destructive operations
- [ ] Token Efficiency (TE-1 to TE-8) applied
- [ ] Self-healing framework with ≥3 recovery paths
- [ ] GCL rubric + prompt templates (when `required`/`recommended`)
- [ ] Well-Architected Assessment (5 pillars)
- [ ] Eval queries (≥20) for trigger accuracy
- [ ] All internal links valid

---

## Diagnostic Logging Standard

All remote scripts use the structured log format:

```
[HH:MM:SS] [PHASE] key=value
```

Phases: `DIAG` / `INSTALL` / `EXEC` / `RESULT` / `WARN` / `ERROR` / `SUMMARY`

Full spec at [`docs/diagnostic-logging-standard.md`](docs/diagnostic-logging-standard.md).

---

## Security

- **Never output credentials**: Replace access tokens and SA keys in logs with `****`
- **Passwords via env vars**: Use `MYSQL_PWD` / `PGPASSWORD` instead of `-p<password>`
- **Delete operations**: Must obtain explicit confirmation with resource identifier
- **IAM dry-run**: Preview IAM policy changes before applying
- **Python SDK**: Credentials auto-read via `GOOGLE_APPLICATION_CREDENTIALS` — safe by default
- **Go SDK**: Prohibit `fmt.Println(config)` and `log.Printf("%+v", ...)` — these can leak SA keys

---

## Related Projects

- [Google Cloud SDK & gcloud CLI](https://cloud.google.com/sdk/gcloud)
- [Google Cloud Client Libraries (Go)](https://pkg.go.dev/cloud.google.com/go)
- [Agent Skills Open Specification](https://agentskills.io/specification)
- [Google Cloud Architecture Framework](https://cloud.google.com/architecture/framework)

---

## License

MIT License — see [LICENSE](LICENSE) file.

---

## Contributing

1. Read [`AGENTS.md`](AGENTS.md) — this is the single source of truth for all conventions
2. Read the full architecture specification in the repo documentation
3. Use [`gcp-skill-generator`](gcp-skill-generator/SKILL.md) to scaffold new skills
4. Run the 2-round self-review after every update
5. Pass the GCL adversarial review before merge

---

> **Questions?** Open an issue or refer to the detailed specs in [`docs/`](docs/).