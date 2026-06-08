---
name: billing-gcloud-usage
description: Full gcloud CLI command map, execution flows, validation, and recovery for Cloud Billing operations

<!---
load_condition: "[CLI 操作时加载]"
token_cost_estimate: "~3000 tokens"
dependencies: []
--->
---

# gcloud — Cloud Billing CLI

## Conventions (agent execution)

- Always use `--format=json` for machine-parseable output.
- Use `jq` for field extraction from JSON output.
- Budget commands are under `gcloud alpha billing budgets` (alpha track).
- Billing account commands are under `gcloud billing accounts`.
- Project billing info is under `gcloud billing projects`.
- Export commands use `gcloud beta billing` or the Billing Budgets API directly.

## Command Map

| Goal | gcloud Invocation | Notes |
|------|-------------------|-------|
| List billing accounts | `gcloud billing accounts list --format=json` | Shows all accessible accounts |
| Describe billing account | `gcloud billing accounts describe "{{user.billing_account_id}}" --format=json` | Full account metadata |
| List project billing info | `gcloud billing projects describe "{{user.project_id}}" --format=json` | Shows linked billing account |
| Link project | `gcloud billing projects link "{{user.project_id}}" --billing-account="{{user.billing_account_id}}"` | Enables billing |
| Unlink project | `gcloud billing projects unlink "{{user.project_id}}"` | Disables billable services |
| List budgets | `gcloud alpha billing budgets list --billing-account="{{user.billing_account_id}}" --format=json` | All budgets for account |
| Describe budget | `gcloud alpha billing budgets describe "{{user.budget_id}}" --billing-account="{{user.billing_account_id}}" --format=json` | Full budget config |
| Create budget | `gcloud alpha billing budgets create --billing-account="{{user.billing_account_id}}" --display-name="{{user.budget_display_name}}" --budget-amount="{{user.budget_amount}}" --threshold-rule=percent=0.5 --threshold-rule=percent=0.9` | See full syntax below |
| Update budget | `gcloud alpha billing budgets update "{{user.budget_id}}" --billing-account="{{user.billing_account_id}}" --display-name="new-name"` | Field mask applied |
| Delete budget | `gcloud alpha billing budgets delete "{{user.budget_id}}" --billing-account="{{user.billing_account_id}}"` | Requires confirmation |
| List services | `gcloud beta billing services list --format=json` | All billable GCP services |
| List SKUs | `gcloud beta billing skus list --service="{{user.service_id}}" --format=json` | SKU pricing for a service |

## Execution Flows

### Operation: List Billing Accounts

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Credentials | `gcloud auth application-default print-access-token --quiet` | Exit 0 | HALT — authenticate |
| Billing API | `gcloud services list --enabled --filter='config.name=cloudbilling.googleapis.com'` | API listed | HALT — enable API |

#### Execution

```bash
gcloud billing accounts list --format=json
```

#### Validate

```bash
# Extract account IDs and display names
gcloud billing accounts list --format="json" | jq '.[] | {id: .name, displayName: .displayName, open: .open}'
```

#### Failure Recovery

| Error pattern | Agent Action | UX Feedback |
|--------------|--------------|-------------|
| `PERMISSION_DENIED` | HALT | `[ERROR] Missing billing.viewer role. Grant roles/billing.viewer to your account.` |
| Empty list | Report | `No billing accounts accessible. Check permissions or create a billing account.` |

### Operation: List/Describe Project Billing Info

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Project exists | `gcloud projects describe "{{user.project_id}}"` | Exit 0 | HALT — invalid project |
| Billing API | API enabled check | Enabled | HALT — enable API |

#### Execution

```bash
# Describe project billing info
gcloud billing projects describe "{{user.project_id}}" --format=json

# Extract billing account
gcloud billing projects describe "{{user.project_id}}" --format="json" | jq '{project: .name, billingAccount: .billingAccountName, billingEnabled: .billingEnabled}'
```

#### Failure Recovery

| Error pattern | Agent Action | UX Feedback |
|--------------|--------------|-------------|
| `PERMISSION_DENIED` | HALT | `[ERROR] Missing billing.viewer or resourcemanager.projects.get permission.` |
| `NOT_FOUND` | HALT | `[ERROR] Project "{{user.project_id}}" not found. Verify project ID.` |

### Operation: Link Project to Billing Account

#### Pre-flight (Safety Gate)

- **MUST** confirm: project `{{user.project_id}}` will be linked to billing account `{{user.billing_account_id}}`.
- **MUST** warn: linking enables billable services; costs will accrue.

#### Execution

