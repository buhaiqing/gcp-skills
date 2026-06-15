# API & SDK — Google Cloud Composer

## REST API

- Discovery doc: `https://composer.googleapis.com/$discovery/rest?version=v2`
- Base URL: `https://composer.googleapis.com/v2/`

## SDK Operations Map

| Goal | REST Method & Path | Go SDK Method |
|------|-------------------|---------------|
| Create Environment | `POST /v2/projects/{project}/locations/{location}/environments` | `CreateEnvironment` |
| Describe Environment | `GET /v2/projects/{project}/locations/{location}/environments/{environment}` | `GetEnvironment` |
| Update Environment | `PATCH /v2/projects/{project}/locations/{location}/environments/{environment}` | `UpdateEnvironment` |
| Delete Environment | `DELETE /v2/projects/{project}/locations/{location}/environments/{environment}` | `DeleteEnvironment` |
| List Environments | `GET /v2/projects/{project}/locations/{location}/environments` | `ListEnvironments` |
| List Operations | `GET /v2/projects/{project}/locations/{location}/operations` | `ListOperations` |
| Get Operation | `GET /v2/projects/{project}/locations/{location}/operations/{operation}` | `GetOperation` |

## Request / Response Notes

- **Long-running operations**: Create/Update/Delete return operations that must be polled
- **Environment size**: Use `Environment.Size` enum (SMALL, MEDIUM, LARGE)
- **Software config**: Specify Airflow and Python versions
- **Workloads**: Optional workload configuration for environment

## Go SDK Package

```go
import (
    composer "cloud.google.com/go/composer/apiv1"
    composerpb "cloud.google.com/go/composer/apiv1/composerpb"
)
```

## Python SDK Package

```python
from google.cloud import composer_v1
```
