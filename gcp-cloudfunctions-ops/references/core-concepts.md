# Core Concepts — Cloud Functions (2nd gen)

## Architecture Overview

Cloud Functions 2nd gen is an event-driven, serverless compute platform built on Cloud Run infrastructure. Unlike 1st gen (which used a custom runtime), 2nd gen functions are backed by Cloud Run, enabling:

- **Longer timeouts**: Up to 3600s (vs 540s for gen1)
- **VPC connectivity**: Native VPC connector support
- **Flexible scaling**: Configurable min/max instances, concurrency
- **More runtimes**: Latest Python, Node.js, Go, Java, .NET, Ruby versions
- **Eventarc integration**: Unified event routing with Eventarc
- **Better observability**: Cloud Monitoring, Cloud Logging, Cloud Trace built-in

### Execution Model

```
Client/Event → Cloud Functions API → Cloud Run Service → Function Container
                                                    ↓
                                          Cloud Monitoring/Logging
```

### Resource Model

- **Function** = Cloud Run Service (gen2 internally creates a Cloud Run service)
- **Build Config** = Cloud Build build for source compilation
- **Service Config** = Runtime configuration (memory, CPU, scaling, env vars, secrets)
- **Event Trigger** = Eventarc trigger binding (for event-driven functions)

## Runtime Support

| Language | Supported Versions | Entry Point Pattern |
|----------|-------------------|---------------------|
| Python | 3.10, 3.11, 3.12 | `def function_name(request):` (HTTP) or `def function_name(event, context):` (event) |
| Node.js | 18, 20, 22 | `exports.functionName = (req, res) => {}` (HTTP) or `exports.functionName = (event, context) => {}` (event) |
| Go | 1.21, 1.22, 1.23 | `func FunctionName(w http.ResponseWriter, r *http.Request)` (HTTP) or `func FunctionName(ctx context.Context, event CloudEvent) error` (event) |
| Java | 11, 17, 21 | `public class Function implements HttpFunction` or `BackgroundFunction<T>` |
| .NET | 8.0 | `[FunctionsStartup] public class Function : ICloudFunction` |
| Ruby | 3.2, 3.3 | `def function_name(request:)` (HTTP) or `def function_name(event:, context:)` (event) |

> **TE-1**: Runtime versions change. Query `gcloud functions runtimes list` for current support instead of hardcoding.

## Scaling Model

### Horizontal Scaling

| Parameter | Default (gen2) | Range | Notes |
|-----------|---------------|-------|-------|
| Min instances | 0 | 0–1000 | 0 = scale to zero (cold starts possible) |
| Max instances | 100 (HTTP), 3000 (events) | 1–1000 (HTTP), 1–10000 (events) | Upper bound for concurrent executions |
| Concurrency | 1 | 1–1000 | Requests per instance; higher = more efficient, but isolate carefully |
| CPU allocation | Derived from memory | default, 1, 2, 4, 6, 8 | Higher CPU reduces cold start time |

### Memory & CPU Coupling

| Memory | Default CPU | Max CPU |
|--------|-------------|---------|
| 128 Mi–512 Mi | 0.08–0.5 | 1 |
| 1 Gi–2 Gi | 1 | 2 |
| 4 Gi | 2 | 4 |
| 8 Gi–16 Gi | 4 | 6 |
| 32 Gi | 6 | 8 |

> **Performance tip**: For cold-start-sensitive workloads, set `min-instances > 0` and allocate more CPU.

## Event Ecosystem

### Supported Event Sources (gen2)

| Event Source | Event Type | Filter Pattern |
|-------------|-----------|----------------|
| Cloud Storage | `google.cloud.storage.object.v1.final` | `type=...,bucket=BUCKET` |
| Cloud Storage | `google.cloud.storage.object.v1.archive` | `type=...,bucket=BUCKET` |
| Cloud Storage | `google.cloud.storage.object.v1.delete` | `type=...,bucket=BUCKET` |
| Cloud Pub/Sub | `google.cloud.pubsub.topic.v1.messagePublished` | `type=...,topic=TOPIC` |
| Firebase Auth | `google.firebase.auth.user.v1.created` | `type=...,firebaseAuthentication` |
| Firebase Firestore | `google.cloud.firestore.document.v1.written` | `type=...,database=...,document=...` |
| Firebase Realtime DB | `google.firebase.database.ref.v1.written` | `type=...,instance=...,path=...` |
| Eventarc (custom) | Any CloudEvent | `type=...,source=...` |

> **Delegation**: For complex Eventarc routing or custom event sources, delegate to `gcp-eventarc-ops`.

## Trigger Types

### HTTP Trigger

- Invoked via HTTPS endpoint
- URL format: `https://REGION-PROJECT_ID.cloudfunctions.net/FUNCTION_NAME`
- Supports authentication (IAM) or public access
- Max request/response size: 32 MB

### Event Trigger

- Invoked by Cloud Events via Eventarc
- Supports filtering by event attributes
- Retry on failure (configurable)
- Dead letter queue support (Pub/Sub)

## Pricing Model

| Component | Pricing Unit | Notes |
|-----------|-------------|-------|
| Invocations | Per 1M invocations | First 2M/month free |
| Compute time | Per GB-second | Rounded to 100ms; first 400,000 GB-s free |
| Networking | Per GB egress | Standard GCP egress rates |
| Build | Per build-minute | Cloud Build pricing applies; first 120 min/day free |

> **Cost optimization**: Set `min-instances=0` for sporadic workloads. Use committed use discounts for steady-state.

## Gen1 vs Gen2 Comparison

| Feature | Gen1 | Gen2 |
|---------|------|------|
| Infrastructure | Custom | Cloud Run |
| Max timeout | 540s | 3600s |
| Max memory | 8 GiB | 32 GiB |
| VPC connector | Yes | Yes |
| Min instances | Yes (limited) | Yes (full control) |
| Concurrency tuning | No | Yes (1–1000) |
| Eventarc integration | Limited | Full |
| Custom domains | No | Yes (via Cloud Run) |
| Cloud Build integration | No | Yes (automatic) |
| GPU support | No | No (use Cloud Run/Vertex AI) |

> **Migration**: Use `gcloud functions gen1-to-gen2` for simple migrations, or redeploy manually for full control.

## Key Limits

| Resource | Limit | Notes |
|----------|-------|-------|
| Functions per project per region | 1000 | Soft limit; request increase |
| Deployment package size | 500 MB (compressed) | Source or container image |
| Request size (HTTP) | 32 MB | Response also 32 MB |
| Environment variables | 5.5 KB total | Including keys and values |
| Concurrent requests | Configurable (1–1000) | Per instance |
| Max instances (HTTP) | 1000 | Per function |
| Max instances (events) | 10000 | Per function |

> **TE-1**: Query `gcloud services quotas list --service=cloudfunctions.googleapis.com` for current limits instead of hardcoding.

## Security Considerations

- **IAM authentication**: Use `--no-allow-unauthenticated` to restrict access
- **Service identity**: Each function has a Compute Engine default service account or custom SA
- **VPC connector**: Route traffic through VPC for private resource access
- **Secret Manager**: Mount secrets as env vars (never hardcode)
- **Ingress settings**: Control network access (all, internal-only, internal-and-gclb)
- **Cloud Audit Logs**: All function lifecycle events are logged
