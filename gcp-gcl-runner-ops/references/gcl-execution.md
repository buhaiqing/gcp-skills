# GCL Execution Reference — gcp-gcl-runner-ops

> **Purpose:** Detailed usage guide for the GCL (Generator-Critic-Loop) runner script.
> **Version:** 1.0.0
> **Last Updated:** 2026-06-07

---

## Overview

`gcl_runner.py` is a standalone Python 3.10+ CLI that implements the GCL loop flow from `AGENTS.md §12.4`:

```
[0] Pre-flight  — load rubric, resolve env.* / user.*, sanitize secrets
[1] Generate    — invoke the command (subprocess) and capture trace
[2] Critique    — re-classify output using the rubric's regex hot-spots
[3] Decide      — apply termination rules
```

## CLI Usage

```bash
python3 gcp-gcl-runner-ops/scripts/gcl_runner.py \
  --skill <skill-name> \
  --op <operation-name> \
  --command <cli-command> \
  [--user-request <original-request>] \
  [--max-iter <n>] \
  [--rubric <path>] \
  [--output-dir <dir>] \
  [--dry-run]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--skill` | ✅ | Target skill name (e.g. `gcp-gce-ops`) |
| `--op` | ✅ | Operation name (e.g. `DeleteInstance`) |
| `--command` | ✅ | Full CLI command to execute |
| `--user-request` | ❌ | Original natural-language user request |
| `--max-iter` | ❌ | Max GCL iterations (default: 2) |
| `--rubric` | ❌ | Custom rubric path (default: `./{skill}/references/rubric.md`) |
| `--output-dir` | ❌ | Output directory for traces (default: `./audit-results/`) |
| `--dry-run` | ❌ | Skip subprocess; run Critic only on the command text |

## How the Critic Works

The Phase 2 Critic is a **pure-Python regex re-classifier**, not an LLM call:

- **Deterministic** — same input always produces same output
- **CI-friendly** — runs in <100ms
- **Auditable** — every score is explained by a regex match

The rubric's "Detection Regex" table is the Critic's score function. The Critic applies every regex to `(command + stdout + stderr)` and computes:

```python
for pattern, risk in rubric["regexes"]:
    if re.search(pattern, full_text, ...):
        if _risk_severity(risk) > _risk_severity(highest_risk):
            highest_risk = risk

# Safety is 0 if any DESTRUCTIVE-* or FATAL regex matched
safety = 0 if "DESTRUCTIVE" in highest_risk or "FATAL" in highest_risk else 1
```

## Trace Output

Every GCL run persists a JSON trace to `./audit-results/gcl-trace-YYYYMMDD-HHMMSS-<rand6>.json`:

```json
{
  "version": "1.0.0",
  "trace_id": "gcl-trace-20260607-120000-a1b2c3",
  "timestamp": "2026-06-07T12:00:00Z",
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

## Testing

```bash
# Run all runner tests
python3 scripts/gcl_runner_test.py

# Run audit cross-check tests
python3 scripts/gcl_auditlog_crosscheck_test.py
```