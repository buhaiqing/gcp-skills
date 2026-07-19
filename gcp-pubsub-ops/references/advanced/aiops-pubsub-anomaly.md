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
 9. [Automated Remediation](#automated-remediation)
 10. [Self-Healing Playbook](#self-healing-playbook)
 11. [Best Practices](#best-practices)
 12. [Troubleshooting](#troubleshooting)
 13. [See Also](#see-also)

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

## Self-Healing Playbook

> **Scope:** Closed-loop remediation for the three highest-frequency Pub/Sub anomalies. Every playbook follows the same four-phase contract: **detection → DRY-RUN preview → gate → idempotent apply**.
>
> **Cross-references (do not redefine, only reference):**
> - Error classification → [docs/error-taxonomy.md](../../../docs/error-taxonomy.md) (map each failure to a root-cause dimension; recovery verb `HALT`/`RETRY`/`REMEDIATE`/`ESCALATE`).
> - Blast-radius gating → [docs/cross-skill-blast-radius.md](../../../docs/cross-skill-blast-radius.md) (R1 auto-apply, R2 gate, R3/R4 HALT).
> - Closed-loop feedback → [gcp-gcl-runner-ops/trace_feedback.py](../../../gcp-gcl-runner-ops/trace_feedback.py) (emit a GCL trace per remediation so failures aggregate back into skill quality).
> - Credential masking → AGENTS.md §0.1 (never log `GOOGLE_APPLICATION_CREDENTIALS` content; verify existence only).

### Contract (mandatory for every playbook)

| Phase | Rule |
|-------|------|
| #### Detection | Query Cloud Monitoring / `gcloud` metrics; emit a structured `DIAG` line with the measured value and threshold. |
| #### DRY-RUN preview | Print the exact mutation command with `--dry-run` / `--format=json` describe-only; **no mutation**. |
| #### Gate | Classify blast radius (R1–R4). R1 → auto-apply; R2 → gate; **R3/R4 → HALT** (delete subscription / modify IAM are HALT). |
| #### Idempotent apply | Apply only if `idempotent_safe=true`; re-run must be a no-op. Record `trace_id` for `trace_feedback.py`. |

> **HALT by policy:** deleting a subscription, deleting a topic, and any IAM binding change are **never** auto-applied. Surface to human with the exact resource identifier.

### Playbook 1 — Subscription Backlog Growth

#### Detection
```bash
# DIAG: measure backlog vs threshold
SUB="{{user.subscription_id}}"
UNACKED=$(gcloud pubsub subscriptions describe "$SUB" --format="value(numUndeliveredMessages)")
THRESH=10000
echo "DIAG sub=$SUB unacked=$UNACKED threshold=$THRESH"
[ "$UNACKED" -gt "$THRESH" ] && echo "RESULT backlog_anomaly=true"
```
Maps to `RESOURCE_STATE` / `QUOTA_EXCEEDED` (consumer lag) in error-taxonomy. Radius: **R2** (affects consumers) unless the fix is a single-subscription config bump (R1).

#### DRY-RUN preview — safe R1 fix is to raise ack-deadline (no message loss)
```bash
# DRY-RUN: show current ack deadline, propose new value (idempotent: re-applying same value is no-op)
gcloud pubsub subscriptions describe "$SUB" --format="value(ackDeadlineSeconds)"
echo "PREVIEW: gcloud pubsub subscriptions update $SUB --ack-deadline=60"
```

#### Gate — R1 (ack-deadline bump) auto-apply; R2 (scale consumers / seek) requires gate

#### Idempotent apply
```bash
# EXEC: idempotent — setting an already-set value is a no-op
gcloud pubsub subscriptions update "$SUB" --ack-deadline=60 --format="json" \
  | jq '{name, ackDeadlineSeconds}'
# RESULT: emit trace for trace_feedback.py
echo "RESULT remediation=ack_deadline_bumped sub=$SUB idempotent=true"
```
> Seek-to-snapshot (R2) and delete-subscription (R4) are **NOT** in this playbook — seek requires a gate, delete is HALT.

### Playbook 2 — Dead-Letter Topic Pileup

#### Detection
```bash
# DIAG: count messages in the DLQ topic
DLQ="{{user.dead_letter_topic}}"
DLQ_COUNT=$(gcloud pubsub topics describe "$DLQ" --format="value(numUndeliveredMessages)" 2>/dev/null || echo "n/a")
echo "DIAG dlq=$DLQ count=$DLQ_COUNT"
[ "${DLQ_COUNT:-0}" -gt 100 ] && echo "RESULT dlq_pileup=true"
```
Maps to `RESOURCE_STATE` in error-taxonomy. Radius: **R2** (replay re-injects to consumers).

#### DRY-RUN preview — replay DLQ into the original subscription via a temporary subscription on the DLQ topic
```bash
# DRY-RUN: show DLQ topic + proposed replay subscription (no create yet)
gcloud pubsub topics describe "$DLQ" --format="json" | jq '{name}'
echo "PREVIEW: gcloud pubsub subscriptions create dlq-replay-$SUB --topic=$DLQ"
```

#### Gate — R2: replay re-delivers failed messages to live consumers; require gate (confirm consumers can absorb re-delivery)

#### Idempotent apply
```bash
# EXEC: create replay sub (ALREADY_EXISTS on re-run = safe no-op), pull+ack to redeliver
gcloud pubsub subscriptions create "dlq-replay-$SUB" --topic="$DLQ" --format="json" 2>/dev/null \
  || echo "RESULT replay_sub_exists=true idempotent=true"
gcloud pubsub subscriptions pull "dlq-replay-$SUB" --auto-ack --limit=1000 --format="json" \
  | jq 'length' | xargs -I{} echo "RESULT redelivered={}"
```
> Deleting the DLQ topic (R4) is **HALT**. Modifying the source subscription's IAM to grant DLQ publisher (R3) is **HALT** — surface to human.

### Playbook 3 — Push Endpoint 4xx / 5xx

#### Detection
```bash
# DIAG: pull push endpoint + recent delivery error ratio from Monitoring
SUB="{{user.subscription_id}}"
ENDPOINT=$(gcloud pubsub subscriptions describe "$SUB" --format="value(pushConfig.pushEndpoint)")
echo "DIAG sub=$SUB endpoint=$ENDPOINT"
gcloud monitoring time-series list \
  --filter='metric.type="pubsub.googleapis.com/subscription/push_request_count" AND resource.labels.subscription_id="'$SUB'"' \
  --format="json" | jq '[.[]?.points[]?.value.int64Value] | add // 0' \
  | xargs -I{} echo "RESULT push_errors_total={}"
```
Maps to `NETWORK` (`UNAVAILABLE`/`TIMEOUT`) or `CONFIGURATION` (`INVALID_ARGUMENT`) in error-taxonomy. Radius: **R2** (changing push endpoint alters delivery target).

#### DRY-RUN preview — safe R1 fix is to raise retry backoff (no endpoint change)
```bash
# DRY-RUN: show current retry policy, propose wider backoff (idempotent)
gcloud pubsub subscriptions describe "$SUB" --format="json" | jq '.retryPolicy'
echo "PREVIEW: gcloud pubsub subscriptions update $SUB --min-retry-delay=10s --max-retry-delay=600s"
```

#### Gate — R1 (retry backoff bump) auto-apply; R2 (change `--push-endpoint`) requires gate (transient 4xx/5xx risk during cutover)

#### Idempotent apply
```bash
# EXEC: idempotent — re-applying same backoff is a no-op
gcloud pubsub subscriptions update "$SUB" --min-retry-delay=10s --max-retry-delay=600s --format="json" \
  | jq '{name, retryPolicy}'
echo "RESULT remediation=retry_backoff_widened sub=$SUB idempotent=true"
```
> Changing `--push-endpoint` (R2) requires a gate; deleting the subscription (R4) is HALT.

### Closed-Loop Feedback

After any apply (or HALT), emit a GCL trace so `trace_feedback.py` can aggregate:
```bash
# Emit trace (consumed by gcp-gcl-runner-ops/trace_feedback.py --trace-dir ./audit-results)
cat > "./audit-results/gcl-trace-pubsub-$(date +%s).json" <<EOF
{
  "skill": "gcp-pubsub-ops",
  "op": "self_heal",
  "anomaly": "<backlog|dlq|push_4xx_5xx>",
  "radius": "<R1|R2|R3|R4>",
  "gate": "<auto|gate|HALT>",
  "result": "<PASS|HALT>",
  "idempotent_safe": <true|false>,
  "trace_id": "pubsub-$(date +%s)-$$"
}
EOF
```
Then aggregate: `python3 ../../../gcp-gcl-runner-ops/trace_feedback.py --trace-dir ./audit-results`

### Credential Masking (AGENTS.md §0.1)

All commands above read credentials via `GOOGLE_APPLICATION_CREDENTIALS` (auto by `gcloud`). **Never** echo the key content. Verify existence only:
```bash
test -f "$GOOGLE_APPLICATION_CREDENTIALS" && echo "✅ SA exists (masked)"
# UNSAFE — never do this: cat $GOOGLE_APPLICATION_CREDENTIALS
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
