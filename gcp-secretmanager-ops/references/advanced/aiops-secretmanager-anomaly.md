# AIOps Self-Healing Anchors — Google Cloud Secret Manager

> Anomaly detection + self-healing runbook for Secret Manager. Each failure mode lists detection (gcloud/log queries), a self-healing action with **dry-run + idempotency + human-review gate**, and the upstream/downstream skills in its blast radius. Destructive actions are marked **HALT** — never auto-execute.

Credential masking per AGENTS.md §0.1: never print secret **value** or `GOOGLE_APPLICATION_CREDENTIALS` path value; verify existence only (`test -f "$GOOGLE_APPLICATION_CREDENTIALS"`). Secret payloads are masked as `****` in all output.

## Failure Modes Covered

| # | Failure Mode | Severity | Self-Healing Class |
|---|-------------|----------|--------------------|
| FM-1 | Secret version disabled / not enabled | High | Auto (with gate) |
| FM-2 | Access denied (IAM binding drift) | High | Auto (with gate) |
| FM-3 | Secret scheduled for destruction (accidental) | Critical | **HALT** (human only) |

---

## FM-1: Secret Version Disabled / Not Enabled

### Detection

```bash
# List versions and their state
gcloud secrets versions list "{{user.secret_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json \
  | jq -r '.[] | {name, state, createTime}'

# Enabled version count
gcloud secrets versions list "{{user.secret_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json \
  | jq '[.[] | select(.state=="ENABLED")] | length'

# Access errors in audit logs (never print secret value)
gcloud logging read 'resource.type=secret_manager_secret AND protoPayload.status.code=7' \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --limit=20 --format=json
```

### Self-Healing Action

| Step | Action | dry-run | Idempotent | Gate |
|------|--------|---------|------------|------|
| 1 | Enable a previously disabled version | `--dry-run` | Yes (state) | **Human review** |
| 2 | Add a new version from a safe source | `--dry-run` | No (new version) | **Human review** — needs new value |

```bash
# DRY-RUN: preview enable version
gcloud secrets versions enable "{{user.version_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --dry-run --format=json
```

> Enabling a version is safe (no data loss). **HALT** on disabling the only ENABLED version — that breaks all consumers.

### Blast Radius

- **Upstream**: `gcp-kms-ops` (CMEK-wrapped secrets); `gcp-iam-ops` (caller SA).
- **Downstream**: `gcp-cloudfunctions-ops` (secret mount); `gcp-gce-ops` (secret access at init); `gcp-lb-ops` (TLS cert stored as secret).

---

## FM-2: Access Denied (IAM Drift)

### Detection

```bash
# Check binding for the caller
gcloud secrets get-iam-policy "{{user.secret_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json \
  | jq '.bindings[] | select(.role | test("secretmanager"))'

# Denied access in audit logs
gcloud logging read 'resource.type=secret_manager_secret AND protoPayload.status.code=7' \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --limit=20 --format=json
```

### Self-Healing Action

| Step | Action | dry-run | Idempotent | Gate |
|------|--------|---------|------------|------|
| 1 | Add `roles/secretmanager.secretAccessor` to SA | `--dry-run` | Yes (additive) | **Human review** — least-privilege |
| 2 | Verify via access test (no value printed) | n/a | Yes | Auto (safe) |

```bash
# DRY-RUN: preview IAM binding add
gcloud secrets add-iam-policy-binding "{{user.secret_name}}" \
  --member="serviceAccount:{{user.sa_email}}" \
  --role="roles/secretmanager.secretAccessor" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --dry-run --format=json
```

> **HALT** on granting to `allUsers` / `allAuthenticatedUsers` — escalate instead.

### Blast Radius

- **Upstream**: `gcp-iam-ops` (SA lifecycle); `gcp-kms-ops` (encryption identity).
- **Downstream**: every consumer (Functions, GCE, LB, Cloud Build).

---

## FM-3: Secret Scheduled for Destruction (Accidental)

### Detection

```bash
gcloud secrets versions list "{{user.secret_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json \
  | jq -r '.[] | select(.state=="DESTROY_SCHEDULED") | {name, destroyTime}'

# Scheduled-destroy window
gcloud secrets versions describe "{{user.version_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json \
  | jq '{name, state, destroyTime}'
```

### Self-Healing Action

| Step | Action | dry-run | Idempotent | Gate |
|------|--------|---------|------------|------|
| 1 | **Restore** scheduled-destroy version (within 30-day window) | `--dry-run` | No (state change) | **Human review** — recovery only |
| 2 | Cancel destruction | `--dry-run` | Yes | **HALT** — destructive prevention, human only |

```bash
# DRY-RUN: preview restore (only valid before destroyTime)
gcloud secrets versions restore "{{user.version_name}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --dry-run --format=json
```

> **HALT** — never auto-destroy or auto-restore without explicit human approval. A destroyed secret value is unrecoverable and breaks all dependent services.

### Blast Radius

- **Upstream**: `gcp-iam-ops` (who scheduled it); `gcp-kms-ops` (CMEK key state).
- **Downstream**: `gcp-cloudfunctions-ops` / `gcp-gce-ops` / `gcp-lb-ops` (all consumers fail to start).

---

## Cross-Skill References

- Error taxonomy: [../../docs/error-taxonomy.md](../../docs/error-taxonomy.md)
- Blast radius map: [../../docs/cross-skill-blast-radius.md](../../docs/cross-skill-blast-radius.md)
- Related skills: [gcp-kms-ops](../gcp-kms-ops/SKILL.md) · [gcp-iam-ops](../gcp-iam-ops/SKILL.md) · [gcp-cloudfunctions-ops](../gcp-cloudfunctions-ops/SKILL.md) · [gcp-gce-ops](../gcp-gce-ops/SKILL.md) · [gcp-lb-ops](../gcp-lb-ops/SKILL.md)
