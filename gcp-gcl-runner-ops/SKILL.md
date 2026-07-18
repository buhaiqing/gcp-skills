---
name: gcp-gcl-runner-ops
description: >-
  Shared skill for the Generator-Critic-Loop (GCL) adversarial quality gate.
  Use when any gcp-*-ops skill needs to run a GCL loop — pre-flight check,
  command generation, rubric-based critique, and termination decision — on a
  write/destructive operation. Other skills delegate GCL execution here rather
  than implementing inline GCL logic. Do NOT use for read-only operations, or
  for non-GCL tasks.
license: MIT
compatibility: >-
  Python 3.10+ (for scripts/gcl_runner.py), Google Cloud CLI (`gcloud`,
  Python-based), valid service account credentials, network access to GCP
  endpoints, Cloud Audit Logs API enabled (for cross-check).
metadata:
  author: gcp-skills
  version: "1.0.0"
  last_updated: "2026-06-07"
  type: shared-framework
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  environment:
    - GOOGLE_APPLICATION_CREDENTIALS
    - CLOUDSDK_CORE_PROJECT
---

> This skill follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# GCP GCL Runner — Shared Quality Gate Skill

This skill provides the **Generator-Critic-Loop (GCL)** adversarial quality gate
as defined in `AGENTS.md §11`. It is a **shared framework skill**: other `gcp-*-ops`
skills delegate their GCL execution here rather than implementing inline GCL logic.

## Trigger & Scope

| Scope | Description |
|-------|-------------|
| **SHOULD use** | Any `gcp-*-ops` skill executing a write/destructive cloud operation that requires GCL quality gate before presenting results to the user |
| **SHOULD NOT use** | Read-only operations (Describe/List/Get); operations on skills without GCL classification (`optional` / read-only skills); non-cloud tasks |

### Delegation Rules

This skill **receives** delegation from other skills. It does **not** delegate
to other skills.

| Source Skill Type | Trigger | Context Passed |
|-------------------|---------|----------------|
| All `required` / `recommended` skills | Before executing a write/destructive operation: "Delegate GCL quality gate to gcp-gcl-runner-ops" | `skill`, `op`, `command`, `user_request`, `max_iter` |
| `gcp-skill-generator` | When validating generated skill content: "Run GCL on the generated commands" | `skill`, `op`, `command` |

## Variable Convention

| Variable | Meaning | Source |
|----------|---------|--------|
| `{{env.GOOGLE_APPLICATION_CREDENTIALS}}` | Path to SA key JSON | Environment (NEVER ask user, NEVER log content) |
| `{{env.CLOUDSDK_CORE_PROJECT}}` | GCP project ID | Environment (NEVER ask user) |
| `{{env.GCP_SKILLS_ROOT}}` | Repository root | Environment or autodetected via `git rev-parse --show-toplevel` |
| `{{user.skill}}` | Target skill name (e.g. `gcp-gce-ops`) | Delegate context |
| `{{user.op}}` | Operation name (e.g. `DeleteInstance`) | Delegate context |
| `{{user.command}}` | Full CLI command to execute | Delegate context |
| `{{user.user_request}}` | Original natural-language request | Delegate context |
| `{{user.max_iter}}` | Maximum GCL iterations (default: 2) | Delegate context or interactive prompt |

## Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| `gcloud` CLI installed | `command -v gcloud` | Binary found | HALT — install `gcloud` per `gcp-skill-generator/references/execution-environment.md` |
| Python 3.10+ available | `python3 --version` | Version ≥ 3.10 | HALT — install Python 3.10+ (or use Docker `google/cloud-sdk`) |
| `gcl_runner.py` exists | `ls {{env.GCP_SKILLS_ROOT}}/gcp-gcl-runner-ops/scripts/gcl_runner.py` | File found | HALT — re-clone or check repo integrity |
| Target skill rubric exists | `ls {{env.GCP_SKILLS_ROOT}}/{{user.skill}}/references/rubric.md` | File found | HALT — rubric missing, check skill structure |
| Credentials configured | `gcloud auth application-default print-access-token --quiet` | Non-empty token | HALT — configure SA key or ADC per `.env.example` |
| Project set | `gcloud config get-value core/project` or `{{env.CLOUDSDK_CORE_PROJECT}}` | Non-empty project | HALT — `export CLOUDSDK_CORE_PROJECT=my-project` |

## Execution — CLI

```bash
# Locate the script (relative to repo root)
python3 {{env.GCP_SKILLS_ROOT}}/gcp-gcl-runner-ops/scripts/gcl_runner.py \
  --skill "{{user.skill}}" \
  --op "{{user.op}}" \
  --command "{{user.command}}" \
  --user-request "{{user.user_request}}" \
  --max-iter {{user.max_iter}}
```

### Example

```bash
python3 /path/to/gcp-skills/gcp-gcl-runner-ops/scripts/gcl_runner.py \
  --skill gcp-gce-ops \
  --op DeleteInstance \
  --command 'gcloud compute instances delete my-instance --zone=us-central1-a --quiet' \
  --user-request "Delete the instance my-instance in us-central1-a" \
  --max-iter 2
```

### Exit Codes

| Code | Status | Meaning | Action |
|:---:|---|---|---|
| 0 | `PASS` | All rubric dimensions ≥ threshold (0.5) | Done |
| 1 | `MAX_ITER` | Reached `max_iter`; best-so-far returned | Inspect trace, refine rubric |
| 2 | `SAFETY_FAIL` | Safety = 0 (destructive op not confirmed, or SA key leaked) | **ABORT**; do not retry without user re-confirmation |
| 3 | `USAGE_ERROR` | Bad CLI args, wrong product prefix, op not in rubric | Fix CLI invocation |
| 4 | `RUBRIC_ERROR` | Rubric file missing or unparseable | Check `references/rubric.md` exists and is well-formed |

## Execution — Python SDK (Alternative)

When `gcloud` CLI does not support the operation, use the Python SDK equivalent:

```bash
python3 {{env.GCP_SKILLS_ROOT}}/gcp-gcl-runner-ops/scripts/gcl_runner.py \
  --skill "{{user.skill}}" \
  --op "{{user.op}}" \
  --command 'python3 -c "from google.cloud import compute_v1; ..."' \
  --user-request "{{user.user_request}}" \
  --max-iter {{user.max_iter}}
```

## References

- [GCL Execution Reference](references/gcl-execution.md) — detailed runner usage guide
- [Integration](references/integration.md) — cross-skill integration and audit cross-check
- AGENTS.md §11 — canonical GCL spec
- `gcp-skill-generator/references/gcl-rollout-spec.md` — how to generate GCL files for a new skill

## Quality Gate (GCL)

This skill implements the GCL quality gate defined in `AGENTS.md §11`. As a **shared framework skill**, it operates at `required` level:

| Property | Value |
|----------|-------|
| Classification | `required` |
| `max_iter` | 2 |
| Most-scrutinized ops | All write/destructive operations across delegated skills |
| Rubric | `references/gcl-execution.md` (mechanical Critic) |

### Anti-Patterns Enforced

- Shared context G+C (banned)
- Critic seeing user request (banned)
- Silently downgrading Safety fail (banned)

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-06-07 | Initial GCL runner with mechanical Critic, `gcloud`/Python SDK support |

## See Also

- [`audit-results/`](../audit-results/) — gitignored; ephemeral GCL trace storage
- `gcp-skill-generator/references/gcl-orchestrator-agent.md` — custom subagent-framework agent definition (framework-specific; **deprecated** in favor of `## Delegation Rules`)