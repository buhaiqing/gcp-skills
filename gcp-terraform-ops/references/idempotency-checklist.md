<!---
load_condition: "[执行重试/幂等操作时加载]"
token_cost_estimate: "~600 tokens"
dependencies: []
--->

# Idempotency Checklist — Terraform Operations

## Global Checklist

- [ ] Identify whether operation is read-only (plan/show/output) or mutation (apply/destroy/import/state).
- [ ] Confirm target environment directory (`environments/dev/` or `staging/` or `prod/`).
- [ ] Verify backend GCS bucket matches environment (not another env's bucket).
- [ ] For all mutations: run `terraform plan` first and show plan summary.
- [ ] For destroy: run `terraform state pull > backup.json` before apply.
- [ ] Redact sensitive values from plan output before reporting.
- [ ] Validate final state with `terraform state list` or `terraform show`.

## Operations

| Operation | Idempotency Rule |
|-----------|------------------|
| `terraform init` | Idempotent if provider/modules already downloaded; safe to re-run |
| `terraform validate` | Idempotent; always safe to re-run |
| `terraform plan` | Idempotent read-only operation; always safe to re-run |
| `terraform apply` | **Not inherently idempotent**; running twice applies changes twice. Idempotent only if configuration is stable and plan shows 0 changes on second run |
| `terraform destroy` | **Not idempotent**; destroys resources. Require state backup + exact confirmation before execution |
| `terraform import` | Idempotent only if resource not already in state; use `terraform state list` first to check |
| `terraform state mv` | Not idempotent; moving a resource twice changes its address. Verify current address before mv |
| `terraform state rm` | Not idempotent; removes resource from state. Use `terraform state pull` backup first |
| `terraform workspace new` | Idempotent only if workspace does not already exist |
| `terraform workspace select` | Idempotent; always safe |
| `terraform output` | Idempotent read-only |

## Apply Idempotency Path

Before `terraform apply`:
1. Run `terraform plan -out={{user.plan_out_file}}`
2. If plan shows `No changes`, skip apply and report "configuration matches state"
3. If plan shows changes, proceed with apply only after GCL confirmation

## Retry Policy

| Error | Retry? | Conditions |
|-------|--------|------------|
| State lock held | Wait | Lock usually released by running process; check if other process active |
| `UNAVAILABLE` from GCS | Yes | Transient GCS error; retry with exponential backoff |
| `DEADLINE_EXCEEDED` | Maybe | Large state or many resources; increase timeout or split into modules |
| Provider download failed | Yes | Network issue; retry with `terraform init -upgrade` |
| `apply` partial failure | No | Inspect `terraform show`; decide whether to fix config and re-plan or accept partial state |
| `destroy` partial failure | No | Inspect remaining resources; fix GCP API errors; re-plan destroy |
| `import` resource already in state | N/A | Use `terraform state rm` first, then import |