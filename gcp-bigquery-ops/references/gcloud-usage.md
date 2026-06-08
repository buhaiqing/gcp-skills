# gcloud/bq CLI Usage — Cloud BigQuery

## Command Overview

All commands use the `bq` CLI (part of Cloud SDK). Format: `bq [global_flags] <command> [flags] <args>`

## Dataset Operations

### Create Dataset
```bash
# Basic
bq --location="{{user.location:-US}}" mk --dataset "{{user.dataset_id}}"

# With description, labels, expiration
bq --location="US" mk --dataset \
  --description="Production analytics dataset" \
  --label=env=prod,app=analytics \
  --default_table_expiration=86400000 \
  "{{user.dataset_id}}"
```

### Describe Dataset
```bash
# JSON output
bq show --format=prettyjson "{{user.dataset_id}}"

# Pretty output
bq show "{{user.dataset_id}}"

# Tables in dataset
bq ls "{{user.dataset_id}}"
```

### List Datasets
```bash
# All datasets in project
bq ls --format=prettyjson --project_id="{{env.CLOUDSDK_CORE_PROJECT}}"

# Filter by label
bq ls --filter=labels.env=prod

# Include hidden datasets
bq ls -a
```

### Update Dataset
```bash
# Set label
bq update --set_label=env=prod "{{user.dataset_id}}"

# Delete label
bq update --clear_label=env "{{user.dataset_id}}"

# Update description
bq update --description="Updated description" "{{user.dataset_id}}"

# Set default table expiration (milliseconds)
bq update --default_table_expiration=86400000 "{{user.dataset_id}}"

# Set default partition expiration
bq update --default_partition_expiration=2592000000 "{{user.dataset_id}}"
```

### Delete Dataset
```bash
# Empty dataset only
bq rm --dataset "{{user.dataset_id}}"

# Force delete with all tables (DANGEROUS)
bq rm -r -f --dataset "{{user.dataset_id}}"
```

## Table Operations

### Create Table
```bash
# Empty table with schema (JSON file)
bq mk --table --schema="/path/to/schema.json" "{{user.table_id}}"

# Empty table with inline schema
bq mk --table \
  --schema="id:INTEGER,name:STRING,created_at:TIMESTAMP" \
  "{{user.table_id}}"

# Time-partitioned table
bq mk --table \
  --schema="/path/to/schema.json" \
  --time_partitioning_field=date_column \
  --time_partitioning_type=DAY \
  "{{user.table_id}}"

# Clustered table
bq mk --table \
  --schema="/path/to/schema.json" \
  --clustering_fields=column1,column2 \
  "{{user.table_id}}"

# Partitioned + clustered
bq mk --table \
  --schema="/path/to/schema.json" \
  --time_partitioning_field=date_column \
  --clustering_fields=column1,column2 \
  "{{user.table_id}}"

# Table with expiration (milliseconds)
bq mk --table \
  --schema="/path/to/schema.json" \
  --expiration=86400000 \
  "{{user.table_id}}"

# Table from GCS (load)
bq load --source_format=CSV --autodetect \
  "{{user.table_id}}" "gs://bucket/path/file.csv"

# Table from GCS (Parquet)
bq load --source_format=PARQUET --autodetect \
  "{{user.table_id}}" "gs://bucket/path/*.parquet"

# External table (federated query)
bq mk --external_table_definition=gs://bucket/path/file.csv \
  "{{user.table_id}}"
```

### Describe Table
```bash
# Full metadata
bq show --format=prettyjson "{{user.table_id}}"

# Schema only
bq show --schema --format=prettyjson "{{user.table_id}}"

# Table data preview
bq head --max_rows=10 "{{user.table_id}}"
```

### List Tables
```bash
# All tables in dataset
bq ls --format=prettyjson "{{user.dataset_id}}"

# Filter by table type
bq ls "{{user.dataset_id}}" | grep TABLE
bq ls "{{user.dataset_id}}" | grep VIEW
bq ls "{{user.dataset_id}}" | grep MATERIALIZED_VIEW

# With max results
bq ls --max_results=50 "{{user.dataset_id}}"
```

