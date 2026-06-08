# API & SDK Usage — Cloud Functions

## REST API Reference

- **Discovery doc**: `https://cloudfunctions.googleapis.com/$discovery/rest?version=v2beta`
- **Base URL**: `https://cloudfunctions.googleapis.com/v2beta/`
- **Resource path pattern**: `projects/{project}/locations/{location}/functions/{function}`

## SDK Operations Map

| Goal | REST Method & Path | Python SDK Method | Go SDK Method |
|------|-------------------|-------------------|---------------|
| Deploy (create) | `POST /v2beta/projects/{project}/locations/{location}/functions` | `FunctionServiceClient.create_function()` | `FunctionClient.CreateFunction()` |
| Deploy (update) | `PATCH /v2beta/projects/{project}/locations/{location}/functions/{function}` | `FunctionServiceClient.update_function()` | `FunctionClient.UpdateFunction()` |
| Describe | `GET /v2beta/projects/{project}/locations/{location}/functions/{function}` | `FunctionServiceClient.get_function()` | `FunctionClient.GetFunction()` |
| List | `GET /v2beta/projects/{project}/locations/{location}/functions` | `FunctionServiceClient.list_functions()` | `FunctionClient.ListFunctions()` |
| Delete | `DELETE /v2beta/projects/{project}/locations/{location}/functions/{function}` | `FunctionServiceClient.delete_function()` | `FunctionClient.DeleteFunction()` |
| Generate Upload URL | `POST /v2beta/projects/{project}/locations/{location}/functions:generateUploadUrl` | `FunctionServiceClient.generate_upload_url()` | `FunctionClient.GenerateUploadUrl()` |
| Invoke (HTTP) | N/A (use serviceConfig.uri) | HTTP call to function URL | HTTP call to function URL |

## Request / Response Notes

### Deploy (Create) Request Body

```json
{
  "name": "projects/{project}/locations/{location}/functions/{function_id}",
  "build_config": {
    "runtime": "python312",
    "entry_point": "my_function",
    "source": {
      "storage_source": {
        "bucket": "gcf-v2-sources-{project}-{location}",
        "object": "function-source-{uuid}"
      }
    }
  },
  "service_config": {
    "max_instance_count": 100,
    "min_instance_count": 0,
    "available_memory": "256Mi",
    "timeout_seconds": 60,
    "ingress_settings": "ALLOW_ALL",
    "environment_variables": {"KEY": "value"}
  }
}
```

### Describe Response (key fields)

```json
{
  "name": "projects/my-project/locations/us-central1/functions/my-function",
  "state": "ACTIVE",
  "build_config": {
    "runtime": "python312",
    "entry_point": "my_function"
  },
  "service_config": {
    "uri": "https://my-function-xyz.uc.a.run.app",
    "available_memory": "256Mi",
    "timeout_seconds": 60,
    "max_instance_count": 100,
    "min_instance_count": 0
  },
  "update_time": "2026-06-08T10:00:00.000Z"
}
```

### Event Trigger (additional fields)

```json
{
  "event_trigger": {
    "trigger_region": "us-central1",
    "event_type": "google.cloud.storage.object.v1.final",
    "event_filters": [
      {"attribute": "type", "value": "google.cloud.storage.object.v1.final"},
      {"attribute": "bucket", "value": "my-bucket"}
    ],
    "service_account_email": "sa@project.iam.gserviceaccount.com"
  }
}
```

## Python SDK — Operation Examples

### Install

```bash
pip install google-cloud-functions
```

### Create HTTP Function

```python
import os
from google.cloud import functions_v2
from google.cloud.functions_v2 import types

client = functions_v2.FunctionServiceClient()
project = os.environ["CLOUDSDK_CORE_PROJECT"]
location = "us-central1"
parent = f"projects/{project}/locations/{location}"

function = types.Function(
    name=f"{parent}/functions/my-http-function",
    build_config=types.BuildConfig(
        runtime="python312",
        entry_point="hello_http",
        source=types.Source(
            storage_source=types.StorageSource(
                bucket="gcf-v2-sources",
            ),
        ),
    ),
    service_config=types.ServiceConfig(
        max_instance_count=100,
        min_instance_count=0,
        available_memory="256Mi",
        timeout_seconds=60,
        ingress_settings=types.ServiceConfig.IngressSettings.ALLOW_ALL,
    ),
)

operation = client.create_function(parent=parent, function=function)
result = operation.result()  # Wait for LRO
print(f"Deployed: {result.service_config.uri}")
```

