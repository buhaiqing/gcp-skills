<!---
load_condition: "[总是加载 — 核心执行流程]"
token_cost_estimate: "~2500 tokens"
dependencies: ["references/core-concepts.md", "references/variables-and-conventions.md", "references/troubleshooting.md", "references/idempotency-checklist.md"]
--->

# Execution Flows — Terraform Operations

Detailed Pre-flight → Execute → Validate → Recover for every Terraform operation. SKILL.md links here per operation. GCL is **required** (max_iter=2) for apply, destroy, import, and state mv/rm.

## Operation: terraform init

### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Terraform CLI installed | `terraform version` | Version ≥ 1.6.0 | HALT — install Terraform |
| Working directory | `test -d environments/{{user.environment}}/` | Directory exists | HALT — specify environment |
| GCS backend bucket exists | `gsutil ls gs://tf-state-{{user.environment}}-{project}-terraform/` | Bucket accessible | HALT — create GCS bucket |
| DynamoDB lock table exists | `aws dynamodb describe-table --table-name terraform-state-lock-{{user.environment}}` | Table present | HALT — create DynamoDB lock table |
| Backend config valid | `grep backend environments/{{user.environment}}/backend.tf` | backend "gcs" block present | HALT — check backend.tf |
| Terraform service account has GCS permissions | `gsutil ls gs://tf-state-{{user.environment}}-{project}-terraform/environments/{{user.environment}}/` | Exit 0 | HALT — grant storage.objectAdmin |
| Provider versions pinned | `grep required_providers environments/{{user.environment}}/versions.tf` | version constraint present | HALT — add version constraint |

### Execution

1. `cd environments/{{user.environment}}/`
2. `terraform init -reconfigure` (force re-read of backend config)
3. Store `{{output.state_lock_id}}` if returned

### Post-execution Validation

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Provider downloaded | `ls .terraform/providers/` | Provider directory present | Retry init |
| State connected | `ls .terraform/terraform.tfstate` (local cache) | File present | Check GCS state |

### Failure Recovery

- On `Backend initialization required`, re-run with `-reconfigure`
- On provider download failure, check network and retry `terraform init -upgrade`
- On lock table error, verify DynamoDB table exists and Terraform SA has permissions

---

## Operation: terraform validate

### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Init completed | `test -d .terraform/` | `.terraform/` present | HALT — run `terraform init` first |
| Configuration files exist | `ls environments/{{user.environment}}/*.tf` | At least one `.tf` file | HALT — no `.tf` files found |

### Execution

1. `cd environments/{{user.environment}}/`
2. `terraform validate .`
3. Store exit code and any error messages

### Post-execution Validation

- Exit code 0 and no error output → validation passed

### Failure Recovery

- HCL syntax errors: identify the `.tf` file and line number from error output; do not modify `.tf` files (user manages configuration)
- Reference errors (missing variables): report the variable name and which file references it

---

## Operation: terraform plan (MUST precede all apply/destroy)

### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Init completed | `test -d .terraform/` | `.terraform/` present | HALT — run `terraform init` |
| Backend bucket isolation | `grep bucket environments/{{user.environment}}/backend.tf` | Unique bucket for this environment | HALT — verify bucket isolation |
| State lock available | `terraform plan` (will acquire lock) | Lock acquired | HALT — investigate stale lock |
| Variable file present | `test -f environments/{{user.environment}}/terraform.tfvars` | File exists | HALT — provide tfvars |
| No secrets in tfvars | `grep -E 'password|secret|api_key' environments/{{user.environment}}/terraform.tfvars` | No matches | HALT — move secrets to Secret Manager |

### Execution

1. `cd environments/{{user.environment}}/`
2. `terraform plan -out={{user.target_dir}}/.tfplan`
3. Capture plan summary: `+N create, ~M modify, -K destroy`
4. Store `{{output.plan_summary}}`
5. Parse destroy count: look for lines starting with `-/+ destroy`

### Post-execution Validation

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Plan completed | Exit code 0 | Plan file created | Diagnose errors |
| No unexpected destroy in dev/staging | Inspect destroy count | 0 destroy for dev/staging | Investigate — config may have stale resources |
| Plan file created | `test -f {{user.target_dir}}/.tfplan` | File exists | Retry plan |

### Failure Recovery

- On state lock error, wait or investigate stale lock; do not force-unlock unless lock > 10 min old
- On GCS permission error, verify Terraform SA has `storage.objectAdmin` on bucket
- On HCL errors, report error message; do not modify `.tf` files

