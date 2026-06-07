# gcloud — Cloud IAM CLI

## Conventions
- Always use `--format=json` for machine-parseable output
- Resource names follow: `projects/{project}/roles/{roleId}` or `projects/{project}/serviceAccounts/{email}`
- Use `--project` flag consistently; falls back to `CLOUDSDK_CORE_PROJECT`
- Many IAM operations are synchronous (no polling needed)

## Command Map: IAM Policies

| Goal | gcloud command |
|------|---------------|
| Get project policy | gcloud projects get-iam-policy PROJECT_ID --format=json |
| Set project policy | gcloud projects set-iam-policy PROJECT_ID POLICY_FILE --format=json |
| Dry-run set policy | gcloud projects set-iam-policy PROJECT_ID POLICY_FILE --dry-run --format=json |
| Add binding | gcloud projects add-iam-policy-binding PROJECT_ID --member=MEMBER --role=ROLE --format=json |
| Add binding with condition | gcloud projects add-iam-policy-binding PROJECT_ID --member=MEMBER --role=ROLE --condition=COND --format=json |
| Remove binding | gcloud projects remove-iam-policy-binding PROJECT_ID --member=MEMBER --role=ROLE --format=json |
| Get org policy | gcloud organizations get-iam-policy ORG_ID --format=json |
| Set org policy | gcloud organizations set-iam-policy ORG_ID POLICY_FILE --format=json |
| Add org binding | gcloud organizations add-iam-policy-binding ORG_ID --member=MEMBER --role=ROLE --format=json |
| Get folder policy | gcloud resource-manager folders get-iam-policy FOLDER_ID --format=json |
| Add folder binding | gcloud resource-manager folders add-iam-policy-binding FOLDER_ID --member=MEMBER --role=ROLE --format=json |
| Test permissions | gcloud iam test-iam-permissions RESOURCE --permissions=PERMS --format=json |

## Command Map: Roles

| Goal | gcloud command |
|------|---------------|
| List predefined roles | gcloud iam roles list --format=json |
| List custom roles | gcloud iam roles list --project=PROJECT --format=json |
| Describe role | gcloud iam roles describe ROLE_NAME --format=json |
| Create custom role | gcloud iam roles create ROLE_ID --project=PROJECT --permissions=PERMS --title=TITLE --format=json |
| Update custom role | gcloud iam roles update ROLE_ID --project=PROJECT --add-permissions=PERMS --format=json |
| Delete custom role | gcloud iam roles delete ROLE_ID --project=PROJECT --format=json |
| Undelete custom role | gcloud iam roles undelete ROLE_ID --project=PROJECT --format=json |
| List testable permissions | gcloud iam list-testable-permissions RESOURCE --format=json |

## Command Map: Service Accounts

| Goal | gcloud command |
|------|---------------|
| Create SA | gcloud iam service-accounts create SA_NAME --project=PROJECT --display-name=NAME --format=json |
| List SAs | gcloud iam service-accounts list --project=PROJECT --format=json |
| Describe SA | gcloud iam service-accounts describe SA_EMAIL --project=PROJECT --format=json |
| Delete SA | gcloud iam service-accounts delete SA_EMAIL --project=PROJECT --format=json |
| Disable SA | gcloud iam service-accounts disable SA_EMAIL --project=PROJECT --format=json |
| Enable SA | gcloud iam service-accounts enable SA_EMAIL --project=PROJECT --format=json |
| Create key | gcloud iam service-accounts keys create KEY_FILE --iam-account=SA_EMAIL --project=PROJECT --format=json |
| List keys | gcloud iam service-accounts keys list --iam-account=SA_EMAIL --managed-by=user --project=PROJECT --format=json |
| Delete key | gcloud iam service-accounts keys delete KEY_ID --iam-account=SA_EMAIL --project=PROJECT --format=json |
| Get SA IAM policy | gcloud iam service-accounts get-iam-policy SA_EMAIL --project=PROJECT --format=json |
| Add SA IAM binding | gcloud iam service-accounts add-iam-policy-binding SA_EMAIL --member=MEMBER --role=ROLE --format=json |

## Command Map: Workload Identity

