# API & SDK — Cloud BigQuery

## REST API
- Discovery doc: https://bigquery.googleapis.com/$discovery/rest?version=v2
- Base URL: https://bigquery.googleapis.com/bigquery/v2/

## Operations Map

| Goal | REST Method | Python SDK Method | Go SDK Method |
|------|------------|-------------------|---------------|
| Create dataset | POST /projects/{p}/datasets | client.create_dataset() | Client.Dataset().Create() |
| Get dataset | GET /projects/{p}/datasets/{d} | client.get_dataset() | Client.Dataset().Metadata() |
| List datasets | GET /projects/{p}/datasets | client.list_datasets() | Client.Datasets() |
| Update dataset | PATCH /projects/{p}/datasets/{d} | client.update_dataset() | Client.Dataset().Update() |
| Delete dataset | DELETE /projects/{p}/datasets/{d} | client.delete_dataset() | Client.Dataset().Delete() |
| Create table | POST /projects/{p}/datasets/{d}/tables | client.create_table() | Client.Dataset().Table().Create() |
| Get table | GET /projects/{p}/datasets/{d}/tables/{t} | client.get_table() | Client.Dataset().Table().Metadata() |
| List tables | GET /projects/{p}/datasets/{d}/tables | client.list_tables() | Client.Dataset().Tables() |
| Update table | PATCH /projects/{p}/datasets/{d}/tables/{t} | client.update_table() | Client.Dataset().Table().Update() |
| Delete table | DELETE /projects/{p}/datasets/{d}/tables/{t} | client.delete_table() | Client.Dataset().Table().Delete() |
| Query | POST /projects/{p}/queries | client.query() | Client.Query().Read() |
| Get job | GET /projects/{p}/jobs/{j} | client.get_job() | Client.JobFromID().Status() |
| Cancel job | POST /projects/{p}/jobs/{j}/cancel | client.cancel_job() | Client.JobFromID().Cancel() |
| List jobs | GET /projects/{p}/jobs | client.list_jobs() | Client.Jobs() |
| Insert data | POST /projects/{p}/datasets/{d}/tables/{t}/insertAll | client.insert_rows() | Client.Dataset().Table().Inserter().Put() |
| Load job | POST /projects/{p}/jobs (config.load) | client.load_table_from_uri() | Client.LoadFromGCS() |
| Extract job | POST /projects/{p}/jobs (config.extract) | client.extract_table_to_uri() | Client.Dataset().Table().ExtractorTo() |
| Copy job | POST /projects/{p}/jobs (config.copy) | client.copy_table() | Client.Dataset().Table().CopierFrom() |
| Create MV | POST /projects/{p}/datasets/{d}/tables | client.create_table(MV) | Client.Dataset().Table().Create(MV) |
| Create routine | POST /projects/{p}/datasets/{d}/routines | client.create_routine() | Client.Dataset().Routine().Create() |
| Get IAM policy | GET /projects/{p}/datasets/{d}/iam | client.get_iam_policy() | Client.Dataset().IAM().Policy() |
| Set IAM policy | PUT /projects/{p}/datasets/{d}/iam | client.set_iam_policy() | Client.Dataset().IAM().SetPolicy() |

## Python SDK Code Snippets

### Create Dataset
```python
# create_dataset.py — REST: POST /projects/{project}/datasets
import os
from google.cloud import bigquery

client = bigquery.Client(project=os.environ["CLOUDSDK_CORE_PROJECT"])
dataset_id = os.environ.get("BQ_DATASET_ID", "my_dataset")
dataset = bigquery.Dataset(f"{client.project}.{dataset_id}")
dataset.location = "US"
dataset.description = "My dataset"
dataset.labels = {"env": "dev"}
dataset = client.create_dataset(dataset)
print(f"Created dataset: {dataset.full_dataset_id}")
```

### Describe Dataset
```python
# describe_dataset.py
import os
from google.cloud import bigquery
client = bigquery.Client()
dataset = client.get_dataset("{{user.dataset_id}}")
print(f"ID: {dataset.full_dataset_id}")
print(f"Location: {dataset.location}")
print(f"Labels: {dataset.labels}")
print(f"Tables: {list(client.list_tables(dataset))}")
```

