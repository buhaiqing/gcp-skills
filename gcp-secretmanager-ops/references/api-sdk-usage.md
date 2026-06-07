# API & SDK Usage — Cloud Secret Manager

## REST API Overview

- **Base URL:** `https://secretmanager.googleapis.com/v1`
- **Discovery:** https://secretmanager.googleapis.com/$discovery/rest?version=v1
- **Auth:** Bearer token via `gcloud auth print-access-token`

## Operation Map

| Operation | Method | Endpoint |
|-----------|--------|----------|
| Create Secret | POST | `/v1/projects/{project}/secrets` |
| Describe Secret | GET | `/v1/projects/{project}/secrets/{secret}` |
| Update Secret | PATCH | `/v1/projects/{project}/secrets/{secret}` |
| Delete Secret | DELETE | `/v1/projects/{project}/secrets/{secret}` |
| List Secrets | GET | `/v1/projects/{project}/secrets` |
| Add Version | POST | `/v1/projects/{project}/secrets/{secret}:addVersion` |
| Access Version | GET | `/v1/projects/{project}/secrets/{secret}/versions/{version}:access` |
| Describe Version | GET | `/v1/projects/{project}/secrets/{secret}/versions/{version}` |
| List Versions | GET | `/v1/projects/{project}/secrets/{secret}/versions` |
| Disable Version | POST | `/v1/projects/{project}/secrets/{secret}/versions/{version}:disable` |
| Enable Version | POST | `/v1/projects/{project}/secrets/{secret}/versions/{version}:enable` |
| Destroy Version | POST | `/v1/projects/{project}/secrets/{secret}/versions/{version}:destroy` |
| Set IAM Policy | POST | `/v1/projects/{project}/secrets/{secret}:setIamPolicy` |
| Get IAM Policy | POST | `/v1/projects/{project}/secrets/{secret}:getIamPolicy` |

## Python SDK (Primary)

### Installation
```bash
pip install google-cloud-secret-manager
```

### Create Secret
```python
from google.cloud import secretmanager_v1 as sm
client = sm.SecretManagerServiceClient()
parent = f"projects/{project_id}"
secret = sm.Secret(replication=sm.Replication(automatic=sm.Replication.Automatic()))
response = client.create_secret(request={"parent": parent, "secret_id": secret_id, "secret": secret})
# Add version
version = client.add_secret_version(request={"parent": response.name, "payload": sm.SecretPayload(data=payload_bytes)})
```

### Access Secret Version
```python
name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
response = client.access_secret_version(request={"name": name})
payload = response.payload.data.decode("UTF-8")
```

### List Secrets
```python
for secret in client.list_secrets(request={"parent": f"projects/{project_id}"}):
    print(f"{secret.name} created={secret.create_time}")
```

### Delete Secret
```python
name = f"projects/{project_id}/secrets/{secret_id}"
client.delete_secret(request={"name": name})
```

## Pagination

All list operations support `page_size` and `page_token`:
```python
request = {"parent": f"projects/{project_id}", "page_size": 50}
while True:
    response = client.list_secrets(request=request)
    for secret in response:
        print(secret.name)
    if response.next_page_token:
        request["page_token"] = response.next_page_token
    else:
        break
```

## Go SDK (Secondary)

### Import
```go
import (
    secretmanager "cloud.google.com/go/secretmanager/apiv1"
    smpb "cloud.google.com/go/secretmanager/apiv1/secretmanagerpb"
)
```

### Create Secret
```go
client, _ := secretmanager.NewClient(ctx)
defer client.Close()
req := &smpb.CreateSecretRequest{
    Parent:   fmt.Sprintf("projects/%s", projectID),
    SecretId: secretID,
    Secret:   &smpb.Secret{Replication: &smpb.Replication{Automatic: &smpb.Replication_Automatic{}}},
}
resp, err := client.CreateSecret(ctx, req)
```

### Access Secret Version
```go
req := &smpb.AccessSecretVersionRequest{Name: fmt.Sprintf("projects/%s/secrets/%s/versions/%s", projectID, secretID, versionID)}
resp, err := client.AccessSecretVersion(ctx, req)
payload := string(resp.Payload.Data)
```

## Error Mapping

| gRPC Code | HTTP Status | Meaning |
|-----------|-------------|---------|
| INVALID_ARGUMENT | 400 | Request validation failed |
| PERMISSION_DENIED | 403 | Insufficient IAM permissions |
| NOT_FOUND | 404 | Resource does not exist |
| ALREADY_EXISTS | 409 | Secret name already exists |
| FAILED_PRECONDITION | 412 | Secret/version in wrong state |
| RESOURCE_EXHAUSTED | 429 | Quota exceeded or payload too large |
| ABORTED | 409 | Concurrent modification conflict |
| DEADLINE_EXCEEDED | 504 | Request timeout |
| INTERNAL | 500 | Server error |
| UNAVAILABLE | 503 | Service temporarily unavailable |
