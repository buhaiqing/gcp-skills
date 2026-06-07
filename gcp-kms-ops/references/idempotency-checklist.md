# Idempotency Checklist — Cloud KMS

## Create

| Resource | Key | Retry Behavior |
|----------|-----|----------------|
| Key ring | name (location-unique) | ALREADY_EXISTS / 409 |
| Crypto key | name (keyring-unique) | ALREADY_EXISTS / 409 |
| Key version | version number (auto-increment) | Duplicate create is idempotent (ignored) |

## Update

| Operation | Idempotent? |
|-----------|-------------|
| Update rotation period | Yes (same value = no-op) |
| Update labels | Yes (same value = no-op) |
| Enable version | Yes (already enabled = no-op) |
| Disable version | Yes (already disabled = no-op) |

## Delete

| Resource | Retry Safe? |
|----------|-------------|
| Key version destroy | Safe — DESTROY_SCHEDULED on second attempt = no error |
| Key version restore | Safe — already restored = no-op |

## Safe Retry Pattern

```bash
if ! gcloud kms keyrings describe "my-keyring" --location=global --quiet 2>/dev/null; then
    gcloud kms keyrings create "my-keyring" --location=global
else
    echo "Already exists — no action needed"
fi
```