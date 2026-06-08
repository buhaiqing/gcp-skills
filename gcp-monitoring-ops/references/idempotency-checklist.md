# Idempotency Checklist — Cloud Monitoring

## Create

| Resource | Key | Retry Behavior |
|----------|-----|----------------|
| Alert Policy | displayName (project-unique) | `ALREADY_EXISTS` / 409 — list first, update if exists |
| Notification Channel | displayName + type + labels | `ALREADY_EXISTS` / 409 — list first, update if exists |
| Dashboard | displayName (project-unique) | No conflict — multiple dashboards with same name allowed; use unique names |
| Uptime Check | displayName (project-unique) | No conflict — use unique names per check target |
| Metric Descriptor | metric.type (project-unique) | `ALREADY_EXISTS` / 409 — no-op if descriptor matches; error if structure differs |

## Update

| Operation | Idempotent? | Notes |
|-----------|-------------|-------|
| Enable/disable alert policy | Yes | Same state = no-op |
| Update alert threshold | Yes | Replacing value is idempotent |
| Add notification channel to policy | Yes | Duplicate channel references ignored |
| Update dashboard from JSON file | No — etag conflict | Must fetch latest etag before update |
| Update uptime check config | Yes | Replacing config is idempotent |

## Delete

| Resource | Retry Safe? | Notes |
|----------|-------------|-------|
| Alert Policy | Safe | `NOT_FOUND` on second attempt |
| Notification Channel | Safe | `NOT_FOUND` on second attempt; check if referenced by alerts first |
| Dashboard | Safe | `NOT_FOUND` on second attempt |
| Uptime Check | Safe | `NOT_FOUND` on second attempt |
| Metric Descriptor | Safe | `NOT_FOUND` on second attempt; also deletes all time series data |

## Dashboard Etag Handling

```bash
# 1. Fetch current etag
ETAG=$(gcloud monitoring dashboards describe DASHBOARD_ID --format=json | jq -r '.etag')

# 2. Update with etag in request
# API requires etag match for optimistic concurrency
# gcloud handles etag automatically; for REST API, include etag in PATCH body
```

## Alert Policy Idempotency

```bash
# Idempotent create/update pattern
if ! gcloud monitoring alert-policies list --filter="displayName='POLICY_NAME'" --format=json | jq '.[] | .name' | grep -q .; then
    gcloud monitoring alert-policies create "POLICY_NAME" --display-name="POLICY_NAME" ...
else
    echo "Alert policy already exists — no action needed"
fi
```

## Notification Channel Deduplication

```bash
# Check if channel already exists before creating
CHANNEL_NAME="ops-team-email"
EXISTING=$(gcloud monitoring channels list --format=json \
  | jq -r ".[] | select(.displayName == \"$CHANNEL_NAME\") | .name")

if [ -z "$EXISTING" ]; then
    gcloud monitoring channels create --display-name="$CHANNEL_NAME" --type=email --channel-labels=email_address=ops@example.com
else
    echo "Channel already exists: $EXISTING"
fi
```

## Uptime Check Idempotency

```bash
# Idempotent uptime check creation
CHECK_NAME="api-health"
EXISTING=$(gcloud monitoring uptime list --format=json \
  | jq -r ".[] | select(.displayName == \"$CHECK_NAME\") | .name")

if [ -z "$EXISTING" ]; then
    gcloud monitoring uptime create "$CHECK_NAME" --display-name="$CHECK_NAME" --hostname=api.example.com --check-type=HTTPS --period=60 --timeout=10
else
    echo "Uptime check already exists: $EXISTING"
fi
```

## Safe Retry Pattern (All Resources)

| Resource | Create Retry | Update Retry | Delete Retry |
|----------|-------------|-------------|-------------|
| Alert Policy | List → create or skip | Direct update (idempotent) | Delete → ignore NOT_FOUND |
| Notification Channel | List → create or skip | Direct update (idempotent) | Delete → ignore NOT_FOUND |
| Dashboard | Direct create (allow duplicates) | Fetch etag → update | Delete → ignore NOT_FOUND |
| Uptime Check | List → create or skip | Direct update (idempotent) | Delete → ignore NOT_FOUND |
