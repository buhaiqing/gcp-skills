# Enhanced GCL Runner (EGR) — Agent Guide

> **Version:** 1.0.0
> **Scope:** Level 3 Enhanced GCL Runner (EGR) agent-facing documentation
> **Last Updated:** 2026-07-18

---

## 1. Level 3 Overview

Level 3 extends Level 2 with five enhanced capabilities (EGR-1 through EGR-5) that enable autonomous retry with backoff, immediate safety termination, BigQuery observability, autonomy ratio tracking, and state diff detection.

| Capability | Feature | Description |
|------------|---------|-------------|
| EGR-1 | Auto-Retry with Backoff | Transient GCP errors trigger exponential backoff retry (up to 3 attempts) |
| EGR-2 | Safety=0 Termination | Destructive operations with `safety=0` terminate immediately without retry |
| EGR-3 | BigQuery + Cloud Logging | Traces uploaded to BigQuery; structured logs to Cloud Logging |
| EGR-4 | Autonomy Engine | Tracks consecutive failures, calculates `autonomy_ratio`, degrades to human at threshold |
| EGR-5 | State Snapshot Diff | Captures pre/post resource state; diffs detect unintended changes |

---

## 2. Enhanced GCL Runner Components

### 2.1 Component Summary

| Component | Responsibility | EGR Level |
|-----------|---------------|-----------|
| **GCL Runner Core** | Generator-Critic-Loop execution | Base + EGR-1, EGR-2 |
| **Trace Collector** | Aggregates traces from all iterations | EGR-3 |
| **BigQuery Writer** | Persists traces to BigQuery for analytics | EGR-3 |
| **Cloud Logging** | Structured error/decision logging | EGR-3 |
| **Autonomy Engine** | Tracks failures, calculates ratio, triggers degradation | EGR-4 |
| **State Snapshot Diff** | Captures pre/post resource state and diffs | EGR-5 |

### 2.2 Data Flow Diagram

```
User/Agent
    │
    ▼
┌────────────────────────────────────────────────────────────────┐
│ Pre-flight: Load rubric, parse command, capture pre-state     │
│             (State Snapshot Diff — EGR-5)                      │
└────────────────────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────────────────────┐
│ Loop (max_iter times):                                          │
│   1. Generate: Execute command with retry (EGR-1)              │
│   2. Critique: Score with rubric regexes                        │
│   3. Decide:                                                   │
│      - safety = 0 → SAFETY_FAIL (immediate, EGR-2)            │
│      - all ≥ threshold → PASS                                  │
│      - retryable error + attempts < 3 → RETRY (backoff)       │
│      - exhausted → MAX_ITER                                     │
└────────────────────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────────────────────┐
│ Autonomy Engine (EGR-4):                                        │
│   • Track consecutive failures                                  │
│   • Calculate autonomy_ratio                                    │
│   • Check degradation threshold (≥3 consecutive failures)      │
│   • degrade_to_human if threshold exceeded                      │
└────────────────────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────────────────────┐
│ Post-execution:                                                │
│   1. Capture post-state, compute diff (EGR-5)                  │
│   2. Collect trace + metrics                                   │
│   3. Upload to BigQuery (EGR-3, async, non-blocking)          │
│   4. Log to Cloud Logging (EGR-3, synchronous)                │
│   5. Calculate new autonomy_ratio                              │
│   6. Check degradation threshold                              │
└────────────────────────────────────────────────────────────────┘
    │
    ▼
Exit code (0=PASS, 1=MAX_ITER, 2=SAFETY_FAIL, 5=DEGRADED)
```

---

## 3. EGR Feature Descriptions

### EGR-1: Auto-Retry with Backoff

**What:** Transient GCP errors trigger exponential backoff retry before failing.

**Trigger:** Exit code ≠ 0 AND stderr matches `RETRYABLE_ERROR_TYPES`:
- `TIMEOUT`, `UNAVAILABLE`, `INTERNAL`, `RESOURCE_EXHAUSTED`, `ABORTED`

**Backoff Schedule:**
| Attempt | Delay |
|---------|-------|
| 1 | 2 seconds |
| 2 | 4 seconds |
| 3 | 8 seconds |
| Max | 60 seconds |

**Non-retryable errors** (fail immediately): `NOT_FOUND`, `PERMISSION_DENIED`, `INVALID_ARGUMENT`

**Agent action:** On retryable error, log `WARN "Retry attempt N/M"` and sleep before re-execution.

---

### EGR-2: Safety=0 Termination

**What:** Destructive operations with `safety=0` terminate immediately without retry.

**Trigger:** `critique_result["safety"] == 0.0` — detected when rubric regex matches:
- `DESTRUCTIVE` (e.g., delete without `--quiet` confirmation)
- `DESTRUCTIVE-BATCH` (bulk delete)
- `FATAL` (credential leak, security violation)

**Behavior:** Exit code = 2, `verdict = SAFETY_FAIL`, no retry attempted.

