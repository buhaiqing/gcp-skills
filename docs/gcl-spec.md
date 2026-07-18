# GCL Full Specification — Generator-Critic-Loop

> **Purpose:** Canonical specification for the Generator-Critic-Loop (GCL) adversarial quality gate used across all `gcp-*-ops` skills.
> **Version:** 1.0.0
> **Last Updated:** 2026-06-07

---

## Table of Contents

1. [Overview](#1-overview)
2. [Roles](#2-roles)
3. [Rubric Dimensions](#3-rubric-dimensions)
4. [Loop Flow](#4-loop-flow)
5. [Termination Conditions](#5-termination-conditions)
6. [Trace Schema](#6-trace-schema)
7. [Prompt Templates](#7-prompt-templates)
8. [Anti-Patterns](#8-anti-patterns)
9. [Skill Classification](#9-skill-classification)
10. [Hallucination Detection Layer (H)](#10-hallucination-detection-layer-h)
11. [Rollout Roadmap](#11-rollout-roadmap)

---

## 1. Overview

GCL enforces a Generator ↔ Critic adversarial loop on every cloud operation, scored against a quantified rubric. It catches **silent destructive failures** that single-shot pre-flight checks miss.

**Core contract** is defined in `AGENTS.md §11`. This file is the detailed implementation spec.

---

## 2. Roles

| Role | Responsibility | Banned |
|------|---------------|--------|
| **Generator (G)** | Execute the cloud operation | Modify rubric, self-score |
| **Hallucination Detector (H)** | Pre-execution structural validity check | Execute API calls, mutate G's output |
| **Critic (C)** | Independently audit G's output | Call `gcloud`/SDK, mutate resources |
| **Orchestrator (O)** | Loop control, termination decision | Execute or score |

**H role** (v1.5.0+): Catches LLM hallucinations in generated commands/JSON **before** execution.

---

## 3. Rubric Dimensions

| Dimension | Weight | Meaning | Safety=0 |
|-----------|--------|---------|----------|
| **Correctness** | 1.0 | Resource name/state/config matches request | — |
| **Safety** | 1.0 | Destructive ops confirmed or protected | **Immediate ABORT** |
| **Idempotency** | 0.8 | Repeating the call has no side effects | — |
| **Traceability** | 0.8 | Output is auditable (command, params, response) | — |
| **Spec Compliance** | 0.8 | Complies with core-concepts.md constraints | — |

### GCP-Specific Extensions

| Dimension | Description |
|-----------|-------------|
| **IAM Compliance** | Minimum IAM permissions documented and enforced |
| **Credential Hygiene** | No SA key leakage, token exposure |
| **Well-Architected** | Aligned with Google Cloud Architecture Framework |

---

## 4. Loop Flow

```
[0] Pre-flight — load rubric, resolve env.* / user.*, sanitize secrets
    │
[1] H Check — validate structural correctness of generated command
    │          (flag unknown flags, malformed resources, hallucinated endpoints)
    │
[2] Generate — execute the command via subprocess, capture trace
    │
[3] Critique — re-classify output using rubric's regex hot-spots
    │
[4] Decide — apply termination rules
    │
    ├── PASS → return result
    ├── MAX_ITER → return best-so-far + unresolved issues
    ├── SAFETY_FAIL → ABORT
    └── HALLUCINATION_ABORT → ABORT + hallucination report
```

---

## 5. Termination Conditions

| Condition | Action |
|-----------|--------|
| **PASS** | All dimensions ≥ threshold → return G's result |
| **MAX_ITER** | Reached max_iter → return best-so-far + unresolved issues |
| **SAFETY_FAIL** | Safety=0 → **ABORT**, no partial result |
| **HALLUCINATION_ABORT** | H detected unresolved hallucinations → **ABORT**, return hallucination report |

---

## 6. Trace Schema

```json
{
  "version": "1.0.0",
  "trace_id": "gcl-trace-YYYYMMDD-HHMMSS-<rand6>",
  "timestamp": "ISO8601",
  "skill": "gcp-gce-ops",
  "op": "DeleteInstance",
  "iterations": [
    {
      "iteration": 0,
      "command": "gcloud compute instances delete ...",
      "stdout": "...",
      "stderr": "...",
      "exit_code": 0,
      "critique": {
        "correctness": 1.0,
        "safety": 0.0,
        "idempotency": 1.0,
        "traceability": 0.8,
        "spec_compliance": 1.0,
        "matched_regexes": ["--quiet without confirmation"]
      },
      "verdict": "SAFETY_FAIL"
    }
  ],
  "final_verdict": "SAFETY_FAIL",
  "max_iter": 2
}
```

Trace is persisted to `./audit-results/gcl-trace-*.json` (gitignored).

---

## 7. Prompt Templates

### Generator Template

```
You are the Generator. Generate the gcloud command for:
Operation: {op}
Skill: {skill}
User request: {user_request}

Hard rules (from rubric):
- {rule_1}
- {rule_2}

Output ONLY the command. No explanation.
```

### Critic Template

```
You are the Critic. Independently audit the Generator's output.

Generator's command: {command}
Generator's stdout: {stdout}
Operation: {op}

Rubric dimensions:
{dimensions}

Score each dimension 0.0-1.0. Report matched regexes.
**CRITICAL**: You MUST NOT see the original {{user.request}}.
```

### H (Hallucination Detector) Template

```
You are the Hallucination Detector. Pre-check this command for structural validity:

Command: {command}
Skill: {skill}
Operation: {op}

Flag:
1. Unknown gcloud flags not in `gcloud {product} --help`
2. Malformed resource names
3. Hallucinated endpoints or service names
4. Incorrect --format usage

Output: PASS or list of hallucination findings with fix suggestions.
```

---

## 8. Anti-Patterns (Banned)

| Anti-Pattern | Why |
|-------------|-----|
| Shared context G+C (same session) | Enables collusion; C re-uses G's reasoning |
| Subjective scoring | Must use quantified rubric |
| Unbounded loop | Always set max_iter |
| Critic seeing user request | **Rubber-stamping** — C must be blind to original intent |
| Silently downgrading on Safety fail | Safety=0 is ABORT, never soft-pass |
| Trace not persisted | Required for audit trail per §6 (Trace Schema) |
| Critic mutating resources | Read-only role |
| Trace leaking secrets | Sanitize command output before persisting |

---

## 9. Skill Classification

| Level | max_iter | Key Risk | Example Skills |
|-------|:--------:|----------|----------------|
| **required** | 2 | Data destruction / deletion | gce, gke, cloudsql, gcs, iam, kms, vpc |
| **recommended** | 3 | Configuration changes | cloudrun, cloudfunctions, monitoring, pubsub |
| **optional** | 5 | Read-only audit | billing, resourcemanager, cdn |

**Decision rule:** Any skill with a `Delete*` or `Drop*` operation MUST be classified as `required`.

---

## 10. Hallucination Detection Layer (H)

### Purpose
Validates the generated command for structural correctness **before execution**, catching:

- Unknown `gcloud` flags (e.g., `--force` where the API uses `--quiet`)
- Malformed resource identifiers (e.g., wrong zone format)
- Hallucinated service names (e.g., `gcloud sql` vs `gcloud sql instances`)
- Incorrect `--format` usage

### Integration
- H runs between Pre-flight and Generate in the loop flow
- H output feeds into the termination decision
- H findings are recorded in the trace JSON

### Threshold
- H must flag ≥ 3 hallucination types per skill's primary operations
- H must have false positive rate < 10% on valid commands

---

## 11. Rollout Roadmap

| Phase | Scope | Status |
|-------|-------|--------|
| Phase 1 | GCL spec + rubric design | ✅ Shipped 2026-06-07 |
| Phase 2 | Mechanical Critic (gcl_runner.py), subprocess Generator, JSON trace | ✅ Shipped 2026-06-07 |
| Phase 3 | LLM-based Critic, Cloud Audit Logs cross-check | 🔜 Planned |
| Phase 4 | Cloud Monitoring alarm on SAFETY_FAIL rate | 🔜 Planned |
| Phase 5 | Auto-rollout to `recommended` skills | 🔜 Planned |

### References

- `AGENTS.md §11` — canonical GCL spec (summary level)
- `gcp-gcl-runner-ops/SKILL.md` — shared runner skill
- `gcp-skill-generator/references/gcl-rollout-spec.md` — how to generate GCL files for new skills