# Token Efficiency Optimization Strategy

> **Purpose:** Always-loaded vs lazy-loaded optimization methodology for the AGENTS.md file and skill ecosystem.
> **Version:** 1.0.0
> **Last Updated:** 2026-06-07

---

## Overview

AGENTS.md is always loaded by the agent. Every token consumed there reduces the context budget available for actual skill execution. This document defines the optimization strategy to minimize AGENTS.md token footprint while preserving all critical structural and safety information.

## TE-A: Always-Loaded Content (AGENTS.md)

Content that MUST remain in AGENTS.md (non-compressible):

| Section | Rationale |
|---------|-----------|
| §1 Repo Layout | Navigation and structure; agent must know the repo shape |
| §2 Content Separation Rule | Critical design principle; cannot be deferred |
| §3 Operation Design Pattern | Template for all operations; agent must follow it |
| §4 CLI & SDK Conventions | GCP-specific tooling; agent must know gcloud vs SDK |
| §5-8 Security / Patterns | Safety-critical; cannot be lazy-loaded |
| §10 Quality Gates | Five gates; applies to every skill |
| §12 GCL (summary) | High-level overview; detail is in docs/gcl-spec.md |
| Key References table | Navigation aid |

## TE-B: Lazy-Loaded Content (references/ + docs/)

Content that can be deferred to lazy-loaded files:

| Section | Lazy-Load Target | Trigger |
|---------|-----------------|---------|
| Detailed GCL spec | `docs/gcl-spec.md` | When a GCL loop is actually run |
| Token Efficiency details | `docs/token-efficiency-strategy.md` | (This file) |
| Post-update self-review | `docs/post-update-self-review.md` | After a skill update |
| Diagnostic logging | `docs/diagnostic-logging-standard.md` | When writing data-plane scripts |
| Full P0/P1 checklist | `gcp-skill-generator/SKILL.md` | When generating a new skill |

## TE-C: Audit Checklist

When scanning existing skills for token efficiency:

| Item | Check | Action |
|------|-------|--------|
| Static tables > 20 rows | Replace with API query | TE-1 |
| Go docstrings in snippets | Replace with `#` inline comment | TE-2 |
| Error table > 3 columns | Compress to Code + Action | TE-3 |
| JSON paths repeated > 2x | Centralize to file top | TE-4 |
| Example config with > 20 lines duplication | Use YAML anchors | TE-5 |
| SKILL.md and references/ duplicate flow | Remove from references/ | TE-6 |
| Advanced content in main flow | Move to `references/advanced/` | TE-7 |