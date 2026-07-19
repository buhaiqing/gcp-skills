# AIOps Self-Healing Anchors — Google Cloud DNS

> Anomaly detection + self-healing runbook for Cloud DNS. Each failure mode lists detection (gcloud/log queries), a self-healing action with **dry-run + idempotency + human-review gate**, and the upstream/downstream skills in its blast radius. Destructive actions are marked **HALT** — never auto-execute.

Credential masking per AGENTS.md §0.1: never print SA key content or `GOOGLE_APPLICATION_CREDENTIALS` path value; verify existence only (`test -f "$GOOGLE_APPLICATION_CREDENTIALS"`).

## Failure Modes Covered

| # | Failure Mode | Severity | Self-Healing Class |
|---|-------------|----------|--------------------|
| FM-1 | Record-set resolution failure (wrong/missing A record) | High | Auto (with gate) |
| FM-2 | Propagation delay / stale cache after change | Medium | Auto (with gate) |
| FM-3 | DNSSEC signing failure / key rotation issue | High | Auto (with gate) |

---

## FM-1: Record-Set Resolution Failure

### Detection

```bash
# Verify record exists and data is correct
gcloud dns record-sets describe "{{user.record_name}}" \
  --type="{{user.record_type}}" --zone="{{user.zone_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json

# Compare against expected (e.g., LB IP from gcp-lb-ops)
dig +short "{{user.record_name}}" A

# Resolution errors in query logs
gcloud logging read 'resource.type=dns_query AND jsonPayload.response_code!="NOERROR"' \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --limit=20 --format=json
```

### Self-Healing Action

| Step | Action | dry-run | Idempotent | Gate |
|------|--------|---------|------------|------|
| 1 | Transaction: correct the record-set data | `--dry-run` shows diff | Yes (replace) | **Human review** — wrong data breaks resolution |
| 2 | Lower TTL before change, restore after | `--dry-run` | Yes | Auto (safe) |

```bash
# DRY-RUN: preview record correction (transaction)
gcloud dns record-sets transaction start --zone="{{user.zone_name}}"
gcloud dns record-sets transaction remove "{{user.record_name}}" \
  --type="{{user.record_type}}" --ttl="{{user.ttl}}" --rrdatas="{{user.old_data}}" \
  --zone="{{user.zone_name}}" --dry-run
gcloud dns record-sets transaction add "{{user.record_name}}" \
  --type="{{user.record_type}}" --ttl="{{user.ttl}}" --rrdatas="{{user.new_data}}" \
  --zone="{{user.zone_name}}" --dry-run
gcloud dns record-sets transaction execute --zone="{{user.zone_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --dry-run --format=json
```

> **HALT** on deleting a record-set that serves production traffic — confirm replacement exists first (delegate to `gcp-lb-ops` for LB IP).

### Blast Radius

- **Upstream**: `gcp-lb-ops` (A record must point at live LB IP); `gcp-cdn-ops` (CDN origin DNS).
- **Downstream**: all clients resolving the name (outage if wrong); `gcp-vpc-ops` (private zone VPC binding).

---

## FM-2: Propagation Delay / Stale Cache

### Detection

```bash
# Check change status (pending vs done)
gcloud dns record-sets transaction execute --zone="{{user.zone_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json \
  | jq '{changeId: .change.id, status: .change.status}'

# Compare resolver views
dig +short "{{user.record_name}}" A @8.8.8.8
dig +short "{{user.record_name}}" A @1.1.1.1
```

### Self-Healing Action

| Step | Action | dry-run | Idempotent | Gate |
|------|--------|---------|------------|------|
| 1 | Pre-change: lower TTL to 60s | `--dry-run` | Yes | Auto (safe) |
| 2 | Post-stabilization: restore TTL to 300/3600 | `--dry-run` | Yes | Auto (safe) |

> No destructive action. Propagation is time-bound by TTL; self-heal by TTL management only. **HALT** on any attempt to force-flush public resolvers (not possible).

### Blast Radius

- **Upstream**: `gcp-lb-ops` (IP change triggers this flow).
- **Downstream**: clients with cached records (transient mismatch until TTL expires).

---

## FM-3: DNSSEC Signing Failure / Key Rotation

### Detection

```bash
gcloud dns managed-zones describe "{{user.zone_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json \
  | jq '{name, dnssecConfig: {state, kind, defaultKeySpecs}}'

# DS record at parent (registrar) mismatch
gcloud dns dns-keys list --zone="{{user.zone_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json \
  | jq -r '.[] | {id, type, isActive, algorithm}'
```

### Self-Healing Action

| Step | Action | dry-run | Idempotent | Gate |
|------|--------|---------|------------|------|
| 1 | If DNSSEC `off` but should be `on`: enable signing | `--dry-run` | Yes | **Human review** — DS at parent must match |
| 2 | If key rotation needed: trigger rotate | `--dry-run` | No | **HALT** — coordinate DS update at registrar |

```bash
# DRY-RUN: preview DNSSEC enable
gcloud dns managed-zones update "{{user.zone_name}}" \
  --dnssec-state=on --project="{{env.CLOUDSDK_CORE_PROJECT}}" --dry-run --format=json
```

> **HALT** — enabling DNSSEC without a matching DS record at the parent registrar causes full resolution failure. Always verify DS before applying.

### Blast Radius

- **Upstream**: Registrar / parent zone (DS record).
- **Downstream**: `gcp-lb-ops` / `gcp-cdn-ops` (validated domains); all resolvers (SERVFAIL if DS mismatch).

---

## Cross-Skill References

- Error taxonomy: [../../docs/error-taxonomy.md](../../docs/error-taxonomy.md)
- Blast radius map: [../../docs/cross-skill-blast-radius.md](../../docs/cross-skill-blast-radius.md)
- Related skills: [gcp-lb-ops](../gcp-lb-ops/SKILL.md) · [gcp-cdn-ops](../gcp-cdn-ops/SKILL.md) · [gcp-vpc-ops](../gcp-vpc-ops/SKILL.md)
