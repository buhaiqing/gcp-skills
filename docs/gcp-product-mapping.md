# GCP Product → Directory Mapping

> **Purpose:** Reference mapping of GCP products to their skill directories.
> **Lazy-loaded by:** AGENTS.md Appendix A

---

## Active Skills

| GCP Product | Directory | Operations |
|-------------|-----------|------------|
| Compute Engine | `gcp-gce-ops` | VM lifecycle, disks, snapshots, instance groups |
| Google Kubernetes Engine | `gcp-gke-ops` | Cluster lifecycle, node pools, workloads, IAM |
| Cloud SQL | `gcp-cloudsql-ops` | MySQL/PostgreSQL/SQL Server instances, backups |
| Cloud Storage | `gcp-gcs-ops` | Buckets, objects, lifecycle policies, IAM |
| Cloud Run | `gcp-cloudrun-ops` | Services, revisions, traffic splitting |
| Cloud Functions | `gcp-cloudfunctions-ops` | Functions, triggers, source repos |
| Cloud Build | `gcp-cloudbuild-ops` | Triggers, builds, artifacts |
| Cloud Monitoring | `gcp-monitoring-ops` | Metrics, dashboards, alert policies |
| Cloud Logging | `gcp-logging-ops` | Log buckets, views, log-based metrics |
| Cloud IAM | `gcp-iam-ops` | Roles, policies, service accounts |
| Cloud VPC | `gcp-vpc-ops` | Networks, subnets, firewall rules, VPN |
| Cloud DNS | `gcp-dns-ops` | Zones, records, policies |
| Cloud Load Balancing | `gcp-lb-ops` | Forwarding rules, backend services, health checks |
| Cloud CDN | `gcp-cdn-ops` | Origins, cache policies |
| Cloud Pub/Sub | `gcp-pubsub-ops` | Topics, subscriptions, schemas |
| Cloud BigQuery | `gcp-bigquery-ops` | Datasets, tables, queries, jobs |
| Cloud Spanner | `gcp-spanner-ops` | Instances, databases, backups |
| Cloud Bigtable | `gcp-bigtable-ops` | Instances, clusters, tables |
| Cloud Memorystore (Redis) | `gcp-memorystore-ops` | Redis/Memcached instances |
| Cloud Filestore | `gcp-filestore-ops` | Fileshares, backups |
| Cloud KMS | `gcp-kms-ops` | Key rings, keys, versions |
| Cloud Secret Manager | `gcp-secretmanager-ops` | Secrets, versions, IAM |
| Cloud Deployment Manager | `gcp-deployment-ops` | Deployments, templates |
| Cloud Resource Manager | `gcp-resourcemanager-ops` | Projects, folders, organizations |
| Cloud Billing | `gcp-billing-ops` | Budgets, exports, cost analysis |

---

## Planned Skills

For each planned skill, a corresponding `gcp-[product]-ops/` directory should be created following the canonical structure in AGENTS.md.
