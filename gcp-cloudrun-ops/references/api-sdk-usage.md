# API & SDK — Cloud Run

## REST API

- Discovery doc: https://run.googleapis.com/$discovery/rest?version=v1
- Base URL (v1): https://run.googleapis.com/v1/
- Base URL (v2): https://run.googleapis.com/v2/

## Operations Map

| Goal | REST Method (v2) | Python SDK Method | Go SDK Method |
|------|-------------------|-------------------|---------------|
| Create service | POST /v2/projects/{p}/locations/{l}/services | ServicesClient.create_service() | ServicesClient.CreateService() |
| Get service | GET /v2/{name} | ServicesClient.get_service() | ServicesClient.GetService() |
| List services | GET /v2/projects/{p}/locations/{l}/services | ServicesClient.list_services() | ServicesClient.ListServices() |
| Update service | PATCH /v2/{name} | ServicesClient.update_service() | ServicesClient.UpdateService() |
| Delete service | DELETE /v2/{name} | ServicesClient.delete_service() | ServicesClient.DeleteService() |
| List revisions | GET /v2/{parent}/revisions | RevisionsClient.list_revisions() | RevisionsClient.ListRevisions() |
| Get revision | GET /v2/{name} | RevisionsClient.get_revision() | RevisionsClient.GetRevision() |
| Delete revision | DELETE /v2/{name} | RevisionsClient.delete_revision() | RevisionsClient.DeleteRevision() |

## Key JSON Paths (Centralized)

| Operation | JSON Path | Description |
|-----------|-----------|-------------|
| Create/Get service | `$.name` | Full resource name |
| Service URL | `$.uri` | Service URL (v2 API) |
| Container image | `$.template.containers[0].image` | Container image ref |
| Container resources | `$.template.containers[0].resources` | CPU/memory limits |
| Container env | `$.template.containers[0].env` | Environment variables |
| Container ports | `$.template.containers[0].ports` | Container port |
| Scaling | `$.template.scaling` | min/max instances |
| Traffic | `$.traffic` | Traffic split |
| Conditions | `$.conditions` | Ready/ConfigurationsReady/RoutesReady |
| Latest revision | `$.latestReadyRevision` | Latest ready revision name |
| List services | `$.services[]` | Array of services |
| List revisions | `$.revisions[]` | Array of revisions |

## Python SDK Code Snippets

Install: `pip install --quiet --user google-cloud-run`

> **Security**: SDK auto-reads credentials from `GOOGLE_APPLICATION_CREDENTIALS`. NEVER log credential values.

### Create Service

```python
import os
from google.cloud import run_v2

client = run_v2.ServicesClient()
project = os.environ["CLOUDSDK_CORE_PROJECT"]
location = os.environ.get("CLOUDSDK_RUN_LOCATION", "us-central1")
parent = f"projects/{project}/locations/{location}"

service = run_v2.Service(
    name=f"{parent}/services/my-service",
    template=run_v2.RevisionTemplate(
        containers=[run_v2.Container(
            image="us-docker.pkg.dev/my-project/my-repo/my-image:latest",
            ports=[run_v2.ContainerPort(container_port=8080)],
            resources=run_v2.ResourceRequirements(
                limits={"cpu": "1", "memory": "512Mi"},
            ),
        )],
        scaling=run_v2.RevisionScaling(
            min_instance_count=0,
            max_instance_count=1000,
        ),
        max_instance_request_count=80,
        timeout="300s",
    ),
    traffic=[run_v2.TrafficTarget(percent=100, type_="TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST")],
)

operation = client.create_service(parent=parent, service=service, service_id="my-service")
result = operation.result()
print(f"Created: {result.uri}")
```

### Describe Service

```python
import os
from google.cloud import run_v2

client = run_v2.ServicesClient()
name = f"projects/{os.environ['CLOUDSDK_CORE_PROJECT']}/locations/{os.environ.get('CLOUDSDK_RUN_LOCATION', 'us-central1')}/services/my-service"
service = client.get_service(name=name)
print(f"URL: {service.uri}, Image: {service.template.containers[0].image}")
print(f"Traffic: {service.traffic}")
print(f"Conditions: {service.conditions}")
```

### List Services

```python
import os
from google.cloud import run_v2

client = run_v2.ServicesClient()
parent = f"projects/{os.environ['CLOUDSDK_CORE_PROJECT']}/locations/{os.environ.get('CLOUDSDK_RUN_LOCATION', 'us-central1')}"
for svc in client.list_services(parent=parent):
    print(f"{svc.name}: {svc.uri}")
```

### Update Service (Deploy)

```python
import os
from google.cloud import run_v2

client = run_v2.ServicesClient()
name = f"projects/{os.environ['CLOUDSDK_CORE_PROJECT']}/locations/{os.environ.get('CLOUDSDK_RUN_LOCATION', 'us-central1')}/services/my-service"
service = run_v2.Service(
    name=name,
    template=run_v2.RevisionTemplate(
        containers=[run_v2.Container(
            image="us-docker.pkg.dev/my-project/my-repo/my-image:v2",
        )],
    ),
)
operation = client.update_service(service=service)
result = operation.result()
print(f"Deployed: {result.uri}")
```

### Update Traffic

```python
import os
from google.cloud import run_v2

client = run_v2.ServicesClient()
name = f"projects/{os.environ['CLOUDSDK_CORE_PROJECT']}/locations/{os.environ.get('CLOUDSDK_RUN_LOCATION', 'us-central1')}/services/my-service"

# First get current service to preserve spec
service = client.get_service(name=name)
service.traffic = [
    run_v2.TrafficTarget(revision="my-service-00001-xit", percent=80),
    run_v2.TrafficTarget(revision="my-service-00002-xit", percent=20),
]

operation = client.update_service(service=service)
result = operation.result()
print(f"Traffic updated: {result.traffic}")
```

### Delete Service

```python
import os
from google.cloud import run_v2

client = run_v2.ServicesClient()
name = f"projects/{os.environ['CLOUDSDK_CORE_PROJECT']}/locations/{os.environ.get('CLOUDSDK_RUN_LOCATION', 'us-central1')}/services/my-service"
operation = client.delete_service(name=name)
operation.result()
print("Deleted")
```

### List Revisions

```python
import os
from google.cloud import run_v2

client = run_v2.RevisionsClient()
parent = f"projects/{os.environ['CLOUDSDK_CORE_PROJECT']}/locations/{os.environ.get('CLOUDSDK_RUN_LOCATION', 'us-central1')}/services/my-service"
for rev in client.list_revisions(parent=parent):
    print(f"{rev.name}: {rev.conditions}")
```

## Pagination

All list operations support pagination via `page_size` and `page_token` in the request, with `next_page_token` in the response.
