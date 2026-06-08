---
name: billing-api-sdk-usage
description: REST API map, Python/Go SDK code, JSON paths, and response conventions for Cloud Billing

<!---
load_condition: "[SDK 操作或需要 JSON path 时加载]"
token_cost_estimate: "~1500 tokens"
dependencies: []
--->
---

# API & SDK — Cloud Billing

## REST API Endpoints

| API | Base URL | Purpose |
|-----|----------|---------|
| Cloud Billing | `https://cloudbilling.googleapis.com/v1/` | Billing accounts, project billing info |
| Billing Budgets | `https://billingbudgets.googleapis.com/v1/` | Budget CRUD |
| Cloud Billing (exports) | `https://billing.googleapis.com/v1/` | BigQuery billing exports |
| Cloud Billing Catalog | `https://cloudbilling.googleapis.com/v1/` | SKU and pricing queries |

## Centralized JSON Paths

### Billing Account
```text
$.name                         # "billingAccounts/XXXXXX-XXXXXX-XXXXXX"
$.displayName                  # Human-readable account name
$.open                         # true/false — whether account is open
$.masterBillingAccount         # Parent account for sub-accounts
```

### Budget
```text
$.name                         # "billingAccounts/{id}/budgets/{budgetId}"
$.displayName                  # User-defined budget name
$.amount.specifiedAmount.units # Budget amount (string, e.g. "100")
$.amount.specifiedAmount.nanos # Budget amount nanos (e.g. 0)
$.amount.specifiedAmount.currencyCode # e.g. "USD"
$.amount.lastPeriodAmount      # Last period's spend (output only)
$.thresholdRules[]             # Array of threshold rules
$.thresholdRules[].thresholdPercent # e.g. 0.5, 0.9, 1.0
$.thresholdRules[].spendBasis  # CURRENT_SPEND or FORECASTED_SPEND
$.notificationsRule            # Pub/Sub topic, email recipients, etc.
$.filter                       # Budget scope filter (projects, services, labels)
$.etag                         # Concurrency control for updates
```

### Billing Export (BigQuery)
```text
$.name                         # Export resource name
$.datasetSpec.datasetId        # BigQuery dataset ID
$.datasetSpec.tablePrefix      # Table name prefix
```

### Project Billing Info
```text
$.name                         # "projects/{projectId}/billingInfo"
$.billingAccountName           # "billingAccounts/XXXXXX-XXXXXX-XXXXXX"
$.billingEnabled               # true/false
```

## SDK Operations Map

| Goal | REST Method & Path | Python SDK Method |
|------|-------------------|-------------------|
| List Billing Accounts | `GET /v1/billingAccounts` | `CloudBillingClient.list_billing_accounts()` |
| Get Billing Account | `GET /v1/{name=billingAccounts/*}` | `CloudBillingClient.get_billing_account()` |
| List Project Billing Info | `GET /v1/{name=projects/*}/billingInfo` | `CloudBillingClient.get_project_billing_info()` |
| Update Project Billing Info | `PUT /v1/{name=projects/*/billingInfo}` | `CloudBillingClient.update_project_billing_info()` |
| Create Budget | `POST /v1/{parent=billingAccounts/*}/budgets` | `BudgetServiceClient.create_budget()` |
| List Budgets | `GET /v1/{parent=billingAccounts/*}/budgets` | `BudgetServiceClient.list_budgets()` |
| Get Budget | `GET /v1/{name=billingAccounts/*/budgets/*}` | `BudgetServiceClient.get_budget()` |
| Update Budget | `PATCH /v1/{budget.name}` | `BudgetServiceClient.update_budget()` |
| Delete Budget | `DELETE /v1/{name=billingAccounts/*/budgets/*}` | `BudgetServiceClient.delete_budget()` |
| List SKUs | `GET /v1/{parent=services/*}/skus` | `CloudCatalogClient.list_skus()` |
| List Services | `GET /v1/services` | `CloudCatalogClient.list_services()` |

## Python SDK Examples

### List Billing Accounts
```python
# list_billing_accounts.py
import os
from google.cloud import billing_v1

client = billing_v1.CloudBillingClient()
accounts = client.list_billing_accounts()
for acct in accounts:
    print(f"{acct.name}: {acct.display_name} (open={acct.open})")
```

### Create Budget
```python
# create_budget.py
import os
from google.cloud.billing import budgets_v1
from google.cloud.billing.budgets_v1 import types

parent = f"billingAccounts/{os.environ['BILLING_ACCOUNT_ID']}"
client = budgets_v1.BudgetServiceClient()

budget = types.Budget(
    display_name="{{user.budget_display_name}}",
    amount=types.BudgetAmount(
        specified_amount=types.Money(
            units="{{user.budget_amount}}",
            currency_code="USD",
        )
    ),
    threshold_rules=[
        types.ThresholdRule(threshold_percent=0.5, spend_basis="CURRENT_SPEND"),
        types.ThresholdRule(threshold_percent=0.9, spend_basis="FORECASTED_SPEND"),
    ],
    budget_filter=types.Filter(projects=[f"projects/{os.environ['CLOUDSDK_CORE_PROJECT']}"]),
)

resp = client.create_budget(parent=parent, budget=budget)
print(f"Created budget: {resp.name}")
```

### List SKUs for a Service
```python
# list_skus.py
from google.cloud import billing_v1

client = billing_v1.CloudCatalogClient()
# List all public services first
services = client.list_services()
for svc in services:
    if "Compute Engine" in svc.display_name:
        parent = svc.name
        break

skus = client.list_skus(parent=parent)
for sku in skus:
    print(f"{sku.sku_id}: {sku.description} — {sku.category.resource_group}")
```

## Request / Response Notes

- Budget parent format: `billingAccounts/{billing_account_id}`
- Budget name format: `billingAccounts/{billing_account_id}/budgets/{budget_id}`
- Budget updates require `update_mask` field mask (e.g., `displayName,amount,thresholdRules`)
- Budget etag provides optimistic concurrency control
- SKU queries support pagination with `page_size` and `page_token`
- Currency codes are ISO 4217 (e.g., `USD`, `EUR`, `JPY`)
