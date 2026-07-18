# AGENTS.md Agent Pattern Analysis

> **Version:** 1.0.0
> **Date:** 2026-07-19
> **Task:** P0-3.1

---

## 1. Executive Summary

This document analyzes the agent pattern classifications in `AGENTS.md` (root) and `gcp-gcl-runner-ops/docs/AGENTS.md` (Level 3 architecture). The root AGENTS.md defines shared common blocks and conventions for all GCP skills agents, while the Level 3 AGENTS.md details the Enhanced GCL Runner (EGR) architecture.

**Verdict:** Patterns are broadly consistent but suffer from scattered definitions, one phantom component, and terminology gaps that could cause confusion during implementation.

---

## 2. Agent Patterns Found

### 2.1 Root AGENTS.md Patterns

| Pattern | Location | Definition Status |
|---------|----------|-------------------|
| Generator | §12 GCL | Defined (performs actual execution) |
| Critic | §12 GCL | Defined (independently audits, no mutation) |
| Orchestrator | §12 GCL | Defined (controls the loop) |
| Hallucination Detector | §12 GCL | Mentioned but NOT formally defined |
| Sub-Agent | gcl-rules.md | Referenced but no formal definition in AGENTS.md |
| Main Agent | gcl-rules.md | Referenced but no formal definition in AGENTS.md |

### 2.2 Level 3 AGENTS.md (gcp-gcl-runner-ops/docs/AGENTS.md) Patterns

| Pattern | Location | Definition Status |
|---------|----------|-------------------|
| GCL Runner Core | §EGR Components | Defined |
| Trace Collector | §EGR Components | Defined |
| BigQuery Writer | §EGR Components | Defined |
| Cloud Logging | §EGR Components | Defined |
| Autonomy Engine | §EGR Components | Defined |
| State Snapshot Diff | §EGR Components | Defined |

---

## 3. Inconsistencies and Ambiguities

### 3.1 [MAJOR] Hallucination Detector — Phantom Component

**Location:** Root AGENTS.md §12

> "Generator executes, Hallucination Detector pre-checks validity, Critic independently audits..."

**Problem:** "Hallucination Detector" is mentioned as a component in the GCL flow but:
- No formal definition exists anywhere in AGENTS.md
- No other section defines what it does or how it works
- The Level 3 architecture docs don't mention it at all
- It's unclear if this is a separate agent, a function within an existing agent, or a theoretical component

**Proposed Fix:** Either:
- A. Remove "Hallucination Detector" from §12 if it's not implemented
- B. Add a formal definition in §12 explaining its role and interface

### 3.2 [MAJOR] Autonomy Engine — Missing from Root AGENTS.md

**Location:** gcp-gcl-runner-ops/docs/AGENTS.md §EGR Components

**Problem:** The "Autonomy Engine" is a core EGR component (EGR-4: Auto-degrade) that tracks failures and calculates autonomy ratio, but it has no mention in the root AGENTS.md. An agent implementing GCL from the root AGENTS.md would have no knowledge of this component.

**Proposed Fix:** Add "Autonomy Engine" to §12 GCL as an optional component for Level 3+ implementations.

### 3.3 [MINOR] "Orchestrator" vs "Autonomy Engine" — Terminology Gap

**Location:** Root AGENTS.md §12 vs gcp-gcl-runner-ops/docs/AGENTS.md

**Problem:** Root AGENTS.md §12 uses "Orchestrator" to describe the loop controller. The Level 3 docs use "Autonomy Engine" for a component with broader responsibilities (tracking failures, calculating ratio, degrading autonomy). It's unclear if these are the same thing or different.

**Proposed Fix:** Clarify in §12 that "Orchestrator" is the base term for loop control, and "Autonomy Engine" is the Level 3 specialization that adds failure tracking and ratio calculation.

### 3.4 [MINOR] Sub-Agent Definition Scattered

**Location:** gcl-rules.md (referenced) vs root AGENTS.md

**Problem:** "Sub-Agent" is used throughout gcl-rules.md (Generator Sub-Agent, Critic Sub-Agents, Sub-Agent 1/2/3/4) but root AGENTS.md never formally defines what a Sub-Agent is or how it differs from a main agent.