| Goal | gcloud command |
|------|---------------|
| Create pool | gcloud iam workload-identity-pools create POOL_ID --location=global --project=PROJECT --format=json |
| Describe pool | gcloud iam workload-identity-pools describe POOL_ID --location=global --project=PROJECT --format=json |
| List pools | gcloud iam workload-identity-pools list --location=global --project=PROJECT --format=json |
| Delete pool | gcloud iam workload-identity-pools delete POOL_ID --location=global --project=PROJECT --format=json |
| Create OIDC provider | gcloud iam workload-identity-pools providers create-oidc PROVIDER_ID --location=global --workload-identity-pool=POOL_ID --issuer-uri=URI --attribute-mapping=MAP --project=PROJECT --format=json |
| Describe provider | gcloud iam workload-identity-pools providers describe PROVIDER_ID --location=global --workload-identity-pool=POOL_ID --project=PROJECT --format=json |
| List providers | gcloud iam workload-identity-pools providers list --location=global --workload-identity-pool=POOL_ID --project=PROJECT --format=json |
| Delete provider | gcloud iam workload-identity-pools providers delete PROVIDER_ID --location=global --workload-identity-pool=POOL_ID --project=PROJECT --format=json |

## Command Map: IAM Deny

| Goal | gcloud command |
|------|---------------|
| List deny policies | gcloud iam deny-policies list --project=PROJECT --format=json |
| Describe deny | gcloud iam deny-policies describe POLICY_ID --project=PROJECT --format=json |
| Create deny | gcloud iam deny-policies create POLICY_ID --policy-file=FILE --project=PROJECT --format=json |
| Update deny | gcloud iam deny-policies update POLICY_ID --policy-file=FILE --project=PROJECT --format=json |
| Delete deny | gcloud iam deny-policies delete POLICY_ID --project=PROJECT --format=json |

## Command Map: Policy Analyzer

| Goal | gcloud command |
|------|---------------|
| Analyze for principal | gcloud asset analyze-iam-policy --scope=SCOPE --principal=PRINCIPAL --format=json |
| Analyze for permissions | gcloud asset analyze-iam-policy --scope=SCOPE --permissions=PERMS --format=json |
| Analyze for resource | gcloud asset analyze-iam-policy --scope=SCOPE --resource=RESOURCE --format=json |

## Post-Execution Validation Patterns

Use these `jq` commands to validate operation results:

| Operation | Validation Command |
|-----------|-------------------|
| Get IAM Policy | `gcloud projects get-iam-policy PROJECT_ID --format=json | jq '.bindings | length'` |
| Set IAM Policy | `gcloud projects get-iam-policy PROJECT_ID --format=json | jq '.bindings[] | select(.role == "ROLE")'` |
| Create/Update Role | `gcloud iam roles describe ROLE_ID --project=PROJECT --format=json | jq '{name, title, stage, includedPermissions: (.includedPermissions | length)}'` |
| Delete Role | `gcloud iam roles describe ROLE_ID --project=PROJECT --quiet 2>&1 || echo "Role confirmed deleted"` |
| Create SA | `gcloud iam service-accounts describe SA_EMAIL --project=PROJECT --format=json | jq '{name, email, displayName, uniqueId, disabled}'` |
| List SAs | `gcloud iam service-accounts list --project=PROJECT --format=json | jq '.accounts | length'` |
| Create SA Key | `gcloud iam service-accounts keys list --iam-account=SA_EMAIL --managed-by=user --project=PROJECT --format=json` |
| Delete SA Key | `gcloud iam service-accounts keys list --iam-account=SA_EMAIL --managed-by=user --project=PROJECT --format=json | jq -r '.keys[] | .name' | grep KEY_ID || echo "Key confirmed deleted"` |
| Test Permissions | `gcloud iam test-iam-permissions RESOURCE --permissions=PERMS --format=json | jq -r '.permissions[]'` |
| Deny Policy | `gcloud iam deny-policies list --project=PROJECT --format=json | jq '.denyPolicies[] | select(.name | contains("POLICY_ID"))'` |

## CLI vs API Coverage

| Operation | gcloud | Notes |
|-----------|--------|-------|
| IAM policy get/set (project/org/folder) | ✅ | Fully covered |
| IAM binding add/remove | ✅ | Fully covered |
| Conditional bindings | ✅ | Via --condition flag |
| Custom roles CRUD | ✅ | Fully covered |
| Service accounts CRUD | ✅ | Fully covered |
| SA keys CRUD | ✅ | Fully covered |
| SA disable/enable | ✅ | Fully covered |
| Test permissions | ✅ | Fully covered |
| Workload Identity Pools | ✅ | Fully covered |
| IAM Deny Policies | ✅ | gcloud iam deny-policies * |
| Policy Analyzer | ✅ | Via gcloud asset |
| Primitive roles | ⚠️ | Deprecated; use IAM roles instead |