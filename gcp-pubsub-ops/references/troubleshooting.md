# Troubleshooting — Cloud Pub/Sub

## Error Codes

| HTTP | gRPC | Meaning | Agent Action |
|------|------|---------|--------------|
| 400 | INVALID_ARGUMENT | Request validation failed | Fix parameter per API reference |
| 403 | PERMISSION_DENIED | Insufficient IAM | Grant roles/pubsub.editor or roles/pubsub.admin |
| 404 | NOT_FOUND | Topic/subscription not found | Verify resource name and project |
| 409 | ALREADY_EXISTS | Topic/subscription already exists | Reuse existing or choose different name |
| 412 | FAILED_PRECONDITION | DLQ topic missing or wrong permissions | Create DLQ topic and grant Pub/Sub SA publisher role |
| 429 | QUOTA_EXCEEDED | Topic message rate limit exceeded | Implement backoff; request quota increase |
| 500 | INTERNAL | Server error | Retry with backoff; then escalate |
| 503 | UNAVAILABLE | Service unavailable | Retry with exponential backoff |
| — | BILLING_NOT_ENABLED | Billing not active | Enable in Cloud Console |
| — | TOPIC_NOT_FOUND | Publish to non-existent topic | Create topic first |
| — | SUBSCRIPTION_NOT_FOUND | Pull from non-existent subscription | Create subscription first |
| — | DEADLINE_EXCEEDED | Ack deadline expired | Increase ack deadline or modack |
| — | ORDERING_KEY_VIOLATION | Messages out of order | Retry with same ordering key |
| — | DLQ_OVERFLOW | Dead-letter topic backlog full | Drain DLQ; increase DLQ subscribers |
| — | SNAPSHOT_EXPIRED | Snapshot past 7-day retention | Create new snapshot |
| — | PUSH_ENDPOINT_UNAVAILABLE | Push target not responding | Check endpoint health; configure retry |
| — | SCHEMA_VALIDATION_FAILED | Message doesn't match schema | Fix message format per schema |
| — | EXACTLY_ONCE_DISABLED | Exactly-once not enabled | Enable via --enable-exactly-once-delivery |

## Diagnostic Order

1. Check topic exists: `gcloud pubsub topics describe TOPIC --format=json`
2. Check subscription exists: `gcloud pubsub subscriptions describe SUB --format=json`
3. Check backlog: `gcloud pubsub subscriptions describe SUB --format=json | jq '.numUndeliveredMessages'`
4. Check DLQ config: `gcloud pubsub subscriptions describe SUB --format=json | jq '.deadLetterPolicy'`
5. Check IAM: `gcloud pubsub subscriptions get-iam-policy SUB --format=json`
6. Check push endpoint health (if push sub): curl the endpoint
7. Check Cloud Logging: `resource.type="pubsub_topic" OR resource.type="pubsub_subscription"`
8. Check quotas: Cloud Console → Pub/Sub → Quotas

## Message Backlog Diagnosis

**Check backlog size and age**:
```bash
gcloud pubsub subscriptions describe "{{user.subscription_id}}" --format=json | \
  jq '{numUndeliveredMessages, oldestUnackedMessageAge, ackDeadlineSeconds}'
```

**If backlog growing**:
1. Check if subscriber is running and processing messages
2. Check if ack deadline is too short (messages redelivered): `ackDeadlineSeconds` should be ≥ processing time
3. Check for poison messages causing repeated failures → configure DLQ
4. Check subscriber throughput vs publish rate
5. Scale subscriber horizontally

**If backlog not draining**:
1. Check IAM: subscriber SA has `roles/pubsub.subscriber` on subscription
2. Check push endpoint returns 2xx (if push sub)
3. Check if messages exceed 10-minute ack deadline → increase or use streaming pull with modack
4. Check Cloud Monitoring for `subscription/ack_message_count` vs `subscription/nack_message_count`

## Subscription Stuck

**Symptoms**: No messages delivered, or messages repeatedly fail.

**Diagnosis**:
```bash
# Check subscription state
gcloud pubsub subscriptions describe "{{user.subscription_id}}" --format=json

# Check if detached
gcloud pubsub subscriptions describe "{{user.subscription_id}}" --format=json | jq -r '.state'

# Check topic still exists
gcloud pubsub topics describe "$(gcloud pubsub subscriptions describe "{{user.subscription_id}}" --format=json | jq -r '.topic | split("/")[-1]')" --quiet
```

**Recovery**:
1. If detached: recreate subscription with same topic; messages published after detachment are not recoverable
2. If topic deleted: recreate topic and subscription; messages are lost
3. If subscription misconfigured: update config; seek to snapshot if available
4. If push endpoint down: fix endpoint or switch to pull temporarily

## DLQ Overflow

**Symptoms**: Messages lost after exceeding max delivery attempts and DLQ full.

**Diagnosis**:
```bash
# Check DLQ topic backlog
gcloud pubsub topics describe "{{user.dead_letter_topic}}" --format=json
gcloud pubsub subscriptions list --filter="topic:{{user.dead_letter_topic}}" --format=json
```

**Recovery**:
1. Create a subscription on DLQ topic to drain messages
2. Analyze failed messages for root cause
3. Fix subscriber issue
4. Re-publish corrected messages to original topic
5. Increase `maxDeliveryAttempts` if appropriate

## Ordering Violations

**Symptoms**: Messages with same ordering key delivered out of order.

**Causes**:
1. Subscriber didn't ack within deadline → message redelivered, breaking order
2. Publisher used different ordering key for same logical stream
3. Exactly-once delivery not enabled (at-least-once allows duplicates)

**Recovery**:
1. Enable exactly-once delivery: `gcloud pubsub subscriptions update SUB --enable-exactly-once-delivery`
2. Ensure subscriber acks before deadline
3. Use consistent ordering key per logical stream
4. Consider disabling ordering if not strictly required (improves throughput)

## Snapshot Issues

**Snapshot creation failed**:
1. Check subscription exists and is not detached
2. Check snapshot name uniqueness per project
3. Check snapshot count ≤ 10 per subscription

**Seek failed**:
1. Verify snapshot exists: `gcloud pubsub snapshots describe SNAP --format=json`
2. Check snapshot not expired: `jq -r '.expireTime'` — must be in future
3. Seek re-queues unacked messages from snapshot point; already-acked messages are not replayed

## Common Issues

### Publish Fails
- Topic doesn't exist: create first
- SA lacks publisher role: grant `roles/pubsub.publisher`
- Message too large (>1 MiB): split or use Cloud Storage + publish reference
- Quota exceeded: reduce rate; request increase

### Pull Returns No Messages
- Subscription has no messages: normal if topic idle
- Messages already acked by another subscriber on same subscription
- Exactly-once delivery: messages deduplicated

### Push Delivery Fails
- Endpoint returns non-2xx: Pub/Sub retries with exponential backoff
- Endpoint TLS cert invalid: use valid cert or disable verification (not recommended)
- Push auth (OIDC) misconfigured: verify service account and audience

### Subscription Auto-Deleted
- `expirationPolicy` set with TTL and no activity
- Default: never expires; check if explicitly set
