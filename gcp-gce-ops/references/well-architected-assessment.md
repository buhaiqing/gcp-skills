# Well-Architected Assessment — Compute Engine

## §1 Security

| IAM Role | Use Case |
|----------|----------|
| roles/compute.instanceAdmin.v1 | Full GCE API — production |
| roles/compute.instanceAdmin | Instance CRUD + disk/snapshot |
| roles/compute.viewer | Read-only monitoring |

**Credentials**: Never log SA key content. Only check: `test -f "$GOOGLE_APPLICATION_CREDENTIALS"`
**Shielded VM**: Enable Secure Boot + vTPM + Integrity Monitoring.
**CMEK**: Use Customer-Managed Encryption Keys for sensitive data.
**OS Login**: Prefer OS Login over SSH key metadata.

## §2 Stability

| Strategy | Implementation |
|----------|---------------|
| MIG auto-healing | Health check → recreate unhealthy instances |
| Multi-zone MIG | Regional MIG with distribution zones |
| Disk snapshots | Pre-delete snapshot; schedule automated backups |
| Machine images | Full instance backup (disk + config) |

DR Runbook:
1. Confirm primary zone failed
2. Update MIG distribution policy to healthy zone
3. Restore machine images if needed
4. Update DNS / LB backend

## §3 Cost

| Model | Discount | Best For |
|-------|----------|----------|
| Sustained Use | Auto: up to 30% | Steady workloads |
| Committed Use (1yr) | ~57% | Predictable workloads |
| Committed Use (3yr) | ~70% | Long-term workloads |
| Spot VMs | 60-91% | Batch, fault-tolerant |

Idle detection: Alert on CPU < 5% for 7 days → right-size or stop.

## §4 Efficiency

- Custom machine types: right-size CPU/memory
- Instance templates: repeatable deployment
- Labels: cost tracking (`env`, `app`, `team`)
- Batch ops: `gcloud compute instances create --source-instance-template`

## §5 Performance

| Disk Type | Max IOPS | Max Throughput | Use Case |
|-----------|----------|---------------|----------|
| pd-standard | 300 | 40 MB/s | Boot, low I/O |
| pd-balanced | 15,000 | 200 MB/s | General purpose |
| pd-ssd | 30,000 | 350 MB/s | High performance |
| pd-extreme | 300,000 | 1,000 MB/s | Extreme I/O |

Auto-scaling: CPU > 80% → scale MIG up; CPU < 30% → scale down.