### Create Event-Triggered Function

```python
function = types.Function(
    name=f"{parent}/functions/my-event-function",
    build_config=types.BuildConfig(
        runtime="python312",
        entry_point="handle_gcs_event",
        source=types.Source(
            storage_source=types.StorageSource(
                bucket="gcf-v2-sources",
            ),
        ),
    ),
    service_config=types.ServiceConfig(
        max_instance_count=3000,
        min_instance_count=0,
        available_memory="512Mi",
        timeout_seconds=300,
        service_account_email="my-sa@my-project.iam.gserviceaccount.com",
    ),
    event_trigger=types.EventTrigger(
        event_type="google.cloud.storage.object.v1.final",
        event_filters=[
            types.EventFilter(attribute="type", value="google.cloud.storage.object.v1.final"),
            types.EventFilter(attribute="bucket", value="my-trigger-bucket"),
        ],
        service_account_email="my-sa@my-project.iam.gserviceaccount.com",
    ),
)

operation = client.create_function(parent=parent, function=function)
result = operation.result()
print(f"Deployed: {result.name}")
```

### Describe Function

```python
name = f"projects/{project}/locations/{location}/functions/my-function"
function = client.get_function(name=name)
print(f"State: {function.state}")
print(f"URL: {function.service_config.uri}")
print(f"Memory: {function.service_config.available_memory}")
```

### List Functions

```python
parent = f"projects/{project}/locations/{location}"
functions = client.list_functions(parent=parent)
for f in functions:
    print(f"{f.name}: {types.Function.State(f.state).name} -> {f.service_config.uri}")
```

### Update Function

```python
function = types.Function(
    name=f"projects/{project}/locations/{location}/functions/my-function",
    service_config=types.ServiceConfig(
        max_instance_count=200,
        available_memory="512Mi",
        timeout_seconds=120,
    ),
)

operation = client.update_function(function=function, update_mask="service_config.max_instance_count,service_config.available_memory,service_config.timeout_seconds")
result = operation.result()
print(f"Updated: {result.name}")
```

### Delete Function

```python
name = f"projects/{project}/locations/{location}/functions/my-function"
operation = client.delete_function(name=name)
operation.result()  # Wait for LRO
print("Deleted successfully")
```

## Go SDK — Operation Examples

### Install

```bash
go get cloud.google.com/go/functions/v2
```

### Create Function

```go
package main

import (
    "context"
    "fmt"
    "log"
    "os"

    functions "cloud.google.com/go/functions/v2"
    functionspb "cloud.google.com/go/functions/v2/apiv2/functionspb"
)

func main() {
    ctx := context.Background()
    client, err := functions.NewClient(ctx)
    if err != nil {
        log.Fatalf("Failed to create client: %v", err)
    }
    defer client.Close()

    project := os.Getenv("CLOUDSDK_CORE_PROJECT")
    location := "us-central1"
    parent := fmt.Sprintf("projects/%s/locations/%s", project, location)

    function := &functionspb.Function{
        Name: fmt.Sprintf("%s/functions/my-function", parent),
        BuildConfig: &functionspb.BuildConfig{
            Runtime:    "python312",
            EntryPoint: "hello_http",
            Source: &functionspb.Source{
                StorageSource: &functionspb.StorageSource{
                    Bucket: "gcf-v2-sources",
                },
            },
        },
        ServiceConfig: &functionspb.ServiceConfig{
            MaxInstanceCount:  100,
            MinInstanceCount:  0,
            AvailableMemory:   "256Mi",
            TimeoutSeconds:    60,
            IngressSettings:   functionspb.ServiceConfig_ALLOW_ALL,
        },
    }

    op, err := client.CreateFunction(ctx, &functionspb.CreateFunctionRequest{
        Parent:   parent,
        Function: function,
    })
    if err != nil {
        log.Fatalf("Failed to create function: %v", err)
    }

    result, err := op.Wait(ctx)
    if err != nil {
        log.Fatalf("Deployment failed: %v", err)
    }

    fmt.Printf("Deployed: %s\n", result.ServiceConfig.GetUri())
}
```

