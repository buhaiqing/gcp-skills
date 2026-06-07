# Prompt Library — GCP Skill Generator

> **Purpose:** Centralized, structured repository of all prompts used during the skill generation lifecycle.
> **Version:** 1.0.0
> **Last Updated:** 2026-06-07

---

## Table of Contents

1. [Meta-Prompts (Generator-Level)](#1-meta-prompts-generator-level)
2. [Scaffolding Prompts](#2-scaffolding-prompts)
3. [Analysis Prompts](#3-analysis-prompts)
4. [Validation Prompts](#4-validation-prompts)

---

## 1. Meta-Prompts (Generator-Level)

### P1: Skill Generation Initiator

**ID:** `meta-initiate`
**Usage Context:** Triggered when user requests creation of a new `gcp-[product]-ops` skill.

**Prompt Content:**
```
You are the GCP Skill Generator. Your task is to scaffold a new operational skill for Google Cloud product: {{product.name}}.

Before generating, you MUST:
1. Confirm the product slug via `gcloud {{product.slug}} --help` or official docs
2. Verify API availability at {{doc.url}}
3. Decide: extend existing skill vs create new directory
4. Collect from user: product name, primary resource type, API service identifier, official doc URLs, operation list

Follow the generation process in SKILL.md Step 0–6 exactly.
Output: structured directory tree with populated SKILL.md and references/.
```

### P2: Skill Extender

**ID:** `meta-extend`
**Usage Context:** User requests adding operations to an existing skill.

**Prompt Content:**
```
You are extending the existing `gcp-[product]-ops` skill. The current version is {{current.version}}.

New operations to add: {{new.operations}}

Follow the existing pattern:
- Add to the capabilities table in SKILL.md
- Create a new Execution Flow section (Pre-flight → Execute → Validate → Recover)
- Update references/ as needed (gcloud-usage.md, troubleshooting.md)
- Bump version and update changelog
```

---

## 2. Scaffolding Prompts

### P3: Directory Scaffold

```
Scaffold the following directory structure for `gcp-[product]-ops`:

```
gcp-[product]-ops/
├── SKILL.md
├── references/
│   ├── core-concepts.md
│   ├── api-sdk-usage.md
│   ├── gcloud-usage.md
│   ├── troubleshooting.md
│   ├── monitoring.md
│   ├── integration.md
│   ├── well-architected-assessment.md
│   └── idempotency-checklist.md
├── assets/
│   ├── example-config.yaml
│   └── eval_queries.json
└── scripts/
```

Create each file with the template content from gcp-skill-template.md.
```

---

## 3. Analysis Prompts

### P4: OpenAPI / gcloud Reference Analysis

```
Analyze the following gcloud command group: `gcloud {{product.slug}}`

From `gcloud {{product.slug}} --help`, extract:
1. All subcommands with descriptions
2. Required vs optional flags
3. Output format (JSON paths)
4. Error messages and codes
5. Any async/long-running behavior

Also check: https://cloud.google.com/sdk/gcloud/reference/{{product.slug}}
```

---

## 4. Validation Prompts

### P5: P0/P1 Checklist Runner

```
Run the P0/P1 quality checklist against `gcp-[product]-ops/SKILL.md`:

1. Check frontmatter: name, description, license, compatibility, metadata present?
2. Check SHOULD/SHOULD NOT sections present?
3. Check Five Core Standards table present?
4. Check Well-Architected Framework table present?
5. Check Variables section present?
6. Check Token Efficiency rules applied (TE-1 through TE-6)?
7. Check error taxonomy ≥ 10 error codes?
8. Check safety gates for destructive operations?

Report: PASS/FAIL for each check. For FAIL, provide fix instructions.
```

### P6: Description Optimization

```
Evaluate the `description` field of `gcp-[product]-ops/SKILL.md`:

Current: {description}

Check:
1. Under 1024 characters? (current: {length})
2. Uses "Use when..." imperative phrasing?
3. Includes implicit trigger scenarios?
4. Has negative boundaries?
5. Will it activate correctly for eval queries?

Suggest optimizations if needed.
```