```bash
gcloud billing projects link "{{user.project_id}}" \
  --billing-account="{{user.billing_account_id}}"
```

#### Post-execution Validation

```bash
gcloud billing projects describe "{{user.project_id}}" --format="json" | jq '.billingEnabled'
# Expected: true
```

#### Failure Recovery

| Error pattern | Agent Action | UX Feedback |
|--------------|--------------|-------------|
| `PERMISSION_DENIED` | HALT | `[ERROR] Missing billing.accountAdmin on billing account or resourcemanager.projects.createBillingAssignment on project.` |
| `ALREADY_EXISTS` | Report | `Project is already linked to a billing account. Current: {{output.billingAccountName}}` |
| `INVALID_ARGUMENT` | HALT | `[ERROR] Invalid billing account ID format. Expected: XXXXXX-XXXXXX-XXXXXX` |

### Operation: Unlink Project from Billing Account

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit confirmation: unlinking disables all billable services.
- **MUST** show current billing account and project ID.
- **MUST** require `{{user.confirm_unlink}}` to equal `{{user.project_id}}`.

#### Execution

```bash
gcloud billing projects unlink "{{user.project_id}}"
```

#### Post-execution Validation

```bash
gcloud billing projects describe "{{user.project_id}}" --format="json" | jq '.billingEnabled'
# Expected: false
```

#### Failure Recovery

| Error pattern | Agent Action | UX Feedback |
|--------------|--------------|-------------|
| `PERMISSION_DENIED` | HALT | `[ERROR] Missing billing.accountAdmin role on the billing account.` |
| `FAILED_PRECONDITION` | HALT | `[ERROR] Project has active resources that prevent unlinking. Stop all billable resources first.` |

### Operation: Create Budget

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Billing account exists | `gcloud billing accounts describe "{{user.billing_account_id}}"` | Exit 0 | HALT — invalid account |
| Budgets API enabled | `gcloud services list --enabled --filter='config.name=billingbudgets.googleapis.com'` | API listed | HALT — enable API |
| Budget name unique | `gcloud alpha billing budgets list --billing-account="..." --filter="displayName={{user.budget_display_name}}"` | Empty | Warn if duplicate |

#### Execution

```bash
gcloud alpha billing budgets create \
  --billing-account="{{user.billing_account_id}}" \
  --display-name="{{user.budget_display_name}}" \
  --budget-amount="{{user.budget_amount}}" \
  --threshold-rule=percent=0.5,spend-basis=current-spend \
  --threshold-rule=percent=0.9,spend-basis=forecasted-spend \
  --threshold-rule=percent=1.0,spend-basis=current-spend \
  --filter-projects="projects/{{env.CLOUDSDK_CORE_PROJECT}}" \
  --calendar-period=MONTH \
  --format=json
```

#### Post-execution Validation

```bash
gcloud alpha billing budgets describe "{{output.budget_id}}" \
  --billing-account="{{user.billing_account_id}}" \
  --format=json | jq '{name: .name, displayName: .displayName, amount: .amount.specifiedAmount.units, thresholds: [.thresholdRules[].thresholdPercent]}'
```

#### Failure Recovery

| Error pattern | Agent Action | UX Feedback |
|--------------|--------------|-------------|
| `INVALID_ARGUMENT` | Fix args | `[ERROR] Invalid budget configuration. Check amount format and threshold rules.` |
| `PERMISSION_DENIED` | HALT | `[ERROR] Missing billing.budgetAdmin role on billing account.` |
| `ALREADY_EXISTS` | Describe | `Budget with this name already exists. Update it instead?` |

### Operation: List/Describe Budgets

#### Execution

```bash
# List all budgets
gcloud alpha billing budgets list \
  --billing-account="{{user.billing_account_id}}" \
  --format=json

# Describe specific budget
gcloud alpha billing budgets describe "{{user.budget_id}}" \
  --billing-account="{{user.billing_account_id}}" \
  --format=json | jq '{name, displayName, amount: .amount.specifiedAmount.units, thresholds: [.thresholdRules[] | {percent: .thresholdPercent, basis: .spendBasis}]}'
```

### Operation: Update Budget

#### Pre-flight

- Describe current budget to show before/after diff.
- Preview threshold rule changes and notification impact.

#### Execution

```bash
gcloud alpha billing budgets update "{{user.budget_id}}" \
  --billing-account="{{user.billing_account_id}}" \
  --display-name="{{user.budget_display_name}}" \
  --budget-amount="{{user.budget_amount}}" \
  --format=json
```

#### Post-execution Validation

