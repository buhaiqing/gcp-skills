# Enhanced GCL Runner (EGR) — Architecture Document

> **Version:** 2.0.0 (Level 3)
> **Last Updated:** 2026-07-18
> **Scope:** Level 3 features only (EGR-1 through EGR-5); Level 4 out of scope

---

## 1. System Overview

The Enhanced GCL Runner (EGR) extends the base GCL Runner (`gcl_runner.py`) with autonomous retry, immediate safety termination, BigQuery observability, autonomy ratio tracking, and state diff capabilities.

### 1.1 High-Level Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ENHANCED GCL RUNNER                               │
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                │
│  │ Pre-flight   │───▶│ GCL Runner   │───▶│ Trace        │                │
│  │ State Snap   │    │ Core         │    │ Collector     │                │
│  └──────────────┘    └──────────────┘    └──────────────┘                │
│         │                   │                    │                          │
│         │                   ▼                    ▼                          │
│         │            ┌──────────────┐    ┌──────────────┐                │
│         │            │ Autonomy     │    │ BigQuery     │                │
│         │            │ Engine       │    │ Writer       │                │
│         │            └──────────────┘    └──────────────┘                │
│         │                   │                    │                          │
│         ▼                   ▼                    ▼                          │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │                     Cloud Logging                                   │      │
│  └──────────────────────────────────────────────────────────────────┘      │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │                  Post-execution State Snapshot Diff                │      │
│  └──────────────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Component Summary

| Component | Responsibility | Level 3 New |
|-----------|---------------|--------------|
| **GCL Runner Core** | Generator-Critic-Loop execution | Enhanced with EGR-1, EGR-2 |
| **Trace Collector** | Aggregates traces from all iterations | EGR-3 (BigQuery upload) |
| **BigQuery Writer** | Persists traces to BigQuery for analytics | EGR-3 |
| **Cloud Logging** | Structured error/decision logging | EGR-3 |
| **Autonomy Engine** | Tracks consecutive failures, calculates autonomy ratio, triggers degradation | EGR-4 |
| **State Snapshot Diff** | Captures pre/post resource state and diffs | EGR-5 |

---

## 2. Architecture Diagram

```
                                    ┌─────────────────────────────────────┐
                                    │         GCP Project / Org           │
                                    │                                     │
  ┌──────────────────────────────┐ │  ┌─────────────────────────────────┐│
  │         Agent / Caller        │ │  │      BigQuery Dataset           ││
  └──────────────────────────────┘ │  │  ┌─────────────────────────────┐ ││
                 │                  │  │  │   gcl_traces table         │ ││
                 ▼                  │  │  │   (autonomy_ratio,         │ ││
  ┌──────────────────────────────┐ │  │  │    safety_score, etc)      │ ││
  │    Enhanced GCL Runner       │ │  │  └─────────────────────────────┘ ││
  │  ┌────────────────────────┐  │ │  └─────────────────────────────────┘│
  │  │  Pre-flight           │  │ │              ▲                        │
  │  │  State Snap (EGR-5)   │  │ │              │                       │
  │  └────────────────────────┘  │ │              │ trace + metrics      │
  │             │                │ │  ┌────────────┴──────────┐           │
  │             ▼                │ │  │  BigQuery Writer       │           │
  │  ┌────────────────────────┐  │ │  │  (EGR-3)              │           │
  │  │  GCL Runner Core      │  │ │  └──────────────────────┘           │
  │  │  ┌──────┐ ┌────────┐ │  │ │                                    │
  │  │  │ Gen  │ │ Critic │ │  │ │  ┌─────────────────────────────────┐│
  │  │  └──────┘ └────────┘ │  │ │  │      Cloud Logging              ││
  │  │         │            │  │ │  │  (gcl_runner.log)                ││
  │  │         ▼            │  │ │  └─────────────────────────────────┘│
  │  │  ┌────────────────┐│  │ │              ▲                        │
  │  │  │ Decision Engine ││  │ │              │                        │
  │  │  │ (PASS/FAIL/    ││  │ │  ┌───────────┴────────────┐         │
  │  │  │  RETRY/TERM)   ││  │ │  │  Trace Collector        │         │
  │  │  └────────────────┘│  │ │  │  (EGR-3)                │         │
  │  └──────────────────────│  │ │  └─────────────────────────┘         │
  │              │           │  │                                    │
  │   ┌──────────┴──────────┴──┼──────────────────────────────────┐  │
  │   │                           │                                  │  │
  │   ▼                           ▼                                  │  │
  │  ┌────────────────────────┐  ┌─────────────────────────────┐     │  │
  │  │ Autonomy Engine (EGR-4)│  │ State Snap Diff (EGR-5)    │     │  │
  │  │ • consecutive failures  │  │ • pre_state snapshot       │     │  │
  │  │ • autonomy_ratio calc   │  │ • post_state snapshot       │     │  │
  │  │ • degrade_to_human     │  │ • diff generation           │     │  │
  │  └────────────────────────┘  └─────────────────────────────┘     │  │
  │              │                           │                      │  │
  └──────────────┼───────────────────────────┼──────────────────────┘  │
                 │                           │                           │
                 ▼                           ▼                           │
          ┌──────────────────────────────────────────┐                  │
          │           Cloud Logging (EGR-3)           │                  │
          └──────────────────────────────────────────┘                  │
                                    │                                     │
                                    └─────────────────────────────────────┘
```

