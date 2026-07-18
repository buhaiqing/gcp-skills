# GCL CLI Standardization Report

> **Version:** 1.0.0
> **Date:** 2026-07-19
> **Status:** Draft

---

## 1. Overview

This document standardizes the CLI interface for GCL (Generator-Critic-Loop) runners in the `gcp-gcl-runner-ops` skill. It audits existing runners, identifies inconsistencies, and provides a migration plan.

---

## 2. Current CLI Interface

### 2.1 Base Runner (`gcl_runner.py`)

```bash
python3 gcl_runner.py \
    --skill gcp-gce-ops \
    --op DeleteInstance \
    --command 'gcloud compute instances delete my-instance --zone=us-central1-a --quiet' \
    [--user-request "Delete my instance"] \
    [--max-iter 2] \
    [--rubric /path/to/rubric.md] \
    [--output-dir /path/to/traces] \
    [--dry-run]
```

| Argument | Type | Required | Default | Help Text |
|----------|------|----------|---------|-----------|
| `--skill` | string | Yes | - | Target skill name (e.g., gcp-gce-ops) |
| `--op` | string | Yes | - | Operation name (e.g., DeleteInstance) |
| `--command` | string | Yes | - | Full CLI command to execute |
| `--user-request` | string | No | "" | Original natural-language user request |
| `--max-iter` | int | No | 2 | Max iterations |
| `--rubric` | string | No | None | Custom rubric path |
| `--output-dir` | string | No | TRACE_DIR | Output directory for traces |
| `--dry-run` | flag | No | False | Skip subprocess; run Critic only |

### 2.2 Enhanced Runner (`gcl_runner_enhanced.py`)

```bash
python3 gcl_runner_enhanced.py \
    --skill gcp-gce-ops \
    --op DeleteInstance \
    --command 'gcloud compute instances delete my-instance --zone=us-central1-a --quiet' \
    [--user-request "Delete my instance"] \
    [--max-iter 2] \
    [--rubric /path/to/rubric.md] \
    [--output-dir /path/to/traces] \
    [--dry-run] \
    [--trace-to-bq] \
    [--degrade-threshold 3] \
    [--environment production|staging|development] \
    [--trace-only]
```

| Argument | Type | Required | Default | Help Text |
|----------|------|----------|---------|-----------|
| `--skill` | string | Yes | - | Target skill name (e.g., gcp-gce-ops) |
| `--op` | string | Yes | - | Operation name (e.g., DeleteInstance) |
| `--command` | string | Yes | - | Full CLI command to execute |
| `--user-request` | string | No | "" | Original natural-language user request |
| `--max-iter` | int | No | 2 | Max iterations |
| `--rubric` | string | No | None | Custom rubric path |
| `--output-dir` | string | No | TRACE_DIR | Output directory for traces |
| `--dry-run` | flag | No | False | Skip subprocess; run Critic only |
| `--trace-to-bq` | flag | No | False | Enable BigQuery trace upload (default: false) |
| `--degrade-threshold` | int | No | 3 | Number of consecutive failures before human degradation (default: 3) |
| `--environment` | enum | No | production | Environment (default: production) |
| `--trace-only` | flag | No | False | Async mode, don't wait for result |

---

## 3. Inconsistencies Found

### 3.1 Critical Issues

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| C1 | Missing `--format=json` for machine parsing | BLOCKER | Both runners |
| C2 | Missing `--project` equivalent for `CLOUDSDK_CORE_PROJECT` | BLOCKER | Both runners |
| C3 | Missing `--credential-file` equivalent for `GOOGLE_APPLICATION_CREDENTIALS` | BLOCKER | Both runners |

### 3.2 Major Issues

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| M1 | Exit code 3 (USAGE_ERROR) documented but not implemented | MAJOR | `gcl_runner_enhanced.py:12` (docstring) vs actual (sys.exit not called for usage errors) |
| M2 | Exit code 4 (RUBRIC_ERROR) documented but not implemented consistently | MAJOR | `gcl_runner_enhanced.py:12` - uses `sys.exit(4)` for missing rubric, but `gcl_runner.py` uses it too |
| M3 | Exit code 5 (DEGRADED) not documented in base runner | MAJOR | `gcl_runner.py:12` - only lists 0-4, enhanced has 5 |
| M4 | Missing `--timeout` argument for command execution | MAJOR | Both runners - hardcoded 300s in `generate()` |

### 3.3 Minor Issues

| # | Issue | Severity | Location |
|---|-------|----------|----------|
| m1 | Help text for `--max-iter` doesn't mention rubric override | MINOR | Both runners |
| m2 | `--output-dir` help text says "Output directory for traces" but base runner doesn't actually use it | MINOR | `gcl_runner.py:276` |
| m3 | `--environment` choices use full names (`production`) but AGENTS.md convention uses short (`prod`) | MINOR | `gcl_runner_enhanced.py:812` |

