# Monitoring — Cloud IAM

## Key Audit Logs

All IAM changes are recorded in Cloud Audit Logs. Enable Data Access audit logs for IAM to capture read operations.

| Log Type | Method Name | Description |
|----------|-------------|-------------|
| Admin Activity (always on) | `SetIamPolicy` | Policy changes on any resource |
| Admin Activity | `google.iam.admin.v1.CreateRole` | Custom role creation |
| Admin Activity | `google.iam.admin.v1.DeleteRole` | Custom role deletion |
| Admin Activity | `google.iam.admin.v1.UpdateRole` | Custom role modification |
| Admin Activity | `google.iam.admin.v1.CreateServiceAccount` | SA creation |
| Admin Activity | `google.iam.admin.v1.DeleteServiceAccount` | SA deletion |
| Admin Activity | `google.iam.admin.v1.DisableServiceAccount` | SA disable |
| Admin Activity | `google.iam.admin.v1.EnableServiceAccount` | SA enable |
| Admin Activity | `google.iam.admin.v1.CreateServiceAccountKey` | SA key creation |
| Admin Activity | `google.iam.admin.v1.DeleteServiceAccountKey` | SA key deletion |
| Admin Activity | `DenyPolicy.Create` | Deny policy creation |
| Admin Activity | `DenyPolicy.Delete` | Deny policy deletion |
| Data Access (optional) | `GetIamPolicy` | Policy reads |
| Data Access (optional) | `google.iam.admin.v1.GetServiceAccount` | SA reads |

## Viewing Audit Logs

```bash
# Recent IAM policy changes (last 24 hours)
gcloud logging read 'protoPayload.methodName="SetIamPolicy"' \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --limit=20 \
  --format="json" | jq '.[].protoPayload | {method: .methodName, caller: .authenticationInfo.principalEmail, resource: .resourceName, timestamp: .timestamp}'
```

```bash
# Recent SA key creation events
gcloud logging read 'protoPayload.methodName="google.iam.admin.v1.CreateServiceAccountKey"' \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --limit=10 \
  --format=json
```

## Key Metrics

| Metric | Type | Description |
|--------|------|-------------|
| IAM policy change rate | Derived | Count of SetIamPolicy per hour |
| Custom role count | Custom | Number of custom roles per project |
| SA key age | Custom | Age in days per key |
| SA key count per SA | Custom | Number of keys per service account |
| Bindings per policy | Derived | Size of policy bindings array |

## Alert Policy Suggestions

### Alert on SA Key Creation
```bash
gcloud alpha monitoring policies create \
  --display-name="IAM-SA-Key-Created" \
  --condition-filter='protoPayload.methodName="google.iam.admin.v1.CreateServiceAccountKey"' \
  --condition-threshold-value=1 \
  --condition-duration=0s
```

### Alert on Custom Role Deletion
```bash
gcloud alpha monitoring policies create \
  --display-name="IAM-Custom-Role-Deleted" \
  --condition-filter='protoPayload.methodName="google.iam.admin.v1.DeleteRole"' \
  --condition-threshold-value=1 \
  --condition-duration=0s
```

### Alert on IAM Policy Change
```bash
gcloud alpha monitoring policies create \
  --display-name="IAM-Policy-Change" \
  --condition-filter='protoPayload.methodName="SetIamPolicy"' \
  --condition-threshold-value=1 \
  --condition-duration=0s
```

## Anomaly Patterns

| Pattern | Likely Cause |
|---------|--------------|
| Spike in SetIamPolicy calls | Automated script or CI/CD pipeline misconfigured |
| SA key created at unusual hour | Possible unauthorized access |
| Custom role deleted followed by SA delete | Planned decommission or unauthorized cleanup |
| Repeated ABORTED (etag conflict) | Concurrent policy modifications — use locking |
| Policy size growing steadily | Accumulating bindings without cleanup |
| Deny policy blocking legitimate access | Overly broad deny rules |