### Update Table
```bash
# Update schema
bq update --schema="/path/to/new_schema.json" "{{user.table_id}}"

# Update description
bq update --description="Updated description" "{{user.table_id}}"

# Update expiration
bq update --expiration=86400000 "{{user.table_id}}"

# Set label
bq update --set_label=team=data "{{user.table_id}}"

# Add clustering
bq update --clustering_fields=column1,column2 "{{user.table_id}}"

# Add partition expiration
bq update --time_partitioning_expiration=2592000000 "{{user.table_id}}"
```

### Delete Table
```bash
bq rm -f --table "{{user.table_id}}"
```

### Copy Table
```bash
# Same project
bq cp "{{user.source_table_id}}" "{{user.destination_table_id}}"

# With write disposition
bq cp --destination_table_write_disposition=WRITE_APPEND \
  "{{user.source_table_id}}" "{{user.destination_table_id}}"

# Cross-project
bq cp \
  "source-project:source_dataset.table1" \
  "dest-project:dest_dataset.table1"
```

## Query Operations

### Dry-Run (Cost Estimation)
```bash
# Estimate bytes processed
bq query --dry_run --use_legacy_sql=false \
  "SELECT * FROM \`{{user.dataset_id}}.table1\` WHERE date = '2026-06-08'"

# With job config
bq query --dry_run --use_legacy_sql=false \
  --max_bytes_billed=1000000000 \
  "{{user.query}}"
```

### Run Query
```bash
# Interactive query (default)
bq query --use_legacy_sql=false --format=prettyjson \
  "{{user.query}}"

# With destination table
bq query --use_legacy_sql=false \
  --destination_table="{{user.destination_table_id}}" \
  --replace=true \
  "{{user.query}}"

# Append to destination
bq query --use_legacy_sql=false \
  --destination_table="{{user.destination_table_id}}" \
  --append_table=true \
  "{{user.query}}"

# Batch priority
bq query --use_legacy_sql=false \
  --priority=batch \
  --destination_table="{{user.destination_table_id}}" \
  "{{user.query}}"

# With max results and timeout
bq query --use_legacy_sql=false \
  --max_rows=1000 \
  --max_time_ms=300000 \
  "{{user.query}}"

# With parameterized query
bq query --use_legacy_sql=false \
  --parameter=param1:STRING:value1 \
  "SELECT * FROM \`{{user.dataset_id}}.table1\` WHERE name = @param1"
```

## Job Operations

### Describe Job
```bash
bq show -j "{{user.job_id}}" --format=prettyjson
```

### Cancel Job
```bash
bq cancel "{{user.job_id}}"
```

### List Jobs
```bash
# All jobs
bq ls -j --all

# Recent jobs
bq ls -j --max_results=10

# Filter by state
bq ls -j --all --filter=state=DONE
```

## Partition/Clustering Operations

### Modify Partitioning
```bash
# Add time partitioning to existing table
bq update --time_partitioning_field=date_column \
  --time_partitioning_type=DAY \
  "{{user.table_id}}"

# Set partition expiration (milliseconds)
bq update --time_partitioning_expiration=2592000000 \
  "{{user.table_id}}"

# Remove partition expiration
bq update --time_partitioning_expiration=0 \
  "{{user.table_id}}"
```

### Modify Clustering
```bash
# Set clustering fields (up to 4)
bq update --clustering_fields=column1,column2,column3 \
  "{{user.table_id}}"

# Remove clustering
bq update --clear_clustering "{{user.table_id}}"
```

## IAM Operations

```bash
# Get IAM policy
bq get-iam-policy "{{user.dataset_id}}"

# Add binding
bq add-iam-policy-binding "{{user.dataset_id}}" \
  --member="{{user.iam_member}}" \
  --role="{{user.iam_role}}"

# Remove binding
bq remove-iam-policy-binding "{{user.dataset_id}}" \
  --member="{{user.iam_member}}" \
  --role="{{user.iam_role}}"
```

## Export Operations

```bash
# Export to CSV
bq extract --destination_format=CSV \
  "{{user.table_id}}" "gs://bucket/export.csv"

# Export to JSON
bq extract --destination_format=NEWLINE_DELIMITED_JSON \
  "{{user.table_id}}" "gs://bucket/export.json"

# Export to Avro
bq extract --destination_format=AVRO \
  "{{user.table_id}}" "gs://bucket/export.avro"

# Export with compression
bq extract --destination_format=CSV --compression=GZIP \
  "{{user.table_id}}" "gs://bucket/export.csv.gz"

# Export with header and delimiter
bq extract --destination_format=CSV \
  --field_delimiter="|" --print_header=true \
  "{{user.table_id}}" "gs://bucket/export.csv"

# Export with wildcard (large tables)
bq extract --destination_format=PARQUET \
  "{{user.table_id}}" "gs://bucket/export-*.parquet"
```

