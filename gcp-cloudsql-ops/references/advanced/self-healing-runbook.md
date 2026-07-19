# AIOps Self-Healing Runbook — Cloud SQL

> Agent runbook for closed-loop self-healing of Cloud SQL failures: connection-pool exhaustion, high-QPS disk spill (long queries), replica lag. Every remediation action is **dry-run first**, **idempotent**, and **gated**; destructive actions (failover / restart / promote-replica / delete) are marked `HALT`.

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

Cloud SQL can degrade in ways that surface as availability or performance incidents: connection pools exhaust and new clients are rejected, long-running queries spill to disk and starve slots, or read replicas fall behind the primary. This runbook closes the loop:

```
trigger → detect → classify (error-taxonomy) → dry-run remediation → gate check → apply (or HALT) → validate → cross-skill if needed
```

### Safety posture

- **Credential masking (§0.1):** NEVER print SA key content or `GOOGLE_APPLICATION_CREDENTIALS` value. Verify existence only: `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA exists"`. Use `MYSQL_PWD`/`PGPASSWORD` env vars, never CLI `-p`.
- **Dry-run first:** Every mutating action prints the exact `gcloud sql` command it *would* run, then requires an explicit apply step.
- **Idempotent:** Re-applying a flag/parameter with identical value is a no-op if unchanged.
- **HALT on destructive:** Instance restart, failover, promote-replica, delete instance/database → never auto-run.

## Detection Capabilities

| Anomaly | Signal | Severity | Auto-remediable |
|---------|--------|----------|:----------------:|
| Connection pool exhaustion | `connection_count` > 90% of max | Critical | **Yes** (raise max_connections flag) |
| High-QPS disk spill | Long-running queries (`duration` > 300s) | High | **Yes** (cancel long queries) |
| Replica lag | `seconds_behind_master` rising | Critical | No (HALT — manual) |
| Storage near quota | `diskUsageBytes` > 80% of `diskQuota` | Medium | **Yes** (scale storage up) |
| Instance unhealthy | State ≠ `RUNNABLE` | High | No (HALT — manual) |

## Prerequisites

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| SQL Admin API | `gcloud services list --enabled --filter="name:sqladmin.googleapis.com"` | Enabled | `gcloud services enable sqladmin.googleapis.com` |
| Credentials | `gcloud auth print-access-token` | Token returned | HALT — authenticate |
| Credentials file | `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA exists"` | Exists | HALT — set `GOOGLE_APPLICATION_CREDENTIALS=****` |
| Project | `gcloud config get-value project` | Set | HALT — set project |
| Monitoring API (alert trigger) | `gcloud services list --enabled --filter="name:monitoring.googleapis.com"` | Enabled | Delegate to `gcp-monitoring-ops` |

## Trigger Conditions

### T1 — Connection pool exhaustion

Detected as `connection_count` approaching the configured max (default 90% threshold).

```bash
gcloud monitoring time-series list \
  --filter='metric.type="cloudsql.googleapis.com/database/connection_count" AND resource.labels.instance_name="{{user.instance_name}}"' \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" \
  | jq -r '.[].points[-1].value.int64Value // 0' | head -1
```

### T2 — High-QPS disk spill (long queries)

Detected as queries with `duration` > 300s still in `QUERY` operations.

```bash
gcloud sql operations list --instance="{{user.instance_name}}" \
  --filter="operationType=QUERY" --format="json" \
  | jq '.[] | select(.duration > 300) | {id, user, startTime, duration}'
```

### T3 — Storage near quota

Detected as `diskUsageBytes` > 80% of `diskQuota`.

```bash
gcloud sql instances describe "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" \
  | jq -e '(.diskUsageBytes / .diskQuota * 100 | floor) > 80' \
  && echo "STORAGE_NEAR_QUOTA"
```

## Self-Healing Actions

### Action A — Raise max_connections (T1)

> Idempotent, gated. Adjusts the `max_connections` database flag. Never restarts the instance (flag changes are online for most tiers).

#### Dry-run

