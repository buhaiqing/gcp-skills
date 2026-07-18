# Advanced References — Google Cloud Armor

This directory contains advanced operational guides for Google Cloud Armor beyond the core capabilities documented in the parent references directory.

## Contents

| File | Description |
|------|-------------|
| [advanced-waf-rules.md](advanced-waf-rules.md) | OWASP Top 10 protection, sec_rule language, rate-based rules, custom rule sets |
| [bot-management.md](bot-management.md) | Bot detection signals, bot categories, bot management policies, CAPTCHA integration |
| [adaptive-protection.md](adaptive-protection.md) | ML-based threat detection, auto-deploy rules, threshold tuning, alerting |

## Quick Reference

### Enable Adaptive Protection

```bash
gcloud compute security-policies update {{user.policy_name}} \
  --enable-adaptive-protection \
  --adaptive-protection-auto-deploy-enabled \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### Add OWASP WAF Rule

```bash
gcloud compute security-policies rules create 1000 \
  --security-policy={{user.policy_name}} \
  --expression="evaluatePreconfiguredWaf('sqli-v33-stable')" \
  --action="deny-403" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### Configure Bot Challenge

```bash
gcloud compute security-policies rules create 9100 \
  --security-policy={{user.policy_name}} \
  --expression="origin.region_code == 'XX'" \
  --action="challenge" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

## See Also

- [Core Concepts](../core-concepts.md)
- [gcloud Usage](../gcloud-usage.md)
- [Monitoring](../monitoring.md)
- [Integration](../integration.md)
