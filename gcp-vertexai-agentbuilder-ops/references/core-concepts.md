# Core Concepts — Vertex AI Agent Builder

## What Is Vertex AI Agent Builder

Vertex AI Agent Builder (formerly Agent Builder / Dialogflow CX) is a Google Cloud service for building and deploying generative AI agents. It provides:

- **Conversational AI** — natural language understanding and generation
- **Function Calling** — register custom tools the agent can invoke
- **Vertex AI Search grounding** — ground agent responses in enterprise data
- **Multi-turn sessions** — maintain conversation context across turns
- **Tool orchestration** — chain multiple tools in a single conversation

## Architecture

```
User Input
    │
    ▼
┌─────────────────────────┐
│   Vertex AI Agent        │
│   (Dialogflow CX Agent) │
│   - Intent detection     │
│   - Response generation │
└──────────┬──────────────┘
           │
     ┌─────┴─────┐
     ▼           ▼
┌─────────┐  ┌─────────────────┐
│ Tool 1  │  │ Vertex AI Search │
│(Function │  │   (Grounding)   │
│ Calling) │  └─────────────────┘
└─────────┘
```

## Key Resources

| Resource | Description | CLI |
|---------|-------------|-----|
| **Agent** | Conversational AI agent — intent flows, responses, model config | `gcloud ai agents` |
| **Session** | Single conversation thread, preserves context | `gcloud ai agents sessions` |
| **Tool** | Function Calling definitions (OpenAPI schema or webhook) | `gcloud ai agents tools` |
| **Intent** | Mapping of user phrases to agent responses/actions | `gcloud ai agents intents` |
| **Flow** | Conversation flow graph (advanced agents) | `gcloud ai agents flows` |
| **Page** | Conversation state within a flow | `gcloud ai agents pages` |
| **Version** | Snapshot of agent at a point in time | `gcloud ai agents versions` |
| **Environment** | Deployment target (staging/prod) | `gcloud ai agents environments` |

## Agent Lifecycle

```
DRAFT → ACTIVE → (update) → ACTIVE
         │
         └───(delete)──→ DELETED
```

- **DRAFT**: Agent created but not yet deployed
- **ACTIVE**: Deployed and accepting requests
- **DELETED**: Soft-deleted; purged after retention period

## Tool Types

| Tool Type | Description | Use Case |
|-----------|-------------|----------|
| `FUNCTION_CALLING` | Custom function with parameters (OpenAPI 3.0 schema) | Database lookups, API calls |
| `VERTEX_AI_SEARCH` | Vertex AI Search grounding | RAG over enterprise documents |
| `GENERATIVE_AI` | Vertex AI generative model config | LLM parameters, system prompt |

## Tool Registration Flow

```
1. Define tool schema (OpenAPI 3.0 YAML)
2. Register: gcloud ai agents tools create
3. Test: gcloud ai agents tools validate
4. Agent invokes tool at runtime
```

## Region Support

| Location | Support |
|---------|---------|
| `us-central1` | GA |
| `us-east1` | GA |
| `europe-west1` | GA |
| `asia-northeast1` | GA |
| `global` | Session-only |

> Use `gcloud ai agents list --location=us-central1` to verify available agents.

## Quotas & Limits

| Quota | Default | Notes |
|-------|---------|-------|
| Agents per project | 500 | |
| Sessions per agent | 10,000 concurrent | |
| Tool definitions per agent | 100 | |
| API requests per minute | Varies by quota tier | |
| Conversation turns per session | 1,000 | |

> Quotas are managed via Cloud Console or the Cloud Monitoring API. No gcloud quota command exists for Agent Builder.

## Cost

| Component | Pricing Model |
|-----------|--------------|
| Agent conversation turns | $0.00005 per turn (text) |
| Vertex AI Search grounding | $0.03 per 1,000 queries (standard tier) |
| Function Calling | Billed per API call to the tool endpoint |
| Agent storage | $0.05/GB/month |
| Export/import | Data transfer charges apply |

> See [Google Cloud pricing](https://cloud.google.com/vertex-ai/pricing#agent-builder) for full details.

## SPOF Analysis

| Component | Risk | Mitigation |
|-----------|------|------------|
| Agent model (Vertex AI) | Medium | Use multiple model variants; fallback model |
| Tool endpoint | High | Health check tool endpoints; timeout + circuit breaker |
| Grounding datastore | Medium | Multi-index redundancy; periodic reindex |
| Session storage | Low | Sessions are ephemeral by default; persist if needed |

## Related Services

- **Vertex AI Studio** — prompt design and tuning
- **Vertex AI Search** — enterprise search and grounding data stores
- **Vertex AI Conversation** — contact center AI integration
- **Dialogflow CX** — original Dialogflow API (pre-Vertex AI rebranding)