```bash
gcloud alpha billing budgets describe "{{user.budget_id}}" \
  --billing-account="{{user.billing_account_id}}" \
  --format=json | jq '{displayName, amount: .amount.specifiedAmount.units, etag}'
```

### Operation: Delete Budget

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit confirmation: delete budget `{{user.budget_id}}`.
- **MUST** show budget display name, amount, and threshold rules before delete.
- **MUST** require `{{user.confirm_delete}}` to equal `{{user.budget_id}}`.
- Apply GCL review per [rubric.md](rubric.md).

#### Execution

```bash
gcloud alpha billing budgets delete "{{user.budget_id}}" \
  --billing-account="{{user.billing_account_id}}"
```

#### Post-execution Validation

```bash
gcloud alpha billing budgets list \
  --billing-account="{{user.billing_account_id}}" \
  --format=json | jq '[.[].name]' | grep -v "{{user.budget_id}}"
# Expected: budget_id not in list
```

### Operation: Create Billing Export

#### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| BigQuery dataset exists | `bq show "{{user.export_dataset}}"` | Exit 0 | HALT — create dataset first |
| bq CLI installed | `bq version` | Exit 0 | HALT — install: `gcloud components install bq` or `pip install google-cloud-bigquery` |
| Export not already configured | `gcloud beta billing accounts describe "{{user.billing_account_id}}" --format=json` | No existing export | Warn if exists |
| Billing export API enabled | `gcloud services list --enabled --filter='config.name=billingbudgets.googleapis.com'` | API listed | HALT — enable API |

#### Execution

```bash
# Create BigQuery export via Cloud Billing API
# API: POST https://billing.googleapis.com/v1/billingAccounts/{id}/bigQueryExports
ACCESS_TOKEN=$(gcloud auth application-default print-access-token)
BILLING_ACCOUNT="{{user.billing_account_id}}"
DATASET="{{user.export_dataset}}"
TABLE_PREFIX="{{user.export_prefix}}"

curl -s -X POST \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  "https://billing.googleapis.com/v1/billingAccounts/${BILLING_ACCOUNT}/bigQueryExports" \
  -d "{
    \"datasetSpec\": {
      \"datasetId\": \"${DATASET}\",
      \"tablePrefix\": \"${TABLE_PREFIX}\"
    }
  }"
```

#### Post-execution Validation

```bash
# Verify export configuration
curl -s -H "Authorization: Bearer $(gcloud auth application-default print-access-token)" \
  "https://billing.googleapis.com/v1/billingAccounts/{{user.billing_account_id}}/bigQueryExports" | jq '.'
```

#### Failure Recovery

| Error pattern | Agent Action | UX Feedback |
|--------------|--------------|-------------|
| `PERMISSION_DENIED` | HALT | `[ERROR] Missing billing.costsManager role or BigQuery dataEditor on dataset.` |
| `NOT_FOUND` (dataset) | HALT | `[ERROR] BigQuery dataset not found. Create it first or delegate to gcp-bigquery-ops.` |
| `ALREADY_EXISTS` | Describe | `Export already configured. Delete existing export first or use the existing one.` |

### Operation: Delete Billing Export

#### Pre-flight (Safety Gate)

- **MUST** obtain explicit confirmation: delete export stops cost data pipeline.
- **MUST** show current export configuration.
- Apply GCL review per [rubric.md](rubric.md).

#### Execution

```bash
ACCESS_TOKEN=$(gcloud auth application-default print-access-token)
BILLING_ACCOUNT="{{user.billing_account_id}}"

curl -s -X DELETE \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  "https://billing.googleapis.com/v1/billingAccounts/${BILLING_ACCOUNT}/bigQueryExports/{{user.export_id}}"
```

### Operation: Query Pricing and SKUs

#### Execution

```bash
# List all billable services
gcloud beta billing services list --format=json | jq '.[] | {id: .serviceId, name: .displayName}'

# List SKUs for a specific service (e.g., Compute Engine)
gcloud beta billing skus list \
  --service="{{user.service_id}}" \
  --format=json | jq '.[] | {skuId: .skuId, description: .description, category: .category.resourceGroup}'

# Filter SKUs by region
gcloud beta billing skus list \
  --service="{{user.service_id}}" \
  --filter="regions:us-central1" \
  --format=json
```

#### Failure Recovery

| Error pattern | Agent Action | UX Feedback |
|--------------|--------------|-------------|
| `PERMISSION_DENIED` | HALT | `[ERROR] Missing billing.viewer role.` |
| `NOT_FOUND` (service) | List services | `Service ID not found. Run "gcloud beta billing services list" to find valid IDs.` |
