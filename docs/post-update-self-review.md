# Post-Update Self-Review Specification

> **Purpose:** Defines the mandatory two-round self-review process that runs after every skill update.
> **Version:** 1.0.0
> **Last Updated:** 2026-06-07

---

## Overview

After every skill update, auto-run 2 rounds of self-review and fix all discovered issues before declaring completion.

---

## Round R1: Structural Check

| # | Check | Command | Pass Criteria |
|---|-------|---------|--------------|
| **C1** | Frontmatter | `head -3 SKILL.md | grep "^---"` | Starts with `---`, has `name`, `description`, `license`, `compatibility`, `metadata` |
| **C2** | SHOULD/SHOULD NOT | `grep -c "SHOULD Use" SKILL.md` | ≥ 1 match for each |
| **C3** | Five Core Standards | `grep -c "Five Core Standards" SKILL.md` | ≥ 1 match |
| **C4** | Well-Architected | `grep -c "Well-Architected Framework\|Google Cloud Architecture Framework" SKILL.md` | ≥ 1 match |
| **C5** | Variables | `grep -c "^## Variables" SKILL.md` | ≥ 1 match with `{{env.*}}`/`{{user.*}}`/`{{output.*}}` |
| **C6** | **Token Efficiency** | See §Token Efficiency Requirements | All 6 TE rules applied (MUST PASS) |
| **C7** | **Rubric 存在性** | `grep -q "references/rubric.md" SKILL.md && test -f "references/rubric.md"` | Both true: SKILL.md references AND file exists | Add `references/rubric.md` link to SKILL.md OR create the rubric file per `gcp-skill-generator/references/template-gcl-gate.md` |

---

## Round R2: Content Check

| # | Check | Description | MUST PASS |
|---|-------|-------------|:---------:|
| **F1** | CLI validation | `gcloud` commands verified against `--help` output | No |
| **F2** | Error codes | ≥ 10 product-specific error codes documented | No |
| **F3** | Safety gates | All destructive operations have explicit confirmation | No |
| **F4** | Link integrity | All cross-references resolve to existing files | No |
| **F5** | Token Efficiency | TE-1 through TE-6 rules applied | **Yes** |
| **F6** | Content dedup | No duplicate content across SKILL.md and references/ | **Yes** |
| **F7** | TODO.md sync | All new/modified features updated in TODO.md | **Yes** |
| **F8** | Metadata consistency | version + last_updated bumped in same commit | No |

---

## Verification Script

```bash
# R1: Structural
echo "=== R1 Structural ==="
for check in C1 C2 C3 C4 C5 C6 C7; do
    echo "[ ] $check"
done

# R2: Content
echo "=== R2 Content ==="
for check in F1 F2 F3 F4 F5 F6 F7 F8; do
    echo "[ ] $check"
done
```

Any issue found → fix one by one → all must pass before finishing.