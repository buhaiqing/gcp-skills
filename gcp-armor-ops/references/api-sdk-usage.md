# API & SDK — Google Cloud Armor

## REST API

- Discovery doc: `https://compute.googleapis.com/$discovery/rest?version=v1`
- Base URL: `https://compute.googleapis.com/compute/v1/`

## SDK Operations Map

| Goal | REST Method & Path | Go SDK Method |
|------|-------------------|---------------|
| Create Policy | `POST /v1/projects/{project}/global/securityPolicies` | `InsertSecurityPolicy` |
| Describe Policy | `GET /v1/projects/{project}/global/securityPolicies/{securityPolicy}` | `GetSecurityPolicy` |
| Update Policy | `PATCH /v1/projects/{project}/global/securityPolicies/{securityPolicy}` | `PatchSecurityPolicy` |
| Delete Policy | `DELETE /v1/projects/{project}/global/securityPolicies/{securityPolicy}` | `DeleteSecurityPolicy` |
| List Policies | `GET /v1/projects/{project}/global/securityPolicies` | `ListSecurityPolicies` |
| Add Rule | `POST /v1/projects/{project}/global/securityPolicies/{securityPolicy}/addRule` | `AddRuleSecurityPolicy` |
| Update Rule | `POST /v1/projects/{project}/global/securityPolicies/{securityPolicy}/patchRule` | `PatchRuleSecurityPolicy` |
| Remove Rule | `POST /v1/projects/{project}/global/securityPolicies/{securityPolicy}/removeRule` | `RemoveRuleSecurityPolicy` |
| List Rules | `GET /v1/projects/{project}/global/securityPolicies/{securityPolicy}/rules` | `ListSecurityPolicyRules` |

## Request / Response Notes

- **Fingerprint required**: Updates require `fingerprint` from describe (optimistic locking)
- **Rule priority**: Must be unique within a policy
- **Expression**: CEL (Common Expression Language) syntax
- **Pagination**: `pageToken` in request, `nextPageToken` in response

## Go SDK Package

```go
import (
    compute "cloud.google.com/go/compute/apiv1"
    computepb "cloud.google.com/go/compute/apiv1/computepb"
)
```

## Python SDK Package

```python
from google.cloud import compute_v1
```
