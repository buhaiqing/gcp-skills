# Workload Identity Federation — Troubleshooting Guide

## Table of Contents

- [Overview](#overview)
- [Diagnostic Commands](#diagnostic-commands)
- [Common Issues](#common-issues)
- [Resolution Steps](#resolution-steps)
- [Audit Logging](#audit-logging)
- [Best Practices for Monitoring](#best-practices-for-monitoring)

---

## Overview

Workload Identity Federation enables workloads to impersonate IAM service accounts without long-lived keys. Issues typically fall into three categories: principal impersonation errors, service account key rotation problems, and OIDC token validation failures.

---

## Diagnostic Commands

```bash
# Verify current authentication state
gcloud auth list

# Check service account IAM policy
gcloud iam service-accounts get-iam-policy "{{user.service_account_email}}" --format="json"

# Describe workload identity pool
gcloud iam workload-identity-pools describe "{{user.pool_id}}" --location="global" --format="json"

# List workload identity pools
gcloud iam workload-identity-pools list --location="global" --format="json"

# Describe OIDC provider
gcloud iam workload-identity-pools providers describe "{{user.provider_id}}" --workload-identity-pool="{{user.pool_id}}" --location="global" --format="json"

# List providers in pool
gcloud iam workload-identity-pools providers list --workload-identity-pool="{{user.pool_id}}" --location="global" --format="json"

# Check token creation (STS)
gcloud auth print-access-token --audiences="https://example.com"
```

---

## Common Issues

### 1. Principal Impersonation Errors

| Error Code | Symptom | Likely Cause |
|------------|---------|--------------|
| `IAM_1001` | "Permission 'iam.serviceAccounts.actAs' denied" | Missing `roles/iam.workloadIdentityUser` binding |
| `IAM_1002` | "Principal cannot impersonate Service Account" | Invalid `serviceAccount:` member format in binding |
| `IAM_1003` | "Workload identity pool not found" | Pool ID mismatch or deleted pool |
| `IAM_1004` | "Service account not found" | GSA email typo or project mismatch |

### 2. Service Account Key Rotation Problems

| Error Code | Symptom | Likely Cause |
|------------|---------|--------------|
| `KEY_2001` | "Key not found" after rotation | Old key ID referenced in workload |
| `KEY_2002` | "All keys disabled" | All keys explicitly disabled |
| `KEY_2003` | "Key expired" | Key past `validBeforeTime` |
| `KEY_2004` | "Key algorithm not supported" | Workload using deprecated RSA-1024 |

### 3. OIDC Token Validation Failures

| Error Code | Symptom | Likely Cause |
|------------|---------|--------------|
| `OIDC_3001` | "Issuer mismatch" | Provider `issuer-uri` does not match token `iss` |
| `OIDC_3002` | "Audience mismatch" | Token audience != provider allowed audience |
| `OIDC_3003` | "Subject claim missing" | `google.subject` mapping not defined |
| `OIDC_3004` | "Condition expression evaluated to false" | Attribute condition failed |
| `OIDC_3005` | "Token expired" | Token `exp` claim in past |

---

## Resolution Steps

### Issue: Permission 'iam.serviceAccounts.actAs' denied

**Diagnosis:**
```bash
# Check current bindings on GSA
gcloud iam service-accounts get-iam-policy "{{user.service_account_email}}" --format="json" | jq '.bindings[] | select(.role == "roles/iam.workloadIdentityUser")'
```

**Resolution:**
```bash
# Add workloadIdentityUser binding
gcloud iam service-accounts add-iam-policy-binding "{{user.service_account_email}}" \
  --role="roles/iam.workloadIdentityUser" \
  --member="serviceAccount:PROJECT_ID.svc.id.goog[NAMESPACE/KSA_NAME]"
```

**Validate:**
```bash
gcloud iam service-accounts get-iam-policy "{{user.service_account_email}}" --format="json" | jq '.bindings[] | select(.role == "roles/iam.workloadIdentityUser")'
```

---

### Issue: Workload identity pool not found

**Diagnosis:**
```bash
# List all pools
gcloud iam workload-identity-pools list --location="global" --format="json" | jq '.workloadIdentityPools[].name'

# Describe specific pool
gcloud iam workload-identity-pools describe "{{user.pool_id}}" --location="global" --format="json"
```

**Resolution:**
```bash
# Recreate pool if missing
gcloud iam workload-identity-pools create "{{user.pool_id}}" \
  --location="global" \
  --display-name="Workload Identity Pool" \
  --description="Recreated pool for workloads"
```

**Validate:**
```bash
gcloud iam workload-identity-pools describe "{{user.pool_id}}" --location="global" --format="json" | jq '.name'
```

---

### Issue: OIDC issuer mismatch

**Diagnosis:**
```bash
# Check provider issuer-uri
gcloud iam workload-identity-pools providers describe "{{user.provider_id}}" \
  --workload-identity-pool="{{user.pool_id}}" --location="global" --format="json" | jq '.oidc.issuerUri'

# Verify token issuer (from workload logs)
# kubectl exec -it POD_NAME -- cat /var/run/secrets/tokens/auditor 2>/dev/null || echo "Token not available"
```

**Resolution:**
```bash
# Update provider issuer-uri if external IdP
gcloud iam workload-identity-pools providers update-oidc "{{user.provider_id}}" \
  --workload-identity-pool="{{user.pool_id}}" \
  --location="global" \
  --issuer-uri="https://YOUR_IDP.example.com"
```

---

### Issue: Attribute condition evaluated to false

**Diagnosis:**
```bash
# Check provider attribute conditions
gcloud iam workload-identity-pools providers describe "{{user.provider_id}}" \
  --workload-identity-pool="{{user.pool_id}}" --location="global" --format="json" | jq '.attributeConditions'

# Check attribute mappings
gcloud iam workload-identity-pools providers describe "{{user.provider_id}}" \
  --workload-identity-pool="{{user.pool_id}}" --location="global" --format="json" | jq '.attributeMappings'
```

**Resolution:**
```bash
# Update attribute condition to match IdP claims
gcloud iam workload-identity-pools providers update-oidc "{{user.provider_id}}" \
  --workload-identity-pool="{{user.pool_id}}" \
  --location="global" \
  --attribute-condition="assertion.claims.environment == 'production'"
```

---

### Issue: Service account key still being used after WIF setup

**Diagnosis:**
```bash
# Check if workload has GOOGLE_APPLICATION_CREDENTIALS env var set
kubectl get deployment DEPLOYMENT_NAME -n NAMESPACE -o jsonpath='{.spec.template.spec.containers[*].env[*]}'

# List active keys on GSA
gcloud iam service-accounts keys list --iam-account="{{user.service_account_email}}" --managed-by="user" --format="json"
```

**Resolution:**
```bash
# Disable key-based auth on GSA
gcloud iam service-accounts update "{{user.service_account_email}}" --disable-key-creation

# Remove GOOGLE_APPLICATION_CREDENTIALS from workload
kubectl set env deployment/DEPLOYMENT_NAME GOOGLE_APPLICATION_CREDENTIALS- --namespace=NAMESPACE
```

**Validate:**
```bash
# Verify key creation disabled
gcloud iam service-accounts describe "{{user.service_account_email}}" --format="json" | jq '.disableKeyCreation'
```

---

## Audit Logging

### Enable Cloud Audit Logs

```bash
# Ensure Data Access audit logs are enabled for IAM API
gcloud services list --available | grep iam

# Check current audit config
gcloud projects get-iam-policy "{{env.CLOUDSDK_CORE_PROJECT}}" --format="json" | jq '.auditConfigs'
```

### Query Audit Logs for WIF Events

```bash
# Find impersonation events
gcloud logging read 'resource.type="service_account" AND protoPayload.methodName="google.iam.admin.v1.SetIamPolicy"' --freshness=24h --format="json"

# Find token exchange failures
gcloud logging read 'resource.type="sts.googleapis.com" AND protoPayload.status.code!="0"' --freshness=24h --format="json"

# Find workload identity pool operations
gcloud logging read 'resource.type="iam.googleapis.com" AND protoPayload.methodName:"workloadIdentity"' --freshness=24h --format="json"
```

### Common Audit Log Events

| Event | Log Filter | Severity |
|-------|------------|----------|
| SA key created | `protoPayload.methodName="google.iam.admin.v1.CreateServiceAccountKey"` | NOTICE |
| SA key deleted | `protoPayload.methodName="google.iam.admin.v1.DeleteServiceAccountKey"` | WARNING |
| IAM binding added | `protoPayload.methodName="SetIamPolicy"` | NOTICE |
| Token exchange | `protoPayload.methodName="google.loggingSTS.v2.TokenService.ExchangeToken"` | NOTICE |
| Token exchange failure | `protoPayload.status.code!="0"` | ERROR |

---

## Best Practices for Monitoring

### 1. Key Lifecycle Monitoring

```bash
# List keys nearing expiration (within 30 days)
gcloud iam service-accounts keys list --iam-account="{{user.service_account_email}}" --managed-by="user" --format="json" | jq '[.keys[] | select(.validBeforeTime | fromdateiso8601 < (now + 2592000))]'
```

### 2. WIF Binding Audit

```bash
# Check all workload identity bindings for a project
for sa in $(gcloud iam service-accounts list --format="json" | jq -r '.accounts[].email'); do
  bindings=$(gcloud iam service-accounts get-iam-policy "$sa" --format="json" | jq '.bindings[] | select(.role == "roles/iam.workloadIdentityUser")')
  if [ -n "$bindings" ]; then
    echo "SA: $sa"
    echo "$bindings" | jq '.members'
  fi
done
```

### 3. Alert on Failed Token Exchanges

```bash
# Example log-based alert (use with Cloud Monitoring)
# Metric: log-based metric on `sts.googleapis.com/TokenService.ExchangeToken` failures
# Threshold: > 5 failures in 5 minutes
```

### 4. Regular Rotation Schedule

| Rotation Type | Frequency | Command |
|---------------|-----------|---------|
| SA key audit | Monthly | `gcloud iam service-accounts keys list --iam-account=...` |
| WIF binding review | Quarterly | Review all `workloadIdentityUser` bindings |
| Pool configuration review | Semi-annual | Audit pool/provider settings |
| IdP certificate rotation | Per IdP policy | Update provider if IdP certs rotate |

---

## See Also

- [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)
- [GKE Workload Identity](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity)
- [Workload Identity Deep Dive (GKE)](../gcp-gke-ops/references/advanced/workload-identity-deep-dive.md)
- [IAM Troubleshooting](../troubleshooting.md)
