# AIOps Self-Healing Runbook — BigQuery

> Agent runbook for closed-loop self-healing of BigQuery failures: slot exhaustion, runaway query cost, stale/orphan tables, partition expiry drift. Every remediation action is **dry-run first**, **idempotent**, and **gated**; destructive actions (delete dataset/table, DDL on production) are marked `HALT`.

## Table of Contents

1. [Overview](#overview)
2. [Detection Capabilities](#detection-capabilities)
3. [Prerequisites](#prerequisites)
4. [Trigger Conditions](#trigger-conditions)
5. [Self-Healing Actions](#self-healing-actions)
6. [Error Classification](#error-classification)
7. [Blast Radius](#blast-radius)
8. [GCL Connection](#gcl-connection)
9. [See Also](#see-also)

## Overview

BigQuery can degrade in ways that burn budget or stall pipelines: reservations run out of slots and queries queue indefinitely, a single query blows past the cost ceiling, or partition expiry drifts so cold data never gets pruned. This runbook closes the loop:

```
trigger → detect → classify (error-taxonomy) → dry-run remediation → gate check → apply (or HALT) → validate → cross-skill if needed
```

### Safety posture

- **Credential masking (§0.1):** NEVER print SA key content or `GOOGLE_APPLICATION_CREDENTIALS` value. Verify existence only: `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA exists"`.
- **Dry-run first:** Every mutating action prints the exact `bq` command it *would* run, then requires an explicit apply step.
- **Idempotent:** Re-applying a config with identical params is a no-op if unchanged.
- **HALT on destructive:** Delete dataset/table, DROP column, alter production schema → never auto-run.

## Detection Capabilities

| Anomaly | Signal | Severity | Auto-remediable |
|---------|--------|----------|:----------------:|
| Slot exhaustion | Pending slots > 0 for > 5 min | Critical | **Yes** (assign reservation) |
| Runaway query cost | `total_bytes_billed` > `{{user.cost_ceiling}}` | High | **Yes** (cancel job) |
| Stale/orphan table | `last_modified` > 90d + no access | Low | **Yes** (flag for review) |
| Partition expiry drift | `timePartitioning.expirationMs` unset | Medium | **Yes** (set expiry) |
| Job stuck in PENDING | State `PENDING` > 10 min | Medium | **Yes** (cancel job) |

## Prerequisites

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| BigQuery API | `gcloud services list --enabled --filter="name:bigquery.googleapis.com"` | Enabled | `gcloud services enable bigquery.googleapis.com` |
| Credentials | `gcloud auth print-access-token` | Token returned | HALT — authenticate |
| Credentials file | `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA exists"` | Exists | HALT — set `GOOGLE_APPLICATION_CREDENTIALS=****` |
| Project | `gcloud config get-value project` | Set | HALT — set project |
| Monitoring API (alert trigger) | `gcloud services list --enabled --filter="name:monitoring.googleapis.com"` | Enabled | Delegate to `gcp-monitoring-ops` |

## Trigger Conditions

### T1 — Slot exhaustion

Detected as pending slots > 0 sustained over the window.

```bash
bq ls -j -a --project_id="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json \
  | jq -r '.[] | select(.state=="PENDING") | .id'
```

### T2 — Runaway query cost

Detected as a running job whose `total_bytes_billed` exceeds the cost ceiling.

```bash
bq ls -j -a --project_id="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json \
  | jq -r '.[] | select(.state=="RUNNING") | .id' \
  | while read -r job; do
      billed=$(bq show --format=json "$job" | jq -r '.statistics.totalBytesBilled // 0')
      [ "$billed" -gt "{{user.cost_ceiling_bytes}}" ] && echo "RUNWAY $job billed=$billed"
    done
```

### T3 — Partition expiry drift

Detected as a partitioned table missing `timePartitioning.expirationMs`.

```bash
bq show --format=json "{{user.project}}:{{user.dataset}}.{{user.table}}" \
  | jq -e '.timePartitioning.expirationMs == null' \
  && echo "NO_EXPIRY"
```

## Self-Healing Actions

### Action A — Assign reservation to pending jobs (T1)

> Idempotent, gated. Moves the project/dataset into an existing reservation with spare capacity. Never creates new reservations (cost → HALT).

#### Dry-run

```bash
echo "[DRY-RUN] Would assign {{user.dataset}} to reservation {{user.reservation_id}}:"
echo "  bq update --reservation_assignment_id={{user.reservation_id}} \\"
echo "    --project_id=\"{{env.CLOUDSDK_CORE_PROJECT}}\" {{user.dataset}}"
echo "[DRY-RUN] Blast radius tier: T1 (single dataset, same skill)"
```

#### Idempotency

Re-assigning an already-assigned dataset is a no-op; the describe check confirms current assignment before apply.

#### Gate (MANDATORY — human review)

| Gate | Pass condition | On fail |
|------|---------------|--------|
| Reservation exists | `bq show --reservation` returns 200 | HALT — no spare capacity |
| No new reservation | Only reassign, no create | HALT — cost impact |
| Credential safe | No SA value printed | HALT — mask per §0.1 |

#### Apply

```bash
bq update --reservation_assignment_id="{{user.reservation_id}}" \
  --project_id="{{env.CLOUDSDK_CORE_PROJECT}}" "{{user.dataset}}"
```

#### Validate

```bash
bq show --format=json "{{user.dataset}}" \
  | jq -e '.reservation_assignment_id == "{{user.reservation_id}}"' \
  && echo "✅ Reservation assigned"
```

### Action B — Cancel runaway / stuck job (T2, T1-stuck)

> Idempotent, gated. Cancels only jobs exceeding the cost ceiling or stuck in PENDING. Cancelling a job is non-destructive (it can be re-submitted).

#### Dry-run

```bash
echo "[DRY-RUN] Would cancel the following jobs:"
bq ls -j -a --project_id="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json \
  | jq -r '.[] | select(.state=="RUNNING" or .state=="PENDING") | "[DRY-RUN] job=\(.id) state=\(.state)"'
echo "[DRY-RUN] Blast radius tier: T1 (single project, same skill)"
```

#### Idempotency

Cancelling an already-finished job returns NOT_FOUND; re-running finds nothing to cancel — safe no-op.

#### Gate (MANDATORY — human review)

| Gate | Pass condition | On fail |
|------|---------------|--------|
| Only RUNNING/PENDING | No DDL/DML jobs in cancel set | HALT — protect in-flight writes |
| Credential safe | No SA value printed | HALT — mask per §0.1 |

#### Apply

```bash
bq ls -j -a --project_id="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json \
  | jq -r '.[] | select(.state=="RUNNING" or .state=="PENDING") | .id' \
  | while read -r job; do
      bq cancel --project_id="{{env.CLOUDSDK_CORE_PROJECT}}" "$job" || true
    done
```

#### Validate

```bash
bq ls -j -a --project_id="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json \
  | jq -e '[.[] | select(.state=="RUNNING" or .state=="PENDING")] | length == 0' \
  && echo "✅ No stuck/runaway jobs"
```

### Action C — Set partition expiry (T3)

> Idempotent, gated. Sets `timePartitioning.expirationMs` on a partitioned table. Never deletes data (expiry only prunes future-old partitions).

#### Dry-run

```bash
echo "[DRY-RUN] Would set partition expiry to {{user.expiration_ms}}ms on {{user.table}}:"
echo "  bq update --time_partitioning_expiration={{user.expiration_ms}} \\"
echo "    --project_id=\"{{env.CLOUDSDK_CORE_PROJECT}}\" {{user.dataset}}.{{user.table}}"
echo "[DRY-RUN] Blast radius tier: T1 (single table, same skill)"
```

#### Idempotency

Re-applying the same expiry is a no-op; the describe check confirms current value before apply.

#### Gate (MANDATORY — human review)

| Gate | Pass condition | On fail |
|------|---------------|--------|
| Table partitioned | `timePartitioning.type` set | HALT — not partitionable |
| Credential safe | No SA value printed | HALT — mask per §0.1 |

#### Apply

```bash
bq update --time_partitioning_expiration="{{user.expiration_ms}}" \
  --project_id="{{env.CLOUDSDK_CORE_PROJECT}}" "{{user.dataset}}.{{user.table}}"
```

#### Validate

```bash
bq show --format=json "{{env.CLOUDSDK_CORE_PROJECT}}:{{user.dataset}}.{{user.table}}" \
  | jq -e '.timePartitioning.expirationMs == ({{user.expiration_ms}})' \
  && echo "✅ Partition expiry set"
```

### HALT list (never auto-mutate)

| Action | Reason |
|--------|--------|
| Delete dataset / table | Irreversible, data loss |
| DROP column / ALTER schema | Data-loss / contract break |
| Create new reservation | Cost impact |
| Cross-project query kill | Out of scope, blast radius T3/T4 |

## Error Classification

Map every detected anomaly to [docs/error-taxonomy.md](../../../docs/error-taxonomy.md) before choosing remediation. Recovery vocabulary (`HALT` / `RETRY` / `REMEDIATE` / `ESCALATE`) and `idempotent_safe` flag are defined there.

| BigQuery symptom | Taxonomy dimension | Canonical code | Recovery | Idempotent safe |
|------------------|--------------------|----------------|----------|:----------------:|
| Slot exhaustion | Resource | `RESOURCE_EXHAUSTED` | `REMEDIATE` (assign) | true |
| Runaway query cost | Quota | `QUOTA_EXCEEDED` | `REMEDIATE` (cancel) | true |
| Stuck PENDING job | Performance | `DEADLINE_EXCEEDED` | `REMEDIATE` (cancel) | true |
| Partition expiry drift | Configuration | `INVALID_ARGUMENT` | `REMEDIATE` (set) | true |
| Stale/orphan table | Configuration | `INVALID_ARGUMENT` | `REMEDIATE` (flag) | true |
| Transient API failure | Network | `UNAVAILABLE` | `RETRY` | true |
| Unknown internal | Unknown | `INTERNAL` | `RETRY` → `ESCALATE` | true |

## Blast Radius

Apply the tiers from [docs/cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md) (HARD rule: only a pointer — never inline cross-domain descriptions):

- Assign reservation / cancel job / set expiry → **T1** (same skill, single dataset/table) → dry-run + gate.
- Cross-dataset reservation move → **T2** (affects multiple datasets) → note in output.
- Cross-project query kill / org reservation change → **T3/T4** → `HALT`, never auto-mutate.

> 详见 docs/cross-skill-blast-radius.md

## GCL Connection

This runbook is the detection→remediation leg of the cross-skill GCL loop. Wire it to the runner so every self-healing action is audited and fed back:

- **State capture:** `gcp-gcl-runner-ops/scripts/gcl_runner_enhanced.py` imports `StateSnapshot` (from `self_correction_mechanism.py`) and invokes it per command to capture pre/post execution state. Use `StateSnapshot` to record the dataset reservation / job state / partition config before and after each Action A/B/C so the diff is provable.
- **Degradation gate:** the same script imports `DegradationDetector` and feeds it consecutive failure patterns; when `failure_count` crosses `threshold` it degrades to human-in-the-loop. Surface repeated `HALT`/failed gates to that detector rather than retrying blindly.
- **Feedback loop:** `gcp-gcl-runner-ops/trace_feedback.py` (`scan_traces`, `aggregate`, `build_report`) consumes persisted GCL traces to compute per-skill quality (`SkillQuality`) — feed it the trace from each self-healing run so BigQuery-specific failure patterns refine future auto-remediation thresholds.

> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。

## See Also

- [error-taxonomy.md](../../../docs/error-taxonomy.md) — unified cross-skill error classification + recovery vocabulary
- [cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md) — blast radius tiers and gates
- [aiops-bigquery-anomaly.md](aiops-bigquery-anomaly.md) — sibling runbook (slot/cost anomaly details)
- [gcp-bigquery-ops SKILL.md](../../SKILL.md) — base operations (datasets, jobs, reservations)
- [gcp-gcl-runner-ops](../../../gcp-gcl-runner-ops/SKILL.md) — Generator-Critic-Loop runner