### List Datasets
```python
# list_datasets.py
import os
from google.cloud import bigquery
client = bigquery.Client()
for ds in client.list_datasets():
    print(f"{ds.dataset_id} ({ds.location})")
```

### Update Dataset
```python
# update_dataset.py
import os
from google.cloud import bigquery
client = bigquery.Client()
dataset = client.get_dataset("{{user.dataset_id}}")
dataset.description = "Updated description"
dataset.labels = {"env": "prod", "app": "analytics"}
dataset.default_table_expiration_ms = 86400000  # 1 day
dataset = client.update_dataset(dataset, ["description", "labels", "default_table_expiration_ms"])
print(f"Updated dataset: {dataset.full_dataset_id}")
```

### Delete Dataset
```python
# delete_dataset.py
import os
from google.cloud import bigquery
client = bigquery.Client()
client.delete_dataset("{{user.dataset_id}}", delete_contents=True, not_found_ok=True)
print(f"Deleted dataset: {{user.dataset_id}}")
```

### Create Table
```python
# create_table.py
import os
from google.cloud import bigquery
client = bigquery.Client()
schema = [
    bigquery.SchemaField("id", "INTEGER", mode="REQUIRED"),
    bigquery.SchemaField("name", "STRING", mode="REQUIRED"),
    bigquery.SchemaField("created_at", "TIMESTAMP"),
]
table = bigquery.Table("{{user.table_id}}", schema=schema)
table.time_partitioning = bigquery.TimePartitioning(
    type_=bigquery.TimePartitioningType.DAY,
    field="{{user.partition_field:-created_at}}",
)
table.clustering_fields = ["{{user.cluster_columns:-name}}"]
table = client.create_table(table)
print(f"Created table: {table.full_table_id}")
```

### Describe Table
```python
# describe_table.py
import os
from google.cloud import bigquery
client = bigquery.Client()
table = client.get_table("{{user.table_id}}")
print(f"ID: {table.full_table_id}")
print(f"Rows: {table.num_rows}")
print(f"Bytes: {table.num_bytes}")
print(f"Schema: {[f.name for f in table.schema]}")
print(f"Partition: {table.time_partitioning}")
print(f"Clustering: {table.clustering_fields}")
```

### List Tables
```python
# list_tables.py
import os
from google.cloud import bigquery
client = bigquery.Client()
for table in client.list_tables("{{user.dataset_id}}"):
    print(f"{table.table_id} (type: {table.table_type})")
```

### Update Table
```python
# update_table.py
import os
from google.cloud import bigquery
client = bigquery.Client()
table = client.get_table("{{user.table_id}}")
table.description = "Updated table"
table.labels = {"team": "data"}
table = client.update_table(table, ["description", "labels"])
print(f"Updated table: {table.full_table_id}")
```

### Delete Table
```python
# delete_table.py
import os
from google.cloud import bigquery
client = bigquery.Client()
client.delete_table("{{user.table_id}}", not_found_ok=True)
print(f"Deleted table: {{user.table_id}}")
```

### Run Query (with dry-run)
```python
# run_query.py
import os
from google.cloud import bigquery
client = bigquery.Client()
query = "{{user.query}}"
job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
dry_run = client.query(query, job_config=job_config)
print(f"[DIAG] Estimated bytes: {dry_run.total_bytes_processed}")
print(f"[DIAG] Estimated cost: ${dry_run.total_bytes_processed / 1e12 * 5:.4f}")

job_config = bigquery.QueryJobConfig(use_query_cache=False)
query_job = client.query(query, job_config=job_config)
for row in query_job:
    print(dict(row))
```

### Describe Job
```python
# describe_job.py
import os
from google.cloud import bigquery
client = bigquery.Client()
job = client.get_job("{{user.job_id}}")
print(f"State: {job.state}")
print(f"Type: {job.job_type}")
print(f"Bytes processed: {job.total_bytes_processed}")
print(f"Slot ms: {job.total_slot_ms}")
```

### Cancel Job
```python
# cancel_job.py
import os
from google.cloud import bigquery
client = bigquery.Client()
client.cancel_job("{{user.job_id}}")
print(f"Cancelled job: {{user.job_id}}")
```

### Export Data to GCS
```python
# export_data.py
import os
from google.cloud import bigquery
client = bigquery.Client()
extract_job = client.extract_table(
    "{{user.table_id}}",
    "{{user.destination_uri}}",
    job_config=bigquery.ExtractJobConfig(destination_format="CSV"),
)
extract_job.result()
print(f"Exported to {{user.destination_uri}}")
```

