---
name: billing-idempotency-checklist
description: Idempotent behavior patterns for Cloud Billing operations in retry and automation scenarios

<!---
load_condition: "[自动化/重试时加载]"
token_cost_estimate: "~600 tokens"
dependencies: []
--->
---

# Idempotency Checklist — Cloud Billing

## Idempotency by Operation

| Operation | Idempotent? | Pre-condition Check | Safe Retry? |
|-----------|:-----------:|---------------------|:-----------:|
| List billing accounts | ✅ Always | None | Yes |
| Describe billing account | ✅ Always | None | Yes |
| List project billing info | ✅ Always | None | Yes |
| Describe project billing info | ✅ Always | None | Yes |
| Link project | ✅ Conditional | Check if already linked to same account | Yes — `ALREADY_EXISTS` is acceptable |
| Unlink project | ✅ Conditional | Check if project has billing; `NOT_FOUND` is acceptable after unlink | Yes — idempotent after confirmation |
| Create budget | ❌ Not by default | Check existing budget by display name + scope | No — may create duplicate budgets |
| List budgets | ✅ Always | None | Yes |
| Describe budget | ✅ Always | None | Yes |
| Update budget | ✅ Conditional | Use etag for optimistic concurrency | Yes — same desired state = no change |
| Delete budget | ✅ Conditional | `NOT_FOUND` is acceptable after delete | Yes — idempotent after confirmation |
| Create billing export | ❌ Not by default | Check existing export config | No — only one export per type per account |
| Delete billing export | ✅ Conditional | `NOT_FOUND` is acceptable after delete | Yes — idempotent after confirmation |
| List services/SKUs | ✅ Always | None | Yes |

## Safe Retry Patterns

### Budget Create (Idempotent Wrapper)

```bash
# Check if budget with same display name exists
EXISTING=$(gcloud alpha billing budgets list \
  --billing-account="{{user.billing_account_id}}" \
  --filter="displayName={{user.budget_display_name}}" \
  --format="value(name)")

if [ -n "$EXISTING" ]; then
  echo "Budget already exists: $EXISTING"
  # Optionally update instead
  gcloud alpha billing budgets update "$EXISTING" \
    --billing-account="{{user.billing_account_id}}" \
    --budget-amount="{{user.budget_amount}}" \
    --format=json
else
  gcloud alpha billing budgets create \
    --billing-account="{{user.billing_account_id}}" \
    --display-name="{{user.budget_display_name}}" \
    --budget-amount="{{user.budget_amount}}" \
    --format=json
fi
```

### Budget Update (Etag-based)

```bash
# Get current etag
ETAG=$(gcloud alpha billing budgets describe "{{user.budget_id}}" \
  --billing-account="{{user.billing_account_id}}" \
  --format="value(etag)")

# Update with etag for concurrency control
gcloud alpha billing budgets update "{{user.budget_id}}" \
  --billing-account="{{user.billing_account_id}}" \
  --etag="$ETAG" \
  --budget-amount="{{user.budget_amount}}" \
  --format=json
```

### Project Link (Idempotent)

```bash
# Check current billing
CURRENT=$(gcloud billing projects describe "{{user.project_id}}" \
  --format="value(billingAccountName)")

if [ "$CURRENT" = "billingAccounts/{{user.billing_account_id}}" ]; then
  echo "Project already linked to target billing account"
else
  gcloud billing projects link "{{user.project_id}}" \
    --billing-account="{{user.billing_account_id}}"
fi
```

## Retry Strategy

| Error Type | Max Retries | Backoff | Notes |
|------------|:-----------:|---------|-------|
| `UNAVAILABLE` / 503 | 3 | 1s, 2s, 4s | Transient; safe to retry |
| `INTERNAL` / 500 | 2 | 2s, 4s | May indicate persistent issue |
| `ABORTED` / concurrency | 3 | 2s, 4s, 8s | Wait for conflicting operation |
| `RESOURCE_EXHAUSTED` / 429 | 3 | Exponential with jitter | Rate limit; back off |
| `PERMISSION_DENIED` / 403 | 0 | — | Never retry; fix IAM |
| `INVALID_ARGUMENT` / 400 | 0 | — | Never retry; fix input |
| `NOT_FOUND` / 404 | 0 | — | Never retry for reads; acceptable for deletes |
| `ALREADY_EXISTS` / 409 | 0 | — | Accept as success for idempotent ops |
