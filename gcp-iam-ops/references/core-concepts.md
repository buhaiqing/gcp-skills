# Core Concepts — Cloud IAM

## Architecture

Google Cloud IAM (Identity and Access Management) provides unified access control for all GCP resources. It uses a policy-based model where policies are attached to resources (projects, folders, organizations, and individual services) and define who (principal) has what access (role) on which resource.

### Key Components

| Component | Description | Scope |
|-----------|-------------|-------|
| **Principal (Member)** | Identity that can be granted access: Google Account, Service Account, Google Group, G Suite/Cloud Identity domain, or allUsers/allAuthenticatedUsers | Global |
| **Role** | Collection of permissions. Three types: Basic (primitive), Predefined (fine-grained, Google-managed), Custom (user-defined) | Project, Folder, Organization |
| **Permission** | Granular action on a GCP resource (e.g., `compute.instances.create`) | Resource-specific |
| **Policy** | Collection of bindings that associate one or more members with a role, optionally with a condition | Resource |
| **Binding** | Maps a set of members to a single role (with optional condition) | Resource |
| **Condition** | CEL expression that enforces conditional access (e.g., time-based, resource-based) | Binding |
| **Etag** | Policy version identifier for read-modify-write concurrency control | Policy |
| **Service Account** | Special Google account that belongs to an application or VM, not an individual user | Project |
| **Workload Identity Pool** | Maps external identities (AWS, OIDC, SAML) to GCP service accounts | Global |
| **IAM Deny Policy** | Explicit deny rules that override allow policies | Project, Folder, Organization |
| **Policy Analyzer** | Tool to discover which principals have access to which resources | Organization, Folder, Project |

## Role Types

| Type | Description | Can Create? | Scope |
|------|-------------|-------------|-------|
| **Basic (Primitive)** | Owner, Editor, Viewer (broad, legacy). NOT recommended | No | Project |
| **Predefined** | Fine-grained, Google-managed (e.g., `roles/compute.admin`) | No | Organization/Project |
| **Custom** | User-defined, project/org-level | Yes | Project, Organization |

## Policy Structure

```json
{
  "version": 1,
  "etag": "BwW1Z2Y3X4=",
  "bindings": [
    {
      "role": "roles/storage.objectViewer",
      "members": [
        "user:alice@example.com",
        "serviceAccount:my-sa@project.iam.gserviceaccount.com"
      ],
      "condition": {
        "title": "limited_access",
        "expression": "request.time < timestamp('2026-07-07T00:00:00Z')"
      }
    }
  ]
}
```

**Policy versioning:**
- `version: 1` — No conditions, no deny policies
- `version: 3` — Conditions and deny policies supported

## Quotas and Limits

| Limit | Value | Description |
|-------|-------|-------------|
| Custom roles per project | 300 | Maximum custom roles in a project |
| Custom roles per org | 300 | Maximum custom roles in an organization |
| Permissions per custom role | 3000 | Maximum permissions in a single role |
| Service accounts per project | 100 | Default, can be increased |
| SA keys per service account | 10 | Maximum keys per service account |
| Policy size | 250KB | Maximum IAM policy JSON size |
| Bindings per policy | 1500 | Approximate practical limit |
| Workload Identity Pools per project | 10 | Per project |
| Providers per pool | 20 | Per workload identity pool |

Check current quotas:
```bash
# IAM quotas are enforced server-side; check project limits
gcloud projects describe "{{env.CLOUDSDK_CORE_PROJECT}}" --format="json"
```

## Dependencies

| Depend On | Reason |
|-----------|--------|
| Cloud Resource Manager | Project/folder/org hierarchy for policy attachment |
| Cloud Asset Inventory | Policy Analyzer queries (cloudasset.googleapis.com) |
| IAM API | All IAM operations (iam.googleapis.com) |
| Cloud KMS (indirect) | KMS key IAM delegated to gcp-kms-ops |

## Prerequisites

### 1. Install gcloud CLI
```bash
if ! command -v gcloud &> /dev/null; then
    curl https://sdk.cloud.google.com | bash 2>/dev/null \
    || (echo "Trying apt..." && sudo apt-get update && sudo apt-get install -y google-cloud-sdk) \
    || (echo "Trying manual..." \
        && wget -q https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-linux-x86_64.tar.gz \
        && tar -xf google-cloud-cli-*.tar.gz && ./google-cloud-sdk/install.sh --quiet)
    exec -l $SHELL
    gcloud init
fi
gcloud config list
gcloud auth application-default print-access-token --quiet &>/dev/null && echo "Auth OK"
gcloud iam service-accounts list --limit=1 --format="json" &>/dev/null && echo "IAM API OK"
```

### 2. Bootstrap Go Runtime (JIT SDK fallback)
> See AGENTS.md §0.2 — Go JIT bootstrap is defined once at repo level, not duplicated here.

### 3. Configure Credentials
```bash
export GOOGLE_APPLICATION_CREDENTIALS="{{env.GOOGLE_APPLICATION_CREDENTIALS}}"
export CLOUDSDK_CORE_PROJECT="{{env.CLOUDSDK_CORE_PROJECT}}"
gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS" 2>/dev/null \
|| gcloud auth login --quiet
gcloud config set project "$CLOUDSDK_CORE_PROJECT"
```

### 4. Enable Required APIs
```bash
gcloud services enable iam.googleapis.com cloudresourcemanager.googleapis.com cloudasset.googleapis.com
```

> **Security:** Never commit service account keys to version control. All credentials use `{{env.*}}` placeholders.

## SPOF Analysis

| Scenario | Impact | Mitigation |
|----------|--------|------------|
| SA key compromised | Unauthorized access to resources | Key rotation; use Workload Identity Federation |
| Last admin removed from org | Orphaned org with no admin | Maintain break-glass accounts; use org policies |
| Custom role misconfigured | Over-privileged / under-privileged access | Test with TestIamPermissions; stage: ALPHA first |
| SA deleted with active workloads | Service outage | Warn before delete; check active keys and bindings |
| Quota exhausted (custom roles) | Can't create new roles | Review and clean up unused custom roles |
| IAM Deny policy over-restrictive | Legitimate users locked out | Use dry-run mode; audit before applying |