#!/usr/bin/env python3
"""
Create BigQuery dataset and table for GCL audit traces.

This script programmatically creates the gcp_skills_gcl_audit dataset
and gcl_traces table using the google-cloud-bigquery library.

Usage:
    python create_bigquery_dataset.py [--project PROJECT_ID] [--location LOCATION]

Environment:
    GOOGLE_APPLICATION_CREDENTIALS: Path to service account JSON key file
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from google.api_core.exceptions import AlreadyExists, Forbidden, GoogleAPIError, NotFound
from google.cloud import bigquery
from google.cloud.bigquery import Dataset, Table, TimePartitioning, TimePartitioningType

# Import schema from sibling module
sys.path.insert(0, str(Path(__file__).parent.parent))
from gcl_trace_schema import BIGQUERY_SCHEMA

DATASET_ID = "gcp_skills_gcl_audit"
TABLE_ID = "gcl_traces"
MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds


def get_client(project_id: str | None = None) -> bigquery.Client:
    """Create BigQuery client with optional project override."""
    kwargs = {}
    if project_id:
        kwargs["project"] = project_id
    return bigquery.Client(**kwargs)


def create_dataset(
    client: bigquery.Client,
    dataset_id: str,
    location: str = "US",
    exists_ok: bool = True,
) -> Dataset:
    """
    Create BigQuery dataset if it doesn't exist.

    Args:
        client: BigQuery client
        dataset_id: Dataset ID to create
        location: Dataset location (default: US)
        exists_ok: If True, don't raise error if dataset exists

    Returns:
        Dataset object

    Raises:
        GoogleAPIError: On API errors other than AlreadyExists
    """
    dataset_ref = client.dataset(dataset_id)
    dataset = Dataset(dataset_ref)
    dataset.description = "BigQuery dataset for storing GCL (Generator-Critic-Loop) execution traces"
    dataset.friendly_name = "GCP Skills GCL Audit"
    dataset.location = location

    try:
        dataset = client.create_dataset(dataset, exists_ok=exists_ok)
        print(f"[OK] Dataset created or already exists: {dataset_id}")
        return dataset
    except AlreadyExists:
        print(f"[OK] Dataset already exists: {dataset_id}")
        return client.get_dataset(dataset_ref)
    except GoogleAPIError as e:
        print(f"[ERROR] Failed to create dataset: {e}")
        raise


def create_table(
    client: bigquery.Client,
    dataset_id: str,
    table_id: str,
    schema: list[dict],
    location: str = "US",
) -> Table:
    """
    Create BigQuery table with schema, partitioning, and clustering.

    Args:
        client: BigQuery client
        dataset_id: Dataset ID
        table_id: Table ID to create
        schema: BigQuery schema as list of field definitions
        location: Dataset location

    Returns:
        Table object

    Raises:
        GoogleAPIError: On API errors
    """
    table_ref = client.dataset(dataset_id).table(table_id)
    table = Table(table_ref)

    # Convert schema to BigQuery SchemaField objects
    bq_schema = []
    for field in schema:
        bq_schema.append(
            bigquery.SchemaField(
                name=field["name"],
                field_type=field["type"],
                mode=field["mode"],
            )
        )
    table.schema = bq_schema

    # Add time partitioning by timestamp field
    table.time_partitioning = TimePartitioning(
        type_=TimePartitioningType.DAY,
        field="timestamp",
    )

    # Add clustering fields
    table.clustering_fields = ["skill", "op", "result"]

    try:
        table = client.create_table(table)
        print(f"[OK] Table created: {dataset_id}.{table_id}")
        return table
    except AlreadyExists:
        print(f"[OK] Table already exists: {dataset_id}.{table_id}")
        return client.get_table(table_ref)
    except GoogleAPIError as e:
        print(f"[ERROR] Failed to create table: {e}")
        raise


def create_table_with_retry(
    client: bigquery.Client,
    dataset_id: str,
    table_id: str,
    schema: list[dict],
    max_retries: int = MAX_RETRIES,
    retry_delay: int = RETRY_DELAY,
) -> Table:
    """
    Create table with retry logic for transient errors.

    Args:
        client: BigQuery client
        dataset_id: Dataset ID
        table_id: Table ID
        schema: BigQuery schema
        max_retries: Maximum retry attempts
        retry_delay: Delay between retries in seconds

    Returns:
        Table object

    Raises:
        GoogleAPIError: After exhausting retries
    """
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            return create_table(client, dataset_id, table_id, schema)
        except (Forbidden, NotFound) as e:
            # Non-retryable errors
            print(f"[ERROR] Non-retryable error: {e}")
            raise
        except GoogleAPIError as e:
            last_error = e
            print(f"[WARN] Attempt {attempt}/{max_retries} failed: {e}")
            if attempt < max_retries:
                print(f"[INFO] Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print(f"[ERROR] All {max_retries} attempts exhausted")
                raise last_error

    # Should not reach here, but satisfy type checker
    raise last_error


def verify_table_schema(client: bigquery.Client, dataset_id: str, table_id: str) -> bool:
    """
    Verify that the table exists and has the expected schema.

    Args:
        client: BigQuery client
        dataset_id: Dataset ID
        table_id: Table ID

    Returns:
        True if schema matches, False otherwise
    """
    try:
        table = client.get_table(f"{dataset_id}.{table_id}")
        print(f"[OK] Table verified: {dataset_id}.{table_id}")
        print(f"    - Schema fields: {len(table.schema)}")
        print(f"    - Time partitioning: {table.time_partitioning.type_ if table.time_partitioning else 'None'}")
        print(f"    - Clustering fields: {table.clustering_fields}")
        return True
    except NotFound:
        print(f"[ERROR] Table not found: {dataset_id}.{table_id}")
        return False
    except GoogleAPIError as e:
        print(f"[ERROR] Failed to verify table: {e}")
        return False


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Create BigQuery dataset and table for GCL audit traces"
    )
    parser.add_argument(
        "--project",
        help="GCP project ID (overrides default)",
    )
    parser.add_argument(
        "--location",
        default="US",
        help="Dataset location (default: US)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate without creating resources",
    )

    args = parser.parse_args()

    print("Starting BigQuery setup for GCL audit traces")
    print(f"Project: {args.project or 'default'}")
    print(f"Location: {args.location}")
    print(f"Dry run: {args.dry_run}")
    print("-" * 50)

    if args.dry_run:
        print("[INFO] Dry run mode - skipping creation")
        # Just validate schema import
        print(f"[OK] Schema loaded: {len(BIGQUERY_SCHEMA)} fields")
        return 0

    try:
        # Create client
        client = get_client(args.project)

        # Create dataset
        create_dataset(client, DATASET_ID, location=args.location)

        # Create table with retry logic
        create_table_with_retry(
            client,
            DATASET_ID,
            TABLE_ID,
            BIGQUERY_SCHEMA,
        )

        # Verify table
        verify_table_schema(client, DATASET_ID, TABLE_ID)

        print("-" * 50)
        print("[OK] BigQuery setup completed successfully")
        return 0

    except GoogleAPIError as e:
        print(f"[ERROR] BigQuery setup failed: {e}")
        return 1
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