**Proposed Fix:** Add a brief definition in §12: "Sub-Agent: A spawned agent performing a specialized subtask under Orchestrator control."

### 3.5 [MINOR] §9 Quality Gates — Pattern Language Inconsistent

**Location:** Root AGENTS.md §9

**Problem:** Quality Gates section uses "delegation" but doesn't use the formal agent pattern language (Generator/Critic/Orchestrator). This makes it harder to map quality gate concepts to the GCL pattern.

**Proposed Fix:** Align §9 language with GCL pattern names (e.g., "Critic validates", "Orchestrator gates").

---

## 4. Section-by-Section Verification

| Section | Clear? | Issues |
|---------|--------|--------|
| §0.3 gcloud Execution Conventions | ✅ | Consistent with GCP conventions |
| §2 Content Separation | ✅ | Clear SKILL.md vs references/ split |
| §3 GCP CLI & SDK Conventions | ✅ | Complete tool-to-component mapping |
| §4 Idempotent Provisioning | ✅ | Clear probe → install → execute pattern |
| §5 Cross-Skill Composition | ✅ | Clear on inlining vs importing |
| §6 Control Plane vs Data Plane | ✅ | Clear channel distinction |
| §7 Security Constraints | ✅ | Credential rules consistent with §0.1 |
| §8 Developer Commands | ✅ | Consistent with repo structure |
| §9 Quality Gates | ⚠️ MINOR | Pattern language not aligned with §12 |
| §10 Post-Update Self-Review | ✅ | Clear 2-round review process |
| §11 CADL | ✅ | Extract → Locate → Write → Gate → Reuse loop clear |
| §12 GCL | ⚠️ MAJOR | Hallucination Detector undefined; Autonomy Engine missing |

---

## 5. Proposed Fixes

### 5.1 Fix §12 — Add Autonomy Engine and Clarify Hallucination Detector

**Current text (§12):**
```markdown
## 12. Generator-Critic-Loop (GCL)

Adversarial gate: Generator executes, Hallucination Detector pre-checks validity, Critic independently audits (no resource mutation, verifies factual accuracy), Orchestrator controls loop.
```

**Proposed replacement:**
```markdown
## 12. Generator-Critic-Loop (GCL)

Adversarial gate with 4 roles:

| Role | Responsibility |
|------|---------------|
| **Generator** | Executes actual operations, produces output |
| **Critic** | Independently audits output (no resource mutation, verifies factual accuracy) |
| **Orchestrator** | Controls the GCL loop (start, iterate, terminate) |
| **Autonomy Engine** | (Level 3+) Tracks failures, calculates autonomy ratio, triggers degrade/handoff |

**Hallucination Detector:** Optional pre-check component that validates factual accuracy before Critic review. If not implemented, Critic absorbs this role.

Rubric ≥5 dims (Correctness, Safety [=0 → ABORT], Idempotency, Traceability, Spec Compliance, Factual Accuracy). Levels: required (max_iter 2, destructive) / recommended (3, delete/config) / optional (5, read-only). Persist JSON trace to `./audit-results/gcl-trace-*.json` (gitignored). Full spec at [docs/gcl-spec.md](docs/gcl-spec.md).
```

### 5.2 Fix §9 — Align Pattern Language

Add a note in §9 Quality Gates referencing the GCL pattern names for consistency.

---

## 6. Recommendations

| Priority | Action | Owner |
|----------|--------|-------|
| P0 | Define or remove "Hallucination Detector" from §12 | agents-audit-agent |
| P0 | Add "Autonomy Engine" to §12 | agents-audit-agent |
| P1 | Clarify Orchestrator vs Autonomy Engine relationship | agents-audit-agent |
| P1 | Add Sub-Agent formal definition to §12 | agents-audit-agent |
| P2 | Align §9 Quality Gates language with §12 | agents-audit-agent |

---

## 7. Files Analyzed

| File | Lines | Purpose |
|------|-------|---------|
| `/AGENTS.md` | 182 | Root agent guide (always-loaded) |
| `gcp-gcl-runner-ops/docs/AGENTS.md` | 149 | Level 3 EGR architecture |

---

*Analysis performed by agents-audit-agent as part of P0-3.1*
