#!/usr/bin/env python3
"""
Create BigQuery dataset and table for GCL traces.

Usage:
    python3 scripts/create_bigquery.py --project-id my-project [--dataset-id gcp_skills_gcl_audit]

Prerequisites:
    - google-cloud-bigquery installed: pip install google-cloud-bigquery
    - Application Default Credentials configured: gcloud auth application-default login
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from google.api_core.exceptions import AlreadyExists, NotFound
    from google.cloud import bigquery
    HAS_BIGQUERY = True
except ImportError:
    HAS_BIGQUERY = False


# ── Configuration ──────────────────────────────────────────────────────────────

DEFAULT_DATASET_ID = "gcp_skills_gcl_audit"
DEFAULT_TABLE_ID = "gcl_traces"

SCHEMA_FILE = Path(__file__).parent.parent / "schema" / "gcl_traces_schema.json"


# ── BigQuery Operations ────────────────────────────────────────────────────────


def create_dataset(client: bigquery.Client, dataset_id: str, location: str = "US") -> None:
    """Create BigQuery dataset if not exists."""
    dataset_ref = client.dataset(dataset_id)
    dataset = bigquery.Dataset(dataset_ref)
    dataset.description = "GCL Generator-Critic-Loop execution traces for observability"
    dataset.location = location
    dataset.default_table_expiration_ms = 365 * 24 * 60 * 60 * 1000  # 1 year

    try:
        dataset = client.create_dataset(dataset)
        print(f"[OK] Dataset created: {dataset.dataset_id}")
    except AlreadyExists:
        print(f"[OK] Dataset already exists: {dataset_id}")


def load_schema(schema_path: Path) -> list[dict]:
    """Load schema from JSON file."""
    with open(schema_path) as f:
        return json.load(f)


def create_table(
    client: bigquery.Client,
    dataset_id: str,
    table_id: str,
    schema: list[dict],
    partition_field: str = "timestamp",
) -> None:
    """Create BigQuery table with schema and partitioning."""
    table_ref = client.dataset(dataset_id).table(table_id)
    table = bigquery.Table(table_ref)

    # Convert schema to BigQuery schema format
    bq_schema = []
    for field in schema:
        bq_schema.append(
            bigquery.SchemaField(
                name=field["name"],
                field_type=field["type"],
                mode=field.get("mode", "NULLABLE"),
                description=field.get("description"),
            )
        )
    table.schema = bq_schema

    # Configure partitioning
    table.time_partitioning = bigquery.TimePartitioning(
        type_=bigquery.TimePartitioningType.DAY,
        field=partition_field,
    )

    # Configure clustering
    table.clustering_fields = ["skill", "op", "result"]

    try:
        table = client.create_table(table)
        print(f"[OK] Table created: {dataset_id}.{table.table_id}")
        print(f"     Partitioning: DAY on {partition_field}")
        print("     Clustering: skill, op, result")
    except AlreadyExists:
        print(f"[OK] Table already exists: {dataset_id}.{table_id}")


def verify_table(client: bigquery.Client, dataset_id: str, table_id: str) -> None:
    """Verify table exists and has correct schema."""
    table_ref = client.dataset(dataset_id).table(table_id)
    try:
        table = client.get_table(table_ref)
        print(f"[OK] Table verified: {dataset_id}.{table_id}")
        print(f"     Rows: {table.num_bytes // 1024 if table.num_bytes else 0} KB")
        print(f"     Partitioning: {table.time_partitioning}")
    except NotFound:
        print(f"[ERROR] Table not found: {dataset_id}.{table_id}")
        sys.exit(1)


# ── Main ──────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Create BigQuery dataset and table for GCL traces")
    parser.add_argument(
        "--project-id",
        required=True,
        help="GCP project ID",
    )
    parser.add_argument(
        "--dataset-id",
        default=DEFAULT_DATASET_ID,
        help=f"Dataset ID (default: {DEFAULT_DATASET_ID})",
    )
    parser.add_argument(
        "--table-id",
        default=DEFAULT_TABLE_ID,
        help=f"Table ID (default: {DEFAULT_TABLE_ID})",
    )
    parser.add_argument(
        "--location",
        default="US",
        help="Dataset location (default: US)",
    )
    parser.add_argument(
        "--schema-file",
        type=Path,
        default=SCHEMA_FILE,
        help=f"Path to schema JSON file (default: {SCHEMA_FILE})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be created without creating",
    )
    args = parser.parse_args()

    if not HAS_BIGQUERY:
        print("[ERROR] google-cloud-bigquery not installed.")
        print("         Install with: pip install google-cloud-bigquery")
        sys.exit(1)

    # Load schema
    if not args.schema_file.exists():
        print(f"[ERROR] Schema file not found: {args.schema_file}")
        sys.exit(1)

    schema = load_schema(args.schema_file)
    print(f"[INFO] Schema loaded: {len(schema)} fields")

    if args.dry_run:
        print(f"[DRY-RUN] Would create dataset: {args.dataset_id}")
        print(f"[DRY-RUN] Would create table: {args.dataset_id}.{args.table_id}")
        print(f"[DRY-RUN] Location: {args.location}")
        return

    # Create client
    client = bigquery.Client(project=args.project_id)
    print(f"[INFO] Connected to project: {args.project_id}")

    # Create dataset
    create_dataset(client, args.dataset_id, args.location)

    # Create table
    create_table(client, args.dataset_id, args.table_id, schema)

    # Verify
    verify_table(client, args.dataset_id, args.table_id)

    print("[OK] BigQuery setup complete!")
    print(f"     Dataset: {args.dataset_id}")
    print(f"     Table: {args.dataset_id}.{args.table_id}")


if __name__ == "__main__":
    main()
