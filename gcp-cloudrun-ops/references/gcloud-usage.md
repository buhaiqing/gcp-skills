# gcloud — Cloud Run CLI

## Install and Config

- Install: [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
- Auth: `gcloud auth login` or `gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS"`
- Set project: `gcloud config set project $CLOUDSDK_CORE_PROJECT`
- Set region: `gcloud config set run/region us-central1` (optional default)

## Conventions (Agent Execution)

- Always use `--format=json` for machine-parseable output
- Use `jq` for field extraction from JSON output
- Long-running operations (create/deploy/delete) return when complete — `gcloud` polls automatically
- Credentials via `GOOGLE_APPLICATION_CREDENTIALS` env var
- Project via `CLOUDSDK_CORE_PROJECT` env var

## CLI vs API Coverage Gap

| Operation (REST API) | Available via `gcloud`? | Notes |
|----------------------|------------------------|-------|
| Create service | yes | `gcloud run services create` |
| Describe service | yes | `gcloud run services describe` |
| List services | yes | `gcloud run services list` |
| Update service | yes | `gcloud run services deploy` |
| Delete service | yes | `gcloud run services delete` |
| List revisions | yes | `gcloud run revisions list` |
| Describe revision | yes | `gcloud run revisions describe` |
| Delete revision | yes | `gcloud run revisions delete` |
| Update traffic | yes | `gcloud run services update-traffic` |
| Export service config | yes | `gcloud run services export` |
| Replace service config | yes | `gcloud run services replace` |
| Add IAM policy | yes | `gcloud run services add-iam-policy-binding` |
| Set metadata/labels | yes | `--update-labels` flag |
| Configure custom domains | yes | `gcloud run domain-mappings create` |
| Get IAM policy | yes | `gcloud run services get-iam-policy` |

Full coverage — no significant gaps.

## Command Map

| Goal | Example `gcloud` Invocation | Notes |
|------|-----------------------------|-------|
| Create | `gcloud run services create NAME --image=IMAGE --region=REGION --project=PROJECT --format=json` | JSON output |
| Describe | `gcloud run services describe NAME --region=REGION --project=PROJECT --format=json` | JSON output |
| List | `gcloud run services list --region=REGION --project=PROJECT --format=json` | JSON output |
| Deploy | `gcloud run services deploy NAME --image=IMAGE --region=REGION --project=PROJECT --format=json` | Creates new revision |
| Delete | `gcloud run services delete NAME --region=REGION --project=PROJECT --format=json` | Irreversible |
| Update traffic | `gcloud run services update-traffic NAME --to-revisions=REV1=80,REV2=20 --region=REGION --project=PROJECT --format=json` | Split traffic |
| List revisions | `gcloud run revisions list --service=NAME --region=REGION --project=PROJECT --format=json` | JSON output |
| Describe revision | `gcloud run revisions describe REV --region=REGION --project=PROJECT --format=json` | JSON output |
| Delete revision | `gcloud run revisions delete REV --region=REGION --project=PROJECT --format=json` | JSON output |
| Export | `gcloud run services export NAME --region=REGION --project=PROJECT --format=json` | Export config |
| Add IAM | `gcloud run services add-iam-policy-binding NAME --member=MEMBER --role=ROLE --region=REGION --project=PROJECT --format=json` | IAM binding |
| Get IAM | `gcloud run services get-iam-policy NAME --region=REGION --project=PROJECT --format=json` | Get IAM policy |
| Domain mapping | `gcloud run domain-mappings create --service=NAME --domain=DOMAIN --region=REGION --project=PROJECT --format=json` | Custom domain |

## Common jq Extracts

```bash
# Service URL
gcloud run services describe NAME --region=REGION --format=json | jq -r '.status.url'

# Latest revision
gcloud run services describe NAME --region=REGION --format=json | jq -r '.status.latestReadyRevisionName'

# Current image
gcloud run services describe NAME --region=REGION --format=json | jq -r '.spec.template.spec.containers[0].image'

# Traffic split
gcloud run services describe NAME --region=REGION --format=json | jq '.status.traffic[] | {revision: .revisionName, percent: .percent}'

# Service conditions
gcloud run services describe NAME --region=REGION --format=json | jq '.status.conditions[] | {type: .type, status: .status, reason: .reason, message: .message}'

# List all service names and URLs
gcloud run services list --region=REGION --format=json | jq -r '.[] | "\(.metadata.name)\t\(.status.url)"'

# Revision image mapping
gcloud run revisions list --service=NAME --region=REGION --format=json | jq -r '.[] | "\(.metadata.name)\t\(.spec.containers[0].image)"'
```

## Deployment Flags Reference

> Flags are validated at runtime. Use `gcloud run services create --help` for full list.

| Flag | Default | Description |
|------|---------|-------------|
| `--image` | (required) | Container image URL |
| `--cpu` | 1 | CPU cores (1, 2, 4, 6, 8) |
| `--memory` | 512Mi | Memory (512Mi, 1Gi, 2Gi, 4Gi, 8Gi, 16Gi, 32Gi) |
| `--max-instances` | 1000 | Max concurrent instances |
| `--min-instances` | 0 | Min instances (cold start tradeoff) |
| `--concurrency` | 80 | Max requests per instance |
| `--timeout` | 300 | Request timeout seconds (max 3600) |
| `--port` | 8080 | Container port |
| `--allow-unauthenticated` | (flag) | Public access |
| `--no-allow-unauthenticated` | (flag) | Require authentication |
| `--set-env-vars` | - | KEY=VALUE,... |
| `--update-env-vars` | - | KEY=VALUE,... (merge) |
| `--remove-env-vars` | - | KEY,... |
| `--clear-env-vars` | - | Remove all env vars |
| `--set-secrets` | - | KEY=SECRET:VERSION,... |
| `--ingress` | all | all, internal, internal-and-cloud-load-balancing |
| `--vpc-connector` | - | VPC connector name |
| `--labels` | - | KEY=VALUE,... |
| `--service-account` | default | Service account email |
| `--execution-environment` | gen1 | gen1, gen2 |
