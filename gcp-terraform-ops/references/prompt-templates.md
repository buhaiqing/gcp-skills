# GCL Prompt Templates — Terraform

## Generator Template
Hard rules:
1. Safety gates on all destructive ops (apply, destroy, import, state rm/mv)
2. Follow per-op sub-rules in references/rubric.md
3. Always run `terraform plan` before `terraform apply`; never apply without a plan preview
4. Never use `-auto-approve` for `apply`/`destroy` in production
5. Require human review + typed confirmation for destructive operations
6. Use env vars for credentials (`GOOGLE_APPLICATION_CREDENTIALS`); NEVER output credential values
7. Export state backup (`terraform state pull`) before any `destroy`
8. Delegate IAM policy changes to gcp-iam-ops; delegate resource-specific lifecycle to the owning skill
9. Verify target environment directory + backend GCS bucket match before mutation
10. Mask secrets from plan output; HALT if plaintext secrets detected

## Critic Template
CRITICAL: Critic MUST NOT see the user's original request.

```json
{
  "dimensions": {
    "Correctness": "PASS|FAIL",
    "Safety": "PASS|FAIL|0",
    "Idempotency": "PASS|FAIL",
    "Traceability": "PASS|FAIL",
    "Spec Compliance": "PASS|FAIL"
  },
  "extensions": {
    "Environment Isolation": "PASS|FAIL|N/A",
    "State Integrity": "PASS|FAIL|N/A",
    "Credential Safety": "PASS|FAIL|N/A"
  },
  "terraform_extension": {
    "Drift/Blast-Radius": "PASS|FAIL|N/A"
  },
  "verdict": "PASS|SAFETY_FAIL|REVISE",
  "issues": ["string"]
}
```

Detection regex: terraform apply, terraform destroy, -auto-approve, terraform state rm, terraform import

## Orchestrator
Loop: Generator → Critic → verdict (PASS|SAFETY_FAIL|REVISE). max_iter=2.
