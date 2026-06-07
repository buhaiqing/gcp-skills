# Idempotency Checklist — Compute Engine

## Create

| Resource | Key | Retry Behavior |
|----------|-----|----------------|
| Instance | name (zone-unique) | ALREADY_EXISTS / 409 |
| Disk | name (zone-unique) | ALREADY_EXISTS / 409 |
| Snapshot | name (global-unique) | ALREADY_EXISTS / 409 |
| MIG | name (zone-unique) | ALREADY_EXISTS / 409 |

## Update

| Operation | Idempotent? |
|-----------|-------------|
| Add metadata | Yes (same key:value = no-op) |
| Set machine type | Yes (same type = no-op) |
| Add labels | Yes (same key:value = no-op) |
| Resize disk | Yes (only expansion) |

## Delete

| Resource | Retry Safe? |
|----------|-------------|
| Instance | Safe — NOT_FOUND on second attempt |
| Disk | Safe — NOT_FOUND on second attempt |
| Snapshot | Safe — NOT_FOUND on second attempt |
| MIG | Safe — NOT_FOUND on second attempt |

## Safe Retry Pattern

```bash
if ! gcloud compute instances describe my-instance --zone=Z --quiet 2>/dev/null; then
    gcloud compute instances create my-instance --zone=Z --machine-type=n2-standard-2
else
    echo "Already exists — no action needed"
fi
```

## Label De-Duplication

```bash
gcloud compute instances create my-instance \
  --zone=Z \
  --labels=deployment-id=deploy-20260607-001,created-by=automation
```
