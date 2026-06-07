# Well-Architected Assessment — Cloud IAM

## §1 Security

| IAM Role | Use Case |
|----------|----------|
| roles/iam.securityAdmin | Full IAM policy management (production) |
| roles/iam.roleAdmin | Custom role CRUD |
| roles/iam.serviceAccountAdmin | Service account management |
| roles/iam.serviceAccountKeyAdmin | SA key lifecycle management |
| roles/iam.workloadIdentityUser | Impersonate SAs via Workload Identity |
| roles/iam.denyAdmin | IAM Deny policy management |
| roles/iam.organizationRoleAdmin | Organization-level custom role admin |

**Credentials**: Never log SA key content or private key data. Mask in all outputs.
**Key Rotation**: Regularly rotate SA keys. Set expiry on new keys. Prefer Workload Identity Federation over keys.
**Conditions**: Use IAM conditions for time-bound or resource-scoped access (CEL expressions).
**Deny Policies**: Implement defense-in-depth with IAM Deny for additional protection.
**Least Privilege**: Use predefined roles when possible; custom roles for fine-grained needs.
**Break-glass**: Maintain emergency access accounts at the organization level.

## §2 Stability

| Strategy | Implementation |
|----------|---------------|
| Policy etag | Read-modify-write pattern prevents concurrent overwrite |
| Role undelete | Deleted custom roles can be undeleted within 7 days |
| SA key rotation | Overlapping key rotation (create new, switch, delete old) |
| Policy backup | Export IAM policy before making changes |
| Audit trail | Cloud Audit Logs record all IAM changes |

DR Runbook:
1. If SA deleted: recreate with same ID; re-apply IAM bindings; re-create keys
2. If IAM policy corrupted: restore from backup (policy JSON export)
3. If custom role deleted: `gcloud iam roles undelete ROLE_ID --project=PROJECT`
4. If SA key compromised: create new key, update services, delete old key

## §3 Cost

| Model | Description | Best For |
|-------|-------------|----------|
| Predefined roles | No cost to use; included with GCP services | All workloads |
| Custom roles | No additional cost; subject to quota limits | Fine-grained access needs |
| SA key management | Key operations free; storage costs negligible | Automated workloads |
| Workload Identity Federation | Free to use; reduces SA key dependency | External identity workloads |

Idle detection: Alert on SAs unused for 90 days (no authentication activity) → audit and clean up.

## §4 Efficiency

- Custom roles: create once, reuse across projects
- Policy binding: bulk add/remove members with `--condition`
- Policy Analyzer: identify over-privileged accounts without manual review
- Labeling: tag service accounts with purpose, owner, expiry for lifecycle management
- Automation: use `add-iam-policy-binding` in CI/CD pipelines

## §5 Performance

| Limit | Value | Impact |
|-------|-------|--------|
| Policy size | 250KB | Large policies may be slow to set; split across resources |
| Custom role permissions | 3000 per role | Sufficient for most use cases |
| SA keys per SA | 10 | Rotate keys; delete unused ones |
| Bindings per policy | ~1500 | Use groups for member aggregation |
| Pools per project | 10 | Plan pool structure for multiple external IdPs |

Auto-scaling: Not applicable for IAM (control plane operations are always synchronous).