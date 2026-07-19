# AIOps Self-Healing — Memorystore for Redis

> Agent runbook for AIOps-driven anomaly detection and self-healing of Memorystore for Redis: memory-pressure remediation, slow-query/blocking diagnosis, and HA failover self-verification. Lazy-loaded per TE-7.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Anomaly → Remediation Map](#anomaly--remediation-map)
4. [Memory Pressure (OOM / Eviction Storm)](#memory-pressure-oom--eviction-storm)
5. [Slow Query / Blocking Detection](#slow-query--blocking-detection)
6. [HA Failover Self-Verification](#ha-failover-self-verification)
7. [Blast Radius](#blast-radius)
8. [Self-Healing Safety Model](#self-healing-safety-model)
9. [Error Taxonomy Mapping](#error-taxonomy-mapping)
10. [See Also](#see-also)

## Overview

AIOps self-healing for Memorystore covers three failure classes that managed Redis commonly hits:

- **Memory pressure** — `used_memory` approaching `maxmemory` → eviction storm or OOM → app cache-miss spike.
- **Slow query / blocking** — long-running commands (`KEYS`, `FLUSHALL`, big `MGET`, Lua) block the single-threaded event loop → latency spikes on all clients.
- **HA failover** — Standard-tier primary/replica switch; apps must reconnect idempotently and replica must be healthy.

Every mutating remediation in this runbook is **dry-run first**, **idempotent**, and gated by a **blast-radius tier** (T1–T4). Destructive actions are marked **HALT** and require human confirmation. Credential handling follows **AGENTS.md §0.1** (never log/expose SA keys or auth strings).

### Detection Capabilities

| Anomaly | Signal | Severity | Tier |
|---------|--------|----------|------|
| Memory high | `memory_usage_ratio > 0.85` | High | T1/T2 |
| Eviction storm | `evicted_keys` rate spike | Medium | T1 |
| Slow command | `instantaneous_ops_per_sec` dip + latency | Medium | T1 |
| Blocking cmd | `latest_fork_usec` / `cmd latency` | High | T1 |
| Failover | `redis_replica_lag` / role change | Medium | T3 |
| Auth rejected | `NOAUTH` on clients | High | T3 |

## Prerequisites

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Redis API | `gcloud redis instances list --region="{{user.region}}" --format=json` | Exit 0 | HALT — enable `redis.googleapis.com` |
| Monitoring | `gcloud services list --enabled --filter="name:monitoring.googleapis.com"` | Enabled | `gcloud services enable monitoring.googleapis.com` |
| Credentials | `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA exists"` | File present | HALT — set `GOOGLE_APPLICATION_CREDENTIALS` (never print content) |

## Anomaly → Remediation Map

| Anomaly | Dry-run preview | Auto action | Gate |
|---------|-----------------|-------------|------|
| Memory > 85% | Show target size + eviction policy | Scale up / set `allkeys-lru` | T1: REMEDIATE after dry-run |
| Eviction storm | Show current `maxmemory-policy` | Switch to `volatile-lru` | T1: REMEDIATE |
| Slow/blocking cmd | Show top commands | Advise only (no mutate) | T1: ADVISE |
| Failover | Show replica health | Verify replica + idempotent reconnect | T3: VERIFY + coordinate |
| Auth rotation | Show rotation plan | Rotate + rollout to apps | T3: HALT (credential mutation) |
| Delete / Import | Show impact | — | T4: HALT (human) |

## Memory Pressure (OOM / Eviction Storm)

### Step 1 — Detect & Diagnose

```bash
# Memory usage ratio (Cloud Monitoring)
gcloud monitoring time-series list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --filter='metric.type="redis.googleapis.com/instance/memory_usage_ratio"' \
  --format="json" | jq -r '.timeSeries[].points[-1].value.doubleValue'

# Current config (no credential output — §0.1)
gcloud redis instances describe "{{user.instance_name}}" \
  --region="{{user.region}}" --format="json" \
  | jq '{memorySizeGb, state, tier, redisConfigs}'
```

### Step 2 — Dry-run Preview (MANDATORY before mutate)

```bash
# Preview scale-up target — compute only, no API write
CURRENT_GB=$(gcloud redis instances describe "{{user.instance_name}}" \
  --region="{{user.region}}" --format="json" | jq -r '.memorySizeGb')
TARGET_GB=$(( CURRENT_GB * 2 ))
echo "[DRY-RUN] Would scale {{user.instance_name}} from ${CURRENT_GB}GB to ${TARGET_GB}GB"
echo "[DRY-RUN] Would set maxmemory-policy=allkeys-lru (if eviction storm)"
```

> **Gate:** Present the dry-run block to the operator. Only proceed to Step 3 if confirmed AND tier ≤ T2.

### Step 3 — Execute (idempotent)

```bash
# Scale up — idempotent: re-applying same size is a no-op
gcloud redis instances update "{{user.instance_name}}" \
  --region="{{user.region}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --memory-size="${TARGET_GB}GB" --format="json"

# Eviction policy adjustment (safe, idempotent)
gcloud redis instances update "{{user.instance_name}}" \
  --region="{{user.region}}" \
  --redis-config="maxmemory-policy=allkeys-lru" --format="json"
```

### Step 4 — Validate

```bash
gcloud redis instances describe "{{user.instance_name}}" \
  --region="{{user.region}}" --format="json" \
  | jq '{memorySizeGb, redisConfigs, state}'
```

> **Idempotency:** scaling to the same `memory-size` or re-setting the same `maxmemory-policy` is a no-op; safe to retry.

## Slow Query / Blocking Detection

Redis is single-threaded; one slow command blocks all clients. Diagnosis is **read-only** — the agent ADVISES, it does not mutate.

### Diagnose

```bash
# SLOWLOG — last 20 entries (read-only, safe)
redis-cli -h "{{output.host}}" -p "{{output.port}}" \
  -a "$REDIS_AUTH" SLOWLOG GET 20 2>/dev/null | jq '.[] | {duration: .[1], command: .[3][0]}'

# Identify blocking patterns
redis-cli -h "{{output.host}}" -p "{{output.port}}" \
  -a "$REDIS_AUTH" SLOWLOG GET 20 2>/dev/null \
  | jq -r '.[][3][0]' | sort | uniq -c | sort -rn | head
```

> **Credential note (§0.1):** auth string is passed via env var `$REDIS_AUTH`, never echoed. Verify existence only: `test -n "$REDIS_AUTH" && echo "✅ auth set"`.

### Advice (no mutate)

| Pattern | Likely cause | Recommendation |
|---------|--------------|----------------|
| `KEYS *` | Full scan on large keyspace | Replace with `SCAN` (cursor iterator) |
| `FLUSHALL` / `FLUSHDB` | Manual/buggy purge | Restrict via rename-command; require approval |
| Big `MGET` / `HGETALL` | Large object fetch | Pipeline + shard; cap object size |
| Lua `EVAL` long loop | Blocking script | Move logic to client; add `lua-time-limit` |
| `DEL` large key | Synchronous free | Use `UNLINK` (async free) |

> **Gate:** If a blocking command is **recurring and automated**, escalate to human (HALT) — do not auto-rename commands (config mutation with app impact, T3).

## HA Failover Self-Verification

Standard tier auto-fails over on primary failure. After a failover event (or a manual `gcloud redis instances failover`), verify replica health and that clients can reconnect idempotently.

### Step 1 — Verify Replica Health

```bash
gcloud redis instances describe "{{user.instance_name}}" \
  --region="{{user.region}}" --format="json" \
  | jq '{tier, state, currentLocationId, persistenceConfig}'

# Replica lag (Cloud Monitoring) — should be ~0 after settle
gcloud monitoring time-series list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --filter='metric.type="redis.googleapis.com/replication/redis_replica_lag"' \
  --format="json" | jq -r '.timeSeries[].points[-1].value.int64Value'
```

### Step 2 — Idempotent Reconnect Verification (T3)

```bash
# Probe connectivity — idempotent, no state change
redis-cli -h "{{output.host}}" -p "{{output.port}}" \
  -a "$REDIS_AUTH" PING 2>/dev/null | grep -q PONG \
  && echo "✅ Reconnect OK (idempotent)" \
  || echo "❌ Reconnect FAILED — coordinate with gcp-gce-ops / gcp-gke-ops"
```

> **T3 coordination:** If reconnect fails, the dependent GCE/GKE apps are affected. Delegate connectivity verification to `gcp-gce-ops` / `gcp-gke-ops` — do NOT mutate app config from this skill. See [docs/cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md).

### Step 3 — Validate

```bash
gcloud redis instances describe "{{user.instance_name}}" \
  --region="{{user.region}}" --format="json" | jq '{host, port, state, currentLocationId}'
```

## Blast Radius

Memorystore failures radiate to dependent GCE/GKE workloads. Compute the tier before any mutating action.

> Blast radius follows [docs/cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md) — compute T1–T4 before any mutating action.

| Upstream fault | Downstream impact | Dependent skill | Owner |
|----------------|------------------|----------------|-------|
| OOM / eviction storm | App cache-miss → DB load ↑ | `gcp-gce-ops` / `gcp-gke-ops` | Memorystore (resize) |
| Failover | Brief client reset | `gcp-gce-ops` / `gcp-gke-ops` | Memorystore (verify) + app reconnect |
| Auth rotation | `NOAUTH` on all clients | `gcp-gce-ops` / `gcp-gke-ops` | HALT — coordinate rollout |
| Delete / Import | Total cache loss | `gcp-gce-ops` / `gcp-gke-ops` | HALT — human |

**Tier decision:**

| Radius | Action | Gate |
|--------|--------|------|
| T1 (single instance) | REMEDIATE in-skill | dry-run |
| T2 (region-wide) | REMEDIATE + notify | dry-run |
| T3 (cross-product) | coordinate | dry-run + cross-skill confirm |
| T4 (shared infra) | HALT | human |

## Self-Healing Safety Model

### Dry-run + Idempotency + Gate (all mutating actions)

1. **Dry-run:** Every scale/config change prints a preview block first (Step 2 pattern). No API write until confirmed.
2. **Idempotent:** Re-applying the same `memory-size` / `maxmemory-policy` is a no-op; safe to retry on transient `UNAVAILABLE`.
3. **Gate by tier:** T1/T2 auto-remediate after dry-run; T3 coordinates with dependent skill; T4 HALT.

### Destructive Actions → HALT

| Action | Why HALT |
|--------|---------|
| Delete instance | Irreversible data loss (T4) |
| Import (overwrites data) | Destructive to existing keys (T4) |
| Auth string rotation | Breaks all live connections (T3) |
| Rename/disable commands | App-compatibility breaking change (T3) |

> These are delegated to the operator with explicit resource identifier and impact warning — never auto-applied by the self-heal loop.

### Credential Masking (§0.1 — MANDATORY)

| Context | Safe | Unsafe |
|---------|------|--------|
| Auth string | `redis-cli -a "$REDIS_AUTH"` (env var) | `redis-cli -a 'actual-password'` |
| SA key | `test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA exists"` | `cat $GOOGLE_APPLICATION_CREDENTIALS` |
| Error msg | `Error: API call failed (credential omitted)` | actual SA key / auth string content |

## Error Taxonomy Mapping

Error codes follow [docs/error-taxonomy.md](../../../docs/error-taxonomy.md). Product-specific codes map to a root-cause dimension:

| Memorystore symptom | Canonical code | Dimension | Recovery |
|---------------------|---------------|----------|----------|
| Instance OOM / memory exhausted | `STORAGE_FULL` | Resource State | `REMEDIATE` (resize) |
| Quota / concurrent-op limit | `QUOTA_EXCEEDED` | Quota | `REMEDIATE` (request increase) |
| Replica lag / broken replication | `REPLICA_FAILED` | Resource State | `REMEDIATE` (verify replica) |
| SA lacks `roles/redis.admin` | `PERMISSION_DENIED` | Permission | `REMEDIATE` (grant role) |
| SA key missing / token expired | `AUTH_FAILED` | Authentication | `REMEDIATE` (fix creds) |
| Service temporarily unreachable | `UNAVAILABLE` | Network | `RETRY` (backoff) |
| Invalid memory size / version | `INVALID_ARGUMENT` | Configuration | `HALT` (fix param) |
| Instance not found | `NOT_FOUND` | Resource State | `HALT` (verify name) |

> Per-skill diagnosis stays in `references/troubleshooting.md`; this table only maps to the canonical dimension for cross-skill aggregation.

## See Also

- [Error Taxonomy](../../../docs/error-taxonomy.md) — canonical cross-skill error classification
- [Cross-Skill Blast Radius](../../../docs/cross-skill-blast-radius.md) — T1–T4 impact model
- [Monitoring Reference](../monitoring.md) — Redis metrics & alert policies
- [Troubleshooting](../troubleshooting.md) — product-specific diagnosis
- [VPC Ops AIOps](../../../gcp-vpc-ops/references/advanced/aiops-network-anomaly.md) — sibling AIOps runbook
- [GCE Ops](../../../gcp-gce-ops/SKILL.md) / [GKE Ops](../../../gcp-gke-ops/SKILL.md) — dependent-skill coordination (T3)
