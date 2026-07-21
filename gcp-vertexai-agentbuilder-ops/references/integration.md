# Integration — Vertex AI Agent Builder

## Environment Setup

### Primary Path: gcloud CLI

```bash
# Install ai component
gcloud components install ai --quiet

# Authenticate
gcloud auth activate-service-account \
  --key-file="$GOOGLE_APPLICATION_CREDENTIALS"

# Set project
gcloud config set project "$CLOUDSDK_CORE_PROJECT"

# Set default location
export VERTEX_AI_AGENTBUILDER_LOCATION="us-central1"

# Verify
gcloud ai agents list --format=json --quiet && echo "✅ Agent Builder accessible"
```

### Fallback Path: JIT Python SDK

```bash
# Check Python
if ! command -v python3 &>/dev/null; then
    echo "Python 3 not found"
    exit 1
fi

# Install SDK
pip install --quiet google-cloud-dialogflow

# Run script
python3 create_agent.py
```

### Fallback Path: JIT Go SDK

```bash
# Check Go runtime
if ! command -v go &>/dev/null; then
    OS=$(uname -s | tr '[:upper:]' '[:lower:]')
    ARCH=$(uname -m)
    [ "$ARCH" = "x86_64" ] && ARCH="amd64"
    [ "$ARCH" = "aarch64" ] && ARCH="arm64"
    mkdir -p /tmp/go-runtime
    curl -fsSL "https://go.dev/dl/go1.24.0.${OS}-${ARCH}.tar.gz" | tar -xz -C /tmp/go-runtime
    export PATH="/tmp/go-runtime/go/bin:$PATH"
fi

# Initialize workspace
mkdir -p /tmp/gcp-sdk-workspace
cd /tmp/gcp-sdk-workspace
go mod init sdk-script

# Get dependencies
export GOPROXY="https://proxy.golang.org,direct"
go get cloud.google.com/go/dialogflow/cx/apiv3
go get google.golang.org/genproto/googleapis/cloud/dialogflow/cx/v3
go get google.golang.org/api/option

# Run
go run create_agent.go
```

## Cross-Skill Delegation

| Target Skill | Delegation Trigger |
|-------------|-------------------|
| `gcp-vertexai-ops` | Agent model tuning, foundation model management |
| `gcp-vertexai-search-ops` | Vertex AI Search datastore configuration, grounding setup |
| `gcp-gcs-ops` | Agent export/import via GCS bucket; large config storage |
| `gcp-iam-ops` | Agent service account IAM roles; tool endpoint permissions |
| `gcp-logging-ops` | Conversation audit logs; Cloud Logging filters |
| `gcp-monitoring-ops` | Alert policies for agent metrics |
| `gcp-bigquery-ops` | Conversation analytics export |

## Tool Webhook Integration

```bash
# Example: Register a Function Calling tool with webhook
gcloud ai agents tools create \
  --agent="{{user.agent_id}}" \
  --tool-type=FUNCTION_CALLING \
  --display-name="get_order_status" \
  --description="Get the status of a customer order" \
  --location="{{env.VERTEX_AI_AGENTBUILDER_LOCATION:-us-central1}}" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --webhook-uri="https://my-service.example.com/api/order/status"

# Tool schema (OpenAPI 3.0)
cat << 'EOF' | gcloud ai agents tools create --agent="{{user.agent_id}}" ...
openapi: 3.0.0
info:
  title: Order Service
  version: 1.0.0
paths:
  /order/status:
    get:
      operationId: getOrderStatus
      parameters:
        - name: orderId
          in: query
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Order status
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                  eta:
                    type: string
EOF
```

## Environment Variable Loading

```bash
# .env file (MUST be in .gitignore)
cat << 'EOF' > .env
GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa-key.json
CLOUDSDK_CORE_PROJECT=my-gcp-project
VERTEX_AI_AGENTBUILDER_LOCATION=us-central1
EOF

# Load in shell
set -a
source .env
set +a
```

## Go SDK Script Template

```go
// main.go — Vertex AI Agent Builder SDK script
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
    resp, err := client.ListAgents(ctx, &cxpb.ListAgentsRequest{Parent: parent})
    if err != nil {
        log.Fatalf("Failed to list agents: %v", err)
    }

    for _, agent := range resp.Agents {
        fmt.Printf("Agent: %s (state: %s)\n", agent.DisplayName, agent.State)
    }
}
```

> Credential handling: always read from `os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")`. Never hardcode or echo credential values.
