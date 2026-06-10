---
name: cloudbuild-api-sdk-usage
description: Cloud Build API and Python SDK usage patterns for builds, triggers, worker pools, and diagnostics

<!---
load_condition: "[SDK/API fallback 时加载]"
token_cost_estimate: "~1300 tokens"
dependencies: ["references/troubleshooting.md"]
--->
---

# API/SDK Usage — Cloud Build

Use the SDK/API when structured automation is preferred or `gcloud` is unavailable. Python SDK reads ADC from the environment; do not print credential paths or credential objects.

## Install/Import

```bash
python3 -m pip install --user google-cloud-build
```

```python
from google.cloud.devtools import cloudbuild_v1
```

## Client Setup

```python
from google.cloud.devtools import cloudbuild_v1

project = "{{user.project}}"
client = cloudbuild_v1.CloudBuildClient()
```

## Submit Build

```python
from google.cloud.devtools import cloudbuild_v1

client = cloudbuild_v1.CloudBuildClient()
build = cloudbuild_v1.Build(
    steps=[cloudbuild_v1.BuildStep(name="gcr.io/cloud-builders/gcloud", args=["version"])],
    timeout={"seconds": 600},
)
operation = client.create_build(project_id="{{user.project}}", build=build)
result = operation.result(timeout=900)
print({"id": result.id, "status": cloudbuild_v1.Build.Status(result.status).name, "log_url": result.log_url})
```

For source/config-file submission, `gcloud builds submit` is usually safer because it packages source and applies `.gcloudignore`. API callers must explicitly provide source storage/repo fields. For regional builds, use `gcloud builds submit --region="{{user.region}}"` when supported or the regional REST resource path `/v1/projects/{{user.project}}/locations/{{user.region}}/builds` for create/list and `/v1/projects/{{user.project}}/locations/{{user.region}}/builds/{{user.build_id}}` for describe/cancel-compatible calls.

## List and Describe Builds

```python
client = cloudbuild_v1.CloudBuildClient()
for build in client.list_builds(project_id="{{user.project}}", filter='status="FAILURE"'):
    print({"id": build.id, "status": cloudbuild_v1.Build.Status(build.status).name, "log_url": build.log_url})

build = client.get_build(project_id="{{user.project}}", id="{{user.build_id}}")
print({"id": build.id, "status": cloudbuild_v1.Build.Status(build.status).name, "finish_time": str(build.finish_time)})
```

## Cancel and Retry Builds

```python
client = cloudbuild_v1.CloudBuildClient()
cancelled = client.cancel_build(project_id="{{user.project}}", id="{{user.build_id}}")
print({"id": cancelled.id, "status": cloudbuild_v1.Build.Status(cancelled.status).name})
```

Retry is available in the REST/CLI surface; use `gcloud builds retry` unless the local SDK version exposes a dedicated retry method. Do not synthesize a retry by blindly re-submitting unless the build config and source are confirmed idempotent.

## Triggers

```python
client = cloudbuild_v1.CloudBuildClient()
# Legacy/global listing; regional trigger support varies by client version.
for trigger in client.list_build_triggers(project_id="{{user.project}}"):
    print({"id": trigger.id, "name": trigger.name, "filename": trigger.filename})
```

Trigger create/update/delete fields vary by source type. Prefer config-file-driven `gcloud builds triggers import --region="{{user.region}}"` or explicit REST fallback for `projects/{project}/locations/{region}/triggers` when Python client regional support is ambiguous. Require exact confirmation for delete.

### Regional Trigger REST Fallback

```bash
ACCESS_TOKEN="$(gcloud auth print-access-token)"
BASE="https://cloudbuild.googleapis.com/v1/projects/{{user.project}}/locations/{{user.region}}/triggers"

# List regional triggers
curl -sS -H "Authorization: Bearer ${ACCESS_TOKEN}" "${BASE}"

# Describe one regional trigger
curl -sS -H "Authorization: Bearer ${ACCESS_TOKEN}" "${BASE}/{{user.trigger_id}}"
```

Never echo `${ACCESS_TOKEN}`; redact `Authorization` headers in traces. Use this same regional path for read-only verification before update/delete and after mutation.

## Private Worker Pools

Private worker pool methods are available on recent Cloud Build clients and REST resources. Prefer `gcloud builds worker-pools` for parity with released CLI flags. Validate returned fields:

| Field | Purpose |
|-------|---------|
| `name` | `projects/{project}/locations/{region}/workerPools/{pool}` |
| `state` | Creation/update/delete state |
| `workerConfig` | machine type, disk size |
| `networkConfig` | peered network and egress settings |

## REST Patterns

```bash
ACCESS_TOKEN="$(gcloud auth print-access-token)"

# Legacy/project-level build path
curl -sS -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "https://cloudbuild.googleapis.com/v1/projects/{{user.project}}/builds/{{user.build_id}}"

# Regional build path
curl -sS -H "Authorization: Bearer ${ACCESS_TOKEN}" \
  "https://cloudbuild.googleapis.com/v1/projects/{{user.project}}/locations/{{user.region}}/builds/{{user.build_id}}"
```

Never echo `${ACCESS_TOKEN}`. Store REST traces with headers redacted.

## Pagination

- CLI: use `--limit` and `--page-size` where available.
- SDK: iterate pagers; do not assume all builds/triggers fit in one page.
- REST: follow `nextPageToken`.

## Error Handling

Map API exceptions/statuses to [troubleshooting.md](troubleshooting.md#error-taxonomy). Retry only transient `RESOURCE_EXHAUSTED`, `UNAVAILABLE`, and `INTERNAL` conditions with backoff; do not retry non-idempotent builds unless approved.
