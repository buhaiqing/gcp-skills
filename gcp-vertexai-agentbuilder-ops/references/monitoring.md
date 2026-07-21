# Monitoring — Vertex AI Agent Builder

## Key Metrics

| Metric | Cloud Monitoring Namespace | Description |
|--------|--------------------------|-------------|
| Conversation turns | `agentbuilder.googleapis.com/conversation/turn_count` | Number of turns per session |
| Conversation latency | `agentbuilder.googleapis.com/conversation/latency` | Time from user input to agent response |
| Intent detection confidence | `agentbuilder.googleapis.com/conversation/intent_confidence` | Per-intent confidence score |
| Tool invocation count | `agentbuilder.googleapis.com/tool/invocation_count` | Number of tool calls |
| Tool invocation latency | `agentbuilder.googleapis.com/tool/invocation_latency` | Tool execution time |
| Grounding query count | `agentbuilder.googleapis.com/grounding/query_count` | Vertex AI Search grounding queries |
| Grounding latency | `agentbuilder.googleapis.com/grounding/query_latency` | Grounding response time |
| Error rate | `agentbuilder.googleapis.com/agent/error_rate` | Conversation errors |
| Fallback rate | `agentbuilder.googleapis.com/conversation/fallback_rate` | Unmatched intents |

## Cloud Monitoring Setup

```bash
# List existing alert policies
gcloud alpha monitoring policies list --project="$PROJECT"

# Create alert for high latency
gcloud alpha monitoring policies create \
  --notification-channels="CHANNEL_ID" \
  --display-name="Agent High Latency Alert" \
  --condition-display-name="Conversation latency > 5s" \
  --condition-filter='resource.type="agentbuilder.googleapis.com/Agent"' \
  --condition-threshold-value=5 \
  --condition-threshold-duration=300s
```

## Dashboard Recommendations

| Dashboard | Metrics to Include |
|-----------|-------------------|
| Agent Overview | Turn count, latency p50/p95/p99, error rate, fallback rate |
| Tool Performance | Invocation count, latency, error rate per tool |
| Grounding Quality | Query count, latency, citation rate, no-result rate |
| Session Health | Active sessions, session creation rate, session deletion rate |

## Alert Policy Thresholds

| Alert | Threshold | Duration | Severity |
|-------|-----------|---------|---------|
| High latency | p95 > 5s | 5 min | Warning |
| High latency | p95 > 15s | 2 min | Critical |
| High error rate | > 5% | 5 min | Warning |
| High fallback rate | > 20% | 10 min | Warning |
| Tool timeout rate | > 10% | 5 min | Warning |
| Quota approaching | > 80% of limit | 1 hour | Warning |

## Cost Monitoring

```bash
# List agent billing data (via Cloud Billing API)
# Filter by Dialogflow SKU: F001, F002, F003 (conversation turns, grounding)
# Use Cloud Billing API: https://cloud.google.com/billing/docs/reference/rest

# Key cost signals:
# - High turn count = high conversation cost
# - High grounding query rate = high search cost
# - Tool invocations billed per tool endpoint call (external cost)
```

## Logging

```bash
# View agent conversation logs
gcloud logging read \
  'resource.type="dialogflow_agent" AND severity>=WARNING' \
  --project="$PROJECT" \
  --format="table(timestamp,severity,jsonPayload.conversationId,textPayload)" \
  --order=desc \
  --limit=50

# Filter by agent
gcloud logging read \
  'resource.type="dialogflow_agent" AND resource.labels.agent_id="{{user.agent_id}}"' \
  --project="$PROJECT" \
  --format="json" \
  --limit=100
```

## Session and Intent Analytics

```bash
# Export conversation analytics to BigQuery
# Use Dialogflow CX Analytics API:
# POST https://dialogflow.googleapis.com/v3/{parent=projects/*/locations/*/agents/*}/participants:exportAnalytics

# Key analytics:
# - Top intents by frequency
# - Average conversation length (turns)
# - Unmatched intent rate
# - Tool usage frequency
# - Session duration
```
