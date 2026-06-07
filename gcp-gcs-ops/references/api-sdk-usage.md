# API & SDK — Cloud Storage

## REST API
- Discovery doc: https://storage.googleapis.com/$discovery/rest?version=v1
- Base URL: https://storage.googleapis.com/storage/v1/

## Operations Map

| Goal | REST Method | Go SDK Method |
|------|------------|---------------|
| Create bucket | POST /storage/v1/b?project={p} | BucketHandle.Create() |
| Get bucket | GET /storage/v1/b/{b} | BucketHandle.Attrs() |
| List buckets | GET /storage/v1/b?project={p} | Client.Buckets() |
| Update bucket | PATCH /storage/v1/b/{b} | BucketHandle.Update() |
| Delete bucket | DELETE /storage/v1/b/{b} | BucketHandle.Delete() |
| Get IAM policy | GET /storage/v1/b/{b}/iam | BucketHandle.IAM().Policy() |
| Set IAM policy | PUT /storage/v1/b/{b}/iam | BucketHandle.IAM().SetPolicy() |
| List objects | GET /storage/v1/b/{b}/o | BucketHandle.Objects() |
| Get object | GET /storage/v1/b/{b}/o/{o} | ObjectHandle.Attrs() |
| Upload object | POST /upload/storage/v1/b/{b}/o | ObjectHandle.NewWriter() |
| Download object | GET /storage/v1/b/{b}/o/{o}?alt=media | ObjectHandle.NewReader() |
| Copy object | POST /storage/v1/b/{b}/o/{o}/copy | ObjectHandle.CopyTo() |
| Delete object | DELETE /storage/v1/b/{b}/o/{o} | ObjectHandle.Delete() |
| Compose objects | POST /storage/v1/b/{b}/o/{o}/compose | ObjectHandle.ComposeFrom() |
| Lock retention | POST /storage/v1/b/{b}/lockRetentionPolicy | BucketHandle.LockRetentionPolicy() |
| Get signed URL | Via XML API | ObjectHandle.SignedURL() |
| Get lifecycle | GET /storage/v1/b/{b}?fields=lifecycle | BucketAttrs.Lifecycle |
| Set lifecycle | PATCH /storage/v1/b/{b} | BucketHandle.Update() |

## Python SDK Code Snippets

### Create Bucket
```python
# create_bucket.py — REST: POST /storage/v1/b?project={project}
import os
from google.cloud import storage

project = os.environ["CLOUDSDK_CORE_PROJECT"]
bucket_name = os.environ.get("GCS_BUCKET_NAME", "my-unique-bucket")

client = storage.Client(project=project)
bucket = client.bucket(bucket_name)
bucket.storage_class = "STANDARD"
bucket.location = "US"
bucket.iam_configuration.uniform_bucket_level_access_enabled = True
bucket.iam_configuration.public_access_prevention = "enforced"

bucket = client.create_bucket(bucket)
print(f"Created bucket: {bucket.name} at {bucket.self_link}")
```

### Describe Bucket
```python
# describe_bucket.py
import os
from google.cloud import storage
client = storage.Client(project=os.environ["CLOUDSDK_CORE_PROJECT"])
bucket = client.get_bucket("{{user.bucket_name}}")
print(f"Name: {bucket.name}")
print(f"Location: {bucket.location}")
print(f"Storage Class: {bucket.storage_class}")
print(f"Versioning: {bucket.versioning_enabled}")
print(f"Labels: {bucket.labels}")
```

### List Buckets
```python
# list_buckets.py
import os
from google.cloud import storage
client = storage.Client(project=os.environ["CLOUDSDK_CORE_PROJECT"])
for bucket in client.list_buckets():
    print(f"{bucket.name} ({bucket.location}, {bucket.storage_class})")
```

### Update Bucket
```python
# update_bucket.py
import os
from google.cloud import storage
client = storage.Client(project=os.environ["CLOUDSDK_CORE_PROJECT"])
bucket = client.get_bucket("{{user.bucket_name}}")
bucket.versioning_enabled = True
bucket.labels = {"env": "dev", "app": "web"}
bucket.patch()
print(f"Updated bucket: {bucket.name}")
```

### Delete Bucket
```python
# delete_bucket.py
import os
from google.cloud import storage
client = storage.Client(project=os.environ["CLOUDSDK_CORE_PROJECT"])
bucket = client.get_bucket("{{user.bucket_name}}")
bucket.delete()
print(f"Deleted bucket: {{user.bucket_name}}")
```

### Upload Object
```python
# upload_object.py
import os
from google.cloud import storage
client = storage.Client(project=os.environ["CLOUDSDK_CORE_PROJECT"])
bucket = client.bucket("{{user.bucket_name}}")
blob = bucket.blob("{{user.object_name}}")
blob.upload_from_filename("{{user.source_file}}")
print(f"Uploaded {{user.source_file}} to gs://{{user.bucket_name}}/{{user.object_name}}")
```

### Download Object
```python
# download_object.py
import os
from google.cloud import storage
client = storage.Client(project=os.environ["CLOUDSDK_CORE_PROJECT"])
bucket = client.bucket("{{user.bucket_name}}")
blob = bucket.blob("{{user.object_name}}")
blob.download_to_filename("{{user.destination_file}}")
print(f"Downloaded to {{user.destination_file}}")
```

