# API & SDK Usage — Vertex AI Agent Builder

## REST API

- **Agent Builder API**: `https://dialogflow.googleapis.com/v3/`
- **Base URL**: `https://dialogflow.googleapis.com/v3/projects/{project}/locations/{location}/agents`
- **API discovery**: `https://dialogflow.googleapis.com/$discovery/rest?version=v3`

## SDK Packages

| Language | Package | Install |
|----------|---------|---------|
| Python | `google-cloud-dialogflow` | `pip install google-cloud-dialogflow` |
| Go | `cloud.google.com/go/dialogflow/cx/apiv3` (client) + `google.golang.org/genproto/googleapis/cloud/dialogflow/cx/v3` (proto) | `go get cloud.google.com/go/dialogflow/cx/apiv3` |
| Node.js | `@google-cloud/dialogflow` | `npm install @google-cloud/dialogflow` |

> Find all packages: https://cloud.google.com/dialogflow/docs/reference/libraries

## Operations Map

| Goal | REST Method & Path | gcloud Command | Go SDK Method | Python SDK Method |
|------|--------------------|----------------|---------------|-------------------|
| Create agent | `POST /v3/{parent}/agents` | `gcloud ai agents create` | `cxpb.AgentsClient.CreateAgent` | `AgentsClient.create_agent` |
| List agents | `GET /v3/{parent}/agents` | `gcloud ai agents list` | `cxpb.AgentsClient.ListAgents` | `AgentsClient.list_agents` |
| Get agent | `GET /v3/{agent}` | `gcloud ai agents describe` | `cxpb.AgentsClient.GetAgent` | `AgentsClient.get_agent` |
| Update agent | `PATCH /v3/{agent}` | `gcloud ai agents update` | `cxpb.AgentsClient.UpdateAgent` | `AgentsClient.update_agent` |
| Delete agent | `DELETE /v3/{agent}` | `gcloud ai agents delete` | `cxpb.AgentsClient.DeleteAgent` | `AgentsClient.delete_agent` |
| Create session | `POST /v3/{parent}/sessions` | `gcloud ai agents sessions create` | `cxpb.SessionsClient.CreateSession` | `SessionsClient.create_session` |
| Detect intent | `POST /v3/{session}:detectIntent` | `gcloud ai agents detect-intent` | `cxpb.SessionsClient.DetectIntent` | `SessionsClient.detect_intent` |
| Run agent | `POST /v3/{session}:run` | `gcloud ai agents run` | `cxpb.SessionsClient.Run` | `SessionsClient.run` |
| Create tool | `POST /v3/{parent}/tools` | `gcloud ai agents tools create` | `cxpb.ToolsClient.CreateTool` | `ToolsClient.create_tool` |
| List tools | `GET /v3/{parent}/tools` | `gcloud ai agents tools list` | `cxpb.ToolsClient.ListTools` | `ToolsClient.list_tools` |

## Common JSON Paths

```json
// Agent
$.name                    // Full resource name: projects/.../locations/.../agents/{id}
$.displayName             // Human-readable name
$.state                   // ACTIVE | DRAFT | DELETED
$.description             // Agent description
$.defaultLanguageCode     // Default language (e.g., "en")
$.timeZone                // Agent timezone
$.startFlow              // Entry point flow reference
$.createTime             // RFC 3339 creation timestamp
$.updateTime             // RFC 3339 update timestamp

// Session
$.name                    // Full resource name
$.lastMatchedIntent       // Most recent matched intent
$.lastUtterance          // Last user message
$.languageCode            // Session language

// Intent Detection
$.responses[0].text.text[0]           // Agent response text
$.responses[0].intentDetectionResult    // {intent: {...}, confidence: 0.95}
$.responses[0].parameterValues         // Extracted parameters
$.responses[0].currentPage              // Current page in flow
```

## Required Fields

### Create Agent

| Field | Required | Type | Notes |
|-------|----------|------|-------|
| `parent` | Yes | string | `projects/{project}/locations/{location}` |
| `agent.displayName` | Yes | string | Max 64 chars, alphanumeric + hyphens |
| `agent.defaultLanguageCode` | No | string | Default `"en"` |

### Detect Intent / Run Agent

| Field | Required | Type | Notes |
|-------|----------|------|-------|
| `session` | Yes | string | Full session resource name |
| `queryInput.text.text` | Yes | string | User message |
| `queryParams.timeZone` | No | string | IANA timezone |

## Pagination

- List operations use `pageSize` (default 100) and `nextPageToken`
- Sessions do not paginate; use `pageSize` to limit response
- `gcloud ai agents list --page-size=50` handles pagination automatically

## Async Operations

- Agent **create** and **delete** are long-running operations (LROs)
- Poll via `gcloud ai agents describe` checking `$.state`
- Timeout: 300s; retry on `DEADLINE_EXCEEDED`

## Idempotency

- **Create agent**: Not idempotent. Use `ALREADY_EXISTS` check before creating.
- **Update agent**: Idempotent for non-destructive fields.
- **Delete agent**: Idempotent — subsequent delete of non-existent agent returns `NOT_FOUND`, not error.
- **Create session**: Not idempotent — each call creates a new session. Capture `session.name` as `{{output.session_id}}`.
- **Detect intent**: Idempotent — same input always returns same intent (modulo model randomness in response).

## CLI Coverage Gap

| Operation | gcloud Support | Notes |
|-----------|--------------|-------|
| Create agent | ✅ Yes | Full support |
| List agents | ✅ Yes | Full support |
| Describe agent | ✅ Yes | Full support |
| Update agent | ✅ Yes | Partial — some advanced fields need SDK |
| Delete agent | ✅ Yes | Full support |
| Create session | ✅ Yes | Full support |
| Detect intent | ✅ Yes | Full support |
| Run agent | ✅ Yes | Supports `--streaming` |
| Create tool | ✅ Yes | FUNCTION_CALLING only; Vertex Search needs SDK |
| List tools | ✅ Yes | Full support |
| Export agent | ⚠️ Partial | `gcloud ai agents export` — requires GCS bucket |
| Import agent | ⚠️ Partial | `gcloud ai agents import` — requires GCS object |
| Manage flows/pages | ⚠️ Partial | Basic gcloud; complex flows need SDK |
| Agent versions | ⚠️ Partial | `gcloud ai agents versions` — basic CRUD only |
