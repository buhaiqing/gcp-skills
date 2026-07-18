# Skill Trigger Audit Report

> **Task:** P0-3.2 Skill Trigger 条件标准化
> **Date:** 2026-07-19
> **Scope:** All 28 `gcp-*-ops` SKILL.md files
> **Status:** Complete

---

## 1. Summary Table

| # | Skill | Section Header | Subsection Header | Keywords Line | SHOULD NOT | Delegation |
|---|-------|---------------|-------------------|--------------|------------|------------|
| 1 | gcp-gcs-ops | `## Trigger & Scope` | `### SHOULD Use When` | Inline in bullets | Yes | Yes |
| 2 | gcp-cloudsql-ops | `## Trigger & Scope (Agent-Readable)` | `### SHOULD Use When` | Separate line | Yes | Yes |
| 3 | gcp-iam-ops | `## Trigger & Scope` | `### SHOULD Use When` | Inline at end | Yes | Yes |
| 4 | gcp-cloudrun-ops | `## Trigger & Scope (Agent-Readable)` | `### SHOULD Use This Skill When` | Separate bullet | Yes | Yes |
| 5 | gcp-bigquery-ops | `## Trigger & Scope` | `### SHOULD Use When` | Inline | Yes | Yes |
| 6 | gcp-pubsub-ops | `## Trigger & Scope` | `### SHOULD Use When` | Inline | Yes | Yes |
| 7 | gcp-dns-ops | `## Trigger & Scope (Agent-Readable)` | `### SHOULD Use This Skill When` | Inline in bullets | Yes | Yes |
| 8 | gcp-kms-ops | `## Trigger & Scope (Agent-Readable)` | `### SHOULD Use This Skill When` | Inline in bullets | Yes | Yes |
| 9 | gcp-memorystore-ops | `## Trigger & Scope (Agent-Readable)` | `### SHOULD Use This Skill When` | Inline in bullets | Yes | Yes |
| 10 | gcp-secretmanager-ops | `## Trigger & Scope (Agent-Readable)` | `### SHOULD Use This Skill When` | Inline in bullets | Yes | Yes |
| 11 | gcp-filestore-ops | `## Trigger & Scope (Agent-Readable)` | `### SHOULD Use This Skill When` | Inline in last bullet | Yes | Yes |
| 12 | gcp-cdn-ops | `## Trigger & Scope (Agent-Readable)` | `### SHOULD Use This Skill When` | Inline in last bullet | Yes | Yes |
| 13 | gcp-billing-ops | `## Trigger & Scope (Agent-Readable)` | `### SHOULD Use This Skill When` | **Missing** | Yes | Yes |
| 14 | gcp-cloudbuild-ops | `## Trigger & Scope (Agent-Readable)` | `### SHOULD Use This Skill When` | **Missing** | Yes | Yes |
| 15 | gcp-composer-ops | `## Trigger & Scope (Agent-Readable)` | `### SHOULD Use This Skill When` | **Missing** | Yes | Yes |
| 16 | gcp-gke-ops | `## Trigger & Scope (Agent-Readable)` | `### SHOULD Use This Skill When` | Inline in last bullet | Yes | Yes |
| 17 | gcp-securitycenter-ops | `## Trigger & Scope (Agent-Readable)` | `### SHOULD Use This Skill When` | **Missing** | Yes | Yes |
| 18 | gcp-terraform-ops | `## Trigger & Scope (Agent-Readable)` | `### SHOULD Use This Skill When` | **Missing** | Yes | Yes |
| 19 | gcp-vpc-ops | `## Trigger & Scope (Agent-Readable)` | `### SHOULD Use This Skill When` | Inline in last bullet | Yes | Yes |
| 20 | gcp-logging-ops | `## Trigger & Scope (Agent-Readable)` | `### SHOULD Use This Skill When` | Inline in last bullet | Yes | Yes |
| 21 | gcp-gce-ops | `## Trigger & Scope (Agent-Readable)` | `### SHOULD Use This Skill When` | Inline in last bullet | Yes | Yes |
| 22 | gcp-lb-ops | `## Trigger & Scope (Agent-Readable)` | `### SHOULD Use This Skill When` | Inline in last bullet | Yes | Yes |
| 23 | gcp-cloudfunctions-ops | `## Trigger & Scope (Agent-Readable)` | `### SHOULD Use This Skill When` | Inline in last bullet | Yes | Yes |
| 24 | gcp-armor-ops | `## Trigger & Scope (Agent-Readable)` | `### SHOULD Use This Skill When` | **Missing** | Yes | Yes |
| 25 | gcp-monitoring-ops | `## Trigger & Scope (Agent-Readable)` | `### SHOULD Use This Skill When` | Inline in bullets | Yes | Yes |
| 26 | gcp-skill-generator | **No `## Trigger & Scope`** | `### Use When` (top-level) | N/A | `### Do NOT Use When` | No |
| 27 | gcp-gcl-runner-ops | `## Trigger & Scope` (table) | **N/A** (table format) | N/A | Yes | Yes |

