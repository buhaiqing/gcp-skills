# gcp-cloudsql-ops — TODO

## ✅ Completed Features

- [x] Instance lifecycle: Create, Describe, Update, Delete
- [x] Backup/Restore: Create backup, List backups, Restore backup
- [x] Read replicas: Create read replica, Promote replica
- [x] Export/Import database (SQL & CSV)
- [x] Database CRUD: Create, List, Describe, Delete
- [x] User management: Create, List, Set password, Describe, Delete
- [x] Query Insights enablement
- [x] Restart instance
- [x] Dual-path execution (gcloud CLI + Python/Go SDK)
- [x] Failure Recovery tables on all operations
- [x] Safety gates on all destructive operations
- [x] GCL quality gate (rubric + prompt templates)
- [x] Well-Architected Assessment (5 pillars)
- [x] Monitoring metrics and alert policies
- [x] Troubleshooting guide with 20+ error codes
- [x] Idempotency checklist
- [x] Token efficiency (TE-1 through TE-6)
- [x] SKILL.md <= 500 lines refactored
- [x] Prerequisites moved to core-concepts.md
- [x] SDK code blocks centralized in api-sdk-usage.md / integration.md
- [x] references/advanced/ directory created

## 🔜 Planned Features

- [ ] Advanced: AIOps query insights anomaly detection (references/advanced/aiops-query-insights.md)
- [ ] Advanced: FinOps cost optimization (references/advanced/finops-cost-analysis.md)
- [ ] Advanced: SQL execution with security confirmation (references/advanced/sql-execution.md)
- [ ] PITR clone operation
- [ ] Cross-region replica failover runbook
- [ ] Instance rotate-server-ca operation
- [ ] Reschedule maintenance operation