# AIOps Self-Healing Anchors — Google Cloud KMS

> Anomaly detection + self-healing runbook for Cloud KMS (keys, key rings, rotation). Each failure mode lists detection (gcloud/log queries), a self-healing action with **dry-run + idempotency + human-review gate**, and the upstream/downstream skills in its blast radius. Destructive actions are marked **HALT** — never auto-execute.

Credential masking per AGENTS.md §0.1: never print SA key content or `GOOGLE_APPLICATION_CREDENTIALS` path value; verify existence only (`test -f "$GOOGLE_APPLICATION_CREDENTIALS"`).

## Failure Modes Covered

| # | Failure Mode | Severity | Self-Healing Class |
|---|-------------|----------|--------------------|
| FM-1 | Key rotation overdue / disabled | High | Auto (with gate) |
| FM-2 | Encrypt/Decrypt permission denied (IAM binding drift) | High | Auto (with gate) |
| FM-3 | Key scheduled for destruction (accidental) | Critical | **HALT** (human only) |

---

## FM-1: Key Rotation Overdue / Disabled

### Detection

```bash
# Rotation period and next rotation time
gcloud kms keys describe "{{user.crypto_key_name}}" \
  --keyring="{{user.keyring}}" --location="{{user.location}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json \
  | jq '{name, rotationPeriod, nextRotationTime, purpose}'

# Rotation events in audit logs
gcloud logging read 'resource.type=cloudkms_cryptokey AND protoPayload.methodName=~"RotateCryptoKey"' \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --limit=10 --format=json
```

### Self-Healing Action

| Step | Action | dry-run | Idempotent | Gate |
|------|--------|---------|------------|------|
| 1 | Enable automatic rotation (set period) | `--dry-run` | Yes | **Human review** |
| 2 | Manual rotate now | `--dry-run` | No (new version) | **Human review** — old versions still decrypt |

```bash
# DRY-RUN: preview rotation enable
gcloud kms keys update "{{user.crypto_key_name}}" \
  --keyring="{{user.keyring}}" --location="{{user.location}}" \
  --rotation-period="{{user.rotation_period}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --dry-run --format=json

# DRY-RUN: manual rotate
gcloud kms keys rotate "{{user.crypto_key_name}}" \
  --keyring="{{user.keyring}}" --location="{{user.location}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --dry-run --format=json
```

> Rotation creates a new version; old versions remain for decryption. Safe to auto-enable rotation after review.

### Blast Radius

- **Upstream**: `gcp-iam-ops` (KMS SA permissions); `gcp-secretmanager-ops` (CMEK-wrapped secrets).
- **Downstream**: `gcp-gce-ops` / `gcp-filestore-ops` (CMEK-encrypted disks); `gcp-cloudfunctions-ops` (KMS-encrypted env).

---

## FM-2: Encrypt/Decrypt Permission Denied (IAM Drift)

### Detection

```bash
# Check IAM policy on the key
gcloud kms keys get-iam-policy "{{user.crypto_key_name}}" \
  --keyring="{{user.keyring}}" --location="{{user.location}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json \
  | jq '.bindings[] | select(.role | test("cloudkms.cryptoKeyEncrypterDecrypter"))'

# Denied calls in audit logs
gcloud logging read 'resource.type=cloudkms_cryptokey AND protoPayload.status.code=7' \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --limit=20 --format=json
```

### Self-Healing Action

| Step | Action | dry-run | Idempotent | Gate |
|------|--------|---------|------------|------|
| 1 | Add `roles/cloudkms.cryptoKeyEncrypterDecrypter` to SA | `--dry-run` | Yes (additive) | **Human review** — least-privilege check |
| 2 | Verify via test encrypt/decrypt | n/a | Yes | Auto (safe) |

```bash
# DRY-RUN: preview IAM binding add
gcloud kms keys add-iam-policy-binding "{{user.crypto_key_name}}" \
  --keyring="{{user.keyring}}" --location="{{user.location}}" \
  --member="serviceAccount:{{user.sa_email}}" \
  --role="roles/cloudkms.cryptoKeyEncrypterDecrypter" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --dry-run --format=json
```

> **HALT** on granting to a broad principal (`allUsers`, `allAuthenticatedUsers`) — escalate instead.

### Blast Radius

- **Upstream**: `gcp-iam-ops` (SA lifecycle); `gcp-secretmanager-ops` (caller identity).
- **Downstream**: every consumer of the key (GCE, Filestore, Secret Manager, Functions).

---

## FM-3: Key Scheduled for Destruction (Accidental)

### Detection

```bash
gcloud kms keys versions list "{{user.crypto_key_name}}" \
  --keyring="{{user.keyring}}" --location="{{user.location}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json \
  | jq -r '.[] | {name, state, destroyTime, scheduledDestroyTime}'

# Destruction-scheduled versions
gcloud kms keys versions list "{{user.crypto_key_name}}" \
  --keyring="{{user.keyring}}" --location="{{user.location}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --format=json \
  | jq -r '.[] | select(.state=="DESTROY_SCHEDULED") | .name'
```

### Self-Healing Action

| Step | Action | dry-run | Idempotent | Gate |
|------|--------|---------|------------|------|
| 1 | **Restore** scheduled-destroy version (within 24h window) | `--dry-run` | No (state change) | **Human review** — recovery only |
| 2 | Cancel destruction | `--dry-run` | Yes | **HALT** — destructive prevention, human only |

```bash
# DRY-RUN: preview restore (only valid before destroyTime)
gcloud kms keys versions restore "{{user.version_name}}" \
  --keyring="{{user.keyring}}" --location="{{user.location}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" --dry-run --format=json
```

> **HALT** — never auto-destroy or auto-restore without explicit human approval. Data encrypted under a destroyed key is unrecoverable.

### Blast Radius

- **Upstream**: `gcp-iam-ops` (who scheduled it); `gcp-secretmanager-ops` (CMEK secrets become unreadable).
- **Downstream**: `gcp-gce-ops` / `gcp-filestore-ops` (encrypted disks unreadable); all data-plane consumers.

---

## Cross-Skill References

- Error taxonomy: [../../docs/error-taxonomy.md](../../docs/error-taxonomy.md)
- Blast radius map: [../../docs/cross-skill-blast-radius.md](../../docs/cross-skill-blast-radius.md)
- Related skills: [gcp-iam-ops](../gcp-iam-ops/SKILL.md) · [gcp-secretmanager-ops](../gcp-secretmanager-ops/SKILL.md) · [gcp-gce-ops](../gcp-gce-ops/SKILL.md) · [gcp-filestore-ops](../gcp-filestore-ops/SKILL.md)