**Agent action:** On `SAFETY_FAIL`, log `ERROR "Safety=0 detected — immediate termination"` and exit.

---

### EGR-3: BigQuery + Cloud Logging Integration

**What:** All GCL traces are persisted to BigQuery and logged to Cloud Logging.

**BigQuery Table:** `{{env.GCP_SKILLS_PROJECT}}.gcp_skills_gcl_audit.gcl_traces`

**Trace Schema (key fields):**
```json
{
  "trace_id": "gcl-trace-20260718-120000-abc123",
  "skill": "gcp-gce-ops",
  "op": "DeleteInstance",
  "verdict": "PASS",
  "autonomy_ratio": 0.85,
  "iterations_count": 2,
  "safety_score": 1.0,
  "degraded_to_human": false,
  "iterations": [...]
}
```

**Cloud Logging (gcl_runner.log):**
| Level | Event |
|-------|-------|
| `INFO` | GCL started, iteration started/completed, verdict reached |
| `WARN` | Retry attempted |
| `ERROR` | Safety fail, degradation triggered |

**Agent action:** Upload is async/non-blocking — failures log error but do not fail the GCL run.

---

### EGR-4: Autonomy Engine

**What:** Tracks consecutive failures and degrades to human review when thresholds are exceeded.

**Autonomy Ratio Formula:**
```
autonomy_ratio = (total_ops - degraded_to_human - safety_fails) / total_ops
```

**Degradation Triggers (any one):**
- `consecutive_failures >= 3`
- `autonomy_ratio < 0.5`
- `safety_failures > 5` in 24h

**Degradation Actions:**
1. Log `ERROR` with `trace_id` and reason
2. Set `degraded_to_human = True`
3. Set exit code = 5 (`DEGRADED`)
4. Block final PASS until human acknowledges

**Recovery:** Human calls `gcl_runner.py --reset-degradation` to reset `consecutive_failures = 0` and `autonomy_ratio = 1.0`.

---

### EGR-5: State Snapshot Diff

**What:** Captures resource state before and after GCL execution to detect unintended changes.

**Supported Resources:**
| Resource | Command |
|----------|---------|
| Compute Instance | `gcloud compute instances describe` |
| Cloud SQL Instance | `gcloud sql instances describe` |
| GKE Cluster | `gcloud container clusters describe` |
| Storage Bucket | `gcloud storage buckets describe` |

**Diff Output:**
```json
{
  "state_diff": {
    "resource_type": "compute.googleapis.com/Instance",
    "resource_name": "my-instance",
    "pre_snapshot": { "status": "RUNNING" },
    "post_snapshot": { "status": "TERMINATED" },
    "changes": [{ "path": "status", "old": "RUNNING", "new": "TERMINATED" }]
  }
}
```

**Agent action:** If diff non-empty AND verdict=PASS, log `WARN "State changed despite PASS verdict"` and include diff in trace.

---

## 4. Level 2 vs Level 3 Comparison

| Feature | Level 2 | Level 3 |
|---------|---------|---------|
| Generator-Critic-Loop | ✓ | ✓ |
| Rubric-based scoring | ✓ | ✓ |
| Exit codes (0/1/2/3/4) | ✓ | ✓ (adds 5=DEGRADED) |
| Auto-retry on transient error | ✗ | ✓ (EGR-1) |
| Safety=0 immediate termination | ✗ | ✓ (EGR-2) |
| BigQuery trace upload | ✗ | ✓ (EGR-3) |
| Cloud Logging | ✗ | ✓ (EGR-3) |
| Autonomy ratio tracking | ✗ | ✓ (EGR-4) |
| Human degradation threshold | ✗ | ✓ (EGR-4) |
| Pre/post state snapshots | ✗ | ✓ (EGR-5) |
| State diff detection | ✗ | ✓ (EGR-5) |

---

## 5. Exit Codes

| Code | Status | Meaning |
|:----:|--------|---------|
| 0 | `PASS` | All rubric dimensions ≥ threshold |
| 1 | `MAX_ITER` | Reached `max_iter`; best-so-far returned |
| 2 | `SAFETY_FAIL` | Safety = 0 (destructive op not confirmed) |
| 3 | `USAGE_ERROR` | Bad CLI args |
| 4 | `RUBRIC_ERROR` | Rubric file missing or unparseable |
| 5 | `DEGRADED` | Degraded to human review required (EGR-4) |

---

## 6. Usage

```bash
python3 gcl_runner_enhanced.py \
    --skill gcp-gce-ops \
    --op DeleteInstance \
    --command 'gcloud compute instances delete my-instance --zone=us-central1-a --quiet' \
    --max-iter 2 \
    --trace-to-bq \
    --degrade-threshold 3 \
    --environment production
```

**New flags (Level 3):**
- `--trace-to-bq`: Enable BigQuery trace upload (default: false)
- `--degrade-threshold`: Consecutive failures before human degradation (default: 3)
- `--environment`: production | staging | development (default: production)
- `--trace-only`: Async mode, don't wait for result