```bash
INSTANCE="{{user.instance_name}}"
echo "[DRY-RUN] Would set max_connections flag to {{user.new_max_connections}}:"
echo "  gcloud sql instances patch \"$INSTANCE\" --database-flags max_connections={{user.new_max_connections}} \\"
echo "    --project=\"{{env.CLOUDSDK_CORE_PROJECT}}\" --format=json"
echo "[DRY-RUN] Blast radius tier: T1 (single instance, same skill)"
```

#### Idempotency

Re-applying the same flag value is a no-op; the describe check confirms no change before apply.

#### Gate (MANDATORY — human review)

| Gate | Pass condition | On fail |
|------|---------------|--------|
| Flag supported | Tier allows online flag change | HALT — may require restart |
| Increase-only | new ≥ current `max_connections` | HALT — lowering may drop sessions |
| Credential safe | No SA value printed | HALT — mask per §0.1 |

#### Apply

```bash
gcloud sql instances patch "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --database-flags max_connections="{{user.new_max_connections}}" --format="json"
```

#### Validate

```bash
gcloud sql instances describe "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" \
  | jq -e '.settings.databaseFlags[] | select(.name=="max_connections") | .value == "{{user.new_max_connections}}"' \
  && echo "✅ max_connections updated"
```

### Action B — Cancel long-running queries (T2)

> Idempotent, gated. Cancels only queries exceeding the duration threshold. Cancelling a query is non-destructive (it can be re-submitted).

#### Dry-run

```bash
echo "[DRY-RUN] Would cancel the following long queries (duration > 300s):"
gcloud sql operations list --instance="{{user.instance_name}}" \
  --filter="operationType=QUERY" --format="json" \
  | jq -r '.[] | select(.duration > 300) | "[DRY-RUN] op=\(.id) user=\(.user) duration=\(.duration)"'
echo "[DRY-RUN] Blast radius tier: T1 (single instance, same skill)"
```

#### Idempotency

Cancelling an already-finished operation returns NOT_FOUND; re-running finds nothing to cancel — safe no-op.

#### Gate (MANDATORY — human review)

| Gate | Pass condition | On fail |
|------|---------------|--------|
| Only QUERY ops | No DML/DDL in cancel set | HALT — protect in-flight DDL |
| Credential safe | No SA value printed | HALT — mask per §0.1 |

#### Apply

```bash
gcloud sql operations list --instance="{{user.instance_name}}" \
  --filter="operationType=QUERY" --format="json" \
  | jq -r '.[] | select(.duration > 300) | .id' \
  | while read -r op_id; do
      gcloud sql operations cancel "{{user.instance_name}}" "$op_id" \
        --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" || true
    done
```

#### Validate

```bash
gcloud sql operations list --instance="{{user.instance_name}}" \
  --filter="operationType=QUERY" --format="json" \
  | jq -e '[.[] | select(.duration > 300)] | length == 0' \
  && echo "✅ No long queries remaining"
```

### Action C — Scale storage up (T3)

> Idempotent, gated. Increases `diskSize` (only upward; Cloud SQL cannot shrink disks).

#### Dry-run

```bash
INSTANCE="{{user.instance_name}}"
echo "[DRY-RUN] Would increase storage to {{user.new_storage_gb}}GB:"
echo "  gcloud sql instances patch \"$INSTANCE\" --storage-size={{user.new_storage_gb}} \\"
echo "    --project=\"{{env.CLOUDSDK_CORE_PROJECT}}\" --format=json"
echo "[DRY-RUN] Blast radius tier: T1 (single instance, same skill)"
```

#### Idempotency

Re-applying the same (or smaller) size is a no-op; the pre-check only scales if current < target.

#### Gate (MANDATORY — human review)

| Gate | Pass condition | On fail |
|------|---------------|--------|
| Increase-only | new ≥ current `diskSize` | HALT — cannot shrink |
| Credential safe | No SA value printed | HALT — mask per §0.1 |

#### Apply