### Describe Function

```go
name := fmt.Sprintf("projects/%s/locations/%s/functions/my-function", project, location)
function, err := client.GetFunction(ctx, &functionspb.GetFunctionRequest{
    Name: name,
})
if err != nil {
    log.Fatalf("Failed to get function: %v", err)
}

fmt.Printf("State: %s\n", function.State)
fmt.Printf("URL: %s\n", function.ServiceConfig.GetUri())
```

### List Functions

```go
it := client.ListFunctions(ctx, &functionspb.ListFunctionsRequest{
    Parent: fmt.Sprintf("projects/%s/locations/%s", project, location),
})
for {
    f, err := it.Next()
    if err == iterator.Done {
        break
    }
    if err != nil {
        log.Fatalf("Failed to list functions: %v", err)
    }
    fmt.Printf("%s: %s\n", f.Name, f.State)
}
```

### Delete Function

```go
op, err := client.DeleteFunction(ctx, &functionspb.DeleteFunctionRequest{
    Name: fmt.Sprintf("projects/%s/locations/%s/functions/my-function", project, location),
})
if err != nil {
    log.Fatalf("Failed to delete function: %v", err)
}

if err := op.Wait(ctx); err != nil {
    log.Fatalf("Delete failed: %v", err)
}
fmt.Println("Deleted successfully")
```

## Long-Running Operation (LRO) Polling

Deploy and delete operations return LROs. The SDK `operation.result()` / `op.Wait()` methods handle polling automatically.

For manual polling:

```python
# Python
from google.api_core import operation
op = client.create_function(parent=parent, function=function)
result = op.result(timeout=600)  # 10 minute timeout
```

```go
// Go
op, _ := client.CreateFunction(ctx, req)
result, err := op.Wait(ctx)  // Blocks until done or context cancelled
```

## Error Mapping

| gRPC Status | HTTP Status | SDK Exception Type |
|-------------|-------------|-------------------|
| `INVALID_ARGUMENT` | 400 | `google.api_core.exceptions.InvalidArgument` |
| `PERMISSION_DENIED` | 403 | `google.api_core.exceptions.PermissionDenied` |
| `NOT_FOUND` | 404 | `google.api_core.exceptions.NotFound` |
| `ALREADY_EXISTS` | 409 | `google.api_core.exceptions.AlreadyExists` |
| `FAILED_PRECONDITION` | 412 | `google.api_core.exceptions.FailedPrecondition` |
| `RESOURCE_EXHAUSTED` | 429 | `google.api_core.exceptions.ResourceExhausted` |
| `ABORTED` | 409 | `google.api_core.exceptions.Aborted` |
| `DEADLINE_EXCEEDED` | 504 | `google.api_core.exceptions.DeadlineExceeded` |
| `INTERNAL` | 500 | `google.api_core.exceptions.InternalServerError` |
| `UNAVAILABLE` | 503 | `google.api_core.exceptions.ServiceUnavailable` |

## Pagination

List operations support pagination via `page_size` and `page_token`:

```python
# Python
functions = client.list_functions(parent=parent, page_size=50)
for page in functions.pages:
    for f in page:
        print(f.name)
```

```go
// Go
it := client.ListFunctions(ctx, &functionspb.ListFunctionsRequest{
    Parent:   parent,
    PageSize: 50,
})
```

> **TE-1**: For current API methods and request/response schemas, query the discovery doc: `curl -s "https://cloudfunctions.googleapis.com/$discovery/rest?version=v2beta" | jq '.resources'` instead of hardcoding.