## Load Operations

```bash
# Load CSV with autodetect
bq load --source_format=CSV --autodetect \
  "{{user.table_id}}" "gs://bucket/data.csv"

# Load CSV with schema and header skip
bq load --source_format=CSV \
  --schema="/path/to/schema.json" \
  --skip_leading_rows=1 \
  "{{user.table_id}}" "gs://bucket/data.csv"

# Load JSON
bq load --source_format=NEWLINE_DELIMITED_JSON \
  --autodetect \
  "{{user.table_id}}" "gs://bucket/data.json"

# Load Parquet
bq load --source_format=PARQUET \
  --autodetect \
  "{{user.table_id}}" "gs://bucket/data.parquet"

# Load Avro
bq load --source_format=AVRO \
  "{{user.table_id}}" "gs://bucket/data.avro"

# Load with write disposition
bq load --source_format=CSV \
  --write_disposition=WRITE_TRUNCATE \
  "{{user.table_id}}" "gs://bucket/data.csv"

# Load with append
bq load --source_format=CSV \
  --write_disposition=WRITE_APPEND \
  "{{user.table_id}}" "gs://bucket/data.csv"

# Load with custom delimiter
bq load --source_format=CSV \
  --field_delimiter="|" \
  --autodetect \
  "{{user.table_id}}" "gs://bucket/data.csv"

# Load multiple files with wildcard
bq load --source_format=CSV \
  --autodetect \
  "{{user.table_id}}" "gs://bucket/data/*.csv"
```

## Materialized View Operations

```bash
# Create materialized view
bq mk --materialized_view \
  "{{user.mv_id}}" \
  "{{user.query}}"

# Create with explicit enablement
bq mk --materialized_view \
  --enable_refresh=true \
  --refresh_interval_ms=1800000 \
  "{{user.mv_id}}" \
  "{{user.query}}"

# Describe materialized view
bq show --format=prettyjson "{{user.mv_id}}"
```

## Routine Operations

```bash
# Create SQL UDF
bq mk --routine --routine_type=SCALAR_FUNCTION \
  --language=SQL \
  --definition_body="x * 2" \
  --return_type="INT64" \
  "{{user.dataset_id}}.double_value(x INT64)"

# Create JavaScript UDF
bq mk --routine --routine_type=SCALAR_FUNCTION \
  --language=JAVASCRIPT \
  --definition_body="return x * 2;" \
  --return_type="FLOAT64" \
  "{{user.dataset_id}}.js_double(x FLOAT64)"

# Describe routine
bq show --format=prettyjson "{{user.dataset_id}}.{{user.routine_name}}"

# List routines
bq ls --routines "{{user.dataset_id}}"
```

## Schema Operations

```bash
# Show schema
bq show --schema --format=prettyjson "{{user.table_id}}"

# Update schema from file
bq update --schema="/path/to/new_schema.json" "{{user.table_id}}"
```

## Common Flags Reference

| Flag | Description |
|------|-------------|
| `--format=prettyjson` | JSON output with indentation |
| `--format=json` | Compact JSON output |
| `--use_legacy_sql=false` | Use standard SQL (recommended) |
| `--location=REGION` | Dataset/job location |
| `--project_id=PROJECT` | Override default project |
| `--quiet` | Suppress interactive prompts |
| `--max_rows=N` | Limit output rows |
| `--max_results=N` | Limit list results |
| `--destination_table=TABLE` | Query result destination |
| `--replace` | Replace destination table |
| `--append_table` | Append to destination table |
| `--dry_run` | Estimate cost without executing |
| `--autodetect` | Auto-detect schema for load |
| `--source_format=FORMAT` | CSV/JSON/AVRO/PARQUET |
| `--destination_format=FORMAT` | Export format |
| `--compression=GZIP` | Compress output |
| `--field_delimiter=CHAR` | CSV field delimiter |
| `--skip_leading_rows=N` | Skip header rows |
| `--clustering_fields=COL1,COL2` | Clustering columns |
| `--time_partitioning_field=COL` | Partition column |
| `--time_partitioning_type=TYPE` | DAY/HOUR/MONTH/YEAR |
