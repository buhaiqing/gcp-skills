# gcloud — Cloud SQL CLI

## Conventions
- Always use `--format=json` for machine-parseable output
- Operations API polling: gcloud built-in waiter (returns when DONE)
- **Password security**: `--password` in `gcloud` commands is safe — passwords are transmitted over HTTPS to the Cloud SQL Admin API and never exposed in `ps aux` or shell history. For **local DB client connections** (via `mysql`/`psql`), NEVER use `-p<PASSWORD>` — use `MYSQL_PWD` or `PGPASSWORD` environment variables instead to prevent password exposure.
- Instance names are project-unique; no zone qualification needed

## Command Map: Instances

| Goal | gcloud command |
|------|---------------|
| Create | gcloud sql instances create NAME --region=R --database-version=V --tier=T --format=json |
| Describe | gcloud sql instances describe NAME --format=json |
| List | gcloud sql instances list --format=json |
| Patch | gcloud sql instances patch NAME --tier=T --database-flags=K=V --format=json |
| Delete | gcloud sql instances delete NAME --format=json |
| Restart | gcloud sql instances restart NAME --format=json |
| Clone | gcloud sql instances clone NAME NEW_NAME --format=json |
| Promote replica | gcloud sql instances promote-replica NAME --format=json |
| List operations | gcloud sql operations list --instance=NAME --format=json |
| Describe operation | gcloud sql operations describe OP_ID --format=json |

## Command Map: Backups

| Goal | gcloud command |
|------|---------------|
| Create (on-demand) | gcloud sql backups create --instance=NAME --description=D --format=json |
| List | gcloud sql backups list --instance=NAME --format=json |
| Describe | gcloud sql backups describe BACKUP_ID --instance=NAME --format=json |
| Restore | gcloud sql backups restore BACKUP_ID --restore-instance=NAME --format=json |
| Delete | gcloud sql backups delete BACKUP_ID --instance=NAME --format=json |

## Command Map: Databases

| Goal | gcloud command |
|------|---------------|
| Create | gcloud sql databases create DB_NAME --instance=NAME --format=json |
| List | gcloud sql databases list --instance=NAME --format=json |
| Describe | gcloud sql databases describe DB_NAME --instance=NAME --format=json |
| Delete | gcloud sql databases delete DB_NAME --instance=NAME --format=json |

## Command Map: Users

| Goal | gcloud command |
|------|---------------|
| Create | gcloud sql users create USER_NAME --instance=NAME --password=P --format=json |
| List | gcloud sql users list --instance=NAME --format=json |
| Describe | gcloud sql users describe USER_NAME --instance=NAME --format=json |
| Set password | gcloud sql users set-password USER_NAME --instance=NAME --password=P --format=json |
| Delete | gcloud sql users delete USER_NAME --instance=NAME --format=json |

## Command Map: Export/Import

| Goal | gcloud command |
|------|---------------|
| Export SQL | gcloud sql export sql NAME gs://BUCKET/PATH --database=DB --format=json |
| Export CSV | gcloud sql export csv NAME gs://BUCKET/PATH --database=DB --query=SQL --format=json |
| Import SQL | gcloud sql import sql NAME gs://BUCKET/PATH --database=DB --format=json |
| Import CSV | gcloud sql import csv NAME gs://BUCKET/PATH --database=DB --table=T --format=json |

## Command Map: Flags & Maintenance

| Goal | gcloud command |
|------|---------------|
| List flags | gcloud sql flags list --database-version=V --format=json |
| Set flag | gcloud sql instances patch NAME --database-flags=K=V --format=json |
| Remove flag | gcloud sql instances patch NAME --database-flags=K="" --format=json |
| Set maintenance | gcloud sql instances patch NAME --maintenance-window-day=D --maintenance-window-hour=H --format=json |
| Enable Query Insights | gcloud sql instances patch NAME --insights-config-query-insights-enabled --format=json |
| Enable deletion protection | gcloud sql instances patch NAME --deletion-protection --format=json |
| Remove deletion protection | gcloud sql instances patch NAME --no-deletion-protection --format=json |

## CLI vs API Coverage

| Operation | gcloud | Notes |
|-----------|--------|-------|
| Instance CRUD | ✅ | Fully covered |
| Backup create/list/restore/delete | ✅ | Fully covered |
| Database CRUD | ✅ | Fully covered |
| User CRUD | ✅ | Fully covered |
| Export/Import | ✅ | Fully covered |
| Flags & Maintenance | ✅ | Fully covered |
| Query Insights | ✅ | Fully covered |
| Clone | ✅ | gcloud sql instances clone |
| Failover | ✅ | gcloud sql instances failover |
| Auth Proxy setup | ❌ | Manual download; documented in integration.md |
| Rotate server CA cert | ✅ | gcloud sql instances rotate-server-ca |
| Reschedule maintenance | ✅ | gcloud sql instances reschedule-maintenance |
| SQL Server SSIS catalog | ✅ | gcloud sql instances create --enable-ssis-db |