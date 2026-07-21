---
name: gcp-vertexai-agentbuilder-ops
description: >-
  Use when the user needs to build, deploy, configure, query, or diagnose
  Google Cloud Vertex AI Agent Builder agents — including agent lifecycle
  (create/update/delete/list), tool registration (Function Calling, Data
  Connectors, Vertex AI Search), session and conversation management, intent
  detection, and agent performance monitoring. User mentions Vertex AI Agent
  Builder, Vertex Agent Builder, Dialogflow CX, or describes building
  generative AI agents on Google Cloud. Not for general Vertex AI tuning,
  model deployment, or grounding configuration which have their own ops skills.
license: MIT
compatibility: >-
  Official Google Cloud CLI (`gcloud`), Python 3.8+ (for Python SDK fallback),
  Go 1.21+ runtime (for JIT SDK fallback), valid service account credentials,
  network access to Google Cloud endpoints.
metadata:
  author: gcp-skills
  version: "1.0.0"
  last_updated: "2025-01-20"
  runtime: Harness AI Agent, Claude Code, Cursor, or compatible Agent runtimes
  go_version_minimum: "1.21"
  go_version_jit: "1.24+"
  api_profile: "https://cloud.google.com/dialogflow/cx/docs/reference/rest"
  cli_applicability: "cli-first"
  cli_support_evidence: >-
    `gcloud ai agents` (create/list/describe/delete/update), `gcloud ai
    agents sessions` (create/list/reset/delete), `gcloud ai agents
    run` for conversation runs; confirmed via Google Cloud SDK gcloud reference.
  environment:
    - GOOGLE_APPLICATION_CREDENTIALS
    - CLOUDSDK_CORE_PROJECT
    - CLOUDSDK_AUTH_ACCESS_TOKEN
    - VERTEX_AI_AGENTBUILDER_LOCATION
---