---

## 4. Recommended Standard Format

### 4.1 Argument Naming Convention

| Category | Pattern | Examples |
|----------|---------|----------|
| Required args | `--<noun>` | `--skill`, `--op`, `--command` |
| Optional config | `--<noun>` or `--<noun>-<subnoun>` | `--rubric`, `--output-dir` |
| Boolean flags | `--<verb>` or `--<verb>-<noun>` | `--dry-run`, `--trace-only` |
| Numeric config | `--<noun>-<unit>` (if unit needed) | `--max-iter` |
| Enum config | `--<noun>` with choices defined | `--environment` |

### 4.2 Standard Arguments (All GCL Runners)

```bash
python3 gcl_runner.py \
    --skill <string> \                  # Required: target skill
    --op <string> \                     # Required: operation name
    --command <string> \                # Required: full CLI command
    --format json|table \               # Output format (default: json)
    --project <project-id> \            # GCP project (default: CLOUDSDK_CORE_PROJECT)
    --credential-file <path> \          # SA key path (default: GOOGLE_APPLICATION_CREDENTIALS)
    --timeout <seconds> \               # Command timeout (default: 300)
    --max-iter <n> \                    # Max iterations (default: 2)
    --rubric <path> \                   # Custom rubric path
    --output-dir <path> \               # Trace output directory
    --dry-run \                         # Skip execution, run critic only
    --user-request <string>             # Original user request (for logging)
```

### 4.3 Enhanced Arguments (EGR-specific)

```bash
python3 gcl_runner_enhanced.py \
    # ... standard args above ...
    --trace-to-bq \                     # Upload trace to BigQuery
    --degrade-threshold <n> \           # Failures before human handoff (default: 3)
    --environment prod|staging|dev \    # Environment (default: prod)
    --trace-only \                      # Async mode
```

### 4.4 Enum Value Standardization

| Current | Standard | Notes |
|---------|----------|-------|
| `production` | `prod` | Short form preferred |
| `staging` | `staging` | Keep as-is |
| `development` | `dev` | Short form preferred |

### 4.5 Exit Code Standardization

| Code | Meaning | Notes |
|------|---------|-------|
| 0 | PASS | All checks passed |
| 1 | MAX_ITER | Reached max iterations |
| 2 | SAFETY_FAIL | Safety score = 0 (ABORT) |
| 3 | USAGE_ERROR | Invalid arguments or inline secrets |
| 4 | RUBRIC_ERROR | Rubric not found or invalid |
| 5 | DEGRADED | Degraded to human-in-the-loop |

---

## 5. Migration Plan

### Phase 1: Add Missing Standard Arguments (Non-breaking)

1. Add `--format` argument (default: `json`)
2. Add `--project` argument (default: env `CLOUDSDK_CORE_PROJECT`)
3. Add `--credential-file` argument (default: env `GOOGLE_APPLICATION_CREDENTIALS`)
4. Add `--timeout` argument (default: 300)

### Phase 2: Fix Documented But Not Implemented (Breaking)

1. Implement exit code 3 for usage errors (inline secrets check)
2. Document exit code 5 consistently across runners

### Phase 3: Enum Normalization (Breaking)

1. Change `--environment` choices from `production|staging|development` to `prod|staging|dev`
2. Update all caller scripts

### Phase 4: Deprecation and Removal (Future)

1. Announce deprecation of legacy argument names (if any)
2. Remove after 2 release cycles

---

## 6. Compliance Checklist

| # | Check | Status |
|---|-------|--------|
| 1 | All args have help text | ✅ PASS |
| 2 | Boolean flags use `--flag` format (not `--no-flag`) | ✅ PASS |
| 3 | Enum values are consistent | ⚠️ PARTIAL (environment) |
| 4 | Environment via `CLOUDSDK_CORE_PROJECT` | ❌ MISSING (--project arg) |
| 5 | Credentials via `GOOGLE_APPLICATION_CREDENTIALS` | ❌ MISSING (--credential-file arg) |
| 6 | `--format=json` for machine parsing | ❌ MISSING |
| 7 | Long-running ops use built-in polling | ✅ PASS (in enhanced) |
| 8 | Exit codes documented correctly | ⚠️ PARTIAL |
| 9 | Default values documented in help | ✅ PASS (enhanced), ⚠️ PARTIAL (base) |

---

## 7. References

- AGENTS.md §3: GCP CLI & SDK Conventions
- AGENTS.md §0.1: Credential Masking
- GCP GCL Runner Architecture: [ARCHITECTURE.md](ARCHITECTURE.md)
- EGR Handbook: [EGR_HANDBOOK.md](EGR_HANDBOOK.md)
