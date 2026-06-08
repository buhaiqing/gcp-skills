# gcloud Usage — Cloud Functions

## Install and Config

- **Install**: [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
- **Credentials**: Set `GOOGLE_APPLICATION_CREDENTIALS` or run `gcloud auth login`
- **Project**: `gcloud config set project <project-id>` or `CLOUDSDK_CORE_PROJECT` env var

## Conventions (Agent Execution)

- Always use `--format=json` for machine-parseable output
- Use `jq` for field extraction from JSON output
- Use `--gen2` flag for 2nd generation functions (recommended)
- Use `--gen1` flag only for legacy function management
- Long-running operations (deploy, delete) block until completion by default

## Command Map

| Goal | Example `gcloud` invocation | Notes |
|------|--------------------------|-------|
| Deploy HTTP function | `gcloud functions deploy NAME --gen2 --runtime=RUNTIME --trigger-http --entry-point=EP --source=DIR --region=REGION --project=PROJECT --format=json` | Creates or updates function |
| Deploy event function | `gcloud functions deploy NAME --gen2 --runtime=RUNTIME --trigger-event-filters=FILTERS --entry-point=EP --source=DIR --region=REGION --project=PROJECT --format=json` | Creates event-triggered function |
| Describe function | `gcloud functions describe NAME --gen2 --region=REGION --project=PROJECT --format=json` | Returns full function config |
| List functions (gen2) | `gcloud functions list --gen2 --region=REGION --project=PROJECT --format=json` | Lists all gen2 functions |
| List functions (gen1) | `gcloud functions list --gen1 --region=REGION --project=PROJECT --format=json` | Lists all gen1 functions |
| Update function | `gcloud functions deploy NAME --gen2 --runtime=RUNTIME --entry-point=EP --source=DIR --region=REGION --project=PROJECT --format=json` | Same as deploy; detects existing |
| Delete function | `gcloud functions delete NAME --gen2 --region=REGION --project=PROJECT --format=json` | Irreversible; requires confirmation |
| Invoke function | `gcloud functions call NAME --gen2 --region=REGION --project=PROJECT --data='JSON' --format=json` | HTTP functions only |
| Read logs | `gcloud functions logs read NAME --gen2 --region=REGION --project=PROJECT --limit=50 --format=json` | Recent execution logs |
| Read error logs | `gcloud functions logs read NAME --gen2 --region=REGION --project=PROJECT --min-log-level=error --limit=50 --format=json` | Error-only logs |
| List runtimes | `gcloud functions runtimes list --format=json` | Available runtime versions |
| Gen1 to gen2 migration | `gcloud functions gen1-to-gen2 NAME --gen1-region=REGION --gen2-region=REGION --project=PROJECT` | Migrate gen1 function |
| Add IAM binding | `gcloud functions add-iam-policy-binding NAME --gen2 --region=REGION --member='user:EMAIL' --role='roles/cloudfunctions.invoker' --project=PROJECT` | Grant invocation access |
| Remove IAM binding | `gcloud functions remove-iam-policy-binding NAME --gen2 --region=REGION --member='user:EMAIL' --role='roles/cloudfunctions.invoker' --project=PROJECT` | Revoke invocation access |
| Get IAM policy | `gcloud functions get-iam-policy NAME --gen2 --region=REGION --project=PROJECT --format=json` | View IAM policy |

## CLI vs API Coverage Gap

| Operation (REST API) | Available via `gcloud`? | Notes |
|----------------------|------------------------|-------|
| Create function | Yes | `gcloud functions deploy` |
| Update function | Yes | `gcloud functions deploy` (detects existing) |
| Get function | Yes | `gcloud functions describe` |
| List functions | Yes | `gcloud functions list` |
| Delete function | Yes | `gcloud functions delete` |
| Generate upload URL | No | Use Python/Go SDK directly |
| Invoke function | Yes | `gcloud functions call` (HTTP only) |
| Get IAM policy | Yes | `gcloud functions get-iam-policy` |
| Set IAM policy | Yes | `gcloud functions set-iam-policy` |
| Add IAM binding | Yes | `gcloud functions add-iam-policy-binding` |
| Operations API (LRO) | No (handled internally) | gcloud polls automatically |

## JQ Extraction Patterns

### Deploy Validation

```bash
# Extract function URL
gcloud functions describe NAME --gen2 --region=REGION --format=json | jq -r '.serviceConfig.uri'

# Extract function state
gcloud functions describe NAME --gen2 --region=REGION --format=json | jq -r '.state'

# Extract runtime
gcloud functions describe NAME --gen2 --region=REGION --format=json | jq -r '.buildConfig.runtime'

# Extract memory
gcloud functions describe NAME --gen2 --region=REGION --format=json | jq -r '.serviceConfig.availableMemory'

# Extract timeout
gcloud functions describe NAME --gen2 --region=REGION --format=json | jq -r '.serviceConfig.timeoutSeconds'

# Extract event trigger type (if present)
gcloud functions describe NAME --gen2 --region=REGION --format=json | jq -r '.eventTrigger.eventType // "http"'

# Extract max/min instances
gcloud functions describe NAME --gen2 --region=REGION --format=json | jq '{max: .serviceConfig.maxInstanceCount, min: .serviceConfig.minInstanceCount}'
```

### List Validation

```bash
# List function names and states
gcloud functions list --gen2 --region=REGION --format=json | jq '[.[] | {name: .name, state: .state}]'

# List HTTP functions only
gcloud functions list --gen2 --region=REGION --format=json | jq '[.[] | select(.eventTrigger == null) | {name: .name, url: .serviceConfig.uri}]'

# List event-triggered functions only
gcloud functions list --gen2 --region=REGION --format=json | jq '[.[] | select(.eventTrigger != null) | {name: .name, eventType: .eventTrigger.eventType}]'

# Count functions by state
gcloud functions list --gen2 --region=REGION --format=json | jq 'group_by(.state) | map({state: .[0].state, count: length})'
```

### Logs Validation

```bash
# Extract recent log messages
gcloud functions logs read NAME --gen2 --region=REGION --limit=10 --format=json | jq '[.[] | {timestamp: .timestamp, severity: .severity, message: .textPayload}]'

# Count errors
gcloud functions logs read NAME --gen2 --region=REGION --min-log-level=error --limit=100 --format=json | jq 'length'
```

## Common Recipes

### Deploy with Environment Variables

```bash
gcloud functions deploy my-function \
  --gen2 \
  --runtime=python312 \
  --trigger-http \
  --entry-point=hello \
  --source=. \
  --region=us-central1 \
  --set-env-vars=DB_HOST=10.0.0.1,DB_PORT=5432,DEBUG=false
```

### Deploy with Secret Manager Integration

```bash
gcloud functions deploy my-function \
  --gen2 \
  --runtime=python312 \
  --trigger-http \
  --entry-point=hello \
  --source=. \
  --region=us-central1 \
  --set-secrets=DB_PASSWORD=my-db-password:latest,API_KEY=my-api-key:1
```

### Deploy with VPC Connector

```bash
gcloud functions deploy my-function \
  --gen2 \
  --runtime=python312 \
  --trigger-http \
  --entry-point=hello \
  --source=. \
  --region=us-central1 \
  --vpc-connector=my-connector \
  --vpc-egress=all-traffic
```

### Deploy Internal-Only Function

```bash
gcloud functions deploy my-function \
  --gen2 \
  --runtime=python312 \
  --trigger-http \
  --entry-point=hello \
  --source=. \
  --region=us-central1 \
  --ingress-settings=internal-only \
  --no-allow-unauthenticated
```

### Deploy Event-Triggered Function (Pub/Sub)

```bash
gcloud functions deploy process-message \
  --gen2 \
  --runtime=python312 \
  --trigger-event-filters=type=google.cloud.pubsub.topic.v1.messagePublished,topic=my-topic \
  --entry-point=handle_pubsub \
  --source=. \
  --region=us-central1 \
  --service-account=my-sa@my-project.iam.gserviceaccount.com
```

### Deploy Event-Triggered Function (Cloud Storage)

```bash
gcloud functions deploy process-upload \
  --gen2 \
  --runtime=python312 \
  --trigger-event-filters=type=google.cloud.storage.object.v1.final,bucket=my-bucket \
  --entry-point=handle_gcs \
  --source=. \
  --region=us-central1
```

### Update Scaling Configuration

```bash
gcloud functions deploy my-function \
  --gen2 \
  --runtime=python312 \
  --entry-point=hello \
  --source=. \
  --region=us-central1 \
  --memory=512Mi \
  --cpu=1 \
  --timeout=120 \
  --max-instances=200 \
  --min-instances=2 \
  --concurrency=10
```

### Grant Public Access to HTTP Function

```bash
gcloud functions add-iam-policy-binding my-function \
  --gen2 \
  --region=us-central1 \
  --member="allUsers" \
  --role="roles/cloudfunctions.invoker"
```

### Restrict Function to Specific Service Account

```bash
gcloud functions deploy my-function \
  --gen2 \
  --runtime=python312 \
  --trigger-http \
  --entry-point=hello \
  --source=. \
  --region=us-central1 \
  --service-account=my-function-sa@my-project.iam.gserviceaccount.com
```

### Delete Function (Non-Interactive)

```bash
gcloud functions delete my-function \
  --gen2 \
  --region=us-central1 \
  --quiet
```

### View Function Build Logs

```bash
# Cloud Build logs are associated with function deployments
gcloud builds list --filter="source.storageSource.bucket:gcf-v2-sources" --limit=10 --format=json | jq '[.[] | {id: .id, status: .status, createTime: .startTime}]'
```