---

## 3. Component Details

### 3.1 GCL Runner Core

**Responsibility:** Execute the Generator-Critic-Loop with enhanced retry and safety termination.

**Inputs:**
- `skill`, `op`, `command`, `user_request`, `max_iter`
- Rubric (from `references/rubric.md`)
- GCP credentials via `GOOGLE_APPLICATION_CREDENTIALS`

**Outputs:**
- `GCLTrace` object with iterations, scores, verdict
- Exit codes: `0=PASS`, `1=MAX_ITER`, `2=SAFETY_FAIL`, `3=USAGE_ERROR`, `4=RUBRIC_ERROR`

**Failure Modes:**
| Failure | Detection | Action |
|---------|-----------|--------|
| Command timeout | `subprocess.TimeoutExpired` | Retry with backoff (EGR-1) |
| GCP API error | stderr matches `GCPErrorType` regex | Retry with backoff (EGR-1) |
| Safety score = 0 | `critique_result["safety"] == 0.0` | **Immediate termination** (EGR-2) |
| Rubric not found | File not found | Exit code 4 |

---

### 3.2 Trace Collector

**Responsibility:** Aggregate iteration-level traces into a single `GCLTrace` and forward to BigQuery Writer and Cloud Logging.

**Inputs:**
- `GCLTrace` from Runner Core
- Autonomy decisions from Autonomy Engine

**Outputs:**
- Persisted JSON trace to `audit-results/`
- `GCLTrace.to_dict()` forwarded to BigQuery Writer
- Structured log entries to Cloud Logging

**Failure Modes:**
| Failure | Detection | Action |
|---------|-----------|--------|
| BigQuery write fails | BigQuery API returns error | Log error, continue (non-blocking) |
| JSON persist fails | `OSError` on write | Log error, continue (non-blocking) |

---

### 3.3 BigQuery Writer

**Responsibility:** Upload GCL traces to BigQuery for long-term analytics and querying.

**Inputs:**
- `GCLTrace.to_dict()` (serialized trace)

**Outputs:**
- BigQuery row inserted into `gcl_traces` table
- Upload timestamp logged

**Failure Modes:**
| Failure | Detection | Action |
|---------|-----------|--------|
| BigQuery unavailable | `google.api_core.exceptions` | Log and continue; trace remains in local file |
| Schema mismatch | BigQuery load error | Log error with trace_id; local file preserved |
| Quota exceeded | `RESOURCE_EXHAUSTED` error | Log and continue |