```bash
CURRENT=$(gcloud sql instances describe "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="value(settings.dataDiskSizeGb)")
if [ "$CURRENT" -lt "{{user.new_storage_gb}}" ]; then
  gcloud sql instances patch "{{user.instance_name}}" \
    --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
    --storage-size="{{user.new_storage_gb}}" --format="json"
fi
```

#### Validate

```bash
gcloud sql instances describe "{{user.instance_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" \
  | jq -e '.settings.dataDiskSizeGb >= ({{user.new_storage_gb}})' \
  && echo "✅ Storage scaled"
```

### HALT list (never auto-mutate)

| Action | Reason |
|--------|--------|
| Restart instance | Connection drop, availability impact |
| Failover / promote-replica | Replication break, data-risk |
| Delete instance / database | Irreversible, data loss |
| Replica rebuild (lag) | Manual coordination required |

## Error Classification

Map every detected anomaly to [docs/error-taxonomy.md](../../../docs/error-taxonomy.md) before choosing remediation. Recovery vocabulary (`HALT` / `RETRY` / `REMEDIATE` / `ESCALATE`) and `idempotent_safe` flag are defined there.

| Cloud SQL symptom | Taxonomy dimension | Canonical code | Recovery | Idempotent safe |
|-------------------|--------------------|----------------|----------|:----------------:|
| Connection exhaustion | Resource | `RESOURCE_EXHAUSTED` | `REMEDIATE` (raise flag) | true |
| Long query disk spill | Performance | `DEADLINE_EXCEEDED` | `REMEDIATE` (cancel) | true |
| Replica lag | Dependency | `UNAVAILABLE` | `HALT` / escalate | false |
| Storage near quota | Quota | `QUOTA_EXCEEDED` | `REMEDIATE` (scale up) | true |
| Instance unhealthy | Dependency | `UNAVAILABLE` | `HALT` | false |
| Transient API failure | Network | `UNAVAILABLE` | `RETRY` | true |
| Unknown internal | Unknown | `INTERNAL` | `RETRY` → `ESCALATE` | true |

## Blast Radius

Apply the tiers from [docs/cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md) (HARD rule: only a pointer — never inline cross-domain descriptions):

- max_connections / cancel query / scale storage → **T1** (same skill, single instance) → dry-run + gate.
- Flag change requiring restart → **T2** (brief connection drop) → note in output.
- Cross-region replica failover → **T3** → `HALT`.
- Instance delete / promote-replica → **T4** → `HALT`, never auto-mutate.

> 详见 docs/cross-skill-blast-radius.md

## GCL Connection

This runbook is the detection→remediation leg of the cross-skill GCL loop. Wire it to the runner so every self-healing action is audited and fed back:

- **State capture:** `gcp-gcl-runner-ops/scripts/gcl_runner_enhanced.py` imports `StateSnapshot` (from `self_correction_mechanism.py`) and invokes it per command to capture pre/post execution state. Use `StateSnapshot` to record the instance flags/storage before and after each Action A/B/C so the diff is provable.
- **Degradation gate:** the same script imports `DegradationDetector` and feeds it consecutive failure patterns; when `failure_count` crosses `threshold` it degrades to human-in-the-loop. Surface repeated `HALT`/failed gates to that detector rather than retrying blindly.
- **Feedback loop:** `gcp-gcl-runner-ops/trace_feedback.py` (`scan_traces`, `aggregate`, `build_report`) consumes persisted GCL traces to compute per-skill quality (`SkillQuality`) — feed it the trace from each self-healing run so Cloud SQL-specific failure patterns refine future auto-remediation thresholds.

> 任务完成后按根 AGENTS.md 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。

## See Also

- [error-taxonomy.md](../../../docs/error-taxonomy.md) — unified cross-skill error classification + recovery vocabulary
- [cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md) — blast radius tiers and gates
- [aiops-query-insights.md](aiops-query-insights.md) — sibling runbook (connection/query anomaly details)
- [gcp-cloudsql-ops SKILL.md](../../SKILL.md) — base operations (instances, replicas, backups)
- [gcp-gcl-runner-ops](../../../gcp-gcl-runner-ops/SKILL.md) — Generator-Critic-Loop runner
