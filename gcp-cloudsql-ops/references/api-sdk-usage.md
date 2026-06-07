# API & SDK — Cloud SQL

## REST API
- Discovery doc: https://sqladmin.googleapis.com/$discovery/rest?version=v1
- Base URL: https://sqladmin.googleapis.com/v1/

## Operations Map

| Goal | REST Method | Python SDK Method |
|------|------------|-------------------|
| Create instance | POST /v1/projects/{p}/instances | SqlInstancesServiceClient.Insert() |
| Get instance | GET /v1/projects/{p}/instances/{i} | SqlInstancesServiceClient.Get() |
| List instances | GET /v1/projects/{p}/instances | SqlInstancesServiceClient.List() |
| Update instance | PATCH /v1/projects/{p}/instances/{i} | SqlInstancesServiceClient.Patch() |
| Delete instance | DELETE /v1/projects/{p}/instances/{i} | SqlInstancesServiceClient.Delete() |
| Restart instance | POST /v1/projects/{p}/instances/{i}/restart | SqlInstancesServiceClient.Restart() |
| Promote replica | POST /v1/projects/{p}/instances/{i}/promoteReplica | SqlInstancesServiceClient.PromoteReplica() |
| Export | POST /v1/projects/{p}/instances/{i}/export | SqlInstancesServiceClient.Export() |
| Import | POST /v1/projects/{p}/instances/{i}/import | SqlInstancesServiceClient.Import() |
| Create backup | POST /v1/projects/{p}/instances/{i}/backupRuns | SqlBackupRunsServiceClient.Insert() |
| List backups | GET /v1/projects/{p}/instances/{i}/backupRuns | SqlBackupRunsServiceClient.List() |
| Restore backup | POST /v1/projects/{p}/instances/{i}/restoreBackup | SqlBackupRunsServiceClient.RestoreBackup() |
| Create database | POST /v1/projects/{p}/instances/{i}/databases | SqlDatabasesServiceClient.Insert() |
| List databases | GET /v1/projects/{p}/instances/{i}/databases | SqlDatabasesServiceClient.List() |
| Delete database | DELETE /v1/projects/{p}/instances/{i}/databases/{db} | SqlDatabasesServiceClient.Delete() |
| Create user | POST /v1/projects/{p}/instances/{i}/users | SqlUsersServiceClient.Insert() |
| List users | GET /v1/projects/{p}/instances/{i}/users | SqlUsersServiceClient.List() |
| Update user | PUT /v1/projects/{p}/instances/{i}/users?name={u} | SqlUsersServiceClient.Update() |
| Delete user | DELETE /v1/projects/{p}/instances/{i}/users?name={u}&host={h} | SqlUsersServiceClient.Delete() |
| Get operation | GET /v1/projects/{p}/operations/{op} | SqlOperationsServiceClient.Get() |
| List operations | GET /v1/projects/{p}/operations | SqlOperationsServiceClient.List() |
| List tiers | GET /v1/projects/{p}/tiers | SqlTiersServiceClient.List() |

## Key JSON Paths (Centralized)

| Operation | JSON Path | Description |
|-----------|-----------|-------------|
| Create instance | $.name | Operation name |
| Describe instance | $.{state,name,region,databaseVersion,settings.tier,settings.dataDiskSizeGb,ipAddresses} | Instance details |
| List instances | $.items[].{name,state,region,databaseVersion,settings.tier} | Instance list |
| Create backup | $.id | Backup identifier |
| List backups | $.items[].{id,description,status,type,enqueuedTime} | Backup list |
| Describe operation | $.{status,error} | Operation tracking |
| Create database | $.name | Operation name |
| Create user | $.name | Operation name |
| List tiers | $.items[].{tier,region,maxRamGB} | Available tiers |
| Clone instance | $.name | Operation name |

## Python SDK Code Snippets

All snippets use `google.cloud.sql_v1`. Set env vars `CLOUDSDK_CORE_PROJECT`, `SQL_INSTANCE_NAME`, `SQL_REGION`, `SQL_TIER`, `SQL_DATABASE_VERSION` before execution. Install: `pip install --quiet --user google-cloud-sql`.

> **Security**: SDK auto-reads credentials from `GOOGLE_APPLICATION_CREDENTIALS`. NEVER log credential values.

### Create Instance

```python
import os
from google.cloud import sql_v1
client = sql_v1.SqlInstancesServiceClient()
instance = sql_v1.DatabaseInstance()
instance.name = os.environ.get("SQL_INSTANCE_NAME", "my-instance")
instance.region = os.environ.get("SQL_REGION", "us-central1")
instance.database_version = sql_v1.DatabaseVersion.MYSQL_8_0
instance.settings = sql_v1.Settings()
instance.settings.tier = os.environ.get("SQL_TIER", "db-n1-standard-2")
instance.settings.data_disk_size_gb = 100
instance.settings.data_disk_type = "PD_SSD"
instance.settings.backup_configuration = sql_v1.BackupConfiguration()
instance.settings.backup_configuration.enabled = True
instance.settings.backup_configuration.start_time = "03:00"
op = client.insert(project=os.environ["CLOUDSDK_CORE_PROJECT"], body=instance)
op.result(timeout=600)
print(f"Created: {instance.name}")
```

### Describe Instance

```python
import os
from google.cloud import sql_v1
client = sql_v1.SqlInstancesServiceClient()
resp = client.get(project=os.environ["CLOUDSDK_CORE_PROJECT"], instance="{{user.instance_name}}")
print(f"Name: {resp.name}, State: {resp.state}, DB: {resp.database_version}")
```

### Update Instance

