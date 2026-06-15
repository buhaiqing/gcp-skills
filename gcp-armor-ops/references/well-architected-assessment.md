# Well-Architected Assessment — Google Cloud Armor

## Security Pillar

### Minimum IAM Permissions

| Role | Permissions | Use Case |
|------|-------------|----------|
| `roles/compute.securityAdmin` | Full security policy management | Admin operations |
| `roles/compute.securityPolicyUser` | View policies, attach to backend | Read-only + attach |
| `roles/logging.logWriter` | Write audit logs | Logging integration |

### Credential Masking

All credential references use `{{env.*}}` placeholders. Never log or expose:
- Service account key content
- Access tokens
- API keys

### VPC Service Controls

Recommend VPC SC perimeter for sensitive workloads:
- Restrict security policy modifications to specific projects
- Enable audit logging for all policy changes

## Stability Pillar

### Backup/Restore

- Security policies are versioned (fingerprints)
- Rules can be exported/imported via JSON
- No traditional backup needed; state is managed

### Multi-Region

- Security policies are global resources
- Rules evaluate at edge locations worldwide
- No regional failover required

### DR Runbook

1. Export security policy rules (JSON)
2. Recreate policy in DR project
3. Attach to DR backend services
4. Verify protection is active

## Cost Pillar

### Pricing Model

| Component | Cost |
|-----------|------|
| Security policies | Free |
| WAF rules | Free (pre-configured rules included) |
| Adaptive protection | Free (ML models included) |
| Request-based billing | Per 10,000 requests |

### Right-Sizing

- Monitor request volume to optimize costs
- Use adaptive protection to auto-tune rules
- Review denied requests to reduce false positives

## Efficiency Pillar

### Batch Operations

- Bulk rule creation via JSON import
- Automated rule updates via CI/CD
- Policy templates for common patterns

### Automation

- Terraform integration for policy-as-code
- Cloud Build for automated rule deployment
- GitOps workflow for rule management

## Performance Pillar

### Key Metrics

| Metric | Threshold |
|--------|-----------|
| Rule evaluation latency | < 1ms |
| Request throughput | No limit |
| DDoS mitigation | Automatic |

### Auto-Scaling

- Adaptive protection auto-tunes rules
- Rate limiting scales with traffic
- No manual scaling required
