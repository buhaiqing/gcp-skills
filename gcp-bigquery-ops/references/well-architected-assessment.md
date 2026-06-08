# Well-Architected Assessment — Cloud BigQuery

## §1 Security

| IAM Role | Use Case |
|----------|----------|
| roles/bigquery.admin | Full BigQuery API — production admin |
| roles/bigquery.dataOwner | Full dataset/table CRUD + IAM |
| roles/bigquery.dataEditor | Dataset/table CRUD (no IAM) |
| roles/bigquery.dataViewer | Read-only data access |
| roles/bigquery.jobUser | Execute queries (requires data access too) |
| roles/bigquery.user | Access shared resources, run jobs |

**Credentials**: Never log SA key content. Only check: `test -f "$GOOGLE_APPLICATION_CREDENTIALS"`

**Encryption**: Default encryption at rest always active. Use CMEK for sensitive data via `--destination_kms_key`.

**Data Access**: Column-level and row-level security via authorized views. Row-level via security policies.

**VPC Service Controls**: Restrict data exfiltration by limiting BigQuery access to approved VPCs.

**Audit Logging**: All data access and admin operations logged to Cloud Logging. Enable Data Access logs for row-level audit.

**Materialized Views**: Pre-computed results can expose sensitive data — apply same IAM as base table.

**Routine Security**: JavaScript UDFs run in sandboxed environment. External JS libraries not permitted.

## §2 Stability

| Strategy | Implementation |
|----------|---------------|
| Dataset access controls | Restrict who can create/modify tables |
| Table snapshots | Point-in-time table copies for recovery |
| Backup exports | Export critical tables to GCS for archival |
| Default table expiration | Auto-delete stale tables |
| Partition expiration | Auto-delete old partitions |
| Query caching | Identical queries served from cache (24h) |

**Disaster Recovery Runbook**:
1. Confirm table/dataset is deleted or corrupted
2. Restore from GCS backup export: `bq load --autodetect "{{user.table_id}}" "gs://backup-bucket/table.avro"`
3. Or restore from table snapshot: `CREATE TABLE restored AS SELECT * FROM TABLE_SNAPSHOT('snapshot_id')`
4. Verify row counts: `bq show "{{user.table_id}}" --format=json | jq '.numRows'`
5. Update application references

**High Availability**: BigQuery is a managed service with automatic replication and failover within the location.

## §3 Cost

| Pricing Model | Cost | Best For |
|---------------|------|----------|
| On-Demand | $5/TB processed, first 1TB free/month | Variable, unpredictable workloads |
| Flat-Rate | $400/slot/month (100 slots = 1 unit) | Predictable, high-volume workloads |
| Storage (active) | $0.02/GB/month | Frequently modified tables |
| Storage (long-term) | $0.01/GB/month | Tables not modified for 90+ days |

**Cost Optimization**:
- Always `--dry_run` before executing large queries
- Use partition pruning — filter on partition column
- Cluster on frequently filtered columns
- Use materialized views for repeated aggregations
- Set table expiration policies on temporary data
- Set partition expiration for old data
- Use query result caching for repeated queries
- Use `--max_bytes_billed` to cap query cost
- Monitor cost via `INFORMATION_SCHEMA.JOBS_BY_PROJECT`
- Consider flat-rate reservations for predictable workloads
- Use BI Engine for interactive dashboards (faster, lower cost)

## §4 Efficiency

- **Partitioning**: Split large tables by date/time/integer — reduces bytes scanned
- **Clustering**: Sort within partitions — improves filter/aggregation performance (up to 4 columns)
- **Materialized Views**: Pre-computed results — automatic refresh, query rewrites
- **Query Caching**: Identical queries served from cache — free, 24h validity
- **Table Design**: Normalize where needed, denormalize for query performance
- **Schema Evolution**: Add columns easily (append mode). Removing requires table recreation.
- **External Tables**: Query GCS data without loading — slower but cost-effective for rare access
- **Streaming Inserts**: Real-time data ingestion — use `tabledata.insertAll` API
- **Labels**: Cost tracking (`env`, `app`, `team`, `project`)

**Naming Convention**: `{project}_{dataset}_{table}` — descriptive, lowercase with underscores.

## §5 Performance

| Factor | Impact | Optimization |
|--------|--------|--------------|
| Partition pruning | Reduces bytes scanned 10-100x | Always filter on partition column |
| Clustering | Reduces bytes scanned 2-10x | Cluster on WHERE/JOIN columns |
| Query caching | Zero cost, instant response | Reuse identical queries |
| Materialized views | Pre-computed results | For repeated aggregations |
| Slot availability | Determines concurrency | Use reservations for guaranteed capacity |
| Result size | 1GB API limit | Use destination table for large results |
| BI Engine | In-memory acceleration | For dashboard/BI workloads |

**Performance Optimization**:
- Co-locate datasets with compute (same region)
- Use standard SQL (not legacy SQL)
- Avoid SELECT * — specify needed columns
- Use approximate aggregation functions (APPROX_COUNT_DISTINCT) for large datasets
- Use ARRAY_AGG instead of JOIN when possible
- Avoid cross joins
- Use EXPLAIN to analyze query plans
- Use INFORMATION_SCHEMA for metadata queries

**Benchmark**: BigQuery can process terabytes in seconds, petabytes in minutes, on fully-managed infrastructure.