**BigQuery Table:** `{{env.GCP_SKILLS_PROJECT}}.gcl_observability.gcl_traces`

---

### 3.4 Cloud Logging

**Responsibility:** Structured logging of all GCL events for real-time monitoring and alerting.

**Log Entries (all at `gcl_runner.log`):**

| Log Level | Event |
|-----------|-------|
| `INFO` | GCL started, iteration started/completed |
| `INFO` | Verdict reached (`PASS`, `MAX_ITER`) |
| `WARN` | Retry attempted |
| `ERROR` | Safety fail, degradation triggered |
| `DEBUG` | Command sanitized, rubric loaded |

**Structured Fields:**
```json
{
  "trace_id": "gcl-trace-20260718-120000-abc123",
  "skill": "gcp-gce-ops",
  "op": "DeleteInstance",
  "verdict": "PASS",
  "autonomy_ratio": 0.85,
  "iterations": 2,
  "safety_score": 1.0
}
```

---

### 3.5 Autonomy Engine

**Responsibility:** Track consecutive failures, calculate autonomy ratio, and trigger human degradation.

**Inputs:**
- `GCLResult` from each GCL run
- Historical autonomy ratio from BigQuery

**Outputs:**
- `AutonomyDecision` record (per decision)
- `degraded_to_human: bool` flag
- `autonomy_ratio: float` (0.0–1.0)

**Failure Modes:**
| Failure | Detection | Action |
|---------|-----------|--------|
| BigQuery query fails | BigQuery API error | Default to `autonomy_ratio=0.5` |
| No historical data | Empty query result | Initialize with `autonomy_ratio=1.0` |

---

### 3.6 State Snapshot Diff (EGR-5)

**Responsibility:** Capture resource state before and after GCL execution to detect unintended changes.

**Inputs:**
- Resource identifier from command (parsed from `gcloud` command)
- GCP resource type (parsed from skill name or command)

**Outputs:**
- `pre_state`: JSON snapshot before execution
- `post_state`: JSON snapshot after execution
- `state_diff`: JSON diff between pre and post

**Supported Resources:**
| Resource | Pre-state command | Post-state command |
|----------|-------------------|-------------------|
| Compute Instance | `gcloud compute instances describe` | `gcloud compute instances describe` |
| Cloud SQL Instance | `gcloud sql instances describe` | `gcloud sql instances describe` |
| GKE Cluster | `gcloud container clusters describe` | `gcloud container clusters describe` |
| Storage Bucket | `gcloud storage buckets describe` | `gcloud storage buckets describe` |

**Failure Modes:**
| Failure | Detection | Action |
|---------|-----------|--------|
| Resource not found pre-exec | `NOT_FOUND` in stderr | Log warning, skip diff |
| Resource not found post-exec | `NOT_FOUND` in stderr | Log warning, diff shows only pre-state |
| Diff generation fails | Python dict diff error | Log error, skip diff |

---

## 4. Auto-Retry Logic (EGR-1)

### 4.1 Decision Flow

```
                    ┌─────────────────────────┐
                    │   Command Execution     │
                    │   (Generator)          │
                    └───────────┬─────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │   Exit Code == 0 ?       │
                    └───────────┬─────────────┘
                         YES/   \NO
                                │
                                ▼
                    ┌─────────────────────────┐
                    │   GCP Error?            │
                    │   (stderr match)        │
                    └───────────┬─────────────┘
                         YES/   \NO
                                │
              ┌─────────────────┴─────────────────┐
              │                                   │
              ▼                                   ▼
  ┌─────────────────────────┐       ┌─────────────────────────┐
  │   Retryable Error?      │       │   Non-retryable?        │
  │   (TIMEOUT, UNAVAIL,   │       │   (NOT_FOUND, PERM_     │
  │    INTERNAL, etc.)     │       │    DENIED, etc.)        │
  └───────────┬─────────────┘       └─────────────────────────┘
         YES/         \NO
              │           │
              ▼           ▼
  ┌─────────────────────────┐       ┌─────────────────────────┐
  │   Consecutive failures   │       │   Fail immediately      │
  │   < 3?                  │       │   (Safety=0 or fatal)   │
  └───────────┬─────────────┘       └─────────────────────────┘
         YES/         \NO
              │           │
              ▼           ▼
  ┌─────────────────────────┐
  │   EXPONENTIAL BACKOFF   │
  │   delay = base * 2^n    │
  │   (base=2s, max=60s)   │
  └───────────┬─────────────┘
              │
              ▼
  ┌─────────────────────────┐
  │   Retry + Log WARN      │
  │   "Retry attempt N/M"   │
  └─────────────────────────┘
```

