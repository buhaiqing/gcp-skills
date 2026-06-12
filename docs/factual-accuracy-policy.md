# Factual Accuracy Policy

> **Rule**: All GCP skill content must be verified for completeness, accuracy, and timeliness before each update.
>
> **Scope**: Applies to all 22 gcloud-*ops skills plus gcp-skill-generator.

## Requirement

Every skill MUST have procedural safeguards to ensure factual accuracy:
1. **Adult review**: All operational commands, example code, error codes, and API signatures must be reviewed by a human expert
2. **Version anchoring**: API version numbers, SDK package names, and CLI command syntax must not be hard-coded without reference to discovery URLs
3. **Deprecation tracking**: When gcloud SDK or API deprecation occurs, skills MUST be updated within 30 days
4. **Audit trail**: Major factual changes (e.g., error codes, command flags) must be documented with version reference

sources

## Reporting Inaccuracies

If a skill contains stale or incorrect information:

1. **Severity Triage**:
   - 🔴 HIGH: Command syntax, API signature changes that cause operation failure
   - 🟡 MEDIUM: Misleading descriptions, outdated version numbers
   - 🟢 LOW: Minor formatting issues, non-operational text

2. **Fix Process**:
   - Investigate against official GCP docs: CLI help (`cmd --help`), API discovery, SDK changelogs
   - Update the specific section with correct information
   - Increment version number and last_updated date
   - Document the change in SKILL.md Changelog

3. **Escalation**:
   - If cannot verify accuracy via documentation → HALT and escalate to human expert
   - When uncertain (80/20 rule:如果能验证就验证，不能验证就走人工复核)

## Current Audit Status

| Skill | Last Fact Check | Status |
|-------|----------------|--------|
| gcp-gce-ops | 2026-06-07 | ✅ Reviewed (v1.0.0) |
| gcp-gke-ops | 2026-06-07 | ✅ Reviewed (v1.0.0) |
| ... | ... | ... |

> Skills published after 2026-06-12 (AGENTS.md update) are **automatically marked for fact audit**.
