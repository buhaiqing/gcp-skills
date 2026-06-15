# Core Concepts — Google Cloud Armor

## Architecture Overview

Cloud Armor protects applications behind Google Cloud Load Balancers (GLBs) with:
- **DDoS Protection**: Volumetric, protocol, and application layer attacks
- **WAF (Web Application Firewall)**: Rule-based request filtering
- **Adaptive Protection**: ML-based threat detection
- **Bot Management**: Automated traffic filtering

## Resource Hierarchy

```
Project
├── Security Policy
│   ├── Rule (priority 1-N)
│   ├── Rule (pre-configured WAF)
│   └── Rule (adaptive protection)
└── Attached to Backend Service (via LB)
```

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Security Policy** | Container for rules; attached to backend services |
| **Rule** | Individual allow/deny/throttle/redirect action with expression |
| **Priority** | Integer 1-2147483647; evaluated lowest first |
| **Expression** | CEL (Common Expression Language) for request matching |
| **Action** | allow, deny(403/404/502), throttle, redirect, return-404 |
| **Pre-configured WAF** | Built-in rules for SQL injection, XSS, etc. |
| **Adaptive Protection** | ML-based anomaly detection |

## Rule Evaluation Order

1. Rules evaluated by priority (lowest number = highest priority)
2. First matching rule determines action
3. If no rule matches → default action (typically allow)
4. Pre-configured WAF rules evaluate in priority order

## Pre-configured WAF Rules

| Rule Name | Protection |
|-----------|------------|
| `sqli-v33-stable` | SQL injection (OWASP CRS) |
| `xss-v33-stable` | Cross-site scripting |
| `rfi-v33-stable` | Remote file inclusion |
| `lfi-v33-stable` | Local file inclusion |
| `rce-v33-stable` | Remote code execution |
| `methodenforcement-v33-stable` | HTTP method enforcement |
| `scannerdetection-v33-stable` | Scanner detection |
| `protocolattack-v33-stable` | Protocol attack |
| `phpv33-stable` | PHP injection |
| `sessionfix-v33-stable` | Session fixation |

## Quotas and Limits

| Resource | Default Limit |
|----------|---------------|
| Security policies per project | 100 |
| Rules per security policy | 200 |
| Pre-configured WAF rules | Varies by rule |
| Adaptive protection models | 10 per policy |

## Regions and Availability

- Security policies are global resources
- Rules evaluate at edge locations (global)
- Latency impact: minimal (typically <1ms)

## Dependency Graph

```
Cloud Armor Security Policy
    ↑
Backend Service (attached)
    ↑
URL Map → Forwarding Rule → Load Balancer
```
