# AIOps Self-Healing Anchors — Google Cloud Filestore

> Anomaly detection + self-healing runbook for Cloud Filestore (instances, file shares, backups, snapshots). Each failure mode lists detection (gcloud/log queries), a self-healing action with **dry-run + idempotency + human-review gate**, and the upstream/downstream skills in its blast radius. Destructive actions are marked **HALT** — never auto-execute.

Credential masking per AGENTS.md §0.1: never print SA key content or `GOOGLE_APPLICATION_CREDENTIALS` path value; verify existence only (`test -f "$GOOGLE_APPLICATION_CREDENTIALS"`).

## Failure Modes Covered

| # | Failure Mode | Severity | Self-Healing Class |
|---|-------------|----------|--------------------|
| FM-1 | File share capacity exhausted (quota full) | High | Auto (with gate) |
| FM-2 | Instance unhealthy / state `REPAIRING` stuck | High | Auto (with gate) |
| FM-3 | Backup / snapshot failure | Medium | Auto (with gate) |

---

## FM-1: File Share Capacity Exhausted

### Detection

```bash
# Instance capacity vs used
gcloud filestore instances describe "{{user.instance_name}}" \
  --zone="{{user.zone}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json \
  | jq '{name, state, capacityGb: .fileShares[0].capacityGb, usedGb: .fileShares[0].usedGb}'

# Utilization ratio
gcloud filestore instances describe "{{user.instance_name}}" \
  --zone="{{user.zone}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json \
  | jq '.fileShares[0] | (.usedGb / .capacityGb * 100 | floor) as $pct | "\($pct)%"'

# Capacity alerts in monitoring
gcloud monitoring time-series list \
  --filter='metric.type="filestore.googleapis.com/instance/used_bytes" AND resource.labels.instance="{{user.instance_name}}"' \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json | jq -r '.[].points[0].value.doubleValue'
```

### Self-Healing Action

| Step | Action | dry-run | Idempotent | Gate |
|------|--------|---------|------------|------|
| 1 | Expand instance capacity (upward only) | `--dry-run` | Yes (target size) | **Human review** — cost impact |
| 2 | Snapshot before expansion (safe) | n/a | Yes | Auto (safe) |

```bash
# DRY-RUN: preview capacity expansion
gcloud filestore instances update "{{user.instance_name}}" \
  --zone="{{user.zone}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --file-share="name={{user.file_share_name}},capacity={{user.new_capacity}}" \
  --dry-run --format=json
```

> Filestore capacity can only be **increased**, never decreased — safe direction. **HALT** on any attempt to shrink (not supported; would require recreate + data copy).

### Blast Radius

- **Upstream**: `gcp-gce-ops` (NFS clients mounting the share); `gcp-vpc-ops` (mount connectivity).
- **Downstream**: any workload writing to the share (DB data dir, app files); `gcp-kms-ops` (CMEK-encrypted instances).

---

## FM-2: Instance Unhealthy / Stuck in REPAIRING

### Detection

```bash
gcloud filestore instances describe "{{user.instance_name}}" \
  --zone="{{user.zone}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json \
  | jq '{name, state, statusMessage: .statusMessage}'

# Stuck > expected repair window (compare timestamps)
gcloud logging read 'resource.type=filestore_instance AND jsonPayload.message=~"REPAIRING"' \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --limit=10 --format=json
```

### Self-Healing Action

| Step | Action | dry-run | Idempotent | Gate |
|------|--------|---------|------------|------|
| 1 | Wait + re-check (Filestore self-heals many states) | n/a | Yes | Auto |
| 2 | If stuck >30min, restore from latest backup to new instance | `--dry-run` | No (new resource) | **Human review** — data may lag backup |
| 3 | Failover mount to standby (if HA tier) | `--dry-run` | No | **HALT** — coordinate with clients |

```bash
# DRY-RUN: preview restore from backup
gcloud filestore backups describe "{{user.backup_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json  # verify source exists
gcloud filestore instances create "{{user.instance_name}}-restore" \
  --zone="{{user.zone}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --file-share="name={{user.file_share_name}},capacity={{user.capacity}},source-backup={{user.backup_name}}" \
  --dry-run --format=json
```

> Prefer waiting over recreate. **HALT** on deleting the original instance until clients are remounted to the restore target.

### Blast Radius

- **Upstream**: `gcp-gce-ops` (clients must remount); `gcp-vpc-ops` (IP reassignment on new instance).
- **Downstream**: `gcp-kms-ops` (CMEK key for new instance); all NFS consumers (I/O pause during remount).

---

## FM-3: Backup / Snapshot Failure

### Detection

```bash
gcloud filestore backups list --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --filter="sourceInstance={{user.instance_name}}" --format=json \
  | jq -r '.[] | {name, state, createTime}'

# Failed backups
gcloud filestore backups list --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --filter="sourceInstance={{user.instance_name}} AND state=FAILED" --format=json

# Backup errors in logs
gcloud logging read 'resource.type=filestore_instance AND jsonPayload.message=~"backup.*fail"' \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --limit=10 --format=json
```

### Self-Healing Action

| Step | Action | dry-run | Idempotent | Gate |
|------|--------|---------|------------|------|
| 1 | Retry backup (new name, timestamped) | `--dry-run` | Yes (new resource) | **Human review** — storage cost |
| 2 | Verify source instance is `READY` before retry | n/a | Yes | Auto (safe) |

```bash
# DRY-RUN: preview backup creation
gcloud filestore backups create "{{user.backup_name}}-$(date +%Y%m%d%H%M)" \
  --instance="{{user.instance_name}}" --instance-zone="{{user.zone}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --dry-run --format=json
```

> Backups are additive and safe. **HALT** on deleting old backups before a successful new one exists (retention risk).

### Blast Radius

- **Upstream**: `gcp-gce-ops` (instance must be READY); `gcp-kms-ops` (CMEK key for backup encryption).
- **Downstream**: `gcp-billing-ops` (backup storage cost); DR runbooks (recovery point).

---

## Cross-Skill References

- Error taxonomy: [../../docs/error-taxonomy.md](../../../docs/error-taxonomy.md)
- Blast radius map: [../../docs/cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md)
- Related skills: [gcp-gce-ops](../../../gcp-gce-ops/SKILL.md) · [gcp-vpc-ops](../../../gcp-vpc-ops/SKILL.md) · [gcp-kms-ops](../../../gcp-kms-ops/SKILL.md) · [gcp-billing-ops](../../../gcp-billing-ops/SKILL.md)
