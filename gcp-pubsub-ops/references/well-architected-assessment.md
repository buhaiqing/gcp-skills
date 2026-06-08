# Well-Architected Assessment — Cloud Pub/Sub

## §1 Security

| IAM Role | Use Case |
|----------|----------|
| roles/pubsub.admin | Full Pub/Sub API — production |
| roles/pubsub.editor | Create/manage topics & subscriptions |
| roles/pubsub.publisher | Producer applications (publish only) |
| roles/pubsub.subscriber | Consumer applications (pull only) |
| roles/pubsub.viewer | Read-only access for auditing |

**Credentials**: Never log SA key content. Only check: `test -f "$GOOGLE_APPLICATION_CREDENTIALS"`
**Push Authentication**: Use OIDC tokens for push endpoints; never expose unauthenticated push URLs.
**Encryption**: Use CMEK for sensitive messages; default encryption at rest always active.
**VPC Service Controls**: Restrict Pub/Sub access to approved VPCs; prevent data exfiltration.
**Topic IAM**: Grant `roles/pubsub.publisher` to producers only; `roles/pubsub.subscriber` to consumers.
**Subscription IAM**: Scope pull permissions per subscription, not per topic.

## §2 Stability

| Strategy | Implementation |
|----------|---------------|
| Dead-letter topics | Route failed messages after max delivery attempts for analysis |
| Retry policies | Exponential backoff with min/max bounds |
| Snapshot/seek | Point-in-time replay for recovery and testing |
| Message retention | Up to 7 days; configure per subscription |
| Exactly-once delivery | Beta; deduplicates messages for critical workloads |
| Multiple subscriptions | Fan-out to multiple consumers from same topic |

DR Runbook:
1. Identify affected subscriptions: `gcloud pubsub subscriptions list --filter="topic:TOPIC"`
2. Check snapshot availability: `gcloud pubsub snapshots list --filter="subscription:SUB"`
3. If snapshot exists: seek to snapshot and replay
4. If no snapshot: messages may be lost; republish from source
5. Rebuild consumer from last checkpoint
6. Monitor backlog drain rate

## §3 Cost

| Factor | Impact | Optimization |
|--------|--------|--------------|
| Message volume | Per-operation pricing | Batch publish; compress payloads |
| Egress | Cross-region delivery | Use same region for publisher and subscriber |
| DLQ storage | Messages retained in DLQ | Drain DLQ regularly; set retention policy |
| Retention duration | Longer = more storage | Set appropriate retention (default 7d) |
| Push vs Pull | Push = HTTP costs | Use pull for high-throughput batch processing |

**Cost Optimization:**
- Monitor message volume with `topic/send_request_count`
- Use batch publish for high-throughput producers
- Set appropriate message retention (don't exceed needed duration)
- Drain DLQ subscriptions to avoid accumulation costs
- Use labels for cost attribution (`env`, `app`, `team`)

## §4 Efficiency

- **Batch operations**: Use SDK batch publish for high-throughput producers
- **Streaming pull**: Prefer over polling pull for low-latency consumers
- **Ordering keys**: Use only when message order matters (adds latency)
- **Exactly-once delivery**: Enable for critical workloads; adds deduplication overhead
- **Ack deadlines**: Set to match actual processing time; avoid unnecessary redelivery
- **Push vs Pull**: Push for real-time, pull for controlled throughput
- **Labels**: Cost tracking and resource organization (`env`, `app`, `team`, `project`)

## §5 Performance

| Metric | Target | Notes |
|--------|--------|-------|
| Publish throughput | 10,000 msg/sec per topic (default) | Request increase for higher |
| Pull throughput | Limited by subscriber count | Scale horizontally |
| Message latency | < 100ms (same region) | Cross-region adds latency |
| Push delivery | < 1 second | Depends on endpoint |

**Performance optimization:**
- Co-locate publishers and subscribers in same region
- Use streaming pull for continuous low-latency consumption
- Enable message ordering only when required
- Batch publish for high-throughput scenarios
- Monitor `num_undelivered_messages` for backlog detection
- Scale subscriber instances based on backlog size
- Use `--max-messages` to control pull batch size
