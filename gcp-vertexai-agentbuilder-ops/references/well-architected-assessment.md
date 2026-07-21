# Well-Architected Assessment — Vertex AI Agent Builder

## §1 Security

### IAM Roles

| Role | Use Case |
|------|---------|
| `roles/dialogflow.admin` | Full Agent Builder API — production admin |
| `roles/dialogflow.agentEditor` | Create/update/delete agents and tools (no delete of other agents) |
| `roles/dialogflow.conversationClient` | Run agents, create sessions (no agent management) |
| `roles/dialogflow.conversationViewer` | Read-only agent inspection |
| `roles/dialogflow.sessionUser` | End-user session access |

**Credentials**: Never log SA key content. Use existence check only.

**PII Handling**: Session data may contain user input (PII). Enable Data Loss Prevention (DLP) API on session logs. Do not store session transcripts in persistent storage without DLP.

**Tool Endpoint Security**: Function Calling tool webhooks must be protected:
- Use IAM-authenticated webhooks for internal services
- Validate `X-Dialogflow-Conversation-Signature` header for inbound calls
- Rate-limit tool endpoints to prevent abuse

**Audit Logging**: All agent management and conversation events are logged to Cloud Logging. Enable `ADMIN_READ` and `DATA_WRITE` data access logs for compliance.

## §2 Stability

| Strategy | Implementation |
|----------|----------------|
| Agent versioning | Export agent configs before updates: `gcloud ai agents export` |
| Session expiry | Set `sessionTtl` to auto-expire inactive sessions (default: 30 min) |
| Tool redundancy | Register fallback tools for critical functions |
| Environment promotion | Use separate agents for staging/production; promote via export/import |
| Agent monitoring | Alert on `fallback_rate > 20%` indicating intent model degradation |

**Backup Runbook**:
1. Export agent: `gcloud ai agents export AGENT_ID --gcs-bucket=gs://backup-bucket --location=us-central1`
2. Verify GCS object exists: `gsutil ls gs://backup-bucket/`
3. Store export metadata: timestamp, agent version, GCS path in Cloud Logging

**Restore Runbook**:
1. Verify GCS object: `gsutil ls gs://backup-bucket/agent-export/`
2. Import: `gcloud ai agents import --gcs-bucket=gs://backup-bucket --gcs-object=agent-export/agent.yaml`
3. Verify state: `gcloud ai agents describe RESTORED_AGENT_ID --format=json | jq '.state'`

**Disaster Recovery**: RTO < 30 min via exported YAML + GCS. RPO = last export timestamp.

## §3 Cost

| Component | Pricing | Notes |
|-----------|---------|-------|
| Conversation turns | $0.00005/turn (text) | Based on input + output tokens |
| Vertex AI Search grounding | $0.03/1K queries | Standard tier |
| Agent storage | $0.05/GB/month | Agent config + session logs |
| Tool invocation | External API cost | Billed by tool endpoint provider |

**Waste Detection**:
- Sessions created but never used → implement session TTL + cleanup
- High fallback rate → indicates missing intents → costs wasted on unmatched inputs
- Over-provisioned grounding → reduce search index scope if query volume is low

**Committed Use**: No committed use discounts for Agent Builder. Optimize via:
- Reduce unnecessary grounding queries (cache results)
- Batch tool calls where possible
- Use `global` location to avoid multi-region session overhead

## §4 Efficiency

| Pattern | Description |
|---------|-------------|
| Session pooling | Reuse sessions within a conversation thread; close on completion |
| Streaming runs | Use `--streaming` for real-time UX to avoid timeout |
| Tool batching | Register tools in batch to avoid per-tool overhead |
| Conditional grounding | Only ground queries that require factual grounding |
| Intent fallback routing | Route low-confidence intents to human handoff |

**Batch Tool Registration**:
```bash
# Register multiple tools from a YAML manifest
for tool_file in tools/*.yaml; do
  gcloud ai agents tools create \
    --agent="{{user.agent_id}}" \
    --tool-type=FUNCTION_CALLING \
    --display-name="$(basename "$tool_file" .yaml)" \
    --open-api-spec="$tool_file"
done
```

## §5 Performance

| Metric | Target | Alert Threshold |
|--------|--------|----------------|
| Conversation latency (p95) | < 5s | > 5s (Warning), > 15s (Critical) |
| Intent detection confidence | > 0.85 | < 0.70 |
| Fallback rate | < 10% | > 20% |
| Tool invocation latency | < 2s | > 5s |
| Grounding query latency | < 3s | > 10s |
| Streaming time-to-first-token | < 2s | > 5s |

**Auto-scaling**: Agent Builder itself is managed. Scale considerations:
- Session concurrency: Default 10,000/s; request increase if needed
- Tool endpoint: Scale webhook service based on invocation rate
- Grounding: Vertex AI Search auto-scales; monitor index size

**Performance Baselines**: Run load test with 100 concurrent sessions, measure p95 latency and error rate before production deployment.
