# Bot Management — Google Cloud Armor

> Provides security engineers with a guide to bot detection, classification, and management in Google Cloud Armor — bot category management, detection signals, policies, and Cloud Armor integration.

## Table of Contents

1. [Overview](#overview)
2. [Bot Detection Signals](#bot-detection-signals)
3. [Bot Categories](#bot-categories)
4. [Bot Management Policies](#bot-management-policies)
5. [Cloud Armor Bot Management](#cloud-armor-bot-management)
6. [CAPTCHA Integration](#captcha-integration)
7. [Detection Tuning](#detection-tuning)
8. [Logging and Monitoring](#logging-and-monitoring)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)
11. [See Also](#see-also)

## Overview

Bot management in Google Cloud Armor involves:
- **Detection**: Identifying bot traffic vs. legitimate users
- **Classification**: Categorizing bots (good bots, bad bots, unknown)
- **Management**: Allowing, blocking, or challenging bot traffic
- **Adaptation**: Continuously tuning detection based on traffic patterns

### Bot Management Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                         Bot Management Flow                             │
│                                                                          │
│  Incoming Request                                                        │
│  ┌────────────────┐    ┌────────────────┐    ┌────────────────────┐   │
│  │ Bot Detection  │───►│ Bot Category   │───►│ Bot Policy         │   │
│  │ Signals       │    │ Classification  │    │ Action             │   │
│  └────────────────┘    └────────────────┘    └────────────────────┘   │
│         │                      │                        │                │
│         ▼                      ▼                        ▼                │
│  ┌────────────────┐    ┌────────────────┐    ┌────────────────────┐   │
│  │ User-Agent    │    │ Known Bot      │    │ Allow / Block /    │   │
│  │ Behavior      │    │ Suspicious    │    │ Challenge (CAPTCHA)│   │
│  │ Reputation    │    │ Unknown       │    │ Throttle           │   │
│  └────────────────┘    └────────────────┘    └────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

## Bot Detection Signals

### 1. User-Agent Analysis

#### Standard Bot User-Agents

```bash
# Detect common bot User-Agents
gcloud compute security-policies rules create 8000 \
  --security-policy={{user.policy_name}} \
  --expression="request.headers['user-agent'].contains('curl') || request.headers['user-agent'].contains('wget') || request.headers['user-agent'].contains('python-requests')" \
  --action="allow" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

#### Known Good Bots

| Bot | User-Agent Pattern | Action |
|-----|-------------------|--------|
| Googlebot | `Googlebot/2.1` | Allow |
| Bingbot | `bingbot/2.0` | Allow |
| Yahoo Slurp | `Slurp` | Allow |
| Baidu Spider | `Baiduspider` | Allow |

#### Known Bad Bots

| Bot | User-Agent Pattern | Action |
|-----|-------------------|--------|
| Scrapy | `Scrapy` | Deny |
| AhrefsBot | `AhrefsBot` | Throttle |
| SemrushBot | `SemrushBot` | Throttle |

### 2. Behavioral Analysis

#### Request Rate Detection

```bash
# Detect high-frequency requests (potential scraper)
gcloud compute security-policies rules create 8001 \
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

#### Navigation Pattern Detection

```bash
# Detect rapid page scanning (crawler pattern)
gcloud compute security-policies rules create 8002 \
  --security-policy={{user.policy_name}} \
  --expression="request.headers['referer'].null && request.path.matches('.*\\.html?')" \
  --action="allow" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### 3. IP Reputation

#### Known Bad IP Ranges

```bash
# Block known malicious IPs (example)
gcloud compute security-policies rules create 8003 \
  --security-policy={{user.policy_name}} \
  --expression="inIpRange(origin.ip, '192.0.2.0/24')" \
  --action="deny-403" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### 4. JavaScript Challenge

```bash
# Enable JavaScript challenge for suspicious traffic
gcloud compute security-policies rules create 8004 \
  --security-policy={{user.policy_name}} \
  --expression="origin.region_code == 'XX'" \
  --action="challenge" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

## Bot Categories

### Bot Category Definitions

| Category | Description | Default Action |
|----------|-------------|----------------|
| `BOT_ABUSE` | Malicious bots (scrapers, crawlers) | Deny |
| `BOT_SUSPICIOUS` | Potential bad bots | Challenge |
| `BOT_VERIFIED` | Known good bots (Google, Bing) | Allow |
| `HUMAN` | Legitimate human traffic | Allow |

### Preconfigured Bot Rules

```bash
# Enable bot management policy
gcloud compute security-policies update {{user.policy_name}} \
  --enable-ml \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### Custom Bot Category

```bash
# Create custom bot category
gcloud compute security-policies rules create 8100 \
  --security-policy={{user.policy_name}} \
  --expression="request.headers['user-agent'].contains('my-custom-bot')" \
  --action="allow" \
  --description="Allow custom bot" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

## Bot Management Policies

### 1. Allow Verified Bots

```bash
# Allow Googlebot
gcloud compute security-policies rules create 800 \
  --security-policy={{user.policy_name}} \
  --expression="request.headers['user-agent'].contains('Googlebot')" \
  --action="allow" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Allow Bingbot
gcloud compute security-policies rules create 801 \
  --security-policy={{user.policy_name}} \
  --expression="request.headers['user-agent'].contains('bingbot')" \
  --action="allow" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### 2. Challenge Unknown Traffic

```bash
# Challenge traffic without proper User-Agent
gcloud compute security-policies rules create 810 \
  --security-policy={{user.policy_name}} \
  --expression="request.headers['user-agent'].null || request.headers['user-agent'].contains('bot')" \
  --action="challenge" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### 3. Throttle Suspicious Bots

```bash
# Throttle scrapers based on behavior
gcloud compute security-policies rules create 820 \
  --security-policy={{user.policy_name}} \
  --expression="request.headers['user-agent'].contains('Scrapy') || request.headers['user-agent'].contains('AhrefsBot')" \
  --action="throttle" \
  --rate-limit-threshold-count=20 \
  --rate-limit-threshold-interval-sec=60 \
  --conform-action="allow" \
  --exceed-action="deny-429" \
  --enforce-on-key="IP" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### 4. Block Known Bad Bots

```bash
# Block specific malicious bots
gcloud compute security-policies rules create 830 \
  --security-policy={{user.policy_name}} \
  --expression="request.headers['user-agent'].contains('curl') && origin.region_code == 'XX'" \
  --action="deny-403" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### 5. Graduated Response Policy

```bash
# Layer 1: Allow verified bots (priority 100)
gcloud compute security-policies rules create 100 \
  --security-policy={{user.policy_name}} \
  --expression="request.headers['user-agent'].contains('Googlebot') || request.headers['user-agent'].contains('Bingbot')" \
  --action="allow" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Layer 2: Challenge unknown (priority 1000)
gcloud compute security-policies rules create 1000 \
  --security-policy={{user.policy_name}} \
  --expression="request.headers['user-agent'].null" \
  --action="challenge" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Layer 3: Throttle suspicious (priority 2000)
gcloud compute security-policies rules create 2000 \
  --security-policy={{user.policy_name}} \
  --expression="request.headers['user-agent'].contains('bot', 2)" \
  --action="throttle" \
  --rate-limit-threshold-count=50 \
  --rate-limit-threshold-interval-sec=60 \
  --conform-action="allow" \
  --exceed-action="deny-429" \
  --enforce-on-key="IP" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Layer 4: Block clearly malicious (priority 3000)
gcloud compute security-policies rules create 3000 \
  --security-policy={{user.policy_name}} \
  --expression="request.headers['user-agent'].contains('wget') && origin.region_code != 'US'" \
  --action="deny-403" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

## Cloud Armor Bot Management

### Enable Bot Management

```bash
# Enable ML-based bot detection
gcloud compute security-policies update {{user.policy_name}} \
  --enable-ml \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### Bot Management Policy Structure

```bash
# Create bot management policy
gcloud compute security-policies create bot-policy \
  --description="Bot management policy" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Add bot rules
gcloud compute security-policies rules create 100 \
  --security-policy=bot-policy \
  --expression="evaluatePreconfiguredExpr('bot-cat-abuse')" \
  --action="deny-403" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### Bot Evaluation Functions

| Function | Description |
|----------|-------------|
| `bot-cat-abuse` | Known abusive bots |
| `bot-cat-suspicious` | Suspicious bot behavior |
| `bot-cat-verified` | Known good bots |
| `bot-cat-unknown` | Unclassified traffic |

```bash
# Block abusive bots
gcloud compute security-policies rules create 9000 \
  --security-policy={{user.policy_name}} \
  --expression="evaluatePreconfiguredExpr('bot-cat-abuse')" \
  --action="deny-403" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Challenge suspicious bots
gcloud compute security-policies rules create 9001 \
  --security-policy={{user.policy_name}} \
  --expression="evaluatePreconfiguredExpr('bot-cat-suspicious')" \
  --action="challenge" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

## CAPTCHA Integration

### reCAPTCHA Enterprise Setup

```bash
# Create reCAPTCHA key
gcloud recaptcha keys create \
  --display-name="Cloud Armor reCAPTCHA" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --website-key-domain="example.com" \
  --type="SCORE"
```

### Challenge Action with reCAPTCHA

```bash
# Enable CAPTCHA challenge for suspicious traffic
gcloud compute security-policies rules create 9100 \
  --security-policy={{user.policy_name}} \
  --expression="origin.region_code == 'XX'" \
  --action="challenge" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### Custom Challenge Page

```bash
# Configure redirect for CAPTCHA
gcloud compute security-policies rules create 9101 \
  --security-policy={{user.policy_name}} \
  --expression="request.path.contains('/login')" \
  --action="redirect" \
  --redirect-target="https://captcha.example.com/challenge" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

## Detection Tuning

### Allowlist Known Good Traffic

```bash
# Allow internal traffic without challenge
gcloud compute security-policies rules create 100 \
  --security-policy={{user.policy_name}} \
  --expression="inIpRange(origin.ip, '10.0.0.0/8') || inIpRange(origin.ip, '172.16.0.0/12')" \
  --action="allow" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### Exclude Paths from Bot Detection

```bash
# Skip bot detection for API endpoints
gcloud compute security-policies rules create 200 \
  --security-policy={{user.policy_name}} \
  --expression="request.path.startsWith('/api/v1/')" \
  --action="allow" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### Sensitivity Configuration

```bash
# Set bot detection sensitivity
gcloud compute security-policies update {{user.policy_name}} \
  --bot-sensitivity="HIGH" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

| Sensitivity | Use Case |
|-------------|----------|
| `LOW` | Minimal friction, more false negatives |
| `MEDIUM` | Balanced (default) |
| `HIGH` | Strict, more false positives |

## Logging and Monitoring

### Enable Bot Logging

```bash
# Enable security policy logging
gcloud compute security-policies update {{user.policy_name}} \
  --enable-logging \
  --logging-level=VERBOSE \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### Query Bot Traffic

```bash
# View bot-related requests
gcloud logging read \
  'resource.type="http_load_balancer" AND jsonPayload.enforcedSecurityPolicy.outcome="BOT_DETECTED"' \
  --limit=100 \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Count bot requests by category
gcloud logging read \
  'resource.type="http_load_balancer" AND jsonPayload.enforcedSecurityPolicy.outcome="BOT_DETECTED"' \
  --format="table(jsonPayload.enforcedSecurityPolicy.botCategory, jsonPayload.enforcedSecurityPolicy.outcome)" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

### Cloud Monitoring Dashboard

```bash
# Create bot traffic metric
gcloud monitoring metrics create \
  --metric-type="cloud armor.googleapis.com/security_policy_request_count" \
  --filter='resource.type="http_load_balancer" AND security_policy_action="BOT_DETECTED"' \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"
```

## Best Practices

1. **Allowlist Known Good Bots**: Add Googlebot, Bingbot to avoid SEO impact
2. **Use Graduated Response**: Challenge before blocking to reduce false positives
3. **Monitor Bot Categories**: Review bot traffic regularly to tune rules
4. **Enable ML Detection**: Use `evaluatePreconfiguredExpr('bot-cat-*')` for advanced detection
5. **Test with Captive Portal**: Use `curl -A "bot"` to verify challenge behavior
6. **Maintain Allowlists**: Keep IP allowlists updated for internal services

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Legitimate users blocked | Overly aggressive rules | Add exceptions for legitimate User-Agents |
| Good bots blocked | SEO impact | Add allowlist rules for Googlebot, Bingbot |
| Bot challenge loop | reCAPTCHA misconfiguration | Verify site key and domain |
| High false positive rate | Low bot sensitivity | Increase sensitivity or add allowlists |

### Debug Commands

```bash
# List bot detection events
gcloud logging read \
  'resource.type="http_load_balancer" AND jsonPayload.enforcedSecurityPolicy.name="{{user.policy_name}}"' \
  --limit=50 \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Check rule evaluation
gcloud compute security-policies rules list \
  --security-policy={{user.policy_name}} \
  --format="table(priority,expression,action)" \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}"

# Test User-Agent against rules
curl -A "Googlebot/2.1" -I https://example.com/
```

## See Also

- [Advanced WAF Rules](advanced-waf-rules.md)
- [Adaptive Protection](adaptive-protection.md)
- [Core Concepts](../core-concepts.md)
- [Monitoring](../monitoring.md)
- [Google Cloud Armor Bot Management](https://cloud.google.com/armor/docs/bot-management)
