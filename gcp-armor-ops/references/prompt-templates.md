# GCL Prompt Templates — Cloud Armor (WAF)

## Generator Template
Hard rules:
1. Safety gate on all deny/throttle rule changes (deny-403, throttle, deny-429)
2. Never deploy a rule that matches legitimate traffic without dry-run preview
3. Require human review for production-impacting rules (HALT + confirm with `{{user.policy_name}}` + `{{user.rule_priority}}`)
4. Follow per-op sub-rules in references/rubric.md
5. Use env vars for credentials; NEVER output credential values
6. Validate rate-based burst-rate against baseline before apply
7. Adaptive-protection auto-deploy requires explicit enable flag + T2 human gate
8. Delegate IAM ops to gcp-iam-ops
9. Reference advanced-waf-rules.md / self-healing-runbook.md for rule detail; do not duplicate

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
    "Traffic Impact": "PASS|FAIL|N/A",
    "Rate-Limit Validation": "PASS|FAIL|N/A",
    "Adaptive Enable Flag": "PASS|FAIL|N/A"
  },
  "verdict": "PASS|SAFETY_FAIL|REVISE",
  "issues": ["string"]
}
```

Detection regex: security-policies rules.*(create|update), action=deny, action=throttle, evaluatePreconfiguredWaf, adaptive.*enable

## Orchestrator
Loop: Generator → Critic → verdict (PASS|SAFETY_FAIL|REVISE). max_iter=2.
