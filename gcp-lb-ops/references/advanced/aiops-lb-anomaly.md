# AIOps Self-Healing Anchors — Google Cloud Load Balancing (LB)

> Anomaly detection + self-healing runbook for Cloud Load Balancing. Each failure mode lists detection (gcloud/log queries), a self-healing action with **dry-run + idempotency + human-review gate**, and the upstream/downstream skills in its blast radius. Destructive actions are marked **HALT** — never auto-execute.

Credential masking per AGENTS.md §0.1: never print SA key content or `GOOGLE_APPLICATION_CREDENTIALS` path value; verify existence only (`test -f "$GOOGLE_APPLICATION_CREDENTIALS"`).

## Failure Modes Covered

| # | Failure Mode | Severity | Self-Healing Class |
|---|-------------|----------|--------------------|
| FM-1 | Backend health check failing (backends drained) | High | Auto (with gate) |
| FM-2 | Backend capacity exhausted (no healthy capacity) | High | Auto (with gate) |
| FM-3 | SSL certificate expired / FAILED provisioning | High | Auto (with gate) |

---

## FM-1: Backend Health Check Failing

### Detection

```bash
# Per-backend health status
gcloud compute backend-services get-health "{{user.backend_service_name}}" \
  --global --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json \
  | jq -r '.[] | {instance: .instance, healthState: .healthState, status: .status}'

# Count UNHEALTHY
gcloud compute backend-services get-health "{{user.backend_service_name}}" \
  --global --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json \
  | jq '[.[] | select(.healthState=="UNHEALTHY")] | length'

# Health-check probe logs
gcloud logging read 'resource.type=https_lb_rule AND jsonPayload.environment=~"health"' \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --limit=20 --format=json
```

### Self-Healing Action

| Step | Action | dry-run | Idempotent | Gate |
|------|--------|---------|------------|------|
| 1 | Verify health check config (port/path) matches backend | `--dry-run` shows diff | Yes | Auto |
| 2 | If health check misconfigured, update it | `--dry-run` | Yes | **Human review** |
| 3 | If backend app down, recreate via `gcp-gce-ops` | n/a | No | **HALT** — delegate to GCE |

```bash
# DRY-RUN: preview health-check update
gcloud compute health-checks update http "{{user.health_check_name}}" \
  --port="{{user.port}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" --dry-run --format=json
```

> Do NOT auto-remove the health check or delete the backend service — that drops all traffic. **HALT** on any action that removes capacity.

### Blast Radius

- **Upstream**: `gcp-gce-ops` (backend instances unhealthy → recreate); `gcp-vpc-ops` (firewall blocks probe).
- **Downstream**: `gcp-dns-ops` (if LB IP changes, DNS A record stale); `gcp-cdn-ops` (cache origin failing).

---

## FM-2: Backend Capacity Exhausted

### Detection

```bash
# Backend utilization / connection count
gcloud monitoring time-series list \
  --filter='metric.type="loadbalancing.googleapis.com/https/backend_request_count" AND resource.labels.backend_service_name="{{user.backend_service_name}}"' \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json | jq -r '.[].points[0].value.int64Value'

# MIG size vs target
gcloud compute instance-groups managed describe "{{user.mig_name}}" \
  --zone="{{user.zone}}" --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{targetSize, currentActions}'
```

### Self-Healing Action

| Step | Action | dry-run | Idempotent | Gate |
|------|--------|---------|------------|------|
| 1 | Scale MIG up (resize) | `--dry-run` shows new size | Yes (target size) | **Human review** — cost impact |
| 2 | Raise `maxRatePerInstance` / `maxUtilization` | `--dry-run` | Yes | **Human review** |

```bash
# DRY-RUN: preview MIG scale-up
gcloud compute instance-groups managed resize "{{user.mig_name}}" \
  --zone="{{user.zone}}" --size="{{user.new_size}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --dry-run --format=json
```

> **HALT** if scaling would exceed quota or budget guardrail — escalate instead of auto-scaling unbounded.

### Blast Radius

- **Upstream**: `gcp-gce-ops` (MIG resize creates instances → quota/IP).
- **Downstream**: `gcp-billing-ops` (cost spike); `gcp-lb-ops` URL map (no change needed).

---

## FM-3: SSL Certificate Expired / FAILED

### Detection

```bash
gcloud compute ssl-certificates describe "{{user.certificate_name}}" \
  --global --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json \
  | jq '{name, type, managed: {status: .managed.status, domainStatuses: .managed.domainStatuses, expireTime: .expireTime}}'

# Managed cert domain validation failures
gcloud compute ssl-certificates describe "{{user.certificate_name}}" \
  --global --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json \
  | jq '.managed.domainStatuses'
```

### Self-Healing Action

| Step | Action | dry-run | Idempotent | Gate |
|------|--------|---------|------------|------|
| 1 | For managed cert `FAILED`: re-create cert (new provisioning) | `--dry-run` | No (new resource) | **Human review** |
| 2 | For expired self-managed cert: upload renewed cert | `--dry-run` | Yes (replace) | **Human review** — needs new cert material |
| 3 | Verify DNS points at LB IP (delegated to `gcp-dns-ops`) | n/a | — | **HALT** — DNS must be correct for provisioning |

```bash
# DRY-RUN: preview managed cert re-creation
gcloud compute ssl-certificates create "{{user.certificate_name}}-new" \
  --domains="{{user.domain_name}}" --global \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --dry-run --format=json
```

> Never delete the live cert until the replacement is `FULLY_PROVISIONED` and attached — **HALT** on delete of in-use cert.

### Blast Radius

- **Upstream**: `gcp-dns-ops` (CAA / A record must be valid for provisioning).
- **Downstream**: `gcp-lb-ops` target proxy (cert swap causes brief TLS reload); clients (cert errors until swapped).

---

## Cross-Skill References

- Error taxonomy: [../../docs/error-taxonomy.md](../../docs/error-taxonomy.md)
- Blast radius map: [../../docs/cross-skill-blast-radius.md](../../docs/cross-skill-blast-radius.md)
- Related skills: [gcp-gce-ops](../gcp-gce-ops/SKILL.md) · [gcp-dns-ops](../gcp-dns-ops/SKILL.md) · [gcp-vpc-ops](../gcp-vpc-ops/SKILL.md) · [gcp-cdn-ops](../gcp-cdn-ops/SKILL.md)
