# gcloud — Vertex AI Agent Builder CLI

## Install and Config

```bash
# Install the ai component
gcloud components install ai --quiet

# Or update if already installed
gcloud components update ai

# Authenticate
gcloud auth login
gcloud auth activate-service-account \
  --key-file="$GOOGLE_APPLICATION_CREDENTIALS"

# Set project and location
gcloud config set project "{{env.CLOUDSDK_CORE_PROJECT}}"
export VERTEX_AI_AGENTBUILDER_LOCATION="us-central1"
```

> **CRITICAL Credentials:** Set `GOOGLE_APPLICATION_CREDENTIALS` or run `gcloud auth activate-service-account`.

## Conventions

- Always use `--format=json` for machine-parseable output
- Use `jq` for field extraction: `jq -r '.name'`, `jq -r '.state'`
- Long-running ops (create/delete) return immediately; poll via `describe` until terminal state
- Use `--quiet` to skip confirmation prompts for non-destructive read-only operations
- Location defaults to `us-central1`; set `VERTEX_AI_AGENTBUILDER_LOCATION` env var

## Command Map

### Agent Operations

| Goal | gcloud Command |
|------|---------------|
| Create agent | `gcloud ai agents create --display-name="..." --location="..." --project="..."` |
| List agents | `gcloud ai agents list --location="..." --project="..." --format="json"` |
| Describe agent | `gcloud ai agents describe --agent="ID" --location="..." --project="..."` |
| Update agent | `gcloud ai agents update "AGENT_ID" --display-name="..." --location="..." --project="..."` |
| Delete agent | `gcloud ai agents delete "AGENT_ID" --location="..." --project="..."` |
| Export agent | `gcloud ai agents export "AGENT_ID" --gcs-bucket="gs://bucket/path" --location="..." --project="..."` |
| Import agent | `gcloud ai agents import --gcs-bucket="gs://bucket/path" --location="..." --project="..."` |

### Session Operations

| Goal | gcloud Command |
|------|---------------|
| Create session | `gcloud ai agents sessions create --agent="AGENT_ID" --location="..." --project="..."` |
| List sessions | `gcloud ai agents sessions list --agent="AGENT_ID" --location="..." --project="..."` |
| Run agent (blocking) | `gcloud ai agents run "AGENT_ID" --session="SESSION_ID" --user-input="..." --location="..." --project="..."` |
| Run agent (streaming) | `gcloud ai agents run "AGENT_ID" --session="SESSION_ID" --user-input="..." --streaming --location="..." --project="..."` |
| Detect intent | `gcloud ai agents detect-intent --agent="AGENT_ID" --text="..." --session-id="SESSION_ID" --location="..." --project="..."` |
| Delete session | `gcloud ai agents sessions delete "SESSION_ID" --agent="AGENT_ID" --location="..." --project="..."` |

### Tool Operations

| Goal | gcloud Command |
|------|---------------|
| Create tool | `gcloud ai agents tools create --agent="AGENT_ID" --tool-type=FUNCTION_CALLING --display-name="..." --location="..." --project="..."` |
| List tools | `gcloud ai agents tools list --agent="AGENT_ID" --location="..." --project="..."` |
| Describe tool | `gcloud ai agents tools describe "TOOL_ID" --agent="AGENT_ID" --location="..." --project="..."` |
| Update tool | `gcloud ai agents tools update "TOOL_ID" --agent="AGENT_ID" --location="..." --project="..."` |
| Delete tool | `gcloud ai agents tools delete "TOOL_ID" --agent="AGENT_ID" --location="..." --project="..."` |

## JSON Output Patterns

```bash
# List agents — extract names and states
gcloud ai agents list --location=us-central1 --project="$PROJECT" --format=json \
  | jq '[.agents[] | {name, displayName, state}]'

# Create agent — extract resource name
gcloud ai agents create --display-name="my-agent" --location=us-central1 \
  --project="$PROJECT" --format="value(name)" --quiet

# Run agent — extract response text
gcloud ai agents run "my-agent" --session="$SESSION" --user-input="Hello" \
  --location=us-central1 --project="$PROJECT" --format=json \
  | jq -r '.responses[0].text.text[0]'

# Detect intent — extract intent name and confidence
gcloud ai agents detect-intent --agent="my-agent" --text="Book a flight" \
  --session-id="$SESSION" --location=us-central1 --project="$PROJECT" --format=json \
  | jq '{intent: .responses[0].intentDetectionResult.intent.displayName, confidence: .responses[0].intentDetectionResult.confidence}'
```

## Output Format Options

| Format | Use Case |
|--------|---------|
| `--format=json` | Machine parsing; always use for automation |
| `--format="table(...)"` | Human-readable summaries; display only |
| `--format="value(name)"` | Extract single field for scripting |
| `--format="csv(name,displayName,state)"` | CSV export |
| `--format="yaml"` | Human-readable config; documentation |

## Error Parsing

```bash
# Extract error code from failed command
gcloud ai agents create --display-name="..." --location=us-central1 --project="$PROJECT" 2>&1 \
  | jq -r '.error.code // .code // .@type'

# Map gcloud CLI errors to gRPC codes
# "INVALID_ARGUMENT" → gRPC 400
# "NOT_FOUND" → gRPC 404
# "PERMISSION_DENIED" → gRPC 403
# "UNAUTHENTICATED" → gRPC 401
# "RESOURCE_EXHAUSTED" → gRPC 429
```

## Polling Patterns

```bash
# Poll agent state until ACTIVE
poll_state() {
  local AGENT_ID="$1"
  for i in $(seq 1 60); do
    STATE=$(gcloud ai agents describe "$AGENT_ID" \
      --location="${VERTEX_AI_AGENTBUILDER_LOCATION:-us-central1}" \
      --project="$PROJECT" \
      --format="value(state)" 2>/dev/null)
    [ "$STATE" = "ACTIVE" ] && echo "ACTIVE" && return 0
    [ "$STATE" = "DELETED" ] && echo "DELETED" && return 1
    sleep 5
  done
  echo "TIMEOUT"
  return 2
}
```
