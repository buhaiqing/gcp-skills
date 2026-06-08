---
name: billing-core-concepts
description: Architecture, resource model, permissions, limits, and safety constraints for Cloud Billing operations

<!---
load_condition: "[总是加载 — 架构和权限基础]"
token_cost_estimate: "~1200 tokens"
dependencies: []
--->
---

# Core Concepts — Google Cloud Billing

## Resource Model

| Resource | Scope | Notes |
|----------|-------|-------|
| Billing Account | Organization-level; self-serve or invoiced | Top-level container for costs; linked to Google payments profile |
| Budget | Per billing account | Spending limit with threshold-based alert rules; evaluated daily |
| Budget Alert Threshold Rule | Per budget | Percentage of budget that triggers Pub/Sub or email notifications |
| Billing Export (BigQuery) | Per billing account | Standard usage cost or detailed cost data exported to BigQuery dataset |
| Project Billing Info | Per project | Links a project to a billing account; enables billable services |

## Control Plane vs Data Plane

- **Control plane:** list/describe billing accounts, link/unlink projects, CRUD budgets and exports.
- **Data plane:** query cost data in BigQuery export tables, read pricing catalog, consume Pub/Sub budget alerts. This skill manages the control plane and queries data-plane cost information.

## Billing Account Types

| Type | Description | CLI Access |
|------|-------------|------------|
| Self-serve (online) | Credit card or bank account; immediate setup | Full gcloud support |
| Invoiced | Monthly invoice; requires sales contract | Full gcloud support |
| Sub-account | Child of a master billing account; for resellers | Limited gcloud support |

## IAM and Permissions

| Role | Purpose | Key Permissions |
|------|---------|-----------------|
| `roles/billing.viewer` | Read-only access to billing accounts and spend | `billing.accounts.get`, `billing.accounts.list` |
| `roles/billing.accountAdmin` | Link/unlink projects | `billing.accounts.get`, `resourcemanager.projects.createBillingAssignment` |
| `roles/billing.budgetAdmin` | Full budget CRUD | `billing.budgets.create`, `.get`, `.update`, `.delete` |
| `roles/billing.costsManager` | Manage billing exports and cost views | `billing.exports.*`, `billing.accounts.getSpendingInformation` |
| `roles/billing.creator` | Create new billing accounts | `billing.accounts.create` |

Do not print service account key content or access tokens. Validate IAM by checking operation-specific failures and current service account identity, then delegate broad IAM policy changes to `gcp-iam-ops`.

## Budget Behavior

- Budgets are evaluated **daily** (not real-time).
- Threshold rules trigger when **actual** or **forecasted** spend exceeds the percentage.
- Notifications can go to **Pub/Sub topics** or **email addresses** (monitoring notification channels).
- Budget amount is in the billing account's currency.
- Budget scope can be filtered by project, service, labels, or credit types.
- Calendar period budgets reset monthly/quarterly/yearly; custom period budgets use a date range.

## Billing Export Behavior

- **Standard usage cost export:** daily aggregate cost data to BigQuery.
- **Detailed usage cost export:** hourly resource-level cost data to BigQuery.
- Export destination must be a BigQuery dataset in the same project that owns the export configuration.
- Once enabled, data flows automatically; there is no "pause" — only create or delete.
- Export data schema is defined by Google; do not modify the table schema.

## Project Billing Safety

- **Unlinking** a project from a billing account disables all billable services (Compute Engine, Cloud Storage, etc.).
- Unlink requires `billing.accountAdmin` or `billing.admin` on the billing account.
- Free-tier usage continues after unlink; only billable services stop.
- Re-linking restores service access but does not automatically restart stopped resources.

## Operational Limits and Quotas

Use API/CLI queries over static numbers:

```bash
gcloud billing accounts list --format=json
gcloud alpha billing budgets list --billing-account="{{user.billing_account_id}}" --format=json
gcloud beta billing accounts describe "{{user.billing_account_id}}" --format=json
```

Key limits:
- Budgets per billing account: 20,000 (soft limit)
- Budget threshold rules per budget: 5
- Billing exports per billing account: 1 standard + 1 detailed
- Notification email recipients per threshold: 5

## Idempotency Principles

- Budget create is idempotent only after checking existing budget by display name and scope.
- Budget update is idempotent when the desired state matches current state.
- Export create is idempotent only after checking existing export configuration.
- Project link is idempotent when project is already linked to the target billing account.
- Delete operations are idempotent only when `NOT_FOUND` is an acceptable final state and explicit confirmation was captured.

## Credential and Secret Handling

- Mask `GOOGLE_APPLICATION_CREDENTIALS`, tokens, and billing account sensitive metadata.
- Budget threshold email recipients should be previewed but not printed in full in public logs.
- Never run `cat $GOOGLE_APPLICATION_CREDENTIALS` or print config structs containing credential material.