### Load Data from GCS
```python
# load_data.py
import os
from google.cloud import bigquery
client = bigquery.Client()
load_job = client.load_table_from_uri(
    "{{user.source_uri}}",
    "{{user.table_id}}",
    job_config=bigquery.LoadJobConfig(
        source_format="CSV",
        autodetect=True,
        write_disposition="WRITE_TRUNCATE",
        skip_leading_rows=1,
    ),
)
load_job.result()
print(f"Loaded data into {{user.table_id}}")
```

### Create Materialized View
```python
# create_mv.py
import os
from google.cloud import bigquery
client = bigquery.Client()
mv = bigquery.Table("{{user.mv_id}}")
mv.materialized_view_as_query = "{{user.query}}"
mv = client.create_table(mv)
print(f"Created materialized view: {mv.full_table_id}")
```

### Create Routine (UDF)
```python
# create_routine.py
import os
from google.cloud import bigquery
client = bigquery.Client()
routine = bigquery.Routine("{{user.dataset_id}}.{{user.routine_name}}")
routine.type_ = "SCALAR_FUNCTION"
routine.language = "SQL"
routine.definition_body = "{{user.definition_body}}"
routine.return_type = bigquery.StandardSqlDataType(type="STRING")
routine = client.create_routine(routine)
print(f"Created routine: {routine.reference}")
```

### Set Dataset IAM
```python
# set_dataset_iam.py
import os
from google.cloud import bigquery
from google.cloud import iam
client = bigquery.Client()
policy = client.get_iam_policy("{{user.dataset_id}}")
policy.bindings.append({"role": "{{user.iam_role}}", "members": ["{{user.iam_member}}"]})
client.set_iam_policy("{{user.dataset_id}}", policy)
print(f"Set IAM policy on {{user.dataset_id}}")
```

### Copy Table
```python
# copy_table.py
import os
from google.cloud import bigquery
client = bigquery.Client()
job = client.copy_table("{{user.source_table_id}}", "{{user.destination_table_id}}")
job.result()
print(f"Copied table to {{user.destination_table_id}}")
```

## Go SDK Script Template

```go
// main.go (generated dynamically in /tmp/gcp-sdk-workspace)
package main

import (
    "context"
    "fmt"
    "log"
    "os"

    "cloud.google.com/go/bigquery"
    "google.golang.org/api/option"
)

func main() {
    ctx := context.Background()
    creds := os.Getenv("GOOGLE_APPLICATION_CREDENTIALS")

    client, err := bigquery.NewClient(ctx, os.Getenv("CLOUDSDK_CORE_PROJECT"),
        option.WithCredentialsFile(creds))
    if err != nil { log.Fatalf("NewClient: %v", err) }
    defer client.Close()

    // Example: Create dataset
    ds := client.Dataset("{{user.dataset_id}}")
    meta := &bigquery.DatasetMetadata{
        Location: "{{user.location:-US}}",
    }
    if err := ds.Create(ctx, meta); err != nil {
        log.Fatalf("Create: %v", err)
    }
    fmt.Printf("Created dataset: {{user.dataset_id}}\n")
}
```

> ⚠️ Never output credential values in logs or fmt.Println. Go SDK config structs can leak — prohibit such output.

## Key JSON Paths (Centralized)

| Operation | JSON Path | Description |
|-----------|-----------|-------------|
| Create/Describe dataset | $.{datasetReference,location,description,labels,defaultTableExpirationMs,access} | Dataset details |
| List datasets | $.[].{datasetReference,location,friendlyName} | Dataset list |
| Create/Describe table | $.{tableReference,schema,timePartitioning,clustering,numRows,numBytes,type,creationTime} | Table details |
| List tables | $.[].{tableReference,type,creationTime} | Table list |
| Query result | $.statistics.query.{totalBytesProcessed,totalSlotMs,cacheHit} | Query stats |
| Job status | $.{configuration,statistics,status,jobReference} | Job details |
| Materialized view | $.{type,materializedView.query,lastRefreshTime} | MV details |
| Routine | $.{routineType,definitionBody,returnType,language} | Routine details |
| IAM policy | $.{bindings[],etag,version} | IAM policy |
