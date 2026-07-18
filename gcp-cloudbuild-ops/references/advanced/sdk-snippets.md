# SDK Code Snippets — Google Cloud Build

> Provides developers with ready-to-use Python and Go SDK snippets for Cloud Build operations — build submission, trigger CRUD, and worker pool management.

## Table of Contents

1. [Overview](#overview)
2. [Python SDK Setup](#python-sdk-setup)
3. [Go SDK Setup](#go-sdk-setup)
4. [Build Submission](#build-submission)
5. [Build Inspection](#build-inspection)
6. [Trigger CRUD](#trigger-crud)
7. [Worker Pool Management](#worker-pool-management)
8. [Build Retry and Cancel](#build-retry-and-cancel)
9. [See Also](#see-also)

## Overview

Cloud Build SDK snippets provided for:
- **Python**: `google-cloud-build` library
- **Go**: `cloud.google.com/go/cloudbuild/apiv1` library

Both snippets follow the same pattern: create client → build request → execute → handle response.

## Python SDK Setup

```python
# Install: pip install google-cloud-build

from google.cloud import cloudbuild_v1
from google.cloud.devtools import cloudbuild_v1
from google.protobuf import duration_pb2
import datetime
```

## Go SDK Setup

```go
// Install: go get cloud.google.com/go/cloudbuild/apiv1

import (
    "context"
    "fmt"
    "log"

    cloudbuild "cloud.google.com/go/cloudbuild/apiv1"
    "google.golang.org/api/iterator"
    cloudbuildpb "google.golang.org/genproto/googleapis/devtools/cloudbuild/v1"
)
```

## Build Submission

### Python — Submit Build from YAML Config

```python
def submit_build_from_yaml(
    project_id: str,
    yaml_path: str,
    substitutions: dict[str, str] | None = None,
) -> str:
    client = cloudbuild_v1.CloudBuildClient()

    operation = client.submit_build(
        cloudbuild_v1.SubmitBuildRequest(
            project_id=project_id,
            build=cloudbuild_v1.Build(
                source=cloudbuild_v1.Source(
                    storage_source=cloudbuild_v1.StorageSource(
                        bucket=f"{project_id}_cloudbuild",
                        object="source.tar.gz",
                    )
                ),
                steps=[
                    cloudbuild_v1.BuildStep(
                        name="gcr.io/cloud-builders/docker",
                        args=["build", "-t", f"gcr.io/{project_id}/image:$COMMIT_SHA", "."],
                    )
                ],
                artifacts=cloudbuild_v1.Artifacts(
                    images=[f"gcr.io/{project_id}/image:$COMMIT_SHA"],
                ),
                substitutions=substitutions or {},
            ),
        )
    )

    response = operation.result()
    return response.metadata.build.id
```

### Go — Submit Build Programmatically

```go
func submitBuild(ctx context.Context, projectID string) (string, error) {
    client, err := cloudbuild.NewClient(ctx)
    if err != nil {
        return "", fmt.Errorf("NewClient: %w", err)
    }
    defer client.Close()

    req := &cloudbuildpb.SubmitBuildRequest{
        ProjectId: projectID,
        Build: &cloudbuildpb.Build{
            Source: &cloudbuildpb.Source{
                StorageSource: &cloudbuildpb.StorageSource{
                    Bucket: fmt.Sprintf("%s_cloudbuild", projectID),
                    Object: "source.tar.gz",
                },
            },
            Steps: []*cloudbuildpb.BuildStep{
                {
                    Name: "gcr.io/cloud-builders/docker",
                    Args: []string{"build", "-t", fmt.Sprintf("gcr.io/%s/image:$COMMIT_SHA", projectID), "."},
                },
            },
            Images: []string{fmt.Sprintf("gcr.io/%s/image:$COMMIT_SHA", projectID)},
        },
    }

    op, err := client.SubmitBuild(ctx, req)
    if err != nil {
        return "", fmt.Errorf("SubmitBuild: %w", err)
    }

    resp, err := op.Wait(ctx)
    if err != nil {
        return "", fmt.Errorf("op.Wait: %w", err)
    }

    return resp.Metadata.Build.Id, nil
}
```

### Python — Submit with Timeout and Machine Type

```python
def submit_build_with_options(
    project_id: str,
    image_name: str,
    machine_type: str = "N1_HIGHCPU_8",
    timeout: int = 1200,
) -> str:
    client = cloudbuild_v1.CloudBuildClient()

    operation = client.submit_build(
        cloudbuild_v1.SubmitBuildRequest(
            project_id=project_id,
            build=cloudbuild_v1.Build(
                steps=[
                    cloudbuild_v1.BuildStep(
                        name="gcr.io/cloud-builders/docker",
                        args=["build", "-t", image_name, "."],
                    )
                ],
                images=[image_name],
                options=cloudbuild_v1.BuildOptions(
                    machine_type=cloudbuild_v1.BuildOptions.MachineType.Value(machine_type),
                    logging=cloudbuild_v1.BuildOptions.Logging.GCS_ONLY,
                ),
                timeout=duration_pb2.Duration(seconds=timeout),
            ),
        )
    )

    response = operation.result()
    return response.metadata.build.id
```

## Build Inspection

### Python — List Recent Builds

```python
def list_builds(project_id: str, limit: int = 50) -> list[dict]:
    client = cloudbuild_v1.CloudBuildClient()

    builds = []
    for build in client.list_builds(
        cloudbuild_v1.ListBuildsRequest(project_id=project_id),
        limit=limit,
    ):
        builds.append({
            "id": build.id,
            "status": build.status.name,
            "create_time": str(build.create_time),
            "finish_time": str(build.finish_time) if build.finish_time else None,
            "log_url": build.log_url,
        })
    return builds
```

### Go — List Builds by Status

```go
func listBuildsByStatus(ctx context.Context, projectID, status string) ([]*cloudbuildpb.Build, error) {
    client, err := cloudbuild.NewClient(ctx)
    if err != nil {
        return nil, fmt.Errorf("NewClient: %w", err)
    }
    defer client.Close()

    filter := fmt.Sprintf('status="%s"', status)
    req := &cloudbuildpb.ListBuildsRequest{
        ProjectId: projectID,
        Filter:    &filter,
    }

    var builds []*cloudbuildpb.Build
    it := client.ListBuilds(ctx, req)
    for {
        build, err := it.Next()
        if err == iterator.Done {
            break
        }
        if err != nil {
            return nil, fmt.Errorf("ListBuilds: %w", err)
        }
        builds = append(builds, build)
    }
    return builds, nil
}
```

### Python — Get Build Details

```python
def get_build_details(project_id: str, build_id: str) -> dict:
    client = cloudbuild_v1.CloudBuildClient()

    build = client.get_build(
        cloudbuild_v1.GetBuildRequest(project_id=project_id, id=build_id)
    )

    return {
        "id": build.id,
        "status": build.status.name,
        "steps": [
            {"name": s.name, "status": s.status.name if s.status else None}
            for s in build.steps
        ],
        "source": {
            "storage_source": build.source.storage_source.object if build.source else None
        },
        "artifacts": {
            "images": [a for a in build.artifacts.images] if build.artifacts else []
        },
        "timing": {
            name: {"start": str(t.start_time), "end": str(t.end_time)}
            for name, t in build.timing.items()
        } if build.timing else {},
    }
```

## Trigger CRUD

### Python — Create Build Trigger

```python
def create_trigger(
    project_id: str,
    trigger_id: str,
    repo_name: str,
    branch_pattern: str,
    yaml_path: str,
) -> str:
    client = cloudbuild_v1.CloudBuildClient()

    trigger = cloudbuild_v1.Trigger(
        name=trigger_id,
        github=cloudbuild_v1.GitHubEventsConfig(
            push=cloudbuild_v1.PushFilter(
                branch=branch_pattern,
            ),
            installation_id=123456789,  # GitHub App installation ID
        ),
        build=cloudbuild_v1.Build(
            filename=yaml_path,
            steps=[
                cloudbuild_v1.BuildStep(
                    name="gcr.io/cloud-builders/docker",
                    args=["build", "-t", f"gcr.io/{project_id}/image:$COMMIT_SHA", "."],
                )
            ],
        ),
    )

    created = client.create_build_trigger(
        cloudbuild_v1.CreateBuildTriggerRequest(
            project_id=project_id,
            trigger=trigger,
        )
    )
    return created.name
```

### Go — Create Build Trigger

```go
func createTrigger(ctx context.Context, projectID, triggerID, repoName, branch, filename string) (string, error) {
    client, err := cloudbuild.NewClient(ctx)
    if err != nil {
        return "", fmt.Errorf("NewClient: %w", err)
    }
    defer client.Close()

    trigger := &cloudbuildpb.Trigger{
        Name: triggerID,
        Github: &cloudbuildpb.GitHubEventsConfig{
            Push: &cloudbuildpb.PushFilter{
                Branch: branch,
            },
            InstallationId: 123456789,
        },
        Build: &cloudbuildpb.Build{
            Filename: filename,
        },
    }

    req := &cloudbuildpb.CreateBuildTriggerRequest{
        ProjectId: projectID,
        Trigger:   trigger,
    }

    resp, err := client.CreateBuildTrigger(ctx, req)
    if err != nil {
        return "", fmt.Errorf("CreateBuildTrigger: %w", err)
    }

    return resp.Name, nil
}
```

### Python — List Build Triggers

```python
def list_triggers(project_id: str) -> list[dict]:
    client = cloudbuild_v1.CloudBuildClient()

    triggers = []
    for trigger in client.list_build_triggers(
        cloudbuild_v1.ListBuildTriggersRequest(project_id=project_id)
    ):
        triggers.append({
            "id": trigger.id,
            "name": trigger.name,
            "description": trigger.description,
            "disabled": trigger.disabled,
            "github": {
                "branch": trigger.github.push.branch if trigger.github else None,
            } if trigger.github else None,
        })
    return triggers
```

### Python — Delete Build Trigger

```python
def delete_trigger(project_id: str, trigger_id: str) -> None:
    client = cloudbuild_v1.CloudBuildClient()

    client.delete_build_trigger(
        cloudbuild_v1.DeleteBuildTriggerRequest(
            project_id=project_id,
            trigger_id=trigger_id,
        )
    )
```

## Worker Pool Management

### Python — Create Private Worker Pool

```python
def create_worker_pool(
    project_id: str,
    pool_id: str,
    location: str = "us-central1",
    machine_type: str = "e2-standard-4",
    disk_size_gb: int = 100,
) -> str:
    client = cloudbuild_v1.CloudBuildClient()

    pool = cloudbuild_v1.WorkerPool(
        name=f"projects/{project_id}/locations/{location}/workerPools/{pool_id}",
        display_name=f"Worker pool {pool_id}",
        worker_config=cloudbuild_v1.WorkerConfig(
            machine_type=machine_type,
            disk_size_gb=disk_size_gb,
            network="default",
        ),
        private_pool_v1=cloudbuild_v1.PrivatePoolV1Config(
            worker_pool_name=pool_id,
        ),
    )

    op = client.create_worker_pool(
        cloudbuild_v1.CreateWorkerPoolRequest(
            parent=f"projects/{project_id}/locations/{location}",
            worker_pool=pool,
            worker_pool_id=pool_id,
        )
    )
    op.result()
    return pool.name
```

### Go — Create Private Worker Pool

```go
func createWorkerPool(ctx context.Context, projectID, poolID, location, machineType string) (string, error) {
    client, err := cloudbuild.NewClient(ctx)
    if err != nil {
        return "", fmt.Errorf("NewClient: %w", err)
    }
    defer client.Close()

    parent := fmt.Sprintf("projects/%s/locations/%s", projectID, location)
    name := fmt.Sprintf("%s/workerPools/%s", parent, poolID)

    pool := &cloudbuildpb.WorkerPool{
        Name: name,
        WorkerConfig: &cloudbuildpb.WorkerConfig{
            MachineType: machineType,
            DiskSizeGb:  100,
            Network:     "default",
        },
    }

    req := &cloudbuildpb.CreateWorkerPoolRequest{
        Parent:       parent,
        WorkerPool:   pool,
        WorkerPoolId: poolID,
    }

    op, err := client.CreateWorkerPool(ctx, req)
    if err != nil {
        return "", fmt.Errorf("CreateWorkerPool: %w", err)
    }

    resp, err := op.Wait(ctx)
    if err != nil {
        return "", fmt.Errorf("op.Wait: %w", err)
    }

    return resp.WorkerPool.Name, nil
}
```

### Python — List Worker Pools

```python
def list_worker_pools(project_id: str, location: str = "us-central1") -> list[dict]:
    client = cloudbuild_v1.CloudBuildClient()

    parent = f"projects/{project_id}/locations/{location}"
    pools = []

    for pool in client.list_worker_pools(
        cloudbuild_v1.ListWorkerPoolsRequest(parent=parent)
    ):
        pools.append({
            "id": pool.name.split("/")[-1],
            "name": pool.name,
            "display_name": pool.display_name,
            "state": pool.state.name if pool.state else None,
            "machine_type": pool.worker_config.machine_type if pool.worker_config else None,
            "disk_size_gb": pool.worker_config.disk_size_gb if pool.worker_config else None,
        })
    return pools
```

### Python — Delete Worker Pool

```python
def delete_worker_pool(project_id: str, pool_id: str, location: str = "us-central1") -> None:
    client = cloudbuild_v1.CloudBuildClient()

    client.delete_worker_pool(
        cloudbuild_v1.DeleteWorkerPoolRequest(
            name=f"projects/{project_id}/locations/{location}/workerPools/{pool_id}",
        )
    )
```

## Build Retry and Cancel

### Python — Retry Failed Build

```python
def retry_build(project_id: str, build_id: str) -> str:
    client = cloudbuild_v1.CloudBuildClient()

    operation = client.retry_build(
        cloudbuild_v1.RetryBuildRequest(project_id=project_id, id=build_id)
    )

    response = operation.result()
    return response.metadata.build.id
```

### Python — Cancel Running Build

```python
def cancel_build(project_id: str, build_id: str) -> None:
    client = cloudbuild_v1.CloudBuildClient()

    client.cancel_build(
        cloudbuild_v1.CancelBuildRequest(project_id=project_id, id=build_id)
    )
```

### Go — Cancel Build

```go
func cancelBuild(ctx context.Context, projectID, buildID string) error {
    client, err := cloudbuild.NewClient(ctx)
    if err != nil {
        return fmt.Errorf("NewClient: %w", err)
    }
    defer client.Close()

    req := &cloudbuildpb.CancelBuildRequest{
        ProjectId: projectID,
        Id:        buildID,
    }

    _, err = client.CancelBuild(ctx, req)
    return err
}
```

## See Also

- [Cloud Build API Reference](https://cloud.google.com/build/docs/api/reference/rest)
- [Python SDK Documentation](https://cloud.google.com/python/docs/reference/cloudbuild/latest)
- [Go SDK Documentation](https://pkg.go.dev/cloud.google.com/go/cloudbuild/apiv1)
- [Cloud Build Examples](https://cloud.google.com/build/docs/samples)
