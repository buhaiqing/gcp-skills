---
name: gcl-rollout-spec
description: >-
  Specification for rolling out the Generator-Critic-Loop (GCL) adversarial
  quality gate (defined in `AGENTS.md` §12) into a generated or updated
  `gcp-*-ops` skill. Explains the rubric + prompt-template + SKILL.md
  Quality-Gate-section pattern, per-skill `required` / `recommended` /
  `optional` classification, per-op safety sub-rule format, regex hot-spot
  detection list, and cross-skill delegation.
license: MIT
metadata:
  type: meta-reference
  applies_to: gcp-skill-generator
  author: gcp-skills
  version: "1.0.0"
  last_updated: "2026-06-07"
  parent: ../../AGENTS.md
  related:
    - gcp-skill-template.md
    - prompt-library.md
    - governance-and-adversarial-review.md
---

# GCL Rollout Specification (Generator-Critic-Loop)

> **Authoritative source for the GCL contract is [`AGENTS.md` §12](../../AGENTS.md#12-generator-critic-loop-gcl--adversarial-quality-gate).**
> This reference explains **how to implement** the contract in a generated skill.

---

## 1. Why GCL Is Mandatory

GCL is the adversarial quality gate that catches **silent destructive failures**:

- A `Delete VPC` that passes pre-flight but has active GCE / Cloud SQL / GKE resources
- A `DROP DATABASE` that has a backup but the backup is 6 months old
- A `gcloud compute instances delete --quiet` that bypasses user confirmation

GCL separates the **Generator** from the **Critic** (rubber-stamping prevention).

---

## 2. Classify the Skill

| Side-effect level | Classification | Default `max_iter` |
|---|---|---|
| **High** (delete/stop/IAM/DDL/drop) | `required` | 2 |
| **Medium** (modify with dependency) | `recommended` | 3 |
| **Low** (read-only audit/monitoring) | `optional` | 5 |

**Decision rule:** If the skill has a `Delete*` or `Drop*` operation, it MUST be `required`.

### Per-Skill Defaults (GCP)

| Level | max_iter | Skill Candidates |
|-------|:--------:|------------------|
| **required** | 2 | gce, gke, cloudsql, gcs, iam, kms, vpc, dns, lb, memorystore |
| **recommended** | 3 | cloudrun, cloudfunctions, monitoring, pubsub, bigquery |
| **optional** | 5 | billing, resourcemanager, cdn, bigtable |

---

## 3. Implementation Steps

### Step 1: Create `references/rubric.md`

5 core dimensions + 3 GCP-specific extensions:

| Dimension | Meaning | When Safety=0 |
|-----------|---------|---------------|
| **Correctness** | Resource name/state/config matches request | — |
| **Safety** | Destructive operations confirmed or protected | **Immediate ABORT** |
| **Idempotency** | Repeating the call has no side effects | — |
| **Traceability** | Output is auditable (command, params, response) | — |
| **Spec Compliance** | Complies with core-concepts.md constraints | — |

### Step 2: Create `references/prompt-templates.md`

- **Generator template**: Hard rules list referencing rubric's per-op sub-rules
- **Critic template**: Independent re-query pattern; **MUST NOT see `{{user.request}}`**

### Step 3: Add GCL Section to SKILL.md

Insert between `## Operational Best Practices` and `## See Also — Meta-Skill Rules`.

---

## 4. Anti-Patterns (Banned)

- Shared context G+C (same session)
- Subjective scoring (no quantified rubric)
- Unbounded loop (always set max_iter)
- Critic seeing user request (rubber-stamping)
- Silently downgrading on Safety fail
- Trace not persisted
- Critic mutating resources
- Trace leaking secrets