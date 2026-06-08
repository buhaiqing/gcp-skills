# Monitoring — Cloud Pub/Sub

## Key Metrics

| Metric | Type | Threshold |
|--------|------|-----------|
| pubsub.googleapis.com/subscription/num_undelivered_messages | Gauge | > 10,000 = backlog growing |
| pubsub.googleapis.com/subscription/oldest_unacked_message_age | Gauge | > 300s = consumer lag |
| pubsub.googleapis.com/subscription/num_outstanding_bytes | Gauge | Monitor for memory pressure |
| pubsub.googleapis.com/subscription/push_request_count | Counter | 0 = push endpoint down |
| pubsub.googleapis.com/subscription/push_failed_request_count | Counter | > 0 = endpoint errors |
| pubsub.googleapis.com/subscription/ack_message_count | Counter | Track throughput |
| pubsub.googleapis.com/subscription/nack_message_count | Counter | High nack rate = consumer issues |
| pubsub.googleapis.com/topic/send_request_count | Counter | Publish throughput |
| pubsub.googleapis.com/topic/send_bytes_count | Counter | Bandwidth monitoring |
| pubsub.googleapis.com/topic/num_topics | Gauge | Topic count |
| pubsub.googleapis.com/subscription/subscription_send_request_count | Counter | Pull throughput |

## Alert Policy Examples

**Backlog Alert**:
```bash
gcloud alpha monitoring policies create \
  --display-name="PubSub-Backlog-Alert" \
  --condition-filter='metric.type="pubsub.googleapis.com/subscription/num_undelivered_messages"' \
  --condition-threshold-value=10000 \
  --condition-duration=300s
```

**Oldest Unacked Message Age Alert**:
```bash
gcloud alpha monitoring policies create \
  --display-name="PubSub-Message-Age-Alert" \
  --condition-filter='metric.type="pubsub.googleapis.com/subscription/oldest_unacked_message_age"' \
  --condition-threshold-value=600 \
  --condition-duration=300s
```

**Push Failure Alert**:
```bash
gcloud alpha monitoring policies create \
  --display-name="PubSub-Push-Failure-Alert" \
  --condition-filter='metric.type="pubsub.googleapis.com/subscription/push_failed_request_count"' \
  --condition-threshold-value=10 \
  --condition-duration=60s
```

## Anomaly Patterns

| Pattern | Likely Cause |
|---------|--------------|
| Backlog spike | Consumer down or slow processing; publish burst |
| Oldest unacked age spike | Consumer hung; ack deadline too short |
| Push failed requests > 0 | Endpoint down, TLS error, or auth failure |
| Nack rate spike | Consumer rejecting messages; poison message |
| Publish count drops to 0 | Publisher down; quota exhausted |
| Oldest unacked → 0 after spike | Consumer recovered; backlog drained |

## Dashboard Query (Cloud Monitoring MQL)

**Backlog by Subscription**:
```
fetch pubsub_subscription
| metric 'pubsub.googleapis.com/subscription/num_undelivered_messages'
| group_by [resource.subscription_id], sum()
| every 1m
```

**Message Age by Subscription**:
```
fetch pubsub_subscription
| metric 'pubsub.googleapis.com/subscription/oldest_unacked_message_age'
| group_by [resource.subscription_id], max()
| every 1m
```

**Publish vs Ack Throughput**:
```
fetch pubsub_topic
| metric 'pubsub.googleapis.com/topic/send_request_count'
| group_by [], sum()
| every 1m
| join
  (fetch pubsub_subscription
   | metric 'pubsub.googleapis.com/subscription/ack_message_count'
   | group_by [], sum()
   | every 1m)
```

## DLQ Monitoring

**DLQ Backlog Alert**:
```bash
gcloud alpha monitoring policies create \
  --display-name="PubSub-DLQ-Backlog-Alert" \
  --condition-filter='metric.type="pubsub.googleapis.com/subscription/num_undelivered_messages" AND resource.subscription_id="dlq-subscription"' \
  --condition-threshold-value=1000 \
  --condition-duration=300s
```
