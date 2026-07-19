# AIOps Self-Healing — Google Cloud Composer

> Agent-executable self-healing runbook for Cloud Composer / Airflow anomalies. Covers worker pool exhaustion, DAG task failures, and stuck environment upgrades — each with **dry-run → gate → idempotent apply** discipline. Credential masking per AGENTS.md §0.1.

## Table of Contents

1. [Overview](#overview)
2. [Blast Radius](#blast-radius)
3. [Self-Healing Contract](#self-healing-contract)
4. [Anomaly 1: Worker Pool Exhausted / Stuck](#anomaly-1-worker-pool-exhausted--stuck)
5. [Anomaly 2: DAG Task Consecutive Failures](#anomaly-2-dag-task-consecutive-failures)
6. [Anomaly 3: Environment Upgrade Stuck](#anomaly-3-environment-upgrade-stuck)
7. [Error Taxonomy Mapping](#error-taxonomy-mapping)
8. [See Also](#see-also)

## Overview

Composer runs Airflow on a managed GKE cluster. Self-healing must be **safe-by-default**: every mutating action is gated behind a dry-run and an explicit human approval gate, and is idempotent so re-running never doubles the effect.

| Anomaly | Signal | Recovery Action | Recovery Verb | Idempotent |
|---------|--------|-----------------|---------------|:-----------:|
| Worker pool exhausted / stuck | `worker_pods_pending`, scheduler lag, task queue backlog | Scale worker (increase node count / machine type) | `REMEDIATE` | true |
| DAG task consecutive failures | N failed task instances in window | Pause DAG + notify | `REMEDIATE` | true |
| Environment upgrade stuck | `UPDATE` operation in `RUNNING` > SLA, no progress | Diagnose + recommend rollback | `HALT` | n/a (human) |

> Recovery verbs follow `docs/error-taxonomy.md` (authoritative). `HALT` = stop and require human decision; `REMEDIATE` = apply known-safe action.

## Blast Radius

Composer is **not** a leaf service — it sits on top of other GCP products. A Composer failure cascades into the data pipelines it orchestrates.

| Dependency | Failure Mode in Composer | Downstream Impact |
|------------|--------------------------|-------------------|
| **GKE** (worker/scheduler nodes) | Node pool drained, OOM, image pull backoff | All DAG tasks stall; no new task slots |
| **GCS** (DAG bucket, task logs) | Bucket IAM lost, bucket deleted | DAGs fail to parse/load; logs unavailable |
| **BigQuery** (common operator target) | Quota/permission error on `BigQueryInsertJob` | Data pipeline tasks fail; partial loads |
| **Cloud SQL** (Airflow metadata DB) | Metadata DB unreachable | Scheduler cannot heartbeat; tasks orphaned |
| **Pub/Sub / other operators** | Auth/quota on downstream service | Operator-specific task failures |

**Containment rule:** A Composer anomaly whose root cause is a dependency (GKE/GCS/BigQuery/SQL) MUST be delegated to that product's skill after the local containment step. Do **not** attempt to remediate the dependency from within Composer — only pause/scale the Composer surface to stop the bleed, then hand off.

> Cross-skill blast-radius aggregation is tracked in `docs/cross-skill-blast-radius.md` (⬜ planned — not yet authored). Until that doc exists, use the table above as the local source of truth.

## Self-Healing Contract

Every self-healing action in this runbook obeys:

1. **Dry-run first.** Print the exact command that *would* mutate, with `--dry-run` or a describe-only probe. Never mutate on the first pass.
2. **Gate.** Require explicit human approval (`APPROVE` / `HALT`) before any mutating step. `HALT` anomalies (upgrade stuck) never auto-apply.
3. **Idempotent.** Re-running the action yields no further change (e.g. scaling to a target count that is already met is a no-op; pausing an already-paused DAG is a no-op).
4. **Credential masking (AGENTS.md §0.1).** Never print SA key content or `GOOGLE_APPLICATION_CREDENTIALS` value. Verify existence only: `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA exists"`.

```bash
# Probe env state (read-only, safe)
gcloud composer environments describe "{{user.environment_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --location="{{user.region}}" \
  --format="json" | jq '{name, state, config: .config.softwareConfig.imageVersion}'
```

## Anomaly 1: Worker Pool Exhausted / Stuck

**Symptom:** Tasks queue but no slots free; `kubectl get pods -n {composer-namespace}` shows `Pending` worker pods; scheduler lag rising.

### Step 1 — Diagnose (read-only)

```bash
# Worker pod state
gcloud composer environments describe "{{user.environment_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --location="{{user.region}}" \
  --format="json" | jq '.config.workloadsConfig'

# Node pool utilization (delegates to gcp-gke-ops for deep dive)
gcloud container node-pools list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --region="{{user.region}}" \
  --cluster="$(gcloud composer environments describe {{user.environment_name}} --project={{env.CLOUDSDK_CORE_PROJECT}} --location={{user.region}} --format='get(config.gkeClusterName)')" \
  --format="json"
```

### Step 2 — Dry-run (no mutation)

```bash
# Preview the scale-up target. Compute desired = current + delta; show only.
CURRENT=$(gcloud container node-pools describe "{{user.node_pool}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --region="{{user.region}}" \
  --cluster="{{user.gke_cluster}}" \
  --format="get(initialNodeCount)")
echo "DRY-RUN: would scale node pool {{user.node_pool}} from $CURRENT to $((CURRENT + {{user.scale_delta}}))"
```

### Step 3 — Gate

```
[HALT/APPROVE] Scale worker node pool {{user.node_pool}} +{{user.scale_delta}} nodes?
  DRY-RUN target: {{user.node_pool}} -> $((CURRENT + scale_delta))
  Blast radius: GKE node count increase (cost + scheduling). No DAG data touched.
```
Wait for explicit `APPROVE`. On `HALT`, stop and surface to human.

### Step 4 — Apply (idempotent)

```bash
# Idempotent: if already at/above target, skip.
TARGET=$((CURRENT + {{user.scale_delta}}))
ACTUAL=$(gcloud container node-pools describe "{{user.node_pool}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --region="{{user.region}}" \
  --cluster="{{user.gke_cluster}}" \
  --format="get(initialNodeCount)")
if [ "$ACTUAL" -ge "$TARGET" ]; then
  echo "RESULT: node pool already at $ACTUAL >= $TARGET — no-op"
else
  gcloud container node-pools resize "{{user.node_pool}}" \
    --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
    --region="{{user.region}}" \
    --cluster="{{user.gke_cluster}}" \
    --num-nodes="$TARGET" --quiet
  echo "RESULT: scaled {{user.node_pool}} to $TARGET"
fi
```

### Step 5 — Validate

```bash
# Confirm pending worker pods drain
gcloud composer environments describe "{{user.environment_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --location="{{user.region}}" --format="get(state)"
# Expect RUNNING and task queue backlog decreasing.
```

## Anomaly 2: DAG Task Consecutive Failures

**Symptom:** Same DAG fails ≥ `{{user.fail_threshold}}` (default 3) task instances within `{{user.window}}` (default 1h).

### Step 1 — Diagnose (read-only)

```bash
# List recent failed task instances for a DAG
gcloud composer environments run "{{user.environment_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --location="{{user.region}}" \
  tasks failed-deps "{{user.dag_id}}" -- "{{user.dag_id}}"
```

### Step 2 — Dry-run (no mutation)

```bash
# Preview pause; do not execute.
echo "DRY-RUN: would pause DAG {{user.dag_id}} (currently: $(gcloud composer environments run {{user.environment_name}} --project={{env.CLOUDSDK_CORE_PROJECT}} --location={{user.region}} dags state "{{user.dag_id}}" -- "{{user.dag_id}}"))"
```

### Step 3 — Gate

```
[HALT/APPROVE] Pause DAG {{user.dag_id}} and notify on-call?
  Effect: stops further scheduled runs; in-flight tasks unaffected.
  Blast radius: halts this DAG's pipeline only (contained).
```
Wait for `APPROVE`.

### Step 4 — Apply (idempotent)

```bash
# Idempotent: pausing an already-paused DAG is a no-op.
gcloud composer environments run "{{user.environment_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --location="{{user.region}}" \
  dags pause "{{user.dag_id}}" -- "{{user.dag_id}}"

# Notify (env-var driven; never inline secrets)
"$COMPOSER_NOTIFY_WEBHOOK" && curl -sS -X POST "$COMPOSER_NOTIFY_WEBHOOK" \
  -H "Content-Type: application/json" \
  -d "{\"dag\":\"{{user.dag_id}}\",\"env\":\"{{user.environment_name}}\",\"action\":\"paused\",\"reason\":\"consecutive_task_failures\"}"
echo "RESULT: DAG {{user.dag_id}} paused + on-call notified"
```

### Step 5 — Validate

```bash
gcloud composer environments run "{{user.environment_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --location="{{user.region}}" \
  dags state "{{user.dag_id}}" -- "{{user.dag_id}}"
# Expect: paused
```

## Anomaly 3: Environment Upgrade Stuck

**Symptom:** `UPDATE` operation stays `RUNNING` beyond SLA (e.g. >30 min) with no progress; environment never returns to `RUNNING`.

> **This is a `HALT` anomaly. No auto-mutation. Diagnose and recommend rollback to human.**

### Step 1 — Diagnose (read-only)

```bash
# List in-flight operations
gcloud composer operations list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --location="{{user.region}}" \
  --filter="metadata.target~{{user.environment_name}} AND done=false" \
  --format="json"

# Operation age vs SLA
gcloud composer operations describe "{{user.operation_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --location="{{user.region}}" \
  --format="json" | jq '{name, done, metadata: .metadata.verb, startTime}'
```

### Step 2 — Root-cause probe (read-only)

```bash
# Check if stuck is dependency-side (GKE node drain / GCS IAM) — see Blast Radius.
gcloud composer environments describe "{{user.environment_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --location="{{user.region}}" \
  --format="json" | jq '{state, config: .config.softwareConfig.imageVersion}'
```

### Step 3 — HALT (human decision)

```
[HALT] Environment upgrade {{user.operation_name}} stuck > SLA.
  Recommendation: roll back to previous image version OR cancel update.
  Dependency-side root cause (GKE/GCS/SQL)? → delegate to that skill first.
  No auto-apply. Awaiting human decision: [ROLLBACK | CANCEL | KEEP_WAITING]
```

Provide the human with the exact rollback command (do NOT execute):

```bash
# Rollback preview (HUMAN EXECUTES — agent must not auto-run)
gcloud composer environments update "{{user.environment_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --location="{{user.region}}" \
  --image-version="{{user.previous_image_version}}" \
  --format="json"
```

## Error Taxonomy Mapping

Map Composer self-healing outcomes to `docs/error-taxonomy.md` canonical codes:

| Local Signal | Canonical Code | Recovery | Idempotent |
|--------------|----------------|----------|:-----------:|
| Worker nodes exhausted | `QUOTA_EXCEEDED` / `RESOURCE_EXHAUSTED` | `REMEDIATE` (scale) | true |
| DAG task auth/perm failure | `PERMISSION_DENIED` | `REMEDIATE` (pause + notify) | true |
| Upgrade stuck (timeout) | `TIMEOUT` / `DEADLINE_EXCEEDED` | `HALT` | n/a |
| Dependency (GKE/GCS/SQL) root cause | `UNAVAILABLE` | `HALT` → delegate | n/a |

## See Also

- [Error Taxonomy (authoritative)](../../../docs/error-taxonomy.md) — canonical recovery verbs and idempotency flags
- [Cross-Skill Blast Radius](../../../docs/cross-skill-blast-radius.md) (⬜ planned) — aggregated dependency impact across skills
- [Troubleshooting Guide](../troubleshooting.md) — product-specific diagnosis
- [Advanced DAG Patterns](advanced-dag-patterns.md) — DAG design to reduce failure blast radius
- [gcp-gke-ops](../../../gcp-gke-ops/SKILL.md) — delegate node-pool remediation
- [gcp-gcs-ops](../../../gcp-gcs-ops/SKILL.md) — delegate DAG-bucket IAM remediation