---

## 2. Inconsistencies Found

### 2.1 Parent Section Header Inconsistency

| Header | Skills | Note |
|--------|--------|------|
| `## Trigger & Scope` | 5 (gcs, iam, bigquery, pubsub, gcl-runner) | Older; gcl-runner uses table variant |
| `## Trigger & Scope (Agent-Readable)` | 21 | Newer format |
| No `## Trigger & Scope` | 1 (skill-generator) | Meta-skill exception |

### 2.2 Subsection Header Inconsistency

| Header | Skills | Note |
|--------|--------|------|
| `### SHOULD Use When` | 5 (gcs, cloudsql, iam, bigquery, pubsub) | Older |
| `### SHOULD Use This Skill When` | 18 | Newer standard |
| `### Use When` | 1 (skill-generator) | Meta-skill; no `##` parent |
| Table format (no `###`) | 1 (gcl-runner) | Different structure |

### 2.3 Keywords Line Inconsistency

| Status | Skills |
|--------|--------|
| Has keywords (inline in bullets) | dns, kms, memorystore, secretmanager, logging, gce, lb, cloudfunctions, monitoring |
| Has keywords (separate last bullet) | cloudrun, filestore, cdn, gke, vpc |
| Has keywords (separate line) | cloudsql |
| Has keywords (inline at end) | gcs, iam, bigquery, pubsub |
| **Missing keywords** | billing, cloudbuild, composer, securitycenter, terraform, armor |

### 2.4 Special Cases

| Skill | Issue |
|-------|-------|
| `gcp-skill-generator` | No formal `## Trigger & Scope` section. Uses `### Use When` / `### Do NOT Use When` at document top level. No Delegation Rules. Meta-skill exception. |
| `gcp-gcl-runner-ops` | Uses table format for `## Trigger & Scope` (no `(Agent-Readable)` suffix). No `### SHOULD Use This Skill When` subsection. Different semantic structure from all other skills. |

---

## 3. Recommended Standard Format

### 3.1 Structure

```markdown
## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

| Condition | User Request Pattern |
|-----------|---------------------|
| 操作类请求 | "create/delete/describe/list [resource]" |
| 变更类请求 | "update/modify/change [resource]" |
| 诊断类请求 | "check/monitor/get [resource] status" |
| ... | ... |

Keywords: keyword1, keyword2, keyword3 (optional — see §3.3)

### SHOULD NOT Use This Skill When

| Condition | User Request Pattern |
|-----------|---------------------|
| Read-only operations | "show me / describe / list only" |
| Non-GCP tasks | "help me with kubernetes / ansible / terraform" |
| ... | ... |

### Delegation Rules

| Source | Trigger | Target Skill |
|--------|---------|--------------|
| `gcp-[product]-ops` | Operation requires [specific skill] | `gcp-[target]-ops` |
```

### 3.2 Key Principles

1. **Always use `## Trigger & Scope (Agent-Readable)`** — the `(Agent-Readable)` suffix clarifies the audience
2. **Always use `### SHOULD Use This Skill When`** (not `### SHOULD Use When`) — the `This Skill` explicit reference prevents ambiguity in delegation chains
3. **Always include `### SHOULD NOT Use This Skill When`** — mirrors SHOULD, completes the contract
4. **Always include `### Delegation Rules`** — makes delegation chains traceable
5. **Always include a `Keywords:` line** — enables fast pattern matching by agents

### 3.3 Keywords Line Format

The keywords line should be a **separate line** at the end of the `### SHOULD Use This Skill When` section, formatted as:

