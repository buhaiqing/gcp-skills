# Advanced WAF Rules — Google Cloud Armor

> Provides security engineers with advanced WAF rule patterns for Google Cloud Armor — OWASP Top 10 protection, rate-based rules, custom rule sets, and sec_rule language deep dive.

## Table of Contents

1. [Overview](#overview)
2. [OWASP Top 10 Protection](#owasp-top-10-protection)
3. [sec_rule Language Reference](#sec_rule-language-reference)
4. [Rate-Based Rules](#rate-based-rules)
5. [Preconfigured WAF Rules](#preconfigured-waf-rules)
6. [Custom Rule Sets](#custom-rule-sets)
7. [Rule Evaluation Order](#rule-evaluation-order)
8. [Expression Examples](#expression-examples)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)
11. [See Also](#see-also)

## Overview

Google Cloud Armor provides Layer 7 WAF protection using:
- **Preconfigured rules**: Managed rule sets for common attack patterns
- **Custom rules**: User-defined rules using Common Expression Language (CEL) or sec_rule language
- **Rate-based rules**: Throttling based on request frequency
- **Adaptive Protection**: ML-based threat detection (see [adaptive-protection.md](adaptive-protection.md))

### WAF Rule Types

| Rule Type | Use Case | Action |
|-----------|----------|--------|
| Preconfigured | Common attack vectors | `deny-403`, `deny-429`, `deny-500` |
| Custom CEL | Fine-grained matching | `allow`, `deny-*`, `throttle` |
| Custom sec_rule | Complex conditions | Full rule lifecycle |
| Rate-based | DDoS / brute force | `throttle`, `deny-429` |
| Adaptive | Unknown threats | Auto-generated rules |

## OWASP Top 10 Protection

### 1. SQL Injection (SQLi)

#### Preconfigured Rule

```bash
gcloud compute security-policies rules create 1000 \
  --security-policy={{user.policy_name}} \
  --expression="evaluatePreconfiguredWaf('sqli-v33-stable')" \
  --action="deny-403" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

#### Custom SQLi Rule (Enhanced)

```bash
gcloud compute security-policies rules create 1001 \
  --security-policy={{user.policy_name}} \
  --expression="evaluatePreconfiguredWaf('sqli-v33-stable', {' sensitivity': 'HIGH' })" \
  --action="deny-403" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

#### Custom SQLi with sec_rule

```bash
gcloud compute security-policies rules create 1002 \
  --security-policy={{user.policy_name}} \
  --expression="evaluatePreconfiguredExpr('evaluatePreconfiguredWaf(\"sqli-v33-stable\")') && origin.region_code == 'XX'" \
  --action="allow" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### 2. Cross-Site Scripting (XSS)

#### Preconfigured Rule

```bash
gcloud compute security-policies rules create 1100 \
  --security-policy={{user.policy_name}} \
  --expression="evaluatePreconfiguredWaf('xss-v33-stable')" \
  --action="deny-403" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

#### Custom XSS Rule with Exception

```bash
# Allow specific paths that contain scripts (whitelist approach)
gcloud compute security-policies rules create 1101 \
  --security-policy={{user.policy_name}} \
  --expression="evaluatePreconfiguredWaf('xss-v33-stable') && !inIpRange(origin.ip, '10.0.0.0/8')" \
  --action="deny-403" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### 3. Remote Code Execution (RCE)

#### RCE Detection Patterns

```bash
# Block common RCE patterns
gcloud compute security-policies rules create 1200 \
  --security-policy={{user.policy_name}} \
  --expression="request.path.contains('cgi-bin') || request.path.contains('bin') || request.path.contains('etc')" \
  --action="deny-403" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

#### RCE with Command Injection Patterns

```bash
gcloud compute security-policies rules create 1201 \
  --security-policy={{user.policy_name}} \
  --expression="request.path.contains(';') || request.path.contains('|') || request.path.contains('&&') || request.path.contains('||')" \
  --action="deny-403" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### 4. Local File Inclusion (LFI) / Remote File Inclusion (RFI)

#### LFI Detection

```bash
gcloud compute security-policies rules create 1300 \
  --security-policy={{user.policy_name}} \
  --expression="request.path.contains('../') || request.path.contains('..\\') || request.path.contains('%2e%2e')" \
  --action="deny-403" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

#### RFI Detection

```bash
gcloud compute security-policies rules create 1301 \
  --security-policy={{user.policy_name}} \
  --expression="request.path.contains('http://') || request.path.contains('https://') || request.path.contains('ftp://')" \
  --action="deny-403" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### 5. Path Traversal

```bash
gcloud compute security-policies rules create 1400 \
  --security-policy={{user.policy_name}} \
  --expression="request.path.contains('..') || request.headers['referer'].contains('..')" \
  --action="deny-403" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### 6. Command Injection

```bash
gcloud compute security-policies rules create 1500 \
  --security-policy={{user.policy_name}} \
  --expression="request.path.matches('.*[;&|`$].*') || request.query.contains(';') || request.query.contains('|')" \
  --action="deny-403" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### 7. XML External Entities (XXE)

```bash
gcloud compute security-policies rules create 1600 \
  --security-policy={{user.policy_name}} \
  --expression="request.path.contains('.xml') || request.headers['content-type'].contains('xml')" \
  --action="deny-403" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### 8. Session Fixation

```bash
gcloud compute security-policies rules create 1700 \
  --security-policy={{user.policy_name}} \
  --expression="request.cookie.contains('SESSIONID') && request.headers['cache-control'].null" \
  --action="deny-403" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### 9. Security Misconfiguration

```bash
# Block access to sensitive paths
gcloud compute security-policies rules create 1800 \
  --security-policy={{user.policy_name}} \
  --expression="request.path.matches('.*\\.(env|git|htaccess|htpasswd|ini|log|sh|conf|config).*')" \
  --action="deny-403" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### 10. Insufficient Logging

> Note: This is addressed via Cloud Logging integration rather than WAF rules. See [monitoring.md](../monitoring.md).

## sec_rule Language Reference

The `sec_rule` language provides a declarative rule format for complex WAF scenarios:

```
sec_rule VARIABLE OPERATOR [TRANSFORMATION] \
  "phase:REQUEST,id:ID,msg:'MESSAGE',severity:LEVEL,action:ACTION"
```

### Variables

| Variable | Description |
|----------|-------------|
| `ARGS` | Request arguments |
| `ARGS_GET` | GET query parameters |
| `ARGS_POST` | POST body parameters |
| `REQUEST_BASENAME` | Request filename |
| `REQUEST_COOKIES` | Cookie values |
| `REQUEST_HEADERS` | Request headers |
| `REQUEST_LINE` | Full request line |
| `REQUEST_METHOD` | HTTP method |
| `REQUEST_URI` | Full request URI |
| `REQUEST_URI_RAW` | Raw request URI |

### Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `contains` | Substring match | `ARGS contains 'exec'` |
| `matches` | Regex match | `REQUEST_URI matches '^/admin'` |
| `eq` | Equals | `REQUEST_METHOD eq 'POST'` |
| `startsWith` | Prefix match | `ARGS_GET startsWith 'id'` |
| `endsWith` | Suffix match | `ARGS_GET endsWith 'token'` |

### Transformations

| Transformation | Description |
|----------------|-------------|
| `none` | No transformation |
| `lowercase` | Convert to lowercase |
| `trim` | Remove whitespace |
| `removeNulls` | Remove null bytes |
| `compressWhitespace` | Collapse whitespace |

### Cloud Armor sec_rule Mapping

> Note: Cloud Armor uses CEL expressions primarily. sec_rule is supported in compatibility mode.

```bash
# Cloud Armor sec_rule equivalent
gcloud compute security-policies rules create 2000 \
  --security-policy={{user.policy_name}} \
  --expression="true" \
  --action="deny-403" \
  --description="Block SQL injection via args" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

## Rate-Based Rules

### Basic Rate Limiting

```bash
gcloud compute security-policies rules create 5000 \
  --security-policy={{user.policy_name}} \
  --expression="true" \
  --action="throttle" \
  --rate-limit-threshold-count=100 \
  --rate-limit-threshold-interval-sec=60 \
  --conform-action="allow" \
  --exceed-action="deny-429" \
  --enforce-on-key="IP" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### Rate Limiting by User

```bash
gcloud compute security-policies rules create 5001 \
  --security-policy={{user.policy_name}} \
  --expression="request.headers['authorization'].null" \
  --action="throttle" \
  --rate-limit-threshold-count=5 \
  --rate-limit-threshold-interval-sec=60 \
  --conform-action="allow" \
  --exceed-action="deny-429" \
  --enforce-on-key="HEADER:authorization" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### Rate Limiting by IP + Path

```bash
gcloud compute security-policies rules create 5002 \
  --security-policy={{user.policy_name}} \
  --expression="request.path.matches('^/api/.*')" \
  --action="throttle" \
  --rate-limit-threshold-count=50 \
  --rate-limit-threshold-interval-sec=60 \
  --conform-action="allow" \
  --exceed-action="deny-429" \
  --enforce-on-key="IP_AND_PATH" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### Rate-Based Ban

```bash
gcloud compute security-policies rules create 5003 \
  --security-policy={{user.policy_name}} \
  --expression="origin.ip == '192.168.1.1'" \
  --action="deny-403" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### Adaptive Rate Protection

See [adaptive-protection.md](adaptive-protection.md) for ML-based rate limiting.

## Preconfigured WAF Rules

### Available Rule Sets

| Rule Set ID | Description | Category |
|-------------|-------------|----------|
| `sqli-v33-stable` | SQL injection protection | OWASP |
| `xss-v33-stable` | Cross-site scripting | OWASP |
| `rce-v33-stable` | Remote code execution | OWASP |
| `lfi-v33-stable` | Local file inclusion | OWASP |
| `rfi-v33-stable` | Remote file inclusion | OWASP |
| `protocal-attack-v33-stable` | Protocol attacks | Protocol |
| `scanner-detect-v33-stable` | Security scanner detection | Scanner |
| `csrf-v33-stable` | CSRF protection | Application |

### Rule Set Configuration

```bash
# Enable with specific sensitivity
gcloud compute security-policies rules create 100 \
  --security-policy={{user.policy_name}} \
  --expression="evaluatePreconfiguredWaf('sqli-v33-stable', {'sensitivity': 'HIGH'})" \
  --action="deny-403" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Medium sensitivity (default)
gcloud compute security-policies rules create 101 \
  --security-policy={{user.policy_name}} \
  --expression="evaluatePreconfiguredWaf('sqli-v33-stable', {'sensitivity': 'MEDIUM'})" \
  --action="deny-403" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

## Custom Rule Sets

### Creating a Reusable Rule Set

```bash
# Define custom rule set
gcloud compute security-policies rule-sets create my-custom-ruleset \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --file-format=json \
  --file=./custom-ruleset.json
```

### custom-ruleset.json Example

```json
{
  "name": "my-custom-ruleset",
  "rules": [
    {
      "priority": 1000,
      "match": {
        "expr": {
          "expression": "request.path.contains('/admin')"
        }
      },
      "action": "deny-403"
    }
  ]
}
```

### Applying Rule Set to Policy

```bash
gcloud compute security-policies add-rule-set \
  --security-policy={{user.policy_name}} \
  --rule-set="my-custom-ruleset" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

## Rule Evaluation Order

Cloud Armor evaluates rules in **priority order** (lower number = higher priority).

### Rule Priority Planning

| Priority Range | Purpose |
|---------------|---------|
| 1-999 | Allow rules (whitelist) |
| 1000-4999 | Preconfigured WAF rules |
| 5000-9999 | Rate limiting rules |
| 10000+ | Default deny / catch-all |

### Rule Ordering Best Practices

```bash
# 1. Whitelist trusted IPs (priority 100)
gcloud compute security-policies rules create 100 \
  --security-policy={{user.policy_name}} \
  --expression="inIpRange(origin.ip, '10.0.0.0/8')" \
  --action="allow" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# 2. Allow health checks
gcloud compute security-policies rules create 200 \
  --security-policy={{user.policy_name}} \
  --expression="origin.ip == '35.191.0.0/16' || origin.ip == '130.211.0.0/22'" \
  --action="allow" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# 3. WAF rules (priority 1000-1999)
# ... add WAF rules here ...

# 4. Rate limiting (priority 5000-5999)
# ... add rate rules here ...

# 5. Default deny (priority 2147483647)
gcloud compute security-policies rules create 2147483647 \
  --security-policy={{user.policy_name}} \
  --expression="true" \
  --action="deny-403" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

## Expression Examples

### Common CEL Expressions

```bash
# Country-based blocking
origin.region_code == 'XX'

# IP range matching
inIpRange(origin.ip, '192.168.0.0/16')

# Header matching
request.headers['user-agent'].contains('curl')

# Path matching
request.path.startsWith('/api/')

# Query parameter
request.query.contains('id')

# Method-based
request.method == 'POST'

# Combined conditions
origin.region_code == 'XX' && request.path.contains('/admin')
```

### Complex Expressions

```bash
# Block Tor exit nodes and known bad IPs
gcloud compute security-policies rules create 3000 \
  --security-policy={{user.policy_name}} \
  --expression="origin.region_code == 'XX' || inIpRange(origin.ip, '192.0.2.0/24')" \
  --action="deny-403" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

## Best Practices

1. **Layer Your Defenses**: Use preconfigured rules as a baseline, add custom rules for specific threats
2. **Start with Monitoring**: Deploy new rules in `allow` mode first to observe false positives
3. **Maintain Rule Order**: Keep allow rules at low priorities, deny rules at high priorities
4. **Monitor WAF Logs**: Review Cloud Armor logs to identify attack patterns and tune rules
5. **Use Adaptive Protection**: Enable ML-based detection for unknown threat vectors
6. **Test Before Production**: Use `gcloud compute security-policies rules update` with preview mode

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| False positives | Rule too broad | Add exceptions for legitimate traffic |
| False negatives | Rule not matching | Check expression syntax |
| Rule not evaluated | Priority conflict | Ensure unique priorities |
| Performance impact | Too many rules | Consolidate similar rules |

### Debug Commands

```bash
# List all rules in policy
gcloud compute security-policies rules list \
  --security-policy={{user.policy_name}} \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Test rule evaluation
gcloud compute security-policies describe {{user.policy_name}} \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Check rule hit counts
gcloud logging read \
  'resource.type="http_load_balancer" AND jsonPayload.enforcedSecurityPolicy.name="{{user.policy_name}}"' \
  --limit=100 \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

## See Also

- [Bot Management](bot-management.md)
- [Adaptive Protection](adaptive-protection.md)
- [Core Concepts](../core-concepts.md)
- [Monitoring](../monitoring.md)
- [Google Cloud Armor Documentation](https://cloud.google.com/armor/docs/waf-rules)
