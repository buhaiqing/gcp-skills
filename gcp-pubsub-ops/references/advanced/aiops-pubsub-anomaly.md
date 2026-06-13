# AIOps Anomaly Detection — Google Cloud Pub/Sub

> Provides messaging administrators with a guide to implementing AIOps-driven anomaly detection for Cloud Pub/Sub — message throughput anomalies, subscription backlog growth, ordering violations, and dead letter queue spike detection.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Message Throughput Anomalies](#message-throughput-anomalies)
5. [Subscription Backlog Growth](#subscription-backlog-growth)
6. [Ordering Violations](#ordering-violations)
7. [Dead Letter Queue Spike Detection](#dead-letter-queue-spike-detection)
8. [Real-Time Alerting](#real-time-alerting)
9. [Automated Remediation](#automated-remmediation)
10. [Best Practices](#best-practices)
11. [Troubleshooting](#troubleshooting)
12. [See Also](#see-also)

## Overview

AIOps for Cloud Pub/Sub detects messaging anomalies and predicts backpressure. With Cloud Monitoring and Pub/Sub metrics, you can:

- Detect message throughput anomalies (publish/subscribe rates)
- Monitor subscription backlog growth (consumer lag)
- Track ordering violations (message ordering)
- Identify dead letter queue spikes (failed messages)
- Automate scaling responses

### Detection Capabilities

| Anomaly Type | Detection Method | Severity |
|--------------|-----------------|----------|
| Throughput spike | Volume threshold | High |
| Backlog growth | Rate-of-change analysis | High |
| Ordering violation | Sequence analysis | Medium |
| DLQ spike | Threshold monitoring | Critical |
| Consumer lag | Lag metric monitoring | High |

## Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                          Pub/Sub Monitoring                              │
│                                                                          │
│  Pub/Sub Topics                                                          │
│  ┌────────────────┐    ┌────────────────┐    ┌──────────────────────┐   │
│  │ Messages       │───►│ Pub/Sub API    │───►│ Cloud Monitoring    │   │
│  │ (Published)    │    │ (Metrics)      │    │ (Metrics)           │   │
│  └────────────────┘    └────────────────┘    └──────────────────────┘   │
│                                                       │                  │
│              ┌────────────────────────────────────────┤                  │
│              │                     │                   │                 │
│       ┌──────▼──────┐      ┌──────▼──────┐     ┌──────▼──────┐        │
│       │ Throughput  │      │ Backlog     │     │ Alert       │        │
│       │ Analysis    │      │ Analysis    │     │ Policy      │        │
│       └─────────────┘      └──────┬──────┘     └─────────────┘        │
│                                   │                                     │
│                          ┌────────▼────────┐                           │
│                          │ Automated       │                           │
│                          │ Remediation     │                           │
│                          └─────────────────┘                           │
└────────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

```bash
# 1. Enable required APIs
gcloud services enable pubsub.googleapis.com
gcloud services enable monitoring.googleapis.com

# 2. Set project
export CLOUDSDK_CORE_PROJECT=my-pubsub-project

# 3. Verify Pub/Sub access
gcloud pubsub topics list --format="table(name)"
```

## Message Throughput Anomalies

### Throughput Analysis

```bash
# Analyze message throughput
gcloud pubsub topics list --format="json" | \
  jq -r '.[].name' | \
  while read -r topic; do
    echo "Topic: $topic"
    gcloud pubsub topics describe $topic --format="json" | \
      jq '.messageRetentionDuration'
  done
```

### Throughput Anomaly Detection

```bash
# Detect throughput anomalies
bq query --use_legacy_sql=false \
  "WITH hourly_throughput AS (
    SELECT
      TIMESTAMP_TRUNC(timestamp, HOUR) as hour,
      resource.labels.topic_id as topic,
      SUM(protoPayload.bytesPublishedCount) as message_count
    FROM \`my_project.logging_bucket/pubsub.googleapis.com_activity\`
    WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
    GROUP BY 1, 2
  ),
  stats AS (
    SELECT
      topic,
      AVG(message_count) as mean_count,
      STDDEV(message_count) as stddev_count
    FROM hourly_throughput
    GROUP BY 1
  )
  SELECT
    ht.hour,
    ht.topic,
    ht.message_count,
    (ht.message_count - s.mean_count) / NULLIF(s.stddev_count, 0) as z_score
  FROM hourly_throughput ht
  JOIN stats s ON ht.topic = s.topic
  WHERE ABS((ht.message_count - s.mean_count) / NULLIF(s.stddev_count, 0)) > 2
  ORDER BY ht.hour DESC"
```

## Subscription Backlog Growth

### Backlog Analysis

```bash
# Analyze subscription backlog
gcloud pubsub subscriptions list --format="json" | \
  jq '.[] | {
    name: .name,
    topic: .topic,
    ackDeadlineSeconds: .ackDeadlineSeconds,
    messageRetentionDuration: .messageRetentionDuration
  }'
```

### Backlog Growth Detection

```bash
# Detect backlog growth
bq query --use_legacy_sql=false \
  "SELECT
    resource.labels.subscription_id as subscription,
    protoPayload.numUnackedMessages as unacked_messages,
    protoPayload.oldestUnackedMessageAge as oldest_age_seconds
  FROM \`my_project.logging_bucket/pubsub.googleapis.com_activity\`
  WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
    AND protoPayload.numUnackedMessages > 1000
  ORDER BY unacked_messages DESC"
```

## Ordering Violations

### Ordering Analysis

```bash
# Check ordering settings
gcloud pubsub subscriptions describe my-subscription \
  --format="json" | jq '.enableMessageOrdering'

# Analyze ordering violations
bq query --use_legacy_sql=false \
  "SELECT
    resource.labels.subscription_id as subscription,
    protoPayload.orderingKey,
    COUNT(*) as message_count,
    MIN(timestamp) as first_message,
    MAX(timestamp) as last_message
  FROM \`my_project.logging_bucket/pubsub.googleapis.com_activity\`
  WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
    AND protoPayload.orderingKey IS NOT NULL
  GROUP BY 1, 2
  HAVING message_count > 1
  ORDER BY message_count DESC"
```

## Dead Letter Queue Spike Detection

### DLQ Analysis

```bash
# Analyze dead letter queue
gcloud pubsub subscriptions describe my-subscription \
  --format="json" | jq '.deadLetterPolicy'

# Detect DLQ spikes
bq query --use_legacy_sql=false \
  "SELECT
    resource.labels.subscription_id as subscription,
    protoPayload.deadLetterCount as dlq_count
  FROM \`my_project.logging_bucket/pubsub.googleapis.com_activity\`
  WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
    AND protoPayload.deadLetterCount > 100
  ORDER BY dlq_count DESC"
```

## Real-Time Alerting

### Throughput Alert Setup

```bash
# Create throughput alert
gcloud alpha monitoring policies create \
  --notification-channels="projects/$CLOUDSDK_CORE_PROJECT/notificationChannels/123456789" \
  --display-name="Pub/Sub Throughput High" \
  --condition-display-name="Messages > 10K/min" \
  --condition-filter='metric.type="pubsub.googleapis.com/topic/send_message_operation_count" resource.type="pubsub_topic"' \
  --condition-threshold-value=10000 \
  --condition-threshold-duration=60s \
  --condition-threshold-comparison=COMPARISON_GT
```

### Backlog Alert Setup

```bash
# Create backlog alert
gcloud alpha monitoring policies create \
  --notification-channels="projects/$CLOUDSDK_CORE_PROJECT/notificationChannels/123456789" \
  --display-name="Pub/Sub Backlog High" \
  --condition-display-name="Unacked > 10K" \
  --condition-filter='metric.type="pubsub.googleapis.com/subscription/num_undelivered_messages" resource.type="pubsub_subscription"' \
  --condition-threshold-value=10000 \
  --condition-threshold-duration=300s \
  --condition-threshold-comparison=COMPARISON_GT
```

## Automated Remediation

### Auto-Scale Subscribers

```bash
#!/bin/bash
# auto-scale-subscribers.sh

SUBSCRIPTION=$1
MAX_MESSAGES=10000

UNACKED=$(gcloud pubsub subscriptions describe $SUBSCRIPTION \
  --format="value(numUnackedMessages)")

if [ $UNACKED -gt $MAX_MESSAGES ]; then
  echo "Backlog high: $UNACKED messages"
  # Scale up subscribers
  kubectl scale deployment my-subscriber --replicas=10
fi
```

### Auto-Cancel Stuck Messages

```bash
#!/bin/bash
# auto-cancel-stuck-messages.sh

SUBSCRIPTION=$1
MAX_AGE=3600

gcloud pubsub subscriptions pull $SUBSCRIPTION --limit=100 --auto-ack | \
  while read -r message; do
    AGE=$(echo $message | jq '.publishTime' | \
      jq -r 'fromdateiso8601 - now' | \
      jq 'if . > '$MAX_AGE' then true else false end')
    if [ "$AGE" = "true" ]; then
      echo "Cancelling stuck message: $(echo $message | jq '.messageId')"
    fi
  done
```

## Best Practices

1. **Enable Dead Letter Queues**: Capture failed messages
2. **Set Message Retention**: Configure appropriate retention
3. **Monitor Backlog**: Set alerts for subscription backlog
4. **Use Ordering Keys**: Ensure message ordering when needed
5. **Implement Retries**: Configure retry policies for failures
6. **Scale Consumers**: Auto-scale based on backlog size
7. **Use Flow Control**: Limit outstanding messages

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| High backlog | Consumer lag | Scale consumers |
| Message loss | No dead letter queue | Enable DLQ |
| Ordering violations | Ordering not enabled | Enable ordering |
| Throughput limit | Quota exceeded | Request quota increase |

### Debug Commands

```bash
# Check topic stats
gcloud pubsub topics describe my-topic --format="json"

# Check subscription stats
gcloud pubsub subscriptions describe my-subscription --format="json"

# List recent messages
gcloud pubsub subscriptions pull my-subscription --limit=10
```

## See Also

- [Pub/Sub Monitoring](../monitoring.md)
- [Pub/Sub Core Concepts](../core-concepts.md)
- [Troubleshooting](../troubleshooting.md)
- [Google Cloud Architecture Framework — Reliability](https://cloud.google.com/architecture/framework/reliability)
