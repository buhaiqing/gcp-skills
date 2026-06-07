# Idempotency Checklist — Cloud SQL

## Create

| Resource | Key | Retry Behavior |
|----------|-----|----------------|
| Instance | name (project-unique) | ALREADY_EXISTS / 409 |
| Database | name (instance-unique) | ALREADY_EXISTS / 409 |
| User | name + host (instance-unique) | ALREADY_EXISTS / 409 |
| Backup | auto-generated ID | New backup on each call |
| Read Replica | name (project-unique) | ALREADY_EXISTS / 409 |

## Update

| Operation | Idempotent? |
|-----------|-------------|
| Update tier | Yes (same tier = no-op) |
| Set database flags | Yes (same flags = no-op) |
| Set maintenance window | Yes (same values = no-op) |
| Enable Query Insights | Yes (already enabled = no-op) |
| Set deletion protection | Yes (already set = no-op) |
| Resize storage | Yes (only expansion) |
| Set user password | Yes (same password = no-op) |

## Delete

| Resource | Retry Safe? |
|----------|-------------|
| Instance | Safe — NOT_FOUND on second attempt |
| Database | Safe — NOT_FOUND on second attempt |
| User | Safe — NOT_FOUND on second attempt |
| Backup | Safe — NOT_FOUND on second attempt |

## Safe Retry Pattern

```bash
if ! gcloud sql instances describe my-instance --quiet 2>/dev/null; then
    gcloud sql instances create my-instance --database-version=MYSQL_8_0 --tier=db-n1-standard-2 --region=us-central1
else
    echo "Already exists — no action needed"
fi
```

## Label De-Duplication

```bash
gcloud sql instances create my-instance \
  --region=us-central1 \
  --database-version=MYSQL_8_0 \
  --tier=db-n1-standard-2 \
  --labels=deployment-id=deploy-20260607-001,created-by=gcp-skills
```

## Operation Polling Pattern

```bash
# Poll until DONE
while true; do
  status=$(gcloud sql operations describe "$OP_ID" \
    --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
    --format="json" | jq -r '.status')
  [ "$status" = "DONE" ] && break
  sleep 10
done
```

## Backup Idempotency

On-demand backups always create a new backup run. To avoid unnecessary backup creation:
1. Check last backup time: `gcloud sql backups list --instance=NAME --limit=1 --format="json" | jq -r '.[0] | "\(.id) \(.enqueuedTime)"'`
2. If most recent backup is less than 1 hour old, warn user and skip unless forced.

## Cloning Idempotency

Clone names must be unique per project. Verify target name doesn't exist:
```bash
if gcloud sql instances describe NEW_NAME --quiet 2>/dev/null; then
    echo "Clone target already exists — choose different name"
else
    gcloud sql instances clone SOURCE NEW_NAME
fi
```