---

## Operation: terraform apply (GCL required — dual safety gate)

### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Plan output exists | `test -f {{user.target_dir}}/.tfplan` | Plan file from prior `terraform plan` | HALT — run `terraform plan` first |
| Plan summary shown to user | Display `{{output.plan_summary}}` | User acknowledges | HALT — show plan summary |
| Environment is correct | Show `environments/{{user.environment}}/backend.tf` bucket | User confirms target | HALT — confirm environment |
| No secrets in plan output | Inspect plan output for secret patterns | No secrets exposed | HALT — redact before proceeding |
| GCL review passed | Load `rubric.md` and score operation | Score ≥ threshold | HALT — GCL blocks unsafe apply |
| Prod environment explicit acknowledgement | For prod: show bucket and plan destroy count | Explicit acknowledgement | HALT — prod requires explicit acknowledgement |

### GCL Gate 1: Plan Preview

Before running apply, the Agent must show the plan summary and obtain acknowledgement:
- Display: `Plan: +N create, ~M modify, -K destroy`
- For dev/staging: acknowledge and proceed
- For prod: additionally confirm target GCS bucket and resource list

### Execution

1. `cd environments/{{user.environment}}/`
2. `terraform apply {{user.target_dir}}/.tfplan`
3. Store `{{output.apply_summary}}` (resources added/changed/destroyed)
4. Release state lock (automatic on success)

### Post-execution Validation

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Apply succeeded | Exit code 0 | Resources applied | Diagnose error; do not re-apply without review |
| State updated | `terraform state list | wc -l` | Resource count matches expectation | Inspect state with `terraform show` |
| No resources unexpectedly destroyed | Compare apply summary to plan | No more destroys than plan | Investigate; rollback if possible |

### Failure Recovery

- On partial failure (some resources created, some failed): inspect `terraform show` and decide next action
- On lock not released (crash): wait 5 minutes, then `terraform force-unlock` if lock is confirmed stale
- On state drift after apply: run `terraform plan` to identify changes; do not blindly re-apply

---

## Operation: terraform destroy (GCL required — strictest safety gate)

### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| State backup created | `test -f {{user.backup_file}}` (from `terraform state pull`) | Backup file exists | HALT — create state backup first |
| State backup size > 0 | `wc -c {{user.backup_file}}` | Non-zero file | HALT — backup failed; retry |
| Destroy plan output | `terraform plan -destroy -out={{user.target_dir}}/.destroy.tfplan` | Plan file created | HALT — plan must precede destroy |
| Destroy resource list shown | Display `{{output.destroy_resources}}` | User sees exact resources to be destroyed | HALT — show all resources |
| Exact resource confirmation | `{{user.confirm_destroy}}` matches a specific resource name pattern | Exact match or wildcard for full destroy | HALT — require exact confirmation |
| GCL review passed | Load `rubric.md` and score operation | Score ≥ threshold | HALT — GCL blocks unsafe destroy |
| Prod environment explicit acknowledgement | For prod: explicit acknowledgement of billing impact and resource loss | Explicit acknowledgement | HALT — prod destroy requires explicit acknowledgement |

### Execution

1. `cd environments/{{user.environment}}/`
2. `terraform state pull > {{user.backup_file}}` (state backup — already done in pre-flight, verify)
3. `terraform apply {{user.target_dir}}/.destroy.tfplan`
4. Store `{{output.apply_summary}}`
5. Clear state if all resources destroyed: `echo '{}' > terraform.tfstate`

### Post-execution Validation

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| All resources destroyed | `terraform state list` | Empty state or resources with `deletion_protection=true` | Investigate remaining resources |
| State cleared | `terraform state list | wc -l` | 0 resources or only protected resources | Confirm intentional |

### Failure Recovery

- On partial destroy failure (some resources destroyed, some failed): inspect remaining resources
- On `deletion_protection = true` preventing destroy: remove protection in `.tf` file first, then re-plan destroy
- On state lock held after failure: `terraform force-unlock {lock_id}` only if lock is confirmed stale (> 10 min)
- Restore from backup: `gsutil cp gs://tf-state-{env}-{project}-terraform/backups/{backup}.json .terraform/terraform.tfstate`

---

## Operation: terraform import

### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Init completed | `test -d .terraform/` | `.terraform/` present | HALT — run `terraform init` |
| Resource address valid | `terraform state list` | Check format matches target | Ask once |
| Resource ID format valid | Verify GCP resource ID format | Valid format | HALT — correct resource ID |
| Resource does not already exist in state | `terraform state list | grep {{user.resource_address}}` | Not found | HALT — resource already in state; use `terraform state rm` first |
| GCL review for import | Load `rubric.md` | Score ≥ threshold | HALT — import modifies state |

### Execution

1. `cd environments/{{user.environment}}/`
2. `terraform import {{user.resource_address}} {{user.resource_id}}`
3. Store `{{output.imported_resource}}`
4. Run `terraform plan` to verify state matches configuration

### Post-execution Validation

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Resource in state | `terraform state list | grep {{user.resource_address}}` | Resource present | Retry import |
| Plan shows no unexpected changes | `terraform plan` | 0 changes or expected differences | Investigate drift |

### Failure Recovery

- On import to wrong resource: use `terraform state rm` to remove, then re-import correct resource
- On resource ID format error: verify GCP resource ID against Cloud Console or `gcloud` describe

---

## Operation: terraform state (list/mv/rm/pull)

### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Init completed | `test -d .terraform/` | `.terraform/` present | HALT — run `terraform init` |
| State lock available | `terraform state list` (acquires lock) | Lock acquired | HALT — investigate stale lock |
| State file accessible | `terraform state pull > /dev/null` | Exit 0 | HALT — GCS state inaccessible |

### Execution

- `terraform state list` — list all resources in state
- `terraform state mv old_address new_address` — rename resource in state
- `terraform state rm resource_address` — remove resource from state
- `terraform state pull` — output state JSON to stdout (for backup)
- `terraform state push` — restore state from file

### Post-execution Validation

- For `mv`: run `terraform plan` and expect 0 changes
- For `rm`: run `terraform plan` and expect the removed resource as a destroy
- For `pull`: verify JSON is valid Terraform state format

### Failure Recovery

- On `mv` to already-existing address: use `terraform state rm` first, then mv
- On stale lock after `state list`: wait or `terraform force-unlock`

---

## Operation: terraform workspace

### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Init completed | `test -d .terraform/` | `.terraform/` present | HALT — run `terraform init` |

### Execution

- `terraform workspace list` — list all workspaces
- `terraform workspace select {{user.workspace_name}}` — switch workspace
- `terraform workspace new {{user.workspace_name}}` — create workspace
- `terraform workspace delete {{user.workspace_name}}` — delete (only if state is empty)

### Post-execution Validation

- Confirm current workspace: `terraform workspace show`
- Verify state file is from the correct workspace's GCS prefix

---

## Operation: terraform output and terraform show

### Pre-flight Checks

| Check | Method | Expected | On Failure |
|-------|--------|----------|------------|
| Init completed | `test -d .terraform/` | `.terraform/` present | HALT — run `terraform init` |

### Execution

- `terraform output` — show output variable values
- `terraform output -json` — structured JSON output (preferred for parsing)
- `terraform show` — display current state snapshot as JSON

### Post-execution Validation

- For `output -json`: parse `{{output.output_values}}` from JSON
- For `show`: parse resource list and attributes

---

## Diagnostic Logging Pattern

When wrapping Terraform in scripts, emit structured logs:

```bash
printf '[%(%H:%M:%S)T] [DIAG] action=plan environment=%s target_dir=%s\n' -1 "{{user.environment}}" "{{user.target_dir}}"
# terraform plan command
printf '[%(%H:%M:%S)T] [RESULT] plan_summary="%s" lock_id=%s\n' -1 "${PLAN_SUMMARY}" "${LOCK_ID}"
```

Use `[ERROR] TYPE={category} FIX={action}` for failures and never print credentials.

## Safety Gates Summary

| Operation | Pre-flight | GCL Required | Safety Gate |
|-----------|-----------|-------------|-------------|
| init | Terraform version, backend bucket, lock table | No | None |
| validate | Init completed, .tf files exist | No | None |
| plan | Init, backend isolation, no secrets | No | None |
| **apply** | Plan output exists, summary shown, env confirmed | **Yes** | Plan preview + acknowledgement |
| **destroy** | State backup, destroy plan, resource list, exact confirmation | **Yes** | Plan preview + backup + confirmation |
| import | Init, valid address/ID, not in state | **Yes** | Address confirmation |
| state mv/rm | Init, lock available, state accessible | **Yes** | Current state review |
| output/show | Init | No | None |
| workspace | Init | No | None |