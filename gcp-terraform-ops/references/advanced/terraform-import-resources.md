# Terraform Import Resources

> Import existing GCP resources into Terraform state using `terraform import`. Covers Cloud SQL, GKE, GCS, BigQuery with examples and state file management.

## Table of Contents

1. [Overview](#overview)
2. [Pre-flight Checklist](#pre-flight-checklist)
3. [Import Process](#import-process)
4. [Cloud SQL Import](#cloud-sql-import)
5. [GKE Import](#gke-import)
6. [GCS Import](#gcs-import)
7. [BigQuery Import](#bigquery-import)
8. [State File Management](#state-file-management)
9. [Common Patterns](#common-patterns)
10. [See Also](#see-also)

## Overview

`terraform import` brings existing GCP resources under Terraform management without destroying and recreating them. This is critical for adopting Terraform for existing infrastructure.

### Import Workflow

1. **Identify** the existing resource and its Terraform resource address
2. **Prepare** a minimal HCL configuration for the resource
3. **Import** the resource state
4. **Verify** the import with `terraform show`
5. **Refine** the configuration to match actual state
6. **Plan** to confirm no unexpected changes

## Pre-flight Checklist

```bash
# Verify Terraform version (>= 1.6 required for improved import)
terraform version

# Verify GCP authentication
gcloud auth list
gcloud config list project

# Verify backend access
terraform init -backend=false  # Dry-run init

# Check current state
terraform state list
```

## Import Process

### Step 1: Create Minimal HCL Configuration

```hcl
# import-template.tf
# Minimal configuration matching existing resource
resource "google_sql_database_instance" "imported_instance" {
  # Only include required fields - use computed values from import
  name     = "existing-instance-name"
  database_version = "MYSQL_8_0"
  region   = "us-central1"

  deletion_protection  = false  # Allow destroy after import verification
}
```

### Step 2: Import State

```bash
# Import to Terraform state
terraform import \
  google_sql_database_instance.imported_instance \
  projects/my-project/instances/existing-instance-name
```

### Step 3: Verify and Refine

```bash
# Show imported state
terraform show

# Compare with current state
terraform plan

# Refine HCL to match actual resource (add missing attributes)
# Re-plan to confirm no changes needed
terraform plan
```

## Cloud SQL Import

### Cloud SQL Instance

```bash
# Get existing instance ID
gcloud sql instances describe existing-instance-name \
  --format="value(name,databaseVersion,region)"

# Create minimal configuration
cat > cloudsql-import.tf << 'EOF'
resource "google_sql_database_instance" "prod_mysql" {
  name                = "existing-instance-name"
  database_version    = "MYSQL_8_0"
  region              = "us-central1"
  deletion_protection = false

  settings {
    tier = "db-n1-standard-2"
  }
}
EOF

# Import
terraform import google_sql_database_instance.prod_mysql \
  projects/my-project/instances/existing-instance-name
```

### Cloud SQL Database

```bash
# Import a specific database within an instance
terraform import google_sql_database.prod_db \
  projects/my-project/instances/existing-instance-name/databases/proddb
```

### Cloud SQL User

```bash
# Import a database user
terraform import google_sql_user.app_user \
  projects/my-project/instances/existing-instance-name/users/appuser
```

### Verify Cloud SQL Import

```bash
# Check imported state
terraform state show google_sql_database_instance.prod_mysql

# Show all resources in state
terraform state list | grep sql

# Plan to verify match
terraform plan
```

## GKE Import

### GKE Cluster

```bash
# Get cluster details
gcloud container clusters describe existing-cluster \
  --region us-central1 \
  --format="value(name,location,initialNodeCount,nodeVersion)"

# Create minimal configuration
cat > gke-import.tf << 'EOF'
resource "google_container_cluster" "imported_cluster" {
  name               = "existing-cluster"
  location           = "us-central1"
  deletion_protection = false

  # Import initial node count
  initial_node_count = 3

  # Use placeholder node pool - will refine after import
  node_config {
    oauth_scopes = ["https://www.googleapis.com/auth/cloud-platform"]
  }
}
EOF

# Import cluster
terraform import google_container_cluster.imported_cluster \
  projects/my-project/locations/us-central1/clusters/existing-cluster
```

### GKE Node Pool

```bash
# Import a specific node pool
terraform import google_container_node_pool.imported_pool \
  projects/my-project/locations/us-central1/clusters/existing-cluster/nodePools/node-pool-1
```

### Verify GKE Import

```bash
# Show cluster state
terraform state show google_container_cluster.imported_cluster

# Verify node pools
terraform state list | grep container

# Plan - may show drift if actual config differs
terraform plan
```

## GCS Import

### Storage Bucket

```bash
# Get bucket details
gsutil ls -L gs://existing-bucket/ | head -20

# Create configuration
cat > gcs-import.tf << 'EOF'
resource "google_storage_bucket" "imported_bucket" {
  name     = "existing-bucket"
  location = "US"

  # Import settings from existing bucket
  storage_class = "STANDARD"
}
EOF

# Import
terraform import google_storage_bucket.imported_bucket existing-bucket
```

### Storage Bucket Object (rarely needed)

```bash
# Import specific object metadata
terraform import google_storage_bucket_object.imported_object \
  existing-bucket/path/to/file.txt
```

### Verify GCS Import

```bash
# Check bucket state
terraform state show google_storage_bucket.imported_bucket

# Verify with gsutil
gsutil ls -L gs://existing-bucket/ | head -5

# Plan
terraform plan
```

## BigQuery Import

### BigQuery Dataset

```bash
# Get dataset details
gcloud bigquery datasets describe existing-dataset \
  --format="value(datasetReference.datasetId,location,description)"

# Create configuration
cat > bigquery-import.tf << 'EOF'
resource "google_bigquery_dataset" "imported_dataset" {
  dataset_id    = "existing-dataset"
  friendly_name = "Existing Dataset"
  description   = "Dataset imported from existing infrastructure"
  location      = "US"

  # Import empty tables list
  default_table_expiration_ms = null
}
EOF

# Import
terraform import google_bigquery_dataset.imported_dataset \
  projects/my-project/datasets/existing-dataset
```

### BigQuery Table

```bash
# Import specific table
terraform import google_bigquery_table.imported_table \
  projects/my-project/datasets/existing-dataset/tables/existing-table
```

### BigQuery Routine

```bash
# Import stored procedure or function
terraform import google_bigquery_routine.imported_routine \
  projects/my-project/datasets/existing-dataset/routines/existing-routine
```

### Verify BigQuery Import

```bash
# Show dataset state
terraform state show google_bigquery_dataset.imported_dataset

# List tables
terraform state list | grep bigquery

# Query to verify
gcloud bigquery datasets describe existing-dataset
```

## State File Management

### State Backup Before Import

```bash
# Always backup state before import
terraform state pull > backup-state-$(date +%Y%m%d-%H%M%S).json

# Or use versioned GCS backend (automatic versioning)
gcloud storage objects list gs://tf-state-bucket/terraform.tfstate
```

### State Locking

```bash
# Check if state is locked ( DynamoDB )
terraform plan

# If locked, check lock info
terraform state pull | jq '.metadata'

# Wait for lock release or investigate
# DO NOT force-unlock unless absolutely certain lock is stale
```

### State Verification

```bash
# List all resources in state
terraform state list

# Show specific resource
terraform state show google_sql_database_instance.prod_mysql

# Move resource to new name (if renaming)
terraform state mv google_sql_database_instance.prod_mysql google_sql_database_instance.primary
```

### Handle Import Conflicts

```bash
# If resource already exists in state with different config
terraform import google_sql_database_instance.prod_mysql \
  projects/my-project/instances/existing-instance-name \
  -config=cloudsql-import.tf

# Or manually edit state
terraform state rm google_sql_database_instance.conflicting_name
terraform import google_sql_database_instance.prod_mysql \
  projects/my-project/instances/existing-instance-name
```

## Common Patterns

### Bulk Import Script

```bash
#!/bin/bash
# bulk-import.sh — Import multiple resources

set -euo pipefail

TERRAFORM_DIR="${1:-.}"
IMPORT_LOG="/tmp/import-$(date +%Y%m%d-%H%M%S).log"

cd "$TERRAFORM_DIR"

# Import Cloud SQL
echo "Importing Cloud SQL instances..." | tee -a "$IMPORT_LOG"
terraform import google_sql_database_instance.prod_mysql \
  projects/my-project/instances/prod-mysql 2>&1 | tee -a "$IMPORT_LOG"

# Import GCS buckets
echo "Importing GCS buckets..." | tee -a "$IMPORT_LOG"
for bucket in bucket-1 bucket-2 bucket-3; do
  terraform import google_storage_bucket."$bucket" "$bucket" 2>&1 | tee -a "$IMPORT_LOG"
done

# Import BigQuery datasets
echo "Importing BigQuery datasets..." | tee -a "$IMPORT_LOG"
for dataset in dataset-1 dataset-2; do
  terraform import google_bigquery_dataset."$dataset" \
    projects/my-project/datasets/"$dataset" 2>&1 | tee -a "$IMPORT_LOG"
done

echo "Import complete. Log: $IMPORT_LOG"
```

### Import with Configuration from State

```bash
#!/bin/bash
# import-with-state-refresh.sh

set -euo pipefail

RESOURCE_ADDR="${1}"
RESOURCE_ID="${2}"

echo "Importing $RESOURCE_ADDR from $RESOURCE_ID"

# Backup current state
terraform state pull > backup-before-import.json

# Import
terraform import "$RESOURCE_ADDR" "$RESOURCE_ID"

# Show new state
terraform state show "$RESOURCE_ADDR"

# Plan to check for drift
terraform plan
```

## See Also

- [Terraform Import Documentation](https://developer.hashicorp.com/terraform/cli/commands/import)
- [GCP Provider Import Guide](https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/sql_database_instance#import)
- [Execution Flows - Import](../execution-flows.md#operation-terraform-import)
- [State Management](../execution-flows.md#operation-terraform-state)
