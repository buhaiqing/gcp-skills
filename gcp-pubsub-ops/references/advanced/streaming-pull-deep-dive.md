# Streaming Pull Deep Dive — Google Cloud Pub/Sub

> Provides messaging administrators with an in-depth guide to Cloud Pub/Sub streaming pull — exactly-once delivery, dead letter queues, retry policies, flow control, and consumer health monitoring.

## Table of Contents

1. [Overview](#overview)
2. [Exactly-Once Delivery](#exactly-once-delivery)
3. [Dead Letter Queue Setup](#dead-letter-queue-setup)
4. [Retry Policies](#retry-policies)
5. [Flow Control Settings](#flow-control-settings)
6. [Consumer Health Monitoring](#consumer-health-monitoring)
7. [Troubleshooting](#troubleshooting)
8. [See Also](#see-also)

## Overview

Streaming pull is Pub/Sub's high-throughput subscription mode where subscribers receive messages continuously via bidirectional streaming RPCs. Unlike pull (synchronous request/response), streaming pull maintains a persistent connection and receives messages as they arrive.

### Streaming Pull Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Streaming Pull Architecture                      │
│                                                                          │
│  ┌────────────────┐         ┌────────────────┐         ┌───────────┐ │
│  │  Pub/Sub       │────────▶│  Streaming     │────────▶│ Consumer  │ │
│  │  Service       │         │  Pull Client   │         │ Application│ │
│  └────────────────┘         └────────────────┘         └───────────┘ │
│                                       │                               │
│                                ┌──────▼──────┐                        │
│                                │ Ack Manager  │                        │
│                                │ (batching)  │                        │
│                                └─────────────┘                        │
└────────────────────────────────────────────────────────────────────────┘
```

### Streaming Pull Capabilities

| Feature | Description |
|---------|-------------|
| Exactly-once delivery | Deduplication at Pub/Sub level |
| Dead letter queue | Failed message routing |
| Retry policies | Configurable backoff and attempts |
| Flow control | Subscriber-side limits |
| Consumer health | Ack and nack tracking |

## Exactly-Once Delivery

Exactly-once delivery guarantees that each message is delivered to subscribers exactly once within a configurable deduplication window (up to 10 minutes). This is achieved through:

1. **Publisher-side deduplication** — Messages with identical `message_id` within the deduplication window are rejected
2. **Subscriber-side deduplication** — Pub/Sub tracks already-processed `ack_id`s

### Enable Exactly-Once Delivery

**CLI**:
```bash
gcloud pubsub subscriptions create "{{user.subscription_id}}" \
  --topic="{{user.topic_id}}" \
  --enable-exactly-once-delivery \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

**Update existing subscription**:
```bash
gcloud pubsub subscriptions update "{{user.subscription_id}}" \
  --enable-exactly-once-delivery \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

### Exactly-Once Delivery Settings

| Setting | Description | CLI Flag |
|---------|-------------|----------|
| Enable exactly-once | Enable deduplication | `--enable-exactly-once-delivery` |
| Disable exactly-once | Disable deduplication | `--no-enable-exactly-once-delivery` |

### Exactly-Once Delivery Behavior

| Scenario | Behavior |
|----------|----------|
| First delivery | Message delivered normally |
| Subscriber crash | Message redelivered after ack deadline |
| Duplicate delivery | Rejected if within deduplication window |
| Ack timeout | Message redelivered after deadline |

### Validate Exactly-Once Configuration

**CLI**:
```bash
gcloud pubsub subscriptions describe "{{user.subscription_id}}" \
  --format="json" | jq '.enableExactlyOnceDelivery'
```

**Expected**: `true`

## Dead Letter Queue Setup

Dead letter queues (DLQ) capture messages that fail delivery after the maximum retry attempts. This prevents message loss and enables failed message inspection.

### DLQ Architecture

```
┌──────────────┐     Delivery Failed      ┌─────────────────┐
│   Topic      │────────────────────────▶│   Dead Letter    │
│               │  (after max retries)    │   Topic          │
└──────────────┘                          └─────────────────┘
       │                                          │
       │                                          ▼
       │                                  ┌──────────────┐
       │                                  │   DLQ        │
       │                                  │   Subscription│
       └──────────────────────────────────▶│               │
                  (original subscription)   └──────────────┘
```

### Configure DLQ

**Pre-flight**:
1. Create dead letter topic
2. Grant Pub/Sub SA publisher role on DLQ topic
3. Optionally create DLQ subscription for inspection

**Step 1: Create DLQ topic**:
```bash
gcloud pubsub topics create "{{user.dead_letter_topic}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

**Step 2: Grant publisher role**:
```bash
PROJECT_NUMBER=$(gcloud projects describe "{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="value(projectNumber)")
gcloud pubsub topics add-iam-policy-binding "{{user.dead_letter_topic}}" \
  --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com" \
  --role="roles/pubsub.publisher" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

**Step 3: Configure subscription DLQ**:
```bash
gcloud pubsub subscriptions update "{{user.subscription_id}}" \
  --dead-letter-topic="{{user.dead_letter_topic}}" \
  --max-delivery-attempts="{{user.max_delivery_attempts:-5}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

### DLQ Settings Reference

| Setting | CLI Flag | Default | Range |
|---------|----------|---------|-------|
| Dead letter topic | `--dead-letter-topic` | None | Topic ID |
| Max delivery attempts | `--max-delivery-attempts` | 5 | 1-100 |
| Dead letter project | `--dead-letter-project` | Same as sub | Project ID |

### Inspect DLQ Messages

**Create DLQ subscription** (optional):
```bash
gcloud pubsub subscriptions create "{{user.subscription_id}}-dlq" \
  --topic="{{user.dead_letter_topic}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

**Pull DLQ messages**:
```bash
gcloud pubsub subscriptions pull "{{user.subscription_id}}-dlq" \
  --limit=10 \
  --auto-ack \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

### Disable DLQ

**CLI**:
```bash
gcloud pubsub subscriptions update "{{user.subscription_id}}" \
  --clear-dead-letter-topic \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

**Validate**: `gcloud pubsub subscriptions describe "{{user.subscription_id}}" --format="json" | jq '.deadLetterPolicy == null'`

## Retry Policies

Retry policies control how Pub/Sub handles message delivery failures. Configurable parameters include minimum backoff, maximum backoff, and maximum delivery attempts.

### Retry Policy Architecture

```
Message Delivery Attempt
         │
         ▼
    ┌─────────┐
    │ Success │──▶ Done
    └────┬────┘
         │ Failure
         ▼
    ┌─────────────────────┐
    │ Wait (min_delay)    │
    └──────────┬──────────┘
               │
               ▼
    ┌─────────────────────┐
    │ Retry Delivery      │
    └──────────┬──────────┘
               │
               ▼
    ┌─────────────────────┐
    │ If attempts < max: │
    │   Wait (exponential │◀─┐
    │   backoff up to     │
    │   max_delay)        │  │
    └──────────┬──────────┘  │
               │             │
               ▼             │
    ┌─────────────────────┐   │
    │ If attempts >= max: │   │
    │   Send to DLQ       │   │
    └─────────────────────┘   │
                             │
         (back to retry)─────┘
```

### Configure Retry Policy

**CLI (minimum/maximum backoff)**:
```bash
gcloud pubsub subscriptions update "{{user.subscription_id}}" \
  --min-retry-delay="{{user.min_retry_delay:-10s}}" \
  --max-retry-delay="{{user.max_retry_delay:-600s}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

**CLI (with max delivery attempts)**:
```bash
gcloud pubsub subscriptions update "{{user.subscription_id}}" \
  --min-retry-delay="{{user.min_retry_delay:-10s}}" \
  --max-retry-delay="{{user.max_retry_delay:-600s}}" \
  --max-delivery-attempts="{{user.max_delivery_attempts:-5}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

### Retry Policy Settings

| Setting | CLI Flag | Default | Min | Max |
|---------|----------|---------|-----|-----|
| Minimum delay | `--min-retry-delay` | 10s | 0s | 600s |
| Maximum delay | `--max-retry-delay` | 600s | 10s | 600s |
| Max delivery attempts | `--max-delivery-attempts` | 5 | 1 | 100 |

### Retry Delay Format

| Format | Example |
|--------|---------|
| Seconds | `10s`, `300s` |
| Minutes | `5m`, `10m` |
| Hours | `1h`, `2h` |

### Disable Retry Policy

**CLI**:
```bash
gcloud pubsub subscriptions update "{{user.subscription_id}}" \
  --clear-min-retry-delay \
  --clear-max-retry-delay \
  --clear-max-delivery-attempts \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

**Validate**: `gcloud pubsub subscriptions describe "{{user.subscription_id}}" --format="json" | jq '.retryPolicy'`

### Retry Policy Combinations

| Use Case | min_delay | max_delay | max_attempts |
|----------|-----------|-----------|--------------|
| Fast retry | 1s | 10s | 3 |
| Standard | 10s | 600s | 5 |
| Aggressive | 5s | 300s | 10 |
| Conservative | 60s | 3600s | 3 |
| No retries | N/A | N/A | 1 |

## Flow Control Settings

Flow control limits how many messages a subscriber can have outstanding at once. This prevents memory exhaustion and allows controlled message processing rates.

### Flow Control Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Flow Control                                 │
│                                                                   │
│  Pub/Sub                    Subscriber                    App     │
│    │                            │                            │     │
│    │  ◀── ack_deadline ──────▶  │                            │     │
│    │                            │                            │     │
│    │  ◀── max_messages ───────▶│                            │     │
│    │  ◀── max_bytes ──────────▶│                            │     │
│    │                            │                            │     │
│    │  ── messages ─────────────▶│── forwarded ─────────────▶│     │
│    │                            │                            │     │
│    │  ◀─── acks ─────────────── │                            │     │
│    │                            │                            │     │
└─────────────────────────────────────────────────────────────────┘
```

### Ack Deadline

The ack deadline is the maximum time a subscriber has to acknowledge a message before Pub/Sub redelivers it.

**CLI**:
```bash
gcloud pubsub subscriptions create "{{user.subscription_id}}" \
  --topic="{{user.topic_id}}" \
  --ack-deadline="{{user.ack_deadline_seconds:-60}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

**Update ack deadline**:
```bash
gcloud pubsub subscriptions update "{{user.subscription_id}}" \
  --ack-deadline="{{user.ack_deadline_seconds:-60}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

### Ack Deadline Settings

| Setting | CLI Flag | Default | Min | Max |
|---------|----------|---------|-----|-----|
| Ack deadline | `--ack-deadline` | 10s | 10s | 600s |

### Flow Control Limits

Flow control limits are set via the SDK, not CLI. Key parameters:

| Parameter | Description | Typical Value |
|-----------|-------------|---------------|
| maxOutstandingMessages | Max unacked messages | 100-1000 |
| maxOutstandingBytes | Max unacked bytes | 10MB-100MB |
| enableStreaming Pull | Use streaming pull | true |

### Subscriber Seek

Subscriber seek allows rewinding a subscription to a specific point in time or snapshot.

**Seek to timestamp**:
```bash
gcloud pubsub subscriptions seek "{{user.subscription_id}}" \
  --time="{{user.seek_timestamp}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

**Seek to snapshot**:
```bash
gcloud pubsub subscriptions seek "{{user.subscription_id}}" \
  --snapshot="{{user.snapshot_id}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

### Flow Control Best Practices

1. **Set appropriate ack deadline** — Long enough for processing, short enough for fast redelivery
2. **Monitor backlog** — Track `num_undelivered_messages` metric
3. **Use retry policies** — Configure for expected failure patterns
4. **Enable flow control** — Prevent memory exhaustion in subscribers

## Consumer Health Monitoring

Consumer health monitoring tracks the health of message processing through ack rates, nack rates, and redelivery patterns.

### Key Health Metrics

| Metric | Description | Healthy | Warning | Critical |
|--------|-------------|---------|---------|----------|
| `ack_ratio` | Ack / total delivered | > 0.95 | 0.90-0.95 | < 0.90 |
| `nack_ratio` | Nack / total delivered | < 0.05 | 0.05-0.10 | > 0.10 |
| `redeliver_ratio` | Redelivered / total | < 0.05 | 0.05-0.10 | > 0.10 |
| `backlog` | Unacked messages | < 1000 | 1000-10000 | > 10000 |
| `oldest_message_age` | Age of oldest unacked | < 1 hour | 1-24 hours | > 24 hours |

### Monitor Consumer Health

**CLI**:
```bash
gcloud pubsub subscriptions describe "{{user.subscription_id}}" \
  --format="json" | jq '{
    name: .name,
    ackDeadlineSeconds: .ackDeadlineSeconds,
    numUndeliveredMessages: .numUndeliveredMessages,
    messageRetentionDuration: .messageRetentionDuration,
    enableExactlyOnceDelivery: .enableExactlyOnceDelivery,
    deadLetterPolicy: .deadLetterPolicy,
    retryPolicy: .retryPolicy
  }'
```

### Health Check Commands

**Check backlog**:
```bash
gcloud pubsub subscriptions describe "{{user.subscription_id}}" \
  --format="value(numUndeliveredMessages)"
```

**Check oldest message age**:
```bash
gcloud pubsub subscriptions describe "{{user.subscription_id}}" \
  --format="json" | jq '.oldestUnackedMessageAge'
```

**List subscription metrics**:
```bash
gcloud pubsub subscriptions list \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="table(name,numUndeliveredMessages,ackDeadlineSeconds)"
```

### Consumer Health Dashboard

```bash
# Create monitoring dashboard query
gcloud monitoring dashboard create \
  --config-from-file=dashboard.json
```

**Example dashboard config**:
```json
{
  "displayName": "Pub/Sub Consumer Health",
  "mosaicLayout": {
    "columns": 2,
    "tiles": [
      {"xyChart": {
        "dataSets": [{
          "timeSeriesQuery": {
            "prometheusQuery": "pubsub_subscription_num_undelivered_messages{subscription_id=\"{{user.subscription_id}}\"}"
          }
        }]
      }}
    ]
  }
}
```

### Alert on Consumer Issues

**Alert on high backlog**:
```bash
gcloud alpha monitoring policies create \
  --notification-channels="projects/$CLOUDSDK_CORE_PROJECT/notificationChannels/{{user.channel_id}}" \
  --display-name="PubSub Backlog High" \
  --condition-filter='metric.type="pubsub.googleapis.com/subscription/num_undelivered_messages" AND metric.labels.subscription_id="{{user.subscription_id}}"' \
  --condition-threshold-value=10000 \
  --condition-duration=300s
```

**Alert on redelivery spike**:
```bash
gcloud alpha monitoring policies create \
  --notification-channels="projects/$CLOUDSDK_CORE_PROJECT/notificationChannels/{{user.channel_id}}" \
  --display-name="PubSub Redelivery Spike" \
  --condition-filter='metric.type="pubsub.googleapis.com/subscription/ack_message_operation_count" AND metric.labels.subscription_id="{{user.subscription_id}}"' \
  --condition-threshold-value=1000 \
  --condition-duration=60s
```

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| High redelivery rate | Ack deadline too short | Increase `--ack-deadline` |
| Messages stuck in DLQ | DLQ misconfigured | Verify DLQ topic and IAM |
| Consumer memory exhaustion | No flow control | Set maxOutstandingMessages/Bytes |
| Duplicate messages | Exactly-once disabled | Enable `--enable-exactly-once-delivery` |
| Slow message processing | Retry delays too long | Reduce `--min-retry-delay` |

### Debug Commands

```bash
# Full subscription diagnostics
gcloud pubsub subscriptions describe "{{user.subscription_id}}" \
  --format="json" | jq '{
    name, topic,
    ackDeadlineSeconds,
    enableExactlyOnceDelivery,
    enableMessageOrdering,
    deadLetterPolicy,
    retryPolicy,
    numUndeliveredMessages,
    oldestUnackedMessageAge,
    messageRetentionDuration
  }'

# Check DLQ topic exists
gcloud pubsub topics describe "{{user.dead_letter_topic}}" --format="json"

# Verify Pub/Sub SA permissions on DLQ
gcloud pubsub topics get-iam-policy "{{user.dead_letter_topic}}" --format="json"

# Monitor message flow
gcloud pubsub subscriptions pull "{{user.subscription_id}}" --limit=1 --auto-ack
```

## See Also

- [Pub/Sub Monitoring](../monitoring.md)
- [Pub/Sub Core Concepts](../core-concepts.md)
- [Pub/Sub Troubleshooting](../troubleshooting.md)
- [Pub/Sub Dead Letter Queue Documentation](https://cloud.google.com/pubsub/docs/dead-letter-topics)
- [Pub/Sub Exactly-Once Documentation](https://cloud.google.com/pubsub/docs/exactly-once-delivery)
