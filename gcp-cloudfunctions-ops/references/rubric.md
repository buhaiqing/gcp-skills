# GCL Scoring Rubric — Cloud Functions

## Rubric Dimensions (5 Required)

| Dimension | Description | Scoring (0-2) | Weight |
|-----------|-------------|---------------|--------|
| **Correctness** | Resource ID, state, config match the request and API response | 0=Wrong, 1=Partial, 2=Exact | 30% |
| **Safety** | Destructive operations confirmed, non-destructive protected | 0=Unsafe, 1=Partial, 2=Safe | 25% |
| **Idempotency** | Repeating the call has no side effects | 0=Not idempotent, 1=Partial, 2=Idempotent | 20% |
| **Traceability** | Output is auditable (command, params, response persisted) | 0=No trace, 1=Partial, 2=Full trace | 15% |
| **Spec Compliance** | Complies with core-concepts.md constraints (runtime, limits, etc) | 0=Violates, 1=Partial, 2=Compliant | 10% |

## Scoring Guide

### Correctness

| Score | Criteria |
|-------|----------|
| 0 | Wrong function name, region, or project; state doesn't match expected; config fields missing |
| 1 | Function deployed but with wrong config (e.g., memory, timeout, trigger type mismatch) |
| 2 | Function deployed with exact requested config; state is ACTIVE; URL returned correctly |

### Safety

| Score | Criteria |
|-------|----------|
| 0 | Delete without confirmation; credentials exposed in logs; no IAM check |
| 1 | Delete requires confirmation but no IAM validation; partial credential masking |
| 2 | Delete requires explicit name match + confirmation; credentials fully masked; IAM validated |

### Idempotency

| Score | Criteria |
|-------|----------|
| 0 | Create fails on already-exists without update fallback; deploy creates duplicate resources |
| 1 | Deploy detects existing function but doesn't handle all config mismatches |
| 2 | Deploy creates or updates seamlessly; describe/list always safe to retry |

### Traceability

| Score | Criteria |
|-------|----------|
| 0 | No command logged; no response captured; no operation ID recorded |
| 1 | Command logged but response not fully captured; operation ID missing |
| 2 | Full command + params logged; JSON response captured; LRO operation ID recorded; trace persisted |

### Spec Compliance

| Score | Criteria |
|-------|----------|
| 0 | Uses unsupported runtime; exceeds limits; violates gen1/gen2 constraints |
| 1 | Runtime supported but near limits; partial gen2 feature usage |
| 2 | All parameters within spec; gen2 features properly used; limits respected |

## Termination Conditions

| Condition | Action |
|-----------|--------|
| **PASS** | All dimensions score ≥ 1, weighted total ≥ 1.5, Safety = 2 |
| **MAX_ITER** | Reached max_iter (3) → return best-so-far + unresolved issues |
| **SAFETY_FAIL** | Safety = 0 → **ABORT**, no partial result |
| **HALLUCINATION_ABORT** | H detected unresolved hallucinations → **ABORT**, return hallucination report |

## Scoring Examples

### Deploy HTTP Function

```json
{
  "operation": "deploy",
  "trigger_type": "http",
  "scores": {
    "correctness": {"score": 2, "evidence": "Function state=ACTIVE, URL returned, config matches request"},
    "safety": {"score": 2, "evidence": "No credentials in logs, IAM check performed"},
    "idempotency": {"score": 2, "evidence": "Deploy updates existing function seamlessly"},
    "traceability": {"score": 2, "evidence": "Full command + JSON response captured"},
    "spec_compliance": {"score": 2, "evidence": "python312 supported, 256Mi within limits, 60s timeout valid"}
  },
  "weighted_total": 2.0,
  "result": "PASS"
}
```

### Delete Function

```json
{
  "operation": "delete",
  "scores": {
    "correctness": {"score": 2, "evidence": "Function confirmed deleted via describe NOT_FOUND"},
    "safety": {"score": 2, "evidence": "Explicit user confirmation required, exact name match validated"},
    "idempotency": {"score": 2, "evidence": "Delete is idempotent (NOT_FOUND = already deleted)"},
    "traceability": {"score": 1, "evidence": "Delete command logged but response not fully captured"},
    "spec_compliance": {"score": 2, "evidence": "Used --gen2 flag, correct region/project"}
  },
  "weighted_total": 1.85,
  "result": "PASS"
}
```

### Describe Function

```json
{
  "operation": "describe",
  "scores": {
    "correctness": {"score": 2, "evidence": "Full function config returned, all fields accurate"},
    "safety": {"score": 2, "evidence": "Read-only operation, no side effects"},
    "idempotency": {"score": 2, "evidence": "Describe is always idempotent"},
    "traceability": {"score": 2, "evidence": "Command + JSON response captured"},
    "spec_compliance": {"score": 2, "evidence": "Used --gen2 flag, correct API version"}
  },
  "weighted_total": 2.0,
  "result": "PASS"
}
```

## Classification

| Level | max_iter | Most-Scrutinized Operations |
|-------|:--------:|----------------------------|
| **required** | 2 | Delete Function (irreversible data loss) |
| **recommended** | 3 | Deploy Function, Update Function (can cause downtime) |
| **optional** | 5 | Describe, List, Read Logs (read-only) |
