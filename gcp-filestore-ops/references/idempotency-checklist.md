# Idempotency Checklist — Filestore

## Create

| Resource | Key | Retry Behavior |
|----------|-----|----------------|
| Instance | name (per zone/region) | ALREADY_EXISTS / 409 — choose different name |
| Backup | name (per region) | ALREADY_EXISTS / 409 — choose different name |
| Snapshot | name (per instance) | ALREADY_EXISTS / 409 — choose different name |

## Update

| Operation | Idempotent? |
|-----------|-------------|
| Update instance labels | Yes (same key:value = no-op) |
| Update capacity (scale up) | Yes (same capacity = no-op) |
| Update capacity (scale down) | Yes (same capacity = no-op) |
| Update performance settings | Yes (same settings = no-op) |
| Add IP-based access | Yes (same IP = no-op) |
| Update network config | Yes (same config = no-op) |
| Update CMEK key | Yes (same key = no-op) |

## Delete

| Resource | Retry Safe? |
|----------|-------------|
| Instance | Safe — NOT_FOUND on second attempt |
| Backup | Safe — NOT_FOUND on second attempt |
| Snapshot | Safe — NOT_FOUND on second attempt |
| File share (data) | Unsafe — data permanently lost |

## Safe Retry Pattern

```bash
# Check instance exists before delete
if gcloud filestore instances describe "{{user.instance_name}}" \
  --zone="{{user.zone}}" --format="json" &>/dev/null; then
    gcloud filestore instances delete "{{user.instance_name}}" --zone="{{user.zone}}"
else
    echo "Already deleted — no action needed"
fi
```

## Instance Creation with Pre-Check

```bash
# Verify instance doesn't exist before create
if ! gcloud filestore instances describe "{{user.instance_name}}" \
  --zone="{{user.zone}}" --format="json" &>/dev/null; then
    gcloud filestore instances create "{{user.instance_name}}" \
      --zone="{{user.zone}}" \
      --tier="{{user.tier}}" \
      --file-share=name="{{user.share_name}}",capacity="{{user.capacity}}TiB" \
      --network=name="{{user.network}}" \
      --format="json"
else
    echo "Already exists — no action needed"
fi
```

## Capacity Update Idempotent

```bash
# Only update if capacity differs
CURRENT_CAPACITY=$(gcloud filestore instances describe "{{user.instance_name}}" \
  --zone="{{user.zone}}" --format="json" \
  | jq -r '.fileShares[0].capacityGb')

TARGET_CAPACITY={{user.capacity_gb}}

if [ "$CURRENT_CAPACITY" -ne "$TARGET_CAPACITY" ]; then
    gcloud filestore instances update "{{user.instance_name}}" \
      --zone="{{user.zone}}" \
      --file-share=name="{{user.share_name}}",capacity="$TARGET_CAPACITY" \
      --format="json"
else
    echo "Capacity already at $TARGET_CAPACITY GB — no action needed"
fi
```

## Label De-Duplication

```bash
# Update labels idempotently
gcloud filestore instances update "{{user.instance_name}}" \
  --zone="{{user.zone}}" \
  --update-labels=deployment-id=deploy-20260613-001,created-by=automation \
  --format="json"
```

## Backup Creation with Rate Limit

```bash
# Check last backup time (rate limit: 1 per 10 minutes)
LAST_BACKUP=$(gcloud filestore backups list \
  --region="{{user.region}}" --format="json" \
  | jq -r 'sort_by(.createTime) | last | .createTime')

if [ -n "$LAST_BACKUP" ]; then
    LAST_EPOCH=$(date -d "$LAST_BACKUP" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%S" "$LAST_BACKUP" +%s)
    NOW_EPOCH=$(date +%s)
    DIFF=$((NOW_EPOCH - LAST_EPOCH))
    if [ $DIFF -lt 600 ]; then
        echo "Rate limit: wait $((600 - DIFF)) seconds before next backup"
        exit 1
    fi
fi

gcloud filestore backups create "{{user.backup_name}}" \
  --region="{{user.region}}" \
  --instance="{{user.instance_name}}" \
  --instance-zone="{{user.zone}}" \
  --format="json"
```
