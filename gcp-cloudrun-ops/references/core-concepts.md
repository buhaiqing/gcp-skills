# Core Concepts — Cloud Run (Fully Managed)

## Architecture

Cloud Run is a fully managed serverless platform that executes stateless container images. It abstracts away infrastructure management: no VM provisioning, no Kubernetes cluster configuration. Each deployment creates a **Service**, which manages one or more **Revisions** (immutable snapshots of container + configuration).

```
Project
 └── Region (e.g., us-central1)
      └── Service (e.g., my-api)
           ├── Revision 1 (image:v1, 80% traffic)
           ├── Revision 2 (image:v2, 20% traffic)
           └── URL: https://my-api-xxxx.a.run.app
```

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Service** | Top-level resource; has a stable URL |
| **Revision** | Immutable snapshot of service config + container image |
| **Configuration** | Mutable spec that generates new revisions on update |
| **Traffic Splitting** | Route percentages of requests across revisions |
| **Autoscaling** | Scale to zero (min-instances=0) up to max-instances |
| **Concurrency** | Max requests per instance (default 80) |

## Container Requirements

| Requirement | Default | Notes |
|-------------|---------|-------|
| Port | 8080 | Override with `--port` |
| Protocol | HTTP/1.1 or HTTP/2 | Must listen on TCP |
| Image format | OCI/Docker | From any registry (Artifact Registry, Docker Hub, GCR) |
| Max container size | 32 GB | Including filesystem |
| Request timeout | 300s | Max 3600s (60 min) |

## Resource Limits

> **TE-1**: Query current limits dynamically instead of hardcoding:
> ```bash
> gcloud run services describe NAME --format=json | jq '.spec.template.spec.containers[0].resources'
> ```

| Resource | Default | Maximum |
|----------|---------|---------|
| vCPU | 1 | 8 (GPU: up to 16) |
| Memory | 512 Mi | 32 Gi |
| Max instances | 1000 | 1000 (request increase for more) |
| Min instances | 0 | 1000 |
| Concurrency | 80 | 1000 |
| Request timeout | 300s | 3600s |
| Max request size | 32 MB | 32 MB |
| Max response size | 32 MB | 32 MB |

## Regions

> **TE-1**: Query available regions instead of hardcoding:
> ```bash
> gcloud run regions list --format=json
> ```

| Region | Location | Multi-region |
|--------|----------|--------------|
| us-central1 | Iowa | No |
| us-east1 | South Carolina | No |
| us-east4 | Northern Virginia | No |
| us-west1 | Oregon | No |
| europe-west1 | Belgium | No |
| europe-west3 | Frankfurt | No |
| europe-west6 | Zurich | No |
| asia-east1 | Taiwan | No |
| asia-east2 | Hong Kong | No |
| asia-northeast1 | Tokyo | No |
| asia-northeast2 | Osaka | No |
| australia-southeast1 | Sydney | No |

## Prerequisites

| Prerequisite | Command | Notes |
|--------------|---------|-------|
| Enable Cloud Run API | `gcloud services enable run.googleapis.com` | One-time per project |
| Enable Cloud Build API | `gcloud services enable cloudbuild.googleapis.com` | For source deployments |
| IAM role (admin) | `gcloud projects add-iam-policy-binding PROJECT --member=SERVICE_ACCOUNT --role=roles/run.admin` | For service management |
| IAM role (invoker) | `gcloud run services add-iam-policy-binding NAME --member=MEMBER --role=roles/run.invoker` | For invocation access |
| Container registry access | Artifact Registry or GCR permissions | `roles/artifactregistry.reader` |

## Service Lifecycle

1. **Create**: `gcloud run services create` → creates service + revision 1
2. **Deploy**: `gcloud run services deploy` → creates new revision, traffic stays on old
3. **Traffic Split**: `gcloud run services update-traffic` → route traffic across revisions
4. **Update**: `gcloud run services deploy` → creates revision, optionally shifts traffic
5. **Delete**: `gcloud run services delete` → removes service and all revisions

## Delegation Notes

- **Container images**: Use `gcp-artifactregistry-ops` for registry management
- **VPC connectors**: Use `gcp-vpc-ops` for VPC Serverless Connector setup
- **Secrets**: Use `gcp-secretmanager-ops` for secret creation/management
- **Load balancing**: Use `gcp-lb-ops` for Cloud Run with external LB
- **CI/CD**: Use `gcp-cloudbuild-ops` for automated builds
- **Monitoring**: Use `gcp-monitoring-ops` for dashboards and alerts