```python
import os
from google.cloud import sql_v1
client = sql_v1.SqlInstancesServiceClient()
settings = sql_v1.Settings()
settings.tier = os.environ.get("SQL_TIER", "db-n1-standard-4")
settings.database_flags = [{"name": "max_connections", "value": "250"}]
op = client.update(project=os.environ["CLOUDSDK_CORE_PROJECT"], instance="{{user.instance_name}}", body={"settings": settings})
op.result(timeout=300)
```

### Delete Instance

```python
import os
from google.cloud import sql_v1
client = sql_v1.SqlInstancesServiceClient()
op = client.delete(project=os.environ["CLOUDSDK_CORE_PROJECT"], instance="{{user.instance_name}}")
op.result(timeout=300)
print(f"Deleted: {{user.instance_name}}")
```

### Create Backup

```python
import os
from google.cloud import sql_v1
client = sql_v1.SqlBackupRunsServiceClient()
op = client.insert(project=os.environ["CLOUDSDK_CORE_PROJECT"], instance="{{user.instance_name}}", body={"description": "on-demand"})
op.result(timeout=600)
```

### List Backups

```python
import os
from google.cloud import sql_v1
client = sql_v1.SqlBackupRunsServiceClient()
for b in client.list(project=os.environ["CLOUDSDK_CORE_PROJECT"], instance="{{user.instance_name}}"):
    print(f"ID: {b.id}, Status: {b.status}, Type: {b.type}")
```

### Restore Backup

```python
import os
from google.cloud import sql_v1
client = sql_v1.SqlBackupRunsServiceClient()
op = client.restore_backup(project=os.environ["CLOUDSDK_CORE_PROJECT"], instance="{{user.instance_name}}",
    body={"restoreBackupContext": {"backupRunId": {{user.backup_id}}, "instanceId": "{{user.instance_name}}"}})
op.result(timeout=600)
```

### Create Read Replica

```python
import os
from google.cloud import sql_v1
client = sql_v1.SqlInstancesServiceClient()
replica = sql_v1.DatabaseInstance()
replica.name = "{{user.replica_name}}"
replica.region = "{{user.region}}"
replica.database_version = sql_v1.DatabaseVersion.MYSQL_8_0
replica.settings = sql_v1.Settings()
replica.settings.tier = "db-n1-standard-2"
replica.master_instance_name = "{{user.instance_name}}"
op = client.insert(project=os.environ["CLOUDSDK_CORE_PROJECT"], body=replica)
op.result(timeout=600)
```

### Promote Replica

```python
import os
from google.cloud import sql_v1
client = sql_v1.SqlInstancesServiceClient()
op = client.promote_replica(project=os.environ["CLOUDSDK_CORE_PROJECT"], instance="{{user.replica_name}}")
op.result(timeout=300)
```

### Export Database

```python
import os
from google.cloud import sql_v1
client = sql_v1.SqlInstancesServiceClient()
ctx = sql_v1.ExportContext()
ctx.file_type = sql_v1.ExportContext.SqlFileType.SQL
ctx.uri = "gs://{{user.gcs_bucket}}/{{user.gcs_path}}"
ctx.databases = ["{{user.database_name}}"]
op = client.export(project=os.environ["CLOUDSDK_CORE_PROJECT"], instance="{{user.instance_name}}", body={"exportContext": ctx})
op.result(timeout=1800)
```

### Import Database

```python
import os
from google.cloud import sql_v1
client = sql_v1.SqlInstancesServiceClient()
ctx = sql_v1.ImportContext()
ctx.file_type = sql_v1.ImportContext.SqlFileType.SQL
ctx.uri = "gs://{{user.gcs_bucket}}/{{user.gcs_path}}"
ctx.database = "{{user.database_name}}"
op = client.import_(project=os.environ["CLOUDSDK_CORE_PROJECT"], instance="{{user.instance_name}}", body={"importContext": ctx})
op.result(timeout=1800)
```

### Create Database

```python
import os
from google.cloud import sql_v1
client = sql_v1.SqlDatabasesServiceClient()
op = client.insert(project=os.environ["CLOUDSDK_CORE_PROJECT"], instance="{{user.instance_name}}", body={"name": "{{user.database_name}}"})
op.result(timeout=120)
```

### Delete Database

```python
import os
from google.cloud import sql_v1
client = sql_v1.SqlDatabasesServiceClient()
op = client.delete(project=os.environ["CLOUDSDK_CORE_PROJECT"], instance="{{user.instance_name}}", database="{{user.database_name}}")
op.result(timeout=120)
print(f"Deleted database: {{user.database_name}}")
```

### Create User

```python
import os
from google.cloud import sql_v1
client = sql_v1.SqlUsersServiceClient()
user = sql_v1.User()
user.name = "{{user.user_name}}"
user.password = os.environ.get("SQL_USER_PASSWORD", "{{user.password}}")
op = client.insert(project=os.environ["CLOUDSDK_CORE_PROJECT"], instance="{{user.instance_name}}", body=user)
op.result(timeout=120)
```

### Enable Query Insights

```python
import os
from google.cloud import sql_v1
client = sql_v1.SqlInstancesServiceClient()
settings = sql_v1.Settings()
settings.insights_config = sql_v1.InsightsConfig()
settings.insights_config.query_insights_enabled = True
settings.insights_config.record_application_tags = True
settings.insights_config.record_client_address = True
op = client.patch(project=os.environ["CLOUDSDK_CORE_PROJECT"], instance="{{user.instance_name}}", body={"settings": settings})
op.result(timeout=300)
```

### Restart Instance

```python
import os
from google.cloud import sql_v1
client = sql_v1.SqlInstancesServiceClient()
op = client.restart(project=os.environ["CLOUDSDK_CORE_PROJECT"], instance="{{user.instance_name}}")
op.result(timeout=300)
```