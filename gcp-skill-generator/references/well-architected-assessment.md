# Well-Architected Assessment — GCP Skill Generator

> **Purpose:** Defines how every generated `gcp-[product]-ops` skill MUST incorporate the [Google Cloud Architecture Framework](https://cloud.google.com/architecture/framework) five pillars into its generated content.
> **Version:** 1.0.0
> **Last Updated:** 2026-06-07
> **Status:** MANDATORY — all generated skills MUST include well-architected assessment patterns

---

## Table of Contents

1. [Framework Overview](#1-framework-overview)
2. [五支柱 Skill 集成规范](#2-五支柱-skill-集成规范)
3. [Skill 生成集成点](#3-skill-生成集成点)

---

## 1. Framework Overview

Google Cloud Architecture Framework defines five pillars for cloud architecture excellence:

| Pillar | Core Focus | Official Doc |
|--------|-----------|--------------|
| **Security** | Identity, network, data protection; threat detection | [Security pillar](https://cloud.google.com/architecture/framework/security) |
| **Stability** | High availability, disaster recovery, failure-oriented design | [Reliability pillar](https://cloud.google.com/architecture/framework/reliability) |
| **Cost** | Cost visibility, optimization, committed use, waste elimination | [Cost optimization pillar](https://cloud.google.com/architecture/framework/cost-optimization) |
| **Efficiency** | DevOps, automation, CI/CD, operational model | [Operational efficiency pillar](https://cloud.google.com/architecture/framework/operational-efficiency) |
| **Performance** | Auto-scaling, observability, performance baselines | [Performance optimization pillar](https://cloud.google.com/architecture/framework/performance-optimization) |

---

## 2. 五支柱 Skill 集成规范

### 2.1 Security Pillar (安全)

Every generated skill MUST address security in at least these areas:

#### IAM Requirements

```markdown
### Required IAM Roles

| API Operation | Required IAM Role |
|---------------|------------------|
| [Operation] | roles/[product].[role] |
| [Operation] | roles/[product].[role] |
```

- **Do NOT** use `roles/owner` or `roles/editor` for skill execution
- **Do** use service accounts with least-privilege roles
- **Do** document VPC Service Controls and Private Google Access where applicable

#### Credential Safety

- Service account keys: document expiration and rotation
- Workload Identity Federation: preferred over SA keys for GKE/Cloud Run
- Impersonation: prefer `--impersonate-service-account` over key files

### 2.2 Stability Pillar (稳定)

#### Backup & Recovery

| Scenario | Method | Target RPO | Target RTO |
|----------|--------|-----------|-----------|
| Resource deletion | Snapshot/backup before delete | 24h | 1h |
| Data corruption | Point-in-time recovery (PITR) | 5min (if PITR) | 1h |
| Regional outage | Cross-region replication | 1h | 4h |

#### Multi-Region / Multi-Zone

- Document whether product supports regional vs zonal resources
- Suggest multi-region deployment patterns where applicable
- Document `--zone` vs `--region` usage

### 2.3 Cost Pillar (成本)

#### Pricing Model Comparison

| Model | Use Case | Savings |
|-------|----------|---------|
| On-demand | Short-lived workloads | None |
| Committed Use Discount (CUD) | Steady-state workloads | Up to 70% |
| Preemptible/Spot | Batch, fault-tolerant | Up to 91% |
| Sustained Use Discount (SUD) | Running > 25% of month | Auto-applied |

#### Idle Resource Detection

| Pattern | Detection | Action |
|---------|-----------|--------|
| Low CPU (< 5% for 14 days) | Cloud Monitoring | Right-size or stop |
| Unattached disk | `gcloud compute disks list --filter="-users:*"` | Delete or snapshot |
| Unused IP | `gcloud compute addresses list --filter="status=RESERVED"` | Release |

### 2.4 Efficiency Pillar (效率)

#### Automation Patterns

- Document `gcloud` → script → CI/CD pipeline migration
- Deployment Manager / Terraform integration patterns
- Batch operation: `for` loop or `--parallel` where applicable

### 2.5 Performance Pillar (性能)

#### Key Cloud Monitoring Metrics

| Metric | Product | Threshold |
|--------|---------|-----------|
| CPU utilization | Compute Engine | > 80% for > 5min |
| Memory utilization | Compute Engine | > 90% for > 5min |
| Disk IOPS | Persistent Disk | > 80% of limit |
| Network throughput | Any | > 80% of limit |

#### Auto-scaling Triggers

| Metric | Scale-out | Scale-in |
|--------|-----------|----------|
| CPU utilization | > 70% for 1min | < 50% for 5min |
| Requests/sec (LB) | > 1000 per instance | < 300 per instance |

---

## 3. Skill 生成集成点

### 3.1 集成深度矩阵

| Skill Type | Security | Stability | Cost | Efficiency | Performance |
|-----------|----------|-----------|------|------------|-------------|
| **CRUD/Lifecycle** (GCE, Cloud SQL) | Required | Required | Required | Recommended | Required |
| **Monitoring/Diagnosis** | Recommended | Required | Recommended | Required | Required |
| **Security/Access** (IAM, KMS) | Required | Recommended | Optional | Recommended | Optional |
| **Discovery/Read-Only** | Optional | Optional | Optional | Optional | Optional |

### 3.2 生成时注入位置

Each generated skill MUST include a `well-architected-assessment.md` reference file with:
- Product-specific IAM permissions table
- Backup and restore workflow documentation
- Pricing model recommendations
- Performance baseline metrics