```markdown
Keywords: product-slug, resource-type1, resource-type2, operation-verb1, operation-verb2
```

Examples:
- `gcp-gke-ops`: `Keywords: GKE, Kubernetes, cluster, node pool, kubectl, k8s, autopilot`
- `gcp-logging-ops`: `Keywords: logs, logging, sink, bucket, metric, exclusion`

### 3.4 Exemptions

| Skill | Exemption Reason |
|-------|-----------------|
| `gcp-skill-generator` | Meta-skill (generates other skills, not an ops skill). Its `## When to Use / Not Use` structure is appropriate. |
| `gcp-gcl-runner-ops` | Shared framework skill with fundamentally different delegation semantics (receives delegation, doesn't send). Table format is appropriate. |

---

## 4. Migration Guide

### 4.1 Skills Needing Minor Fix (Section Header)

| Skill | Current | Target | Action |
|-------|---------|--------|--------|
| gcp-gcs-ops | `## Trigger & Scope` | `## Trigger & Scope (Agent-Readable)` | Add `(Agent-Readable)` |
| gcp-iam-ops | `## Trigger & Scope` | `## Trigger & Scope (Agent-Readable)` | Add `(Agent-Readable)` |
| gcp-bigquery-ops | `## Trigger & Scope` | `## Trigger & Scope (Agent-Readable)` | Add `(Agent-Readable)` |
| gcp-pubsub-ops | `## Trigger & Scope` | `## Trigger & Scope (Agent-Readable)` | Add `(Agent-Readable)` |

### 4.2 Skills Needing Minor Fix (Subsection Header)

| Skill | Current | Target | Action |
|-------|---------|--------|--------|
| gcp-gcs-ops | `### SHOULD Use When` | `### SHOULD Use This Skill When` | Rename subsection |
| gcp-cloudsql-ops | `### SHOULD Use When` | `### SHOULD Use This Skill When` | Rename subsection |
| gcp-iam-ops | `### SHOULD Use When` | `### SHOULD Use This Skill When` | Rename subsection |
| gcp-bigquery-ops | `### SHOULD Use When` | `### SHOULD Use This Skill When` | Rename subsection |
| gcp-pubsub-ops | `### SHOULD Use When` | `### SHOULD Use This Skill When` | Rename subsection |

### 4.3 Skills Missing Keywords Line

| Skill | Missing Keywords |
|-------|-----------------|
| gcp-billing-ops | Add: `Keywords: billing, budget, cost, invoice, payment, account, credit, alert` |
| gcp-cloudbuild-ops | Add: `Keywords: cloudbuild, build, trigger, docker, container, artifact, cicd` |
| gcp-composer-ops | Add: `Keywords: composer, airflow, dag, workflow, python-airflow` |
| gcp-securitycenter-ops | Add: `Keywords: securitycenter, scc, security, finding, vulnerability, posture` |
| gcp-terraform-ops | Add: `Keywords: terraform, tf, infrastructure, state, plan, apply, module` |
| gcp-armor-ops | Add: `Keywords: armor, security, policy, firewall, rule, threat` |

### 4.4 Special Cases (No Action Required)

| Skill | Reason |
|-------|--------|
| gcp-skill-generator | Meta-skill. Its structure is appropriate for a skill generator. |
| gcp-gcl-runner-ops | Shared framework. Table format and different structure are appropriate. |

---

## 5. Statistics

| Metric | Count |
|--------|-------|
| Total skills audited | 28 |
| Compliant with recommended format | 18 |
| Need section header fix (`(Agent-Readable)`) | 4 |
| Need subsection header fix (`SHOULD Use This Skill When`) | 5 |
| Missing keywords line | 6 |
| Special exemptions (no action) | 2 |

**Compliance rate:** 18/28 = 64.3%

---

## 6. Action Items

| Priority | Action | Skills |
|----------|--------|--------|
| P0 | Add `(Agent-Readable)` to section header | gcs, iam, bigquery, pubsub |
| P0 | Rename `### SHOULD Use When` → `### SHOULD Use This Skill When` | gcs, cloudsql, iam, bigquery, pubsub |
| P0 | Add keywords line | billing, cloudbuild, composer, securitycenter, terraform, armor |
| Info | No action required | skill-generator (meta-skill), gcl-runner-ops (framework) |