### 4.2 Retryable GCP Errors

```python
RETRYABLE_ERRORS: set[GCPErrorType] = {
    GCPErrorType.TIMEOUT,
    GCPErrorType.UNAVAILABLE,
    GCPErrorType.INTERNAL,
    GCPErrorType.RESOURCE_EXHAUSTED,
    GCPErrorType.ABORTED,
}
```

### 4.3 Backoff Schedule

| Attempt | Delay |
|---------|-------|
| 1 | 2 seconds |
| 2 | 4 seconds |
| 3 | 8 seconds |
| Max | 60 seconds |

---

## 5. Safety=0 Termination (EGR-2)

### 5.1 Trigger Conditions

Safety score = 0.0 is set when the Critic detects:

| Risk Level | Meaning | Action |
|------------|---------|--------|
| `DESTRUCTIVE` | Irreversible operation (delete, terminate) without confirmation | **Terminate immediately** |
| `DESTRUCTIVE-BATCH` | Bulk delete operations | **Terminate immediately** |
| `FATAL` | Credential leak, security violation | **Terminate immediately** |

### 5.2 Termination Flow

```
┌─────────────────────────────────────────┐
│   Critic Score Calculation               │
│   (regex-based detection)               │
└──────────────────┬──────────────────────┘
                   │
                   ▼
        ┌─────────────────────┐
        │  highest_risk in    │
        │  {DESTRUCTIVE,      │
        │   DESTRUCTIVE-BATCH,│
        │   FATAL}?           │
        └──────────┬──────────┘
              YES/  \NO
                   │
                   ▼
        ┌─────────────────────┐
        │  safety_score = 0.0 │
        │  verdict = SAFETY_FAIL │
        └──────────┬──────────┘
                   │
                   ▼
        ┌─────────────────────┐
        │  Log ERROR          │
        │  "Safety=0 detected │
        │   — immediate      │
        │   termination"      │
        └──────────┬──────────┘
                   │
                   ▼
        ┌─────────────────────┐
        │  Do NOT retry       │
        │  Do NOT continue    │
        │  Exit code = 2      │
        └─────────────────────┘
```

### 5.3 Safety Failures Tracked

```python
safety_failures: int  # Incremented each time safety = 0
# Persisted to BigQuery for analytics
# Used in autonomy_ratio calculation
```

---

## 6. Autonomy Ratio Calculation (EGR-4)

### 6.1 Formula

```
autonomy_ratio = (total_ops - degraded_to_human - safety_fails) / total_ops
```

Where:
- `total_ops`: Total GCL operations in the lookback window
- `degraded_to_human`: Number of times degraded to human review
- `safety_fails`: Number of SAFETY_FAIL verdicts

### 6.2 Calculation Trigger

Autonomy ratio is recalculated:
1. After each GCL run completes
2. On startup (look back 7 days from BigQuery)

### 6.3 Degradation Threshold

```
if consecutive_failures >= 3:
    degrade_to_human = True
    autonomy_ratio = max(0.0, autonomy_ratio - 0.2)
```

### 6.4 Examples

#### Example 1: High Autonomy
- Total ops (7d): 100
- Safety fails: 2
- Degraded to human: 1
- `autonomy_ratio = (100 - 1 - 2) / 100 = 0.97`

