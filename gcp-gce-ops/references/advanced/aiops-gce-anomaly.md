# AIOps Self-Healing Anchors — Google Cloud Compute Engine (GCE)

> Anomaly detection + self-healing runbook for Compute Engine. Each failure mode lists detection (gcloud/log queries), a self-healing action with **dry-run + idempotency + human-review gate**, and the upstream/downstream skills in its blast radius. Destructive actions are marked **HALT** — never auto-execute.

Credential masking per AGENTS.md §0.1: never print SA key content or `GOOGLE_APPLICATION_CREDENTIALS` path value; verify existence only (`test -f "$GOOGLE_APPLICATION_CREDENTIALS"`).

## Failure Modes Covered

| # | Failure Mode | Severity | Self-Healing Class |
|---|-------------|----------|--------------------|
| FM-1 | Instance unhealthy / auto-healing failing (MIG) | High | Auto (with gate) |
| FM-2 | Boot / data disk full (low free space) | High | Auto (with gate) |
| FM-3 | Instance stuck in `PROVISIONING` / `STAGING` | Medium | Auto (with gate) |

---

## FM-1: Instance Unhealthy / Auto-Healing Failing (MIG)

### Detection

```bash
# List MIG instances and their health state
gcloud compute instance-groups managed list-instances "{{user.mig_name}}" \
  --zone="{{user.zone}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq -r '.[] | {name, instance: .instance, status, currentAction, healthState}'

# Count UNHEALTHY members
gcloud compute instance-groups managed list-instances "{{user.mig_name}}" \
  --zone="{{user.zone}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '[.[] | select(.healthState=="UNHEALTHY")] | length'

# Serial-port / agent logs for crash signals
gcloud logging read \
  'resource.type=gce_instance AND jsonPayload.message=~"out of memory|OOM|kernel panic"' \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --limit=20 --format=json
```

### Self-Healing Action

| Step | Action | dry-run | Idempotent | Gate |
|------|--------|---------|------------|------|
| 1 | Recreate unhealthy instance via MIG `recreate-instances` | `--dry-run` prints target list | Yes (named instance) | **Human review** — recreating drops in-flight state |
| 2 | If auto-healing disabled, re-enable health check | `--dry-run` shows diff | Yes | Auto after review |

```bash
# DRY-RUN: show which instances would be recreated (no mutation)
gcloud compute instance-groups managed recreate-instances "{{user.mig_name}}" \
  --zone="{{user.zone}}" --instances="<unhealthy-instance>" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --dry-run --format=json

# EXECUTE (only after human approval)
gcloud compute instance-groups managed recreate-instances "{{user.mig_name}}" \
  --zone="{{user.zone}}" --instances="<unhealthy-instance>" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json
```

> **HALT if** >50% of MIG members unhealthy simultaneously — likely a shared dependency (image, startup script, subnet) failure; escalate instead of mass-recreating.

### Blast Radius

- **Upstream**: `gcp-lb-ops` (unhealthy backends removed from LB pool → 5xx spikes); `gcp-vpc-ops` (subnet/IP exhaustion).
- **Downstream**: `gcp-monitoring-ops` (alert fatigue); workloads on instance (data plane).

---

## FM-2: Boot / Data Disk Full

### Detection

```bash
# Guest disk usage via agent metric (requires monitoring agent)
gcloud monitoring time-series list \
  --filter='metric.type="agent.googleapis.com/disk/percent_used" AND resource.labels.instance_id="{{user.instance_id}}"' \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json | jq -r '.[].points[0].value.doubleValue'

# Or via OS Login / serial — never cat credentials
gcloud compute ssh "{{user.instance_name}}" --zone="{{user.zone}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --command='df -h / | tail -1'
```

### Self-Healing Action

| Step | Action | dry-run | Idempotent | Gate |
|------|--------|---------|------------|------|
| 1 | Snapshot disk before any change | n/a | Yes | **HALT** — snapshot is safe, but confirm it's the right disk |
| 2 | Resize disk upward (expansion only) | `--dry-run` shows new size | Yes (target size idempotent) | **Human review** — expansion is safe, shrinking is not |

```bash
# DRY-RUN: preview resize target
gcloud compute disks resize "{{user.disk_name}}" --zone="{{user.zone}}" \
  --size="{{user.new_size}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --dry-run --format=json

# EXECUTE (expansion only; never shrink without backup + explicit confirm)
gcloud compute disks resize "{{user.disk_name}}" --zone="{{user.zone}}" \
  --size="{{user.new_size}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json
```

> Guest filesystem resize (`resize2fs`/`xfs_growfs`) must run inside the VM — **HALT**, requires SSH access and human approval; do not auto-run.

### Blast Radius

- **Upstream**: `gcp-lb-ops` (disk-full backends fail health checks → removed from pool).
- **Downstream**: any service writing to the disk (DB, app logs); `gcp-filestore-ops` if disk backs an NFS cache.

---

## FM-3: Instance Stuck in PROVISIONING / STAGING

### Detection

```bash
gcloud compute instances describe "{{user.instance_name}}" \
  --zone="{{user.zone}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{name, status, statusMessage, lastStartTimestamp}'

# Compare elapsed time vs expected (max 300s per SKILL.md state table)
gcloud logging read 'resource.type=gce_instance AND jsonPayload.message=~"PROVISIONING"' \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --limit=10 --format=json
```

### Self-Healing Action

| Step | Action | dry-run | Idempotent | Gate |
|------|--------|---------|------------|------|
| 1 | Reset instance (only if RUNNING→stuck) | `--dry-run` | No (changes state) | **HALT** — reset loses unsaved state |
| 2 | If persistent >10min, delete+recreate from template | `--dry-run` | No | **Human review** — destructive |

> Prefer waiting + reset over delete. Only delete after human approval and only if a fresh instance from the same template is acceptable.

### Blast Radius

- **Upstream**: `gcp-lb-ops` (backend not READY → LB 502/503).
- **Downstream**: `gcp-vpc-ops` (ephemeral IP reassign on recreate).

---

## Cross-Skill References

- Error taxonomy: [../../docs/error-taxonomy.md](../../docs/error-taxonomy.md)
- Blast radius map: [../../docs/cross-skill-blast-radius.md](../../docs/cross-skill-blast-radius.md)
- Related skills: [gcp-lb-ops](../gcp-lb-ops/SKILL.md) · [gcp-vpc-ops](../gcp-vpc-ops/SKILL.md) · [gcp-monitoring-ops](../gcp-monitoring-ops/SKILL.md)
