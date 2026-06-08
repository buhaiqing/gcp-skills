# Idempotency Checklist — Cloud Pub/Sub

## Create

| Resource | Key | Retry Behavior |
|----------|-----|----------------|
| Topic | name (unique per project) | ALREADY_EXISTS / 409 — reuse existing |
| Subscription | name (unique per project) | ALREADY_EXISTS / 409 — reuse existing |
| Snapshot | name (unique per project) | ALREADY_EXISTS / 409 — reuse existing |

## Update

| Operation | Idempotent? |
|-----------|-------------|
| Update message retention | Yes (same value = no-op) |
| Update ack deadline | Yes (same value = no-op) |
| Update push endpoint | Yes (same URL = no-op) |
| Update DLQ config | Yes (same topic + attempts = no-op) |
| Update retry policy | Yes (same backoff = no-op) |
| Update CMEK key | Yes (same key = no-op) |
| Add IAM binding | Yes (same member+role = no-op) |
| Enable exactly-once delivery | Yes (already enabled = no-op) |
| Enable message ordering | Yes (already enabled = no-op) |

## Delete

| Resource | Retry Safe? |
|----------|-------------|
| Topic | Safe — NOT_FOUND on second attempt |
| Subscription | Safe — NOT_FOUND on second attempt |
| Snapshot | Safe — NOT_FOUND on second attempt |

## Publish

| Scenario | Idempotent? | Notes |
|----------|-------------|-------|
| Publish without ordering | Safe | Message may be duplicated; at-least-once delivery |
| Publish with ordering key | Safe | Order preserved for same key |
| Exactly-once delivery | Safe | Server deduplicates |

## Pull

| Scenario | Idempotent? | Notes |
|----------|-------------|-------|
| Pull + ack | Safe | Ack is idempotent |
| Pull + nack | Safe | Message redelivered |
| Pull without ack | Not safe | Message reappears after deadline |

## Seek

| Operation | Idempotent? | Notes |
|-----------|-------------|-------|
| Seek to snapshot | Safe | Can replay multiple times |
| Seek to timestamp | Safe | Can replay multiple times |

## Safe Retry Pattern

```bash
if ! gcloud pubsub topics describe "{{user.topic_id}}" --quiet 2>/dev/null; then
    gcloud pubsub topics create "{{user.topic_id}}"
else
    echo "Topic already exists — no action needed"
fi
```

## Subscription De-Duplication

```bash
# Create only if not exists
gcloud pubsub subscriptions describe "{{user.subscription_id}}" --quiet 2>/dev/null \
  || gcloud pubsub subscriptions create "{{user.subscription_id}}" \
    --topic="{{user.topic_id}}" \
    --ack-deadline=30 \
    --message-retention-duration=7d
```

## DLQ Idempotency

```bash
# Update DLQ config idempotently
gcloud pubsub subscriptions update "{{user.subscription_id}}" \
  --dead-letter-topic="{{user.dead_letter_topic}}" \
  --max-delivery-attempts=5
# If already configured with same values, no change
```
