---
name: billing-troubleshooting
description: Cloud Billing diagnostics, error taxonomy, and recovery actions

<!---
load_condition: "[报错或诊断时加载]"
token_cost_estimate: "~1400 tokens"
dependencies: []
--->
---

# Troubleshooting — Cloud Billing

## Diagnostic Flow

1. Identify the operation that failed (list accounts, create budget, link project, etc.).
2. Capture the exact error code/message from gcloud or API response.
3. Verify credentials and IAM roles with `gcloud auth application-default print-access-token --quiet`.
4. Verify billing account ID format: `XXXXXX-XXXXXX-XXXXXX` (6 groups of 6 hex chars).
5. Classify using the error taxonomy below.
6. Recommend the smallest safe fix. Do not mutate IAM without approval.

## Error Taxonomy

| Code / Symptom | Likely Cause | Recovery |
|----------------|--------------|----------|
| `PERMISSION_DENIED: billing.accounts.get` | Missing billing.viewer role | HALT — grant `roles/billing.viewer` on the billing account |
| `PERMISSION_DENIED: billing.accounts.update` | Missing billing.accountAdmin | HALT — grant `roles/billing.accountAdmin` on the billing account |
| `PERMISSION_DENIED: billing.budgets.create` | Missing billing.budgetAdmin | HALT — grant `roles/billing.budgetAdmin` on the billing account |
| `PERMISSION_DENIED: billing.exports.*` | Missing billing.costsManager | HALT — grant `roles/billing.costsManager` on the billing account |
| `NOT_FOUND: billing account` | Invalid billing account ID or account not accessible | Verify ID format `XXXXXX-XXXXXX-XXXXXX`; check `gcloud billing accounts list` |
| `NOT_FOUND: project` | Project ID does not exist or is not accessible | Verify project ID; check `gcloud projects list` |
| `NOT_FOUND: budget` | Budget ID invalid or already deleted | List budgets to find correct ID |
| `INVALID_ARGUMENT: billing account ID` | Malformed billing account ID | Use format `XXXXXX-XXXXXX-XXXXXX` from `gcloud billing accounts list` |
| `INVALID_ARGUMENT: budget amount` | Budget amount not a valid number or negative | Use positive numeric string (e.g., "1000") |
| `INVALID_ARGUMENT: threshold percent` | Threshold not between 0.0 and 1.0 | Use decimal (0.5 = 50%, 0.9 = 90%, 1.0 = 100%) |
| `ALREADY_EXISTS: budget` | Budget with same display name exists | Describe existing budget; offer to update instead |
| `ALREADY_EXISTS: billing export` | Export already configured for this account | Describe existing export; offer to delete and recreate |
| `FAILED_PRECONDITION: project unlink` | Project has active billable resources | Stop or migrate resources before unlinking |
| `FAILED_PRECONDITION: billing account closed` | Billing account is closed | Reopen billing account or use a different one |
| `UNAVAILABLE` / transient error | Cloud Billing API temporarily unavailable | Retry with exponential backoff (1s, 2s, 4s); max 3 retries |
| `INTERNAL` / 500 | Server-side error | Retry once; if persists, HALT and suggest filing support case |
| Budget alerts not firing | Notification channel misconfigured or Pub/Sub topic permissions wrong | Verify notification channels; check Pub/Sub topic IAM |
| Export data missing in BigQuery | Export pipeline delay or dataset permission issue | Wait 24-48h for initial data; check dataset IAM and table existence |
| Budget amount in wrong currency | Billing account currency mismatch | Budget amount must match billing account currency; check with `gcloud billing accounts describe` |

## Budget Diagnosis Commands

```bash
# Check budget status and current spend
gcloud alpha billing budgets describe "{{user.budget_id}}" \
  --billing-account="{{user.billing_account_id}}" \
  --format=json | jq '{name, displayName, amount: .amount.specifiedAmount, thresholds: [.thresholdRules[] | {percent: .thresholdPercent, basis: .spendBasis}]}'

# List all budgets with current spend info
gcloud alpha billing budgets list \
  --billing-account="{{user.billing_account_id}}" \
  --format=json | jq '.[] | {name: .name, displayName: .displayName, amount: .amount.specifiedAmount.units}'
```

## Export Diagnosis Commands

```bash
# Check export configuration
ACCESS_TOKEN=$(gcloud auth application-default print-access-token)
curl -s -H "Authorization: Bearer $ACCESS_TOKEN" \
  "https://billing.googleapis.com/v1/billingAccounts/{{user.billing_account_id}}/bigQueryExports" | jq '.'

# Check BigQuery export tables
bq ls "{{user.export_dataset}}" | grep "{{user.export_prefix}}"

# Check latest export data freshness
bq query --nouse_legacy_sql \
  "SELECT MAX(usage_start_time) FROM \`{{user.export_dataset}}.{{user.export_prefix}}\`"
```

## Recovery Rules

| Situation | Rule |
|-----------|------|
| Permission fix needed | Explain exact principal + role + resource; delegate broad IAM changes to `gcp-iam-ops` |
| Budget delete needed | Require exact budget ID confirmation and GCL review |
| Export delete needed | Require exact export ID confirmation and GCL review |
| Project unlink needed | Require project ID confirmation; warn about service disruption |
| Transient API failure | Retry with backoff only after confirming operation idempotency |
| Budget threshold misconfiguration | Update budget with corrected threshold rules; preview before applying |