#### Example 2: Consecutive Failures Trigger Degradation
- Consecutive failures: 3 (PASS → FAIL → FAIL → FAIL)
- Degraded to human: True
- `autonomy_ratio = max(0.0, 0.85 - 0.2) = 0.65`

#### Example 3: Low Autonomy
- Total ops (7d): 50
- Safety fails: 10
- Degraded to human: 5
- `autonomy_ratio = (50 - 5 - 10) / 50 = 0.70`

---

## 7. Degradation Logic (EGR-4)

### 7.1 Degradation Triggers

```
┌────────────────────────────────────────────────────────┐
│                  DEGRADATION DECISION TREE             │
├────────────────────────────────────────────────────────┤
│                                                        │
│  ┌──────────────────────────────────────────────┐      │
│  │ consecutive_failures >= 3?                  │      │
│  └─────────────────────┬────────────────────────┘      │
│                   YES/  \NO                           │
│                        │                               │
│                        ▼                               │
│  ┌──────────────────────────────────────────────┐      │
│  │ autonomy_ratio < 0.5?                        │      │
│  └─────────────────────┬────────────────────────┘      │
│                   YES/  \NO                           │
│                        │                               │
│                        ▼                               │
│  ┌──────────────────────────────────────────────┐      │
│  │ safety_failures > 5 in 24h?                  │      │
│  └─────────────────────┬────────────────────────┘      │
│                   YES/  \NO                           │
│                        │                               │
│                        ▼                               │
│              ┌─────────────────┐                       │
│              │ DEGRADE_TO_HUMAN│                       │
│              │ - Log ERROR     │                       │
│              │ - Set flag      │                       │
│              │ - Notify user   │                       │
│              └─────────────────┘                       │
│                                                        │
└────────────────────────────────────────────────────────┘
```

### 7.2 Degradation Actions

When `degraded_to_human = True`:

1. **Log ERROR** to Cloud Logging with `trace_id` and reason
2. **Set flag** in `GCLTrace.degraded_to_human = True`
3. **Notify user** via structured output with human review request
4. **Continue** GCL execution but block final PASS until human acknowledges

### 7.3 Recovery

Human can reset degradation by:
1. Acknowledging the failed operations via tooling
2. Explicitly calling `gcl_runner.py --reset-degradation`

Recovery resets `consecutive_failures = 0` and `autonomy_ratio = 1.0`.

---

## 8. State Snapshot Diff (EGR-5)

### 8.1 How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                      STATE SNAPSHOT DIFF FLOW                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Phase 1: Pre-execution                                          │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ Parse command → extract:                                │     │
│  │   • resource_type (compute, sql, container, storage)  │     │
│  │   • resource_name (instance-id, cluster-name, etc.)    │     │
│  │   • region/zone (if applicable)                       │     │
│  └─────────────────────────┬──────────────────────────────┘     │
│                            │                                     │
│                            ▼                                     │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ Call describe command for resource_type                 │     │
│  │ e.g., gcloud compute instances describe <name>         │     │
│  └─────────────────────────┬──────────────────────────────┘     │
│                            │                                     │
│                            ▼                                     │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ Store as pre_state JSON                               │     │
│  │ { "resource": {...}, "timestamp": "..." }             │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  Phase 2: GCL Execution                                          │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ Run GCL loop as normal                                 │     │
│  │ (Pre-state preserved throughout iterations)            │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
│  Phase 3: Post-execution                                        │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ Call describe command again                            │     │
│  │ Store as post_state JSON                               │     │
│  └─────────────────────────┬──────────────────────────────┘     │
│                            │                                     │
│                            ▼                                     │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ Compute diff: post_state - pre_state                  │     │
│  │   • Added keys                                        │     │
│  │   • Removed keys                                      │     │
│  │   • Changed values                                    │     │
│  └─────────────────────────┬──────────────────────────────┘     │
│                            │                                     │
│                            ▼                                     │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ If diff non-empty AND verdict=PASS:                   │     │
│  │   → Log WARN: "State changed despite PASS verdict"     │     │
│  │   → Include diff in trace                             │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 8.2 Diff Output Format

