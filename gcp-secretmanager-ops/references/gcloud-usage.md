# gcloud Usage — Cloud Secret Manager

## Command Map

### Secret Lifecycle

| Operation | Command | Notes |
|-----------|---------|-------|
| Create | `gcloud secrets create NAME --data-file=FILE --replication-policy=automatic` | --replication-policy: automatic\|user-managed |
| Describe | `gcloud secrets describe NAME --format=json` | Returns secret details |
| List | `gcloud secrets list --filter="labels.env=prod" --format=json` | Supports filtering |
| Update | `gcloud secrets update NAME --rotation-period=30d --next-rotation-time=TIME` | Rotation, labels |
| Delete | `gcloud secrets delete NAME` | Requires confirmation |

### Version Operations

| Operation | Command | Notes |
|-----------|---------|-------|
| Add | `gcloud secrets versions add NAME --data-file=FILE` | Creates new version |
| Access | `gcloud secrets versions access VERSION --secret=NAME` | Returns payload |
| List | `gcloud secrets versions list NAME --format=json` | Shows version states |
| Describe | `gcloud secrets versions describe VERSION --secret=NAME` | Version details |
| Disable | `gcloud secrets versions disable VERSION --secret=NAME` | Disables access |
| Enable | `gcloud secrets versions enable VERSION --secret=NAME` | Re-enables access |
| Destroy | `gcloud secrets versions destroy VERSION --secret=NAME` | Irreversible |

### IAM & Notifications

| Operation | Command | Notes |
|-----------|---------|-------|
| Add IAM | `gcloud secrets add-iam-policy-binding NAME --member=MEMBER --role=ROLE` | Grant access |
| Remove IAM | `gcloud secrets remove-iam-policy-binding NAME --member=MEMBER --role=ROLE` | Revoke access |
| Get Policy | `gcloud secrets get-iam-policy NAME` | Current policy |
| Add Topic | `gcloud secrets add-topic NAME --topic=TOPIC_RESOURCE` | Pub/Sub notification |
| Remove Topic | `gcloud secrets remove-topic NAME --topic=TOPIC_RESOURCE` | Remove notification |

### Replication

| Operation | Command | Notes |
|-----------|---------|-------|
| Set Replication | `gcloud secrets replication set NAME --replication-policy=automatic` | Change policy |
| Add Location | `gcloud secrets replication add-location NAME --location=LOC` | User-managed only |
| Remove Location | `gcloud secrets replication remove-location NAME --location=LOC` | User-managed only |

## Common Patterns

### Idempotent Create
```bash
if ! gcloud secrets describe "my-secret" --quiet 2>/dev/null; then
    gcloud secrets create "my-secret" --data-file=- <<< "value"
fi
```

### List with Labels Filter
```bash
gcloud secrets list --filter="labels.environment=production" --format="table(name,createTime)"
```

### Access Latest Version to File
```bash
gcloud secrets versions access latest --secret="my-secret" > /tmp/secret-value
```

### Batch Create from File
```bash
while IFS=',' read -r name data; do
    gcloud secrets create "$name" --data-file=- <<< "$data"
done < secrets.csv
```

## Coverage Gaps (SDK-Only Operations)

| Operation | gcloud Support | SDK Alternative |
|-----------|---------------|-----------------|
| Set rotation schedule | Supported via `gcloud secrets update` | — |
| Conditional IAM bindings | Limited | Use REST API or Python SDK |
| Bulk version operations | Manual per-version | Use Python SDK for batch |
