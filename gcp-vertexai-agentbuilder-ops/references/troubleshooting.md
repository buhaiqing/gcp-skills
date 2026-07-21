# Troubleshooting — Vertex AI Agent Builder

## Diagnostic Order

1. **Verify CLI access**: `gcloud ai agents list --format=json --quiet`
2. **Verify credentials**: `gcloud auth application-default print-access-token --quiet`
3. **Check project/location**: `gcloud config get-value project` and `VERTEX_AI_AGENTBUILDER_LOCATION`
4. **Describe the agent**: `gcloud ai agents describe "{{user.agent_id}}"`
5. **Check agent state**: Ensure agent is `ACTIVE` before running conversations
6. **Inspect session**: `gcloud ai agents sessions list` for stale sessions
7. **Review Cloud Logging**: Filter by `resource.type="dialogflow_agent"` for conversation logs

## Error Taxonomy (≥10 Codes)

| gRPC Code / HTTP | Error Pattern | Meaning | Agent Action | UX Feedback |
|-----------------|-------------|---------|--------------|-------------|
| `INVALID_ARGUMENT` / 400 | `displayName` validation | Display name contains invalid chars | Fix name: alphanumeric + hyphens only, max 64 chars | `[ERROR] INVALID_ARGUMENT: Invalid agent display name. Fix: Use only alphanumeric characters and hyphens, max 64 chars.` |
| `INVALID_ARGUMENT` / 400 | `tool schema` malformed | OpenAPI schema validation failed | Validate schema against OpenAPI 3.0 spec | `[ERROR] Tool schema invalid. Fix: Validate your OpenAPI 3.0 schema using `swagger-cli validate` before registering.` |
| `PERMISSION_DENIED` / 403 | Missing IAM role | SA lacks Dialogflow roles | HALT — grant `roles/dialogflow.admin` or scoped role | `[ERROR] PERMISSION_DENIED: Service account needs Dialogflow Admin role. Grant: gcloud projects add-iam-policy-binding $PROJECT --member=serviceAccount:SA --role=roles/dialogflow.admin` |
| `NOT_FOUND` / 404 | Agent does not exist | Wrong agent ID or project | List agents to confirm ID; verify project | `[ERROR] Agent not found. Verify agent ID with: gcloud ai agents list` |
| `NOT_FOUND` / 404 | Session does not exist | Session expired or wrong ID | Create a new session | `[ERROR] Session not found. Session may have expired. Create a new session: gcloud ai agents sessions create` |
| `ALREADY_EXISTS` / 409 | Duplicate agent name | Agent with this display name exists | List existing agents; reuse or pick unique name | `[ERROR] ALREADY_EXISTS: Agent with this display name already exists. List agents: gcloud ai agents list` |
| `UNAUTHENTICATED` / 401 | Expired credentials | SA key expired or invalid | Re-authenticate: `gcloud auth activate-service-account --key-file=$GOOGLE_APPLICATION_CREDENTIALS` | `[ERROR] UNAUTHENTICATED: Credentials expired or invalid. Refresh: gcloud auth activate-service-account --key-file=$GOOGLE_APPLICATION_CREDENTIALS` |
| `RESOURCE_EXHAUSTED` / 429 | API rate limit | Too many requests per minute | Wait 30s; retry with exponential backoff | `⚠️ Rate limit hit. Waiting 30s and retrying... (Attempt {n}/3)` |
| `QUOTA_EXCEEDED` / 429 | Project quota hit | Max agents/sessions reached | Delete unused resources or request quota increase | `[ERROR] QUOTA_EXCEEDED: {resource} quota limit reached. Delete unused agents/sessions or request quota increase.` |
| `FAILED_PRECONDITION` / 400 | Delete active sessions first | Cannot delete agent with active sessions | Delete all sessions: `gcloud ai agents sessions list` then `gcloud ai agents sessions delete` | `[ERROR] FAILED_PRECONDITION: Delete all sessions before deleting agent. List sessions: gcloud ai agents sessions list --agent=AGENT_ID` |
| `INTERNAL` / 500 | GCP internal error | Server-side issue | Retry with backoff; escalate with operation ID | `[ERROR] INTERNAL: GCP internal error. Retry or escalate with operation ID.`
| `DEADLINE_EXCEEDED` / 504 | Long operation timeout | Agent create/delete exceeded timeout | Retry; increase timeout if persistent | `[ERROR] DEADLINE_EXCEEDED: Operation timed out. Retry or increase timeout.` |
| `UNAVAILABLE` / 503 | Service temporarily down | Dialogflow API unavailable | Retry with exponential backoff: 5s, 10s, 20s | `⚠️ Service temporarily unavailable. Retrying in {backoff}s... (Attempt {n}/3)` |
| `ABORTED` / 409 | Concurrent modification | Another operation in progress | Wait for completion; retry | `[ERROR] ABORTED: Concurrent modification detected. Wait and retry.` |

## Tool Registration Failures

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| Tool not invoked at runtime | Tool not enabled in agent config | Update agent: `gcloud ai agents update AGENT --enabled-tools=TOOL_ID` |
| Tool returns 404 | Webhook URI incorrect | Verify endpoint URL; test with `curl` |
| Tool returns timeout | Webhook endpoint slow | Add timeout to tool definition; optimize endpoint |
| Tool schema mismatch | Parameter types don't match | Update OpenAPI schema; ensure types match API spec |
| Tool forbidden (403) | SA lacks permission to call webhook | Grant IAM to webhook service account |

## Session Failures

| Symptom | Root Cause | Fix |
|---------|-----------|-----|
| Session not found | Session expired (default 30 min inactivity) | Create new session; increase `sessionTtl` if needed |
| Context lost after N turns | Session turn limit exceeded (default 1000) | Start new session; archive old session logs |
| Grounding returns no results | Search datastore empty or mismatch | Verify datastore is indexed; check location matches |
| Intent confidence too low | Insufficient training data | Add more training phrases; use fallback intent |

## Streaming Run Issues

| Symptom | Fix |
|---------|-----|
| Streaming hangs | Add `--timeout=60s`; check network connectivity |
| Partial response truncated | Retry without streaming; use blocking `run` |
| Token rate limit in stream | Reduce concurrent streams; use batching |

## Multi-Region Issues

| Symptom | Fix |
|---------|-----|
| Agent not visible in region | List with `--location=<region>` explicitly |
| Cross-region grounding slow | Use `global` location for sessions; region-specific for storage |
| Quota varies by region | Check region-specific quotas via Cloud Console or Cloud Monitoring API |
