# Well-Architected Assessment — Cloud Load Balancing

## Overview

This document maps Cloud Load Balancing operations to the [Google Cloud Architecture Framework](https://cloud.google.com/architecture/framework) five pillars. Each pillar section describes how LB resources relate to the pillar, what to assess, and recommended patterns.

---

## §1 Security

### 1.1 IAM Permissions

| Role | Permissions | Use Case |
|------|-------------|----------|
| `roles/compute.loadBalancerAdmin` | Full LB CRUD + SSL certificates + health checks | Production LB management |
| `roles/compute.loadBalancerViewer` | Read-only LB resources | Monitoring and audit |
| `roles/compute.networkAdmin` | Forwarding rules + firewall rules + network setup | Network team |
| `roles/compute.securityAdmin` | SSL policies + SSL certificates | Security team |

**Minimum permissions for operations:**
- Create/Modify LB: `compute.forwardingRules.create`, `compute.backendServices.create`, `compute.urlMaps.create`, `compute.targetProxies.create`, `compute.sslCertificates.create`
- Read LB: `compute.forwardingRules.get`, `compute.backendServices.get`, `compute.urlMaps.get`
- Delete LB: `compute.forwardingRules.delete`, `compute.backendServices.delete`

### 1.2 Credential Masking

All credential handling follows the masking rules in SKILL.md. For LB-specific operations:
- Forwarding rule target references are self-links (safe to log)
- SSL certificate private keys for self-managed certs MUST NOT be logged or echoed
- Health check responses may contain internal IPs — mask if logging

### 1.3 VPC Service Controls

- Internal LB supports VPC SC boundaries for service isolation
- External LB with Cloud Armor provides WAF-level filtering (OWASP rules, rate limiting)
- Use Private Google Access with internal LB for Cloud SQL / Cloud Run backends

### 1.4 SSL/TLS

| Feature | Recommendation |
|---------|---------------|
| SSL Policy | Use `modern-` prefix policies (TLS 1.2+, strong ciphers) |
| Managed Certs | Prefer Google-managed (auto-renew, no manual rotation) |
| Minimum TLS | TLS 1.2 (enforce via SSL policy) |
| Mutual TLS | Use Cloud Endpoints or Istio for mTLS |
| HSTS | Enable in backend application response headers |

---

## §2 Stability

### 2.1 High Availability

| Strategy | Implementation | RPO | RTO |
|----------|---------------|-----|-----|
| Multi-region backends (global LB) | Backends in ≥ 2 regions; traffic failure detection | N/A (stateless) | Seconds |
| Regional failover | Set `failoverProtocol` and failover backends | N/A | < 60s |
| Auto-healing backends | MIG with health-check-based auto-healing | N/A | < interval + 3 × timeout |

### 2.2 Backup and Recovery

- **Forwarding rules / Backend services / URL maps** are configuration-only; export via `gcloud` or Terraform
- **SSL certificates**: Self-managed certs require private key backup; managed certs auto-renew
- **Export LB configuration:**
  ```bash
  gcloud compute forwarding-rules list --global --format=json > lb-config.json
  gcloud compute backend-services list --global --format=json > bs-config.json
  gcloud compute url-maps list --global --format=json > urlmap-config.json
  ```

### 2.3 DR Runbook

1. **Global LB**: Single anycast IP — backends in another region automatically serve if one region fails
2. **Regional LB**: Create a second LB in another region; update DNS with health-check failover
3. **Restore from config export**: `gcloud compute forwarding-rules create < config.yaml` or Terraform apply

### 2.4 Failure-Oriented Design

| Failure Mode | Detection | Self-Healing |
|-------------|-----------|--------------|
| Backend goes unhealthy | Health check failure → unhealthy status | MIG auto-healing recreates instance |
| All backends unhealthy | Cloud Monitoring alarm | Auto-scale or manual intervention |
| Certificate expiry | Cloud Monitoring (expiry within 30d) | Managed certs auto-renew; alert for self-managed |
| Quota exhaustion | Create/describe returns QUOTA_EXCEEDED | Request increase or delete unused resources |

---

## §3 Cost

### 3.1 Pricing Model

| Component | Pricing |
|-----------|---------|
| Forwarding Rule | Free (no charge per forwarding rule) |
| Data Processing (external) | $0.025/GB for Application LB, $0.008/GB for Network LB |
| Data Processing (internal) | $0.015/GB |
| SSL Certificate | Free (managed) |
| Cloud CDN | $0.02/GB egress from cache; $0.01/GB for cache fill |

### 3.2 Right-Sizing

| Pattern | Recommendation |
|---------|---------------|
| Low traffic service | Use single backend with capacity scaler 1.0 |
| Burstable traffic | Use UTILIZATION balancing mode with maxUtilization 0.8 |
| Session-heavy | Use RATE balancing mode with maxRatePerInstance |
| Global egress | Use regional LB if traffic is region-locked (cost savings) |

### 3.3 Idle Resource Detection

Check for forwarding rules with zero traffic:
```bash
# Check if forwarding rule has received traffic in last 7 days
gcloud monitoring metrics list --filter="metric.type=loadbalancing.googleapis.com/https/request_count"
```

### 3.4 Committed Use Discounts

LB itself has no CUD. Backend instances (GCE) use instance-level CUDs.

---

## §4 Efficiency

### 4.1 Automation Patterns

```bash
# Batch create forwarding rules from JSON config
for rule in $(jq -c '.[]' rules.json); do
    gcloud compute forwarding-rules create $(echo $rule | jq -r '.name') \
      --load-balancing-scheme=$(echo $rule | jq -r '.scheme') \
      --target-https-proxy=$(echo $rule | jq -r '.target') \
      --ports=$(echo $rule | jq -r '.ports') \
      --global
done
```

### 4.2 URL Map Organization

| Pattern | Benefit |
|---------|---------|
| Default service = maintenance page | Graceful degradation during deployment |
| Path matchers by API version | `/v1/*` → v1 backend, `/v2/*` → v2 backend |
| Host rules by environment | `*.dev.example.com` → dev backend, `*.prod.example.com` → prod backend |

### 4.3 CI/CD Integration

- Use `gcloud compute url-maps validate` to test URL map changes before applying
- Export LB config as part of deployment pipeline
- Use Terraform for production LB management

---

## §5 Performance

### 5.1 Latency by LB Type

| LB Type | Typical Latency (P50) | Comments |
|---------|----------------------|----------|
| Global HTTPS LB (external) | 5-20ms | Anycast edge PoP closest to client |
| Regional HTTPS LB (external) | 10-30ms | Single region, no anycast |
| Internal application LB | < 5ms | Inside VPC |
| Passthrough Network LB | < 2ms | Direct forwarding |

### 5.2 Key Metrics with Thresholds

| Metric | Good | Warning | Critical |
|--------|------|---------|----------|
| P50 latency | < 100ms | 100-500ms | > 500ms |
| P99 latency | < 1s | 1-5s | > 5s |
| Backend 5xx rate | < 0.1% | 0.1-1% | > 1% |
| Healthy backends ratio | 100% | 80-99% | < 80% |

### 5.3 Auto-Scaling Triggers

| Metric | Scaling Action | Implementation |
|--------|---------------|----------------|
| CPU utilization > 80% | Scale up MIG | Balancing mode UTILIZATION, maxUtilization 0.8 |
| Request rate per instance > 100 RPS | Scale up MIG | Balancing mode RATE, maxRatePerInstance 100 |
| P99 latency > 1s | Scale up MIG | Custom metric from Cloud Monitoring |

### 5.4 Performance Optimization Tips

- Use **global LB** for latency optimization (anycast edge PoP)
- Enable **CDN** for cacheable content to reduce backend load
- Set **connection draining timeout** to 300s for graceful deployments
- Use **session affinity** (GENERATED_COOKIE or HEADER_FIELD) for stateful backends
- Avoid **CLIENT_IP** affinity for uneven traffic distribution
- Configure **timeouts** per backend service based on application needs