# API & SDK — Cloud IAM

## REST API
- IAM Admin API: https://iam.googleapis.com/$discovery/rest?version=v1
- Cloud Resource Manager API: https://cloudresourcemanager.googleapis.com/$discovery/rest?version=v3
- Cloud Asset API: https://cloudasset.googleapis.com/$discovery/rest?version=v1

### Base URLs
- IAM: https://iam.googleapis.com/v1/
- Resource Manager: https://cloudresourcemanager.googleapis.com/v3/
- Cloud Asset: https://cloudasset.googleapis.com/v1/

## Operations Map

### IAM Roles

| Goal | REST Method | Python SDK Method |
|------|------------|-------------------|
| List roles | GET /v1/{parent}/roles | IAMClient.list_roles() |
| Get role | GET /v1/{name} | IAMClient.get_role() |
| Create role | POST /v1/{parent}/roles | IAMClient.create_role() |
| Update role | PATCH /v1/{name} | IAMClient.update_role() |
| Delete role | DELETE /v1/{name} | IAMClient.delete_role() |
| Undelete role | POST /v1/{name}:undelete | IAMClient.undelete_role() |
| Query testable permissions | POST /v1/permissions:queryTestablePermissions | IAMClient.query_testable_permissions() |

### Service Accounts

| Goal | REST Method | Python SDK Method |
|------|------------|-------------------|
| Create SA | POST /v1/{name}/serviceAccounts | IAMClient.create_service_account() |
| List SAs | GET /v1/{name}/serviceAccounts | IAMClient.list_service_accounts() |
| Get SA | GET /v1/{name} | IAMClient.get_service_account() |
| Delete SA | DELETE /v1/{name} | IAMClient.delete_service_account() |
| Disable SA | POST /v1/{name}:disable | IAMClient.disable_service_account() |
| Enable SA | POST /v1/{name}:enable | IAMClient.enable_service_account() |
| Create key | POST /v1/{name}/keys | IAMClient.create_service_account_key() |
| List keys | GET /v1/{name}/keys | IAMClient.list_service_account_keys() |
| Delete key | DELETE /v1/{name}/keys/{keyId} | IAMClient.delete_service_account_key() |
| Get key | GET /v1/{name}/keys/{keyId} | IAMClient.get_service_account_key() |
| Upload public key | POST /v1/{name}:upload | IAMClient.upload_service_account_key() |

### IAM Policies (via Resource Manager)

| Goal | REST Method | Python SDK Method |
|------|------------|-------------------|
| Get policy | POST /v3/{resource}:getIamPolicy | ProjectsClient.get_iam_policy() |
| Set policy | POST /v3/{resource}:setIamPolicy | ProjectsClient.set_iam_policy() |
| Test permissions | POST /v3/{resource}:testIamPermissions | ProjectsClient.test_iam_permissions() |

### Workload Identity

| Goal | REST Method | Python SDK Method |
|------|------------|-------------------|
| Create pool | POST /v1/{parent}/workloadIdentityPools | Not yet GA in Python SDK |
| List pools | GET /v1/{parent}/workloadIdentityPools | Not yet GA in Python SDK |
| Create OIDC provider | POST /v1/{parent}/providers | Not yet GA in Python SDK |
| Delete provider | DELETE /v1/{parent} | Not yet GA in Python SDK |

### IAM Deny Policies

| Goal | REST Method | Python SDK Method |
|------|------------|-------------------|
| List deny policies | GET /v1/{parent}/denyPolicies | IAMClient.list_deny_policies() |
| Get deny policy | GET /v1/{name} | IAMClient.get_deny_policy() |
| Create deny policy | POST /v1/{parent}/denyPolicies | IAMClient.create_deny_policy() |
| Update deny policy | PATCH /v1/{name} | IAMClient.update_deny_policy() |
| Delete deny policy | DELETE /v1/{name} | IAMClient.delete_deny_policy() |

### Policy Analyzer (via Cloud Asset)

| Goal | REST Method | Python SDK Method |
|------|------------|-------------------|
| Analyze IAM policy | POST /v1/{scope}:analyzeIamPolicy | AssetServiceClient.analyze_iam_policy() |
| Search IAM policies | POST /v1/{scope}:searchAllIamPolicies | AssetServiceClient.search_all_iam_policies() |

## Python SDK — Code Snippets

### Get IAM Policy
```python
import os
from google.cloud import resourcemanager_v3 as resource_manager_v3

project = os.environ["CLOUDSDK_CORE_PROJECT"]
client = resource_manager_v3.ProjectsClient()
resource = f"projects/{project}"
policy = client.get_iam_policy(request={"resource": resource})
print(f"Etag: {policy.etag}")
for binding in policy.bindings:
    print(f"  Role: {binding.role}, Members: {binding.members}")
```

