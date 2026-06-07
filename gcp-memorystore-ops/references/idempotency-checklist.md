# Idempotency Checklist — Memorystore for Redis

## Create

| Resource | Key | Retry Behavior |
|----------|-----|----------------|
| Redis instance | name (region-unique) | ALREADY_EXISTS / 409 |

## Update

| Operation | Idempotent? |
|-----------|-------------|
| Scale memory | Yes (same value = no-op) |
| Update display name | Yes (same value = no-op) |
| Update redis-config | Yes (same value = no-op) |

## Delete

| Resource | Retry Safe? |
|----------|-------------|
| Redis instance | Safe — NOT_FOUND on second attempt |

## Safe Retry Pattern

```bash
if ! gcloud redis instances describe "my-instance" --region=us-central1 --quiet 2>/dev/null; then
    gcloud redis instances create "my-instance" --region=us-central1 --memory-size=1GB
else
    echo "Already exists — no action needed"
fi
```

## Export/Import Idempotency

| Operation | Idempotent? |
|-----------|-------------|
| Export | Yes (overwrites GCS file if same URI) |
| Import | No — overwrites all existing data; must confirm each time |