> This skill follows the [Agent Skill OpenSpec](https://agentskills.io/specification).

# Google Cloud Vertex AI Agent Builder Operations Skill

## Overview

Vertex AI Agent Builder (formerly Agent Builder / Dialogflow CX) lets you build
and deploy generative AI agents that use Google Search grounding, Vertex AI
Search, Function Calling, and data connectors. This skill is an **operational
runbook** for agents: explicit scope, credential rules, pre-flight checks,
CLI-first execution, SDK/API fallback, response validation, and failure
recovery.

> **UX Compliance:** This skill follows [references/user-experience-spec.md](references/user-experience-spec.md).
> All operations include onboarding guidance, minimal prompts, smart defaults,
> clear feedback, and user-friendly error handling.

### CLI applicability: `cli-first`

Official `gcloud` fully supports this product via `gcloud ai agents`. CLI is the
**primary** execution path. JIT Go/Python SDK is the **fallback** for edge-case
operations (e.g., bulk tool registration, custom webhook callbacks). Omit
`references/gcloud-usage.md` content gaps — document coverage gaps in the CLI
coverage table.

## Five Core Standards (Quality Gates)

| # | Standard | How This Skill Fulfills It |
|---|----------|---------------------------|
| 1 | **Clear Boundaries** | SHOULD/SHOULD NOT Use with precise triggers and delegation rules |
| 2 | **Structured I/O** | Placeholder conventions (`{{env.*}}`, `{{user.*}}`, `{{output.*}}`) with type and source |
| 3 | **Explicit Actionable Steps** | Every operation: Pre-flight → Execute → Validate → Recover, numbered imperative steps |
| 4 | **Complete Failure Strategies** | ≥10 product-specific error codes; HALT vs retry per error type |
| 5 | **Absolute Single Responsibility** | One product, one primary resource model; delegation to `gcp-vertexai-ops` for tuning |

### Google Cloud Architecture Framework Integration

| Pillar | Skill Integration | Reference |
|--------|-------------------|-----------|
| **Security** | IAM roles for Agent Builder, credential masking, no PII in session data | `references/well-architected-assessment.md` §2.1 |
| **Stability** | Agent versioning, session expiry, backup/export of agent configs | `references/well-architected-assessment.md` §2.2 |
| **Cost** | Token-based pricing, session duration billing, grounding API costs | `references/well-architected-assessment.md` §2.3 |
| **Efficiency** | Batch tool registration, session pooling, streaming runs | `references/well-architected-assessment.md` §2.4 |
| **Performance** | Latency targets, grounding quality, streaming vs blocking runs | `references/well-architected-assessment.md` §2.5 |

See [references/well-architected-assessment.md](references/well-architected-assessment.md).

## Trigger & Scope (Agent-Readable)

### SHOULD Use This Skill When

- User mentions **Vertex AI Agent Builder**, **Vertex Agent Builder**, **Dialogflow CX**, **Agent Builder**, or **conversational AI agent**
- Task involves agent CRUD (create, describe, list, update, delete), tool registration, session management, conversation runs, or intent detection
- Task keywords: `agent`, `tool`, `function calling`, `grounding`, `session`, `intent`, `conversational AI`, `chatbot`, `RAG`, `Vertex Search`
- User asks to build, deploy, configure, query, or diagnose generative AI agents on Google Cloud **via gcloud, SDK, API, or automation**

### SHOULD NOT Use This Skill When

- Task is about **Vertex AI model tuning** (tuning Vertex AI foundation models) → delegate to: `gcp-vertexai-ops` (when present)
- Task is about **Vertex AI Agent Evaluation** or **Prompt Management** → delegate to: `gcp-vertexai-ops`
- Task is about **general grounding configuration** for Vertex AI Search → delegate to: `gcp-vertexai-search-ops` (when present)
- Task is **billing** or **cost management** → delegate to: `gcp-billing-ops`
- Task is **IAM** or **service account** setup → delegate to: `gcp-iam-ops`
- User insists on **console-only** flows → state limitation; do not invent undocumented gcloud steps

### Delegation Rules

| Capability | Delegation Target | Note |
|-----------|-----------------|------|
| Vertex AI model tuning / foundation model ops | `gcp-vertexai-ops` | Not covered by this skill |
| Vertex AI Search / grounding index | `gcp-vertexai-search-ops` | For search datastore configuration |
| Cloud Storage for agent assets | `gcp-gcs-ops` | For large agent config backups |
| IAM for agent service accounts | `gcp-iam-ops` | For permission model |
| Cloud Logging for agent conversation logs | `gcp-logging-ops` | For session audit trails |

## Variables

| Placeholder | Meaning | Agent Action |
|-------------|---------|--------------|
| `{{env.GOOGLE_APPLICATION_CREDENTIALS}}` | Path to SA key JSON | NEVER ask; fail if unset |
| `{{env.CLOUDSDK_CORE_PROJECT}}` | GCP project ID | NEVER ask; fail if unset |
| `{{env.VERTEX_AI_AGENTBUILDER_LOCATION}}` | Agent location (e.g. `us-central1`) | Ask once; default `us-central1` |
| `{{user.agent_id}}` | User-supplied agent resource ID | Ask once; reuse |
| `{{user.agent_display_name}}` | Human-readable agent name | Ask once |
| `{{user.agent_description}}` | Agent description | Ask once (optional) |
| `{{user.session_id}}` | Conversation session ID | From Create Session output |
| `{{user.tool_name}}` | Function Calling tool name | Ask once |
| `{{user.tool_uri}}` | Function Calling webhook URI | Ask once |
| `{{output.agent_resource_name}}` | Full agent resource name | Parse from create/describe response: `projects/…/locations/…/agents/…` |
| `{{output.session_id}}` | Session ID | Parse from create-session response |
| `{{output.run_id}}` | Conversation run ID | Parse from run response |

> **Security Warning (Credential Masking — MANDATORY):** **NEVER** log, print, or expose service account key content, `GOOGLE_APPLICATION_CREDENTIALS` path content, or any credential field value in console output, debug messages, error messages, or logs. Always check existence only.

## API and Response Conventions

- **REST API base**: `https://dialogflow.googleapis.com/v3/` (Agent Builder API) + `https://aiplatform.googleapis.com/v1/` (Vertex AI extensions)
- **gcloud primary path**: `gcloud ai agents` and `gcloud ai agents sessions`
- **Errors**: Map to gRPC status codes; Dialogflow API uses its own error payloads
- **Long-running ops**: Agent creation/deletion uses Operations API (poll via `gcloud ai agents describe` or `describe-operation`)
- **Agent resource name format**: `projects/{project}/locations/{location}/agents/{agent_id}`
- **Session resource name format**: `projects/{project}/locations/{location}/agents/{agent_id}/sessions/{session_id}`
- **Streaming**: `gcloud ai agents run` supports `--streaming` flag for real-time responses

### Common JSON Paths

```json
// Create agent response
{ "name": "projects/.../locations/.../agents/{agent_id}", "displayName": "...", "createTime": "..." }

// Describe agent response
{ "name": "...", "displayName": "...", "description": "...", "state": "ACTIVE", "createTime": "...", "updateTime": "..." }

// Create session response
{ "name": "projects/.../locations/.../agents/.../sessions/{session_id}", "lastMatchedIntent": "..." }

// Run/conversation response
{ "session": "...", "responses": [{ "text": { "text": ["..."] } }], "endUserInputParameters": [...] }
```

### Expected State Transitions

| Operation | Initial State | Target State | Poll Interval | Max Wait |
|-----------|--------------|--------------|--------------|----------|
| Create agent | — | `ACTIVE` | via Operations API | 300s |
| Delete agent | `ACTIVE` | `DELETED` / not found | via Operations API | 300s |
| Deploy agent | `DRAFT` | `ACTIVE` | 10s | 120s |

## Quick Start

### Prerequisites
- [ ] `gcloud` CLI installed and authenticated
- [ ] Service account with `roles/dialogflow.admin` or scoped custom role
- [ ] Project set: `gcloud config set project <project-id>`

### Verify Setup
```bash
gcloud ai agents list --format="json" --quiet && echo "✅ Agent Builder API accessible"
```

### Your First Command
```bash
# List existing agents
gcloud ai agents list \
  --location="{{env.VERTEX_AI_AGENTBUILDER_LOCATION:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

### Next Steps
- [Core Concepts](references/core-concepts.md) — Agent architecture, tools, grounding
- [Common Operations](#execution-flows) — Create, manage, and delete agents
- [Troubleshooting](references/troubleshooting.md) — Fix common issues

## Capabilities at a Glance

| Operation | Description | Complexity | Risk Level |
|-----------|-------------|------------|------------|
| Create Agent | Create a new conversational AI agent | Medium | Low |
| Describe Agent | View agent configuration and state | Low | None |
| List Agents | List all agents in project/location | Low | None |
| Update Agent | Modify agent settings, description, model config | Medium | Medium |
| Delete Agent | Permanently remove an agent | Low | **High** — irreversible |
| Create Tool | Register Function Calling tool or Vertex Search | Medium | Medium |
| Create Session | Open a conversation session | Low | None |
| Run Agent | Send user input, receive agent response | Low | None |
| Delete Session | End and clean up a session | Low | Medium |
| Detect Intent | Programmatic intent detection | Low | None |

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-01-20 | Initial skill: agent CRUD, session management, conversation runs, tool registration |

---

## Execution Flows (Agent-Readable)

Every operation: **Pre-flight → Execute (CLI primary, SDK fallback) → Validate → Recover**.

### Operation: Create Agent

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| CLI / deps | `gcloud --version` | Exit code 0 | Document gcloud install |
| Credentials | `gcloud auth application-default print-access-token` | Non-empty token | HALT; user authenticates |
| Project | `gcloud config get-value project` | Set and valid | HALT; user sets project |
| Location | `VERTEX_AI_AGENTBUILDER_LOCATION` env or `--location` flag | Valid GCP region | Default to `us-central1` |
| Quota | Agent Builder API quota check | Sufficient quota | HALT; user requests increase |

#### Execution — CLI (`gcloud`) (Primary Path)

```bash
# Create a new Vertex AI Agent Builder agent
gcloud ai agents create \
  --display-name="{{user.agent_display_name}}" \
  --description="{{user.agent_description:-Agent created via gcloud}" \
  --location="{{env.VERTEX_AI_AGENTBUILDER_LOCATION:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"

# Parse agent resource name from response
AGENT_NAME=$(gcloud ai agents create \
  --display-name="{{user.agent_display_name}}" \
  --location="{{env.VERTEX_AI_AGENTBUILDER_LOCATION:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="value(name)" --quiet)
echo "Agent created: $AGENT_NAME"
```

#### Execution — Python SDK (Primary Fallback)

```python
# create_agent.py
# REST: POST https://dialogflow.googleapis.com/v3/projects/{project}/locations/{location}/agents
import os
from google.cloud import dialogflow_v3 as dialogflow

project = os.environ["CLOUDSDK_CORE_PROJECT"]
location = os.environ.get("VERTEX_AI_AGENTBUILDER_LOCATION", "us-central1")
agent_display_name = os.environ.get("AGENT_DISPLAY_NAME", "my-agent")

client = dialogflow.AgentsClient()
parent = f"projects/{project}/locations/{location}"
agent = dialogflow.Agent(display_name=agent_display_name)

response = client.create_agent(parent=parent, agent=agent)
print(f"Created: {response.name}")
```

Execute:
```bash
pip install --quiet google-cloud-dialogflow
python3 create_agent.py
```

#### Execution — JIT Go SDK (Secondary Fallback)

```go
// create_agent.go
// REST: POST /v3/projects/{project}/locations/{location}/agents
package main

import (
    "context"
    "fmt"
    "log"
    "os"

    dialogflowcx "cloud.google.com/go/dialogflow/cx/apiv3"
    cxpb "google.golang.org/genproto/googleapis/cloud/dialogflow/cx/v3"
    "google.golang.org/api/option"
)

func main() {
    ctx := context.Background()
    project := os.Getenv("CLOUDSDK_CORE_PROJECT")
    location := os.Getenv("VERTEX_AI_AGENTBUILDER_LOCATION")
    if location == "" {
        location = "us-central1"
    }

    client, err := dialogflowcx.NewAgentsClient(ctx,
        option.WithCredentialsFile(os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")))
    if err != nil {
        log.Fatalf("Failed to create client: %v", err)
    }
    defer client.Close()

    parent := fmt.Sprintf("projects/%s/locations/%s", project, location)
    agent := &cxpb.Agent{
        DisplayName: os.Getenv("AGENT_DISPLAY_NAME"),
    }

    resp, err := client.CreateAgent(ctx, &cxpb.CreateAgentRequest{
        Parent: parent,
        Agent:  agent,
    })
    if err != nil {
        log.Fatalf("Failed to create agent: %v", err)
    }
    fmt.Printf("Created: %s\n", resp.Name)
}
```

Execute:
```bash
mkdir -p /tmp/gcp-sdk-workspace && cd /tmp/gcp-sdk-workspace
go mod init sdk-script
go get cloud.google.com/go/dialogflow/cx/apiv3
go get google.golang.org/genproto/googleapis/cloud/dialogflow/cx/v3
go get google.golang.org/api/option
go run create_agent.go
```

#### Post-execution Validation

1. Poll via `gcloud ai agents describe` until `state=ACTIVE` or timeout:

```bash
AGENT_ID=$(echo "{{output.agent_resource_name}}" | grep -oP 'agents/\K[^/]+')
gcloud ai agents describe \
  --agent="$AGENT_ID" \
  --location="{{env.VERTEX_AI_AGENTBUILDER_LOCATION:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq -r '.state'
```

2. Confirm `state` is `ACTIVE` — agent is ready.
3. Report `{{output.agent_resource_name}}` and `displayName` to the user.
4. On terminal failure → **Failure Recovery**.

#### Failure Recovery

| Error pattern | Agent Action | UX Feedback |
|--------------|--------------|-------------|
| `INVALID_ARGUMENT` / 400 | Fix display name (alphanumeric + hyphens, ≤64 chars); retry once | `[ERROR] INVALID_ARGUMENT: Invalid display name. Fix: Use alphanumeric characters and hyphens only.` |
| `PERMISSION_DENIED` / 403 | HALT — grant `roles/dialogflow.admin` to SA | `[ERROR] PERMISSION_DENIED: Service account lacks Dialogflow Admin role.` |
| `NOT_FOUND` / 404 | Verify project and location are correct | `[ERROR] NOT_FOUND: Project or location not found.` |
| `QUOTA_EXCEEDED` / 429 | HALT — request quota increase in Cloud Console | `[ERROR] QUOTA_EXCEEDED: Agent quota limit reached. Request increase in Cloud Console.` |
| `ALREADY_EXISTS` / 409 | List existing agents; ask user to reuse or pick new name | `[ERROR] ALREADY_EXISTS: An agent with this name exists. List agents and reuse or pick a new name.` |
| `UNAVAILABLE` / 503 | Back off 5s → 10s → 20s (3 retries); then HALT | `⚠️ Service temporarily unavailable. Retrying in {backoff}s... (Attempt {n}/3)` |
| `INTERNAL` / 500 | Retry 3× with 2s/4s/8s backoff; then HALT with operation ID | `[ERROR] INTERNAL: GCP internal error. Retry or escalate with operation ID.` |
| `DEADLINE_EXCEEDED` / 504 | Retry once with longer timeout | `[ERROR] DEADLINE_EXCEEDED: Operation timed out. Retry or increase timeout.` |
| `UNAUTHENTICATED` / 401 | Re-authenticate SA; verify credentials file | `[ERROR] UNAUTHENTICATED: Credentials invalid or expired. Run: gcloud auth activate-service-account --key-file=$GOOGLE_APPLICATION_CREDENTIALS` |
| `RESOURCE_EXHAUSTED` / 429 | Wait 30s; retry once; check API rate limits | `[ERROR] RESOURCE_EXHAUSTED: API rate limit hit. Waiting 30s and retrying.` |

---

### Operation: List Agents### Operation: List Agents

#### Execution — CLI

```bash
gcloud ai agents list \
  --location="{{env.VERTEX_AI_AGENTBUILDER_LOCATION:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="table(name,displayName,state,createTime,updateTime)"

# JSON output for machine parsing
gcloud ai agents list \
  --location="{{env.VERTEX_AI_AGENTBUILDER_LOCATION:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '[.agents[] | {name, displayName, state}]'
```

#### Post-execution Validation

1. Confirm non-empty response array.
2. Extract `{{output.agent_resource_name}}` for downstream operations.
3. On empty list → inform user no agents exist; suggest `Create Agent` flow.

---

### Operation: Describe Agent

#### Execution — CLI

```bash
gcloud ai agents describe \
  --agent="{{user.agent_id}}" \
  --location="{{env.VERTEX_AI_AGENTBUILDER_LOCATION:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"

# Extract key fields
gcloud ai agents describe \
  --agent="{{user.agent_id}}" \
  --location="{{env.VERTEX_AI_AGENTBUILDER_LOCATION:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json" | jq '{name, displayName, state, description, model, createTime, updateTime}'
```

#### Present to User

| Field | Source | Notes |
|-------|--------|-------|
| Name | `$.name` | Full resource name |
| Display Name | `$.displayName` | Human-readable name |
| State | `$.state` | `ACTIVE`, `DRAFT`, `DELETED` |
| Description | `$.description` | Agent purpose |
| Model | `$.model` | LLM model backing the agent |
| Created | `$.createTime` | RFC 3339 timestamp |
| Updated | `$.updateTime` | RFC 3339 timestamp |

---

### Operation: Update Agent

#### Pre-flight

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Agent exists | Describe agent | State `ACTIVE` or `DRAFT` | HALT — cannot update deleted agent |

#### Execution — CLI

```bash
# Update display name and description
gcloud ai agents update "{{user.agent_id}}" \
  --display-name="{{user.new_display_name}}" \
  --description="{{user.new_description}}" \
  --location="{{env.VERTEX_AI_AGENTBUILDER_LOCATION:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

#### Post-execution Validation

Poll `describe` until `updateTime` advances or `state` reflects changes. Report updated fields.

#### Failure Recovery

| Error pattern | Agent Action | UX Feedback |
|--------------|--------------|-------------|
| `NOT_FOUND` | HALT — agent may have been deleted | `[ERROR] Agent not found. Verify agent ID.` |
| `INVALID_ARGUMENT` | Fix field value; retry once | `[ERROR] Invalid field value. Check agent API documentation.` |
| `PERMISSION_DENIED` | HALT — lacks write permission | `[ERROR] PERMISSION_DENIED: Need Dialogflow Admin or Editor role.` |

---

### Operation: Delete Agent

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit confirmation: irreversible delete of `{{user.agent_id}}`.
- **MUST NOT** proceed without clear user assent.
- **SHOULD** warn: all sessions, tools, and conversation history for this agent will be deleted.

#### Execution — CLI

```bash
# Confirm deletion
gcloud ai agents delete "{{user.agent_id}}" \
  --location="{{env.VERTEX_AI_AGENTBUILDER_LOCATION:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

#### Post-execution Validation

1. Poll `describe` until `NOT_FOUND` (agent deleted) or `state=DELETED`.
2. Verify no sessions remain: `gcloud ai agents sessions list`.
3. On failure → **Failure Recovery**.

#### Failure Recovery

| Error pattern | Agent Action | UX Feedback |
|--------------|--------------|-------------|
| `NOT_FOUND` | Confirm already deleted; report success | `[INFO] Agent already deleted or not found.` |
| `PERMISSION_DENIED` | HALT | `[ERROR] PERMISSION_DENIED: Need Dialogflow Admin role to delete agents.` |
| `FAILED_PRECONDITION` | HALT — agent may have active sessions | `[ERROR] FAILED_PRECONDITION: Delete all sessions first. List sessions: gcloud ai agents sessions list` |

---

### Operation: Register Tool (Function Calling)

#### Pre-flight

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Agent exists | Describe agent | State `ACTIVE` or `DRAFT` | HALT — create agent first |
| Tool definition | Validate tool schema JSON/YAML | Valid OpenAPI 3.0 or custom schema | HALT — fix tool schema |

#### Execution — CLI

```bash
# Register a Function Calling tool
gcloud ai agents tools create \
  --agent="{{user.agent_id}}" \
  --tool-type="FUNCTION_CALLING" \
  --display-name="{{user.tool_name}}" \
  --description="Tool for {{user.tool_name}}" \
  --location="{{env.VERTEX_AI_AGENTBUILDER_LOCATION:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

#### Post-execution Validation

1. Describe agent to confirm tool appears in `tools` list.
2. Report `toolId` and tool name to user.

#### Failure Recovery

| Error pattern | Agent Action | UX Feedback |
|--------------|--------------|-------------|
| `INVALID_ARGUMENT` | Fix tool schema; retry | `[ERROR] Invalid tool schema. Verify OpenAPI 3.0 format.` |
| `NOT_FOUND` | Verify agent ID | `[ERROR] Agent not found. Check agent ID.` |

---

### Operation: Create Session

#### Execution — CLI

```bash
# Create a conversation session
gcloud ai agents sessions create \
  --agent="{{user.agent_id}}" \
  --location="{{env.VERTEX_AI_AGENTBUILDER_LOCATION:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"

# Capture session ID for subsequent runs
SESSION_ID=$(gcloud ai agents sessions create \
  --agent="{{user.agent_id}}" \
  --location="{{env.VERTEX_AI_AGENTBUILDER_LOCATION:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="value(name)" --quiet)
echo "Session: $SESSION_ID"
```

#### Post-execution Validation

Confirm `session.name` is returned. Extract `{{output.session_id}}` for run operations.

---

### Operation: Run Agent (Conversation)

#### Execution — CLI (Blocking)

```bash
# Send a message and receive agent response (blocking)
gcloud ai agents run "{{user.agent_id}}" \
  --session="{{user.session_id}}" \
  --location="{{env.VERTEX_AI_AGENTBUILDER_LOCATION:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --user-input="{{user.user_message}}" \
  --format="json"
```

#### Execution — CLI (Streaming)

```bash
# Streaming conversation for real-time responses
gcloud ai agents run "{{user.agent_id}}" \
  --session="{{user.session_id}}" \
  --location="{{env.VERTEX_AI_AGENTBUILDER_LOCATION:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --user-input="{{user.user_message}}" \
  --streaming \
  --format="json"
```

#### Post-execution Validation

1. Extract response text: `jq -r '.responses[0].text.text[0]'`
2. Extract detected intent: `jq -r '.responses[0].intentDetectionResult.intentName'`
3. Report response to user.
4. On grounding citations → report source URLs.

#### Failure Recovery

| Error pattern | Agent Action | UX Feedback |
|--------------|--------------|-------------|
| `NOT_FOUND` — session | Recreate session | `[ERROR] Session not found. Create a new session first.` |
| `INVALID_ARGUMENT` | Check message encoding | `[ERROR] Invalid user input. Ensure UTF-8 encoding.` |
| `UNAUTHENTICATED` | Re-authenticate | `[ERROR] Authentication failed. Refresh credentials.` |
| `DEADLINE_EXCEEDED` | Retry with shorter context or timeout | `[ERROR] Conversation timed out. Retry with simpler query.` |

---

### Operation: Detect Intent (Programmatic)

#### Execution — CLI

```bash
# Detect intent from text without full conversation context
gcloud ai agents detect-intent \
  --agent="{{user.agent_id}}" \
  --location="{{env.VERTEX_AI_AGENTBUILDER_LOCATION:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --text="{{user.user_message}}" \
  --session-id="{{user.session_id}}" \
  --format="json" | jq '{intent, confidence, parameters}'
```

#### Present to User

| Field | Path | Notes |
|-------|------|-------|
| Intent | `$.responses[0].intentDetectionResult.intent.name` | Matched intent |
| Confidence | `$.responses[0].intentDetectionResult.confidence` | 0.0–1.0 |
| Parameters | `$.responses[0].parameterValues` | Extracted entities |

---

### Operation: Delete Session

#### Pre-flight (Safety Gate)

- Warn: ending a session clears conversation history. Agent configuration is preserved.
- Obtain explicit confirmation for active sessions with ongoing conversations.

#### Execution — CLI

```bash
gcloud ai agents sessions delete "{{user.session_id}}" \
  --agent="{{user.agent_id}}" \
  --location="{{env.VERTEX_AI_AGENTBUILDER_LOCATION:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --format="json"
```

---

## Prerequisites

1. **Install gcloud CLI**:
   ```bash
   curl https://sdk.cloud.google.com | bash
   exec -l $SHELL
   gcloud init
   gcloud components install ai
   ```

2. **Bootstrap Go runtime** (JIT fallback):
   ```bash
   if ! command -v go &>/dev/null; then
       OS=$(uname -s | tr '[:upper:]' '[:lower:]')
       ARCH=$(uname -m)
       [ "$ARCH" = "x86_64" ] && ARCH="amd64"
       [ "$ARCH" = "aarch64" ] && ARCH="arm64"
       mkdir -p /tmp/go-runtime
       curl -fsSL "https://go.dev/dl/go1.24.0.${OS}-${ARCH}.tar.gz" | tar -xz -C /tmp/go-runtime
       export PATH="/tmp/go-runtime/go/bin:$PATH"
   fi
   go version
   ```

3. **Configure credentials**:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="{{env.GOOGLE_APPLICATION_CREDENTIALS}}"
   export CLOUDSDK_CORE_PROJECT="{{env.CLOUDSDK_CORE_PROJECT}}"
   export VERTEX_AI_AGENTBUILDER_LOCATION="{{env.VERTEX_AI_AGENTBUILDER_LOCATION:-us-central1}}"
   gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS"
   ```

4. **Verify**:
   ```bash
   gcloud ai agents list --format="json" --quiet && echo "✅ Agent Builder API accessible"
   ```

## Reference Directory

- [Core Concepts](references/core-concepts.md)
- [API & SDK Usage](references/api-sdk-usage.md)
- [gcloud Usage](references/gcloud-usage.md)
- [Troubleshooting Guide](references/troubleshooting.md)
- [Monitoring & Alerts](references/monitoring.md)
- [Integration](references/integration.md)
- [User Experience Specification](references/user-experience-spec.md)
- [Optimization Analysis](references/optimization-analysis.md)
- [Execution Environment Setup](references/execution-environment.md)
- [Enhanced Self-Healing Framework](references/enhanced-self-healing-framework.md)
- [Well-Architected Assessment](references/well-architected-assessment.md)

## Quality Gate (GCL)

| Classification | `required` | `max_iter` | Most-scrutinized ops |
|---------------|------------|------------|----------------------|
| Destructive | Delete Agent | 2 | `gcloud ai agents delete` |
| Config | Create Agent, Update Agent | 3 | Agent model config, tool registration |
| Read-only | List, Describe | 5 | Session listing |

- **GCL Rubric:** `references/rubric.md`
- **GCL Prompt Templates:** `references/prompt-templates.md`
- **Changelog:** v1.0.0 — Initial skill with agent CRUD, session management, tool registration

## Operational Best Practices

- **Least privilege:** Use scoped Dialogflow roles (`roles/dialogflow.agentEditor`, `roles/dialogflow.conversationViewer`) instead of admin where possible.
- **Session management:** Delete sessions after conversations end to avoid stale state accumulation.
- **Tool registration:** Validate OpenAPI schemas before registration; malformed tools cause runtime failures.
- **Streaming vs blocking:** Use `--streaming` for real-time UX; use blocking for scripted/automated flows.
- **Agent versioning:** Export agent configs before major updates via `gcloud ai agents export`.
- **Cost awareness:** Monitor grounding API call counts; Vertex AI Search grounding is billed per query.

## Token Efficiency Guidelines (P0 — 强制)

| Rule | Key Point | Application |
|------|-----------|-------------|
| TE-1 | API query > static tables | Use `gcloud ai agents list` instead of hardcoding agent limits/regions |
| TE-2 | Omit unnecessary docstrings | Inline `#` comments only; no function docstrings in Go/Python snippets |
| TE-3 | Compact error tables | 1 error code per row, ≤3 columns in troubleshooting |
| TE-4 | Centralized JSON paths | File-top comment block; one per resource type |
| TE-5 | YAML anchors in example-config.yaml | Use `&anchor` for shared fields |
| TE-6 | Eliminate cross-file duplicate flows | SKILL.md has full flow; references/ link, don't repeat |
| TE-7 | Layer professional content | AIOps/FinOps in `references/advanced/`; security-sensitive ops marked explicitly |
| TE-8 | Reference depth ≤2 layers | `references/` nesting max 2 levels; no `references/advanced/deep/` chains |

## See Also — Meta-Skill Rules

- [gcp-skill-generator](../gcp-skill-generator/SKILL.md) — Full generation spec and P0/P1 checklist
- [governance-and-adversarial-review.md](../gcp-skill-generator/references/governance-and-adversarial-review.md) — Adversarial review scenarios
- [AGENTS.md](../../AGENTS.md) — CADL loop, GCL rules, credential masking

> **任务完成后按根 `AGENTS.md` 的「复利资产沉淀机制 (CADL)」复盘并沉淀可复用资产。**