```json
{
  "trace_id": "gcl-trace-20260718-120000-abc123",
  "state_diff": {
    "resource_type": "compute.googleapis.com/Instance",
    "resource_name": "my-instance",
    "pre_snapshot": {
      "status": "RUNNING",
      "diskConfigs": {...}
    },
    "post_snapshot": {
      "status": "TERMINATED",
      "diskConfigs": {...}
    },
    "changes": [
      {
        "path": "status",
        "old": "RUNNING",
        "new": "TERMINATED"
      }
    ],
    "added_keys": [],
    "removed_keys": [],
    "snapshot_time_pre": "2026-07-18T12:00:00Z",
    "snapshot_time_post": "2026-07-18T12:00:05Z"
  }
}
```

### 8.3 Snapshot Commands

| Resource | Command Template |
|----------|------------------|
| Compute Instance | `gcloud compute instances describe {{name}} --zone={{zone}} --format=json` |
| Cloud SQL Instance | `gcloud sql instances describe {{name}} --format=json` |
| GKE Cluster | `gcloud container clusters describe {{name}} --region={{region}} --format=json` |
| Storage Bucket | `gcloud storage buckets describe gs://{{name}} --format=json` |
| Kubernetes Pod | `kubectl get pod {{name}} -n {{namespace}} -o json` |
| Service Account | `gcloud iam service-accounts describe {{name}} --format=json` |

---

## 9. Exit Codes

| Code | Status | Meaning | Autonomy Impact |
|:----:|--------|---------|----------------|
| 0 | `PASS` | All rubric dimensions ≥ threshold | `consecutive_failures = 0` |
| 1 | `MAX_ITER` | Reached `max_iter`; best-so-far returned | `consecutive_failures += 1` |
| 2 | `SAFETY_FAIL` | Safety = 0 (destructive op not confirmed) | `consecutive_failures += 1`, `safety_failures += 1` |
| 3 | `USAGE_ERROR` | Bad CLI args | No impact |
| 4 | `RUBRIC_ERROR` | Rubric file missing or unparseable | No impact |
| 5 | `DEGRADED` | Degraded to human review required | `degraded_to_human = True` |

---

## 10. Data Flow Summary

```
User/Agent
    │
    ▼
┌────────────────────────────────────────────────────────────────┐
│ Pre-flight: Load rubric, parse command, capture pre-state     │
└────────────────────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────────────────────┐
│ Loop (max_iter times):                                          │
│   1. Generate: Execute command                                  │
│   2. Critique: Score with rubric regexes                        │
│   3. Decide:                                                   │
│      - safety = 0 → SAFETY_FAIL (immediate)                   │
│      - all ≥ threshold → PASS                                  │
│      - retryable error + attempts < 3 → RETRY (backoff)       │
│      - exhausted → MAX_ITER                                     │
│   4. Autonomy Engine: Track failures, check degradation         │
└────────────────────────────────────────────────────────────────┘
    │
    ▼
┌────────────────────────────────────────────────────────────────┐
│ Post-execution:                                                │
│   1. Capture post-state, compute diff                          │
│   2. Collect trace + metrics                                   │
│   3. Upload to BigQuery (async, non-blocking)                  │
│   4. Log to Cloud Logging (synchronous)                       │
│   5. Calculate new autonomy_ratio                              │
│   6. Check degradation threshold                              │
└────────────────────────────────────────────────────────────────┘
    │
    ▼
Exit code (0/1/2/3/4/5)
```

---

## 11. Out of Scope (Level 4)

The following are **not** in this Level 3 spec:

- L4-1: Multi-agent orchestration
- L4-2: Cost-aware routing
- L4-3: Custom rubric editor UI
- L4-4: Slack/Teams notifications
- L4-5: SAML/SSO integration
- L4-6: Predictive failure detection