### Add IAM Policy Binding
```python
import os
from google.cloud import resourcemanager_v3 as resource_manager_v3
from google.iam.v1 import policy_pb2

project = os.environ["CLOUDSDK_CORE_PROJECT"]
client = resource_manager_v3.ProjectsClient()
resource = f"projects/{project}"
policy = client.get_iam_policy(request={"resource": resource})
new_binding = policy_pb2.Binding()
new_binding.role = "roles/compute.admin"
new_binding.members.append("user:admin@example.com")
policy.bindings.append(new_binding)
client.set_iam_policy(request={"resource": resource, "policy": policy})
print("Binding added")
```

### Create Custom Role
```python
import os
from google.cloud import iam_admin_v1
from google.cloud.iam_admin_v1 import types

project = os.environ["CLOUDSDK_CORE_PROJECT"]
client = iam_admin_v1.IAMClient()
role = types.Role()
role.title = "My Custom Role"
role.description = "Custom role for specific permissions"
role.included_permissions = ["compute.instances.list", "compute.instances.get"]
role.stage = types.Role.RoleLaunchStage.GA
request = types.CreateRoleRequest(
    parent=f"projects/{project}",
    role_id="myCustomRole",
    role=role)
response = client.create_role(request=request)
print(f"Created role: {response.name}")
```

### Delete Custom Role
```python
import os
from google.cloud import iam_admin_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
client = iam_admin_v1.IAMClient()
request = types.DeleteRoleRequest(
    name=f"projects/{project}/roles/{{user.role_id}}",
    etag="{{output.role_etag}}")
response = client.delete_role(request=request)
print(f"Deleted role: {response.name}")
```

### Create Service Account
```python
import os
from google.cloud import iam_admin_v1
from google.cloud.iam_admin_v1 import types

project = os.environ["CLOUDSDK_CORE_PROJECT"]
client = iam_admin_v1.IAMClient()
sa = types.ServiceAccount()
sa.display_name = "My Service Account"
sa.description = "Created by gcp-skills"
request = types.CreateServiceAccountRequest(
    name=f"projects/{project}",
    account_id="my-sa",
    service_account=sa)
response = client.create_service_account(request=request)
print(f"Created: {response.email}")
```

### List Service Accounts
```python
import os
from google.cloud import iam_admin_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
client = iam_admin_v1.IAMClient()
request = types.ListServiceAccountsRequest(name=f"projects/{project}")
for sa in client.list_service_accounts(request=request):
    print(f"{sa.email} ({sa.display_name}) — {sa.disabled}")
```

### List SA Keys
```python
import os
from google.cloud import iam_admin_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
client = iam_admin_v1.IAMClient()
request = types.ListKeysRequest(
    name=f"projects/{project}/serviceAccounts/{os.environ['SA_EMAIL']}",
    key_types=[types.ListKeysRequest.KeyType.USER_MANAGED])
for key in client.list_service_account_keys(request=request):
    print(f"Key: {key.name.split('/')[-1]} validUntil={key.valid_before_time}")
```

### Delete SA Key
```python
import os
from google.cloud import iam_admin_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
client = iam_admin_v1.IAMClient()
request = types.DeleteServiceAccountKeyRequest(
    name=f"projects/{project}/serviceAccounts/{os.environ['SA_EMAIL']}/keys/{{user.key_id}}")
client.delete_service_account_key(request=request)
print(f"Deleted key: {{user.key_id}}")
```

### Delete Service Account
```python
import os
from google.cloud import iam_admin_v1

project = os.environ["CLOUDSDK_CORE_PROJECT"]
client = iam_admin_v1.IAMClient()
request = types.DeleteServiceAccountRequest(
    name=f"projects/{project}/serviceAccounts/{{user.service_account_email}}")
client.delete_service_account(request=request)
print(f"Deleted SA: {{user.service_account_email}}")
```

### Test IAM Permissions
```python
import os
from google.cloud import resourcemanager_v3 as resource_manager_v3

project = os.environ["CLOUDSDK_CORE_PROJECT"]
client = resource_manager_v3.ProjectsClient()
request = dict(
    resource=f"projects/{project}",
    permissions=["compute.instances.list", "compute.instances.get"])
response = client.test_iam_permissions(request=request)
print(f"Granted permissions: {response.permissions}")
```

## Key JSON Paths (Centralized)

| Operation | JSON Path | Description |
|-----------|-----------|-------------|
| Get policy | $.bindings[].{role,members,condition} | Policy binding list |
| Create role | $.{name,title,stage,etag} | Role metadata |
| List roles | $.roles[].{name,title,stage} | Role list items |
| Create SA | $.{name,email,uniqueId,displayName} | SA metadata |
| List SAs | $.accounts[].{email,displayName,disabled} | SA list items |
| Create SA key | $.{name,privateKeyData,keyAlgorithm,validBeforeTime} | Key metadata + private key (single response) |
| List SA keys | $.keys[].{name,validAfterTime,validBeforeTime,keyAlgorithm} | Key metadata (no private key data) |
| Test permissions | $.permissions[] | List of granted permissions |
| Analyze policy | $.mainAccesses[].{principal,accessState} | Access analysis results |
| Deny policy | $.denyPolicies[].{name,denyRules} | Deny policy list |
| Workload pool | $.name, $.state | Pool metadata |