# Idempotency Checklist — Cloud Storage

## Create

| Resource | Key | Retry Behavior |
|----------|-----|----------------|
| Bucket | name (globally unique) | ALREADY_EXISTS / 409 — choose different name |
| Object | name within bucket | Overwritten on same name (use generation for safe retry) |

## Update

| Operation | Idempotent? |
|-----------|-------------|
| Update bucket labels | Yes (same key:value = no-op) |
| Update versioning | Yes (same setting = no-op) |
| Update retention period (unlocked) | Yes (same period = no-op) |
| Lock retention policy | No — single use, then locked permanently |
| Update lifecycle rules | Yes (same rules = no-op) |
| Add IAM binding | Yes (same member+role = no-op) |
| Enable/disable Autoclass | Yes (same setting = no-op) |
| Update default encryption key | Yes (same key = no-op) |
| Update CORS | Yes (same config = no-op) |

## Delete

| Resource | Retry Safe? |
|----------|-------------|
| Bucket | Safe — NOT_FOUND on second attempt |
| Object (non-versioned) | Safe — NOT_FOUND on second attempt |
| Object (versioned) | Safe — delete marker already exists on second attempt |

## Safe Retry Pattern

```bash
if ! gcloud storage buckets describe "gs://my-bucket" --quiet 2>/dev/null; then
    gcloud storage buckets create "gs://my-bucket" --location=US
else
    echo "Already exists — no action needed"
fi
```

## Object Upload with Generation Precondition

```bash
# Upload only if object does not exist (idempotent)
gsutil cp -n source.txt gs://bucket/object.txt
```

## Label De-Duplication

```bash
gcloud storage buckets update "gs://my-bucket" \
  --update-labels=deployment-id=deploy-20260607-001,created-by=automation
```