### Delete Object
```python
# delete_object.py
import os
from google.cloud import storage
client = storage.Client(project=os.environ["CLOUDSDK_CORE_PROJECT"])
bucket = client.bucket("{{user.bucket_name}}")
blob = bucket.blob("{{user.object_name}}")
blob.delete()
print(f"Deleted object: gs://{{user.bucket_name}}/{{user.object_name}}")
```

### Compose Objects
```python
# compose_objects.py
import os
from google.cloud import storage
client = storage.Client(project=os.environ["CLOUDSDK_CORE_PROJECT"])
bucket = client.bucket("{{user.bucket_name}}")
sources = [bucket.blob("{{user.object1}}"), bucket.blob("{{user.object2}}")]
destination = bucket.blob("{{user.composed_object}}")
destination.compose(sources)
print(f"Composed objects into gs://{{user.bucket_name}}/{{user.composed_object}}")
```

### Set Retention Policy
```python
# set_retention.py
import os
from google.cloud import storage
client = storage.Client(project=os.environ["CLOUDSDK_CORE_PROJECT"])
bucket = client.get_bucket("{{user.bucket_name}}")
bucket.retention_policy = storage.bucket.RetentionPolicy(retention_period={{user.retention_period}})
bucket.patch()
print(f"Set retention period of {bucket.retention_policy.retention_period}s on {bucket.name}")
```

### Lock Retention Policy (with metageneration)
```python
# lock_retention.py
import os
from google.cloud import storage
client = storage.Client(project=os.environ["CLOUDSDK_CORE_PROJECT"])
bucket = client.get_bucket("{{user.bucket_name}}")
# Fetch current metageneration for precondition
bucket.reload()
metageneration = bucket.metageneration
print(f"[DIAG] Metageneration: {metageneration}")
bucket.lock_retention_policy()
print(f"Retention policy LOCKED permanently on {bucket.name}")
```

### Set Bucket IAM
```python
# set_bucket_iam.py
import os
from google.cloud import storage
client = storage.Client(project=os.environ["CLOUDSDK_CORE_PROJECT"])
bucket = client.get_bucket("{{user.bucket_name}}")
policy = bucket.get_iam_policy()
policy.bindings.append({
    "role": "{{user.role}}",
    "members": ["{{user.member}}"]
})
bucket.set_iam_policy(policy)
print(f"Set IAM policy on {bucket.name}")
```

### Set Lifecycle Rules
```python
# set_lifecycle.py
import os, json
from google.cloud import storage
client = storage.Client(project=os.environ["CLOUDSDK_CORE_PROJECT"])
bucket = client.get_bucket("{{user.bucket_name}}")
rules = [
    {"action": {"type": "Delete"}, "condition": {"age": 365}},
    {"action": {"type": "SetStorageClass", "storageClass": "NEARLINE"},
     "condition": {"age": 30, "matches_storage_class": ["STANDARD"]}}
]
bucket.lifecycle_rules = rules
bucket.patch()
print(f"Updated lifecycle rules for {bucket.name}")
```

## Go SDK Script Template

```go
// main.go (generated dynamically in /tmp/gcp-sdk-workspace)
package main

import (
    "context"
    "fmt"
    "log"
    "os"

    "cloud.google.com/go/storage"
    "google.golang.org/api/option"
)

func main() {
    ctx := context.Background()
    project := os.Getenv("CLOUDSDK_CORE_PROJECT")
    creds := os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")

    client, err := storage.NewClient(ctx, option.WithCredentialsFile(creds))
    if err != nil { log.Fatalf("NewClient: %v", err) }
    defer client.Close()

    // Example: Create bucket
    bucket := client.Bucket("{{user.bucket_name}}")
    attrs := &storage.BucketAttrs{
        Name:                     "{{user.bucket_name}}",
        Location:                 "{{user.location:-US}}",
        StorageClass:             "{{user.storage_class:-STANDARD}}",
        UniformBucketLevelAccess: storage.UniformBucketLevelAccess{Enabled: true},
        PublicAccessPrevention:   storage.PublicAccessPreventionEnforced,
    }
    if err := bucket.Create(ctx, project, attrs); err != nil {
        log.Fatalf("Create: %v", err)
    }
    fmt.Printf("Created bucket: gs://{{user.bucket_name}}\n")
}
```

> ⚠️ Never output credential values in logs or fmt.Println. Go SDK config structs can leak — prohibit such output.

## Key JSON Paths (Centralized)

| Operation | JSON Path | Description |
|-----------|-----------|-------------|
| Create/Update bucket | $.name | Bucket name |
| Describe bucket | $.{name,location,storageClass,versioning,encryption,lifecycle,retentionPolicy,iamConfiguration} | Bucket details |
| List buckets | $.items[].{name,location,storageClass} | Bucket list |
| List objects | $.items[].{name,size,contentType,updated,storageClass,generation} | Object list |
| Get object | $.{name,size,md5Hash,crc32c,generation,metageneration,storageClass} | Object metadata |
| Get IAM policy | $.{bindings[],etag,version} | Bucket IAM |
| Retention policy | $.retentionPolicy.{retentionPeriod,effectiveTime,isLocked} | Retention details |
| Lifecycle | $.lifecycle.rule[].{action,condition} | Lifecycle rules |