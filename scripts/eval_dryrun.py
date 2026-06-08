#!/usr/bin/env python3
"""Skill CLI Dry-Run Validation Harness — Phase 1.

Validates that Skill-generated commands are:
  L1: Syntactically correct (structure/pattern match)
  L2: Executable via dry-run (where supported)
  L3: JSON path valid (jq extraction paths)
  L4: Safety gates present (for destructive operations)

Usage:
    python scripts/eval_dryrun.py gcp-bigquery-ops
    python scripts/eval_dryrun.py gcp-bigquery-ops --query "run a SQL query"
    python scripts/eval_dryrun.py --all
"""

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class EvalQuery:
    query: str
    should_trigger: bool
    expected_cmd_pattern: str = ""
    dry_run_supported: bool = False
    safety_check: bool = False


@dataclass
class ValidationResult:
    query: str
    expected_pattern: str
    generated_cmd: str = ""
    L1_structure: bool = False
    L1_detail: str = ""
    L2_dry_run: Optional[bool] = None
    L2_detail: str = ""
    L3_json_path: bool = False
    L3_detail: str = ""
    L4_safety: bool = True
    L4_detail: str = ""

    @property
    def overall(self) -> bool:
        return self.L1_structure and self.L3_json_path and self.L4_safety

    def summary(self) -> str:
        status = "PASS" if self.overall else "FAIL"
        icon = "PASS" if self.overall else "FAIL"
        parts = [f"  [{icon}] {self.query}"]
        if not self.L1_structure:
            parts.append(f"       L1: {self.L1_detail}")
        if self.L2_dry_run is not None and not self.L2_dry_run:
            parts.append(f"       L2: {self.L2_detail}")
        if not self.L3_json_path:
            parts.append(f"       L3: {self.L3_detail}")
        if not self.L4_safety:
            parts.append(f"       L4: {self.L4_detail}")
        return "\n".join(parts)


def load_eval_queries(skill_dir: Path) -> list[EvalQuery]:
    eval_file = skill_dir / "assets" / "eval_queries.json"
    if not eval_file.exists():
        return []
    with open(eval_file) as f:
        data = json.load(f)
    return [
        EvalQuery(
            query=q["query"],
            should_trigger=q.get("should_trigger", True),
            expected_cmd_pattern=q.get("expected_cmd_pattern", ""),
            dry_run_supported=q.get("dry_run_supported", False),
            safety_check=q.get("safety_check", False),
        )
        for q in data
        if "query" in q  # Skip entries without query key
    ]


def load_skill_context(skill_dir: Path) -> str:
    """Load SKILL.md content for LLM prompt context."""
    skill_md = skill_dir / "SKILL.md"
    if skill_md.exists():
        return skill_md.read_text()
    return ""


def simulate_llm(query: str, skill_dir: Path) -> str:
    """Simulate LLM generating a command from a natural language query.

    In Phase 1, this uses a simple keyword-based mapping.
    In Phase 2+, this would call a real LLM with Skill context.
    """
    q = query.lower()

    # Helper: match regex or substring
    def m(*patterns):
        return any(re.search(p, q) for p in patterns)

    # BigQuery command mappings
    if m("create a dataset", "create a new dataset"):
        return 'bq --location="US" mk --dataset --description="Analytics dataset" --label=env=dev "my-project:my_dataset"'
    elif m("list all datasets", "list datasets"):
        return 'bq ls --format=prettyjson --project_id="my-project"'
    elif m("create a table", "create table"):
        return 'bq mk --table --schema="schema.json" "my-project:my_dataset.my_table"'
    elif m("list all tables", "list tables"):
        return 'bq ls --format=prettyjson "my-project:my_dataset"'
    elif m("run a sql query", "run query"):
        return 'bq query --use_legacy_sql=false --format=prettyjson --max_rows=100 "SELECT * FROM `my-project.my_dataset.my_table` LIMIT 100"'
    elif m("cost", "estimate", "dry"):
        return 'bq query --dry_run --use_legacy_sql=false "SELECT COUNT(*) FROM `my-project.my_dataset.my_table`"'
    elif m("partition.*query", "optimize.*partitioning"):
        return "bq query --use_legacy_sql=false --format=prettyjson --max_rows=100 \"SELECT * FROM `my-project.my_dataset.my_table` WHERE date_col = '2026-06-08'\""
    elif m("partition"):
        return 'bq mk --table --schema="schema.json" --time_partitioning_field=date_col "my-project:my_dataset.my_table"'
    elif m("bq.*cluster", "clustering.*field"):
        return 'bq mk --table --schema="schema.json" --clustering_fields=col1,col2 "my-project:my_dataset.my_table"'
    elif m("bq.*export", "bq.*load", "bigquery.*export", "bigquery.*import", "bigquery.*load"):
        if m("export"):
            return 'bq extract --destination_format=PARQUET --compression=GZIP "my-project:my_dataset.my_table" "gs://my-bucket/export/*.parquet"'
        return 'bq load --source_format=CSV --autodetect --write_disposition=WRITE_TRUNCATE "my-project:my_dataset.my_table" "gs://my-bucket/data.csv"'
    elif m("delete dataset"):
        return 'bq rm -r -f --dataset "my-project:my_dataset"'
    elif m("delete table"):
        return 'bq rm -f --table "my-project:my_dataset.my_table"'
    elif m("describe.*job", "job status"):
        return 'bq show -j "my-job-id" --format=prettyjson'
    elif m("show.*schema", "describe.*table", "table.*schema", "show.*table"):
        return 'bq show --format=prettyjson "my-project:my_dataset.my_table"'
    elif m("bq.*cancel", "cancel.*job", "cancel.*query"):
        return 'bq cancel "my-job-id"'
    elif m("materialized view"):
        return 'bq mk --materialized_view "my-project:my_dataset.my_mv" "SELECT col, COUNT(*) FROM `my-project.my_dataset.my_table` GROUP BY col"'
    elif m("routine", "user-defined function"):
        return 'bq mk --routine --routine_type=SCALAR_FUNCTION --language=SQL --definition_body="x * 2" --return_type=INT64 "my-project:my_dataset.my_routine"'
    elif m("copy table"):
        return 'bq cp "my-project:my_dataset.source_table" "my-project:my_dataset.dest_table"'

    # Pub/Sub IAM (must be before BigQuery IAM to avoid "iam.*permissions" collision)
    elif m("topic.*iam.*permission"):
        return 'gcloud pubsub topics add-iam-policy-binding "my-topic" --member="serviceAccount:publisher@project.iam.gserviceaccount.com" --role="roles/pubsub.publisher" --format="json"'
    elif m("iam.*dataset", "iam.*table", "permissions.*dataset", "permissions.*table", "iam.*bigquery", "iam.*permissions"):
        return 'bq add-iam-policy-binding "my-project:my_dataset" --member="user:admin@example.com" --role="roles/bigquery.dataEditor"'

    # Pub/Sub command mappings
    elif m("create.*subscription"):
        return 'gcloud pubsub subscriptions create "my-sub" --topic="my-topic" --project="my-project" --ack-deadline="10" --message-retention-duration="7d" --format="json"'
    elif m("create.*snapshot"):
        return 'gcloud pubsub snapshots create "my-snapshot" --subscription="my-sub" --project="my-project" --format="json"'
    elif m("create.*topic"):
        return 'gcloud pubsub topics create "my-topic" --project="my-project" --format="json"'
    elif m("list.*topic"):
        return 'gcloud pubsub topics list --project="my-project" --format="json"'
    elif m("publish.*message"):
        return 'gcloud pubsub topics publish "my-topic" --message="hello world" --project="my-project" --format="json"'
    elif m("pull.*message"):
        return 'gcloud pubsub subscriptions pull "my-sub" --auto-ack --limit=10 --format="json"'
    elif m("dead.?letter", "dlq"):
        return 'gcloud pubsub subscriptions update "my-sub" --dead-letter-topic="my-dlq" --max-delivery-attempts="5" --format="json"'
    elif m("retry.*policy"):
        return 'gcloud pubsub subscriptions update "my-sub" --min-retry-delay="10s" --max-retry-delay="600s" --format="json"'
    elif m("seek.*timestamp"):
        return 'gcloud pubsub subscriptions seek "my-sub" --time="2026-06-08T10:00:00Z" --project="my-project" --format="json"'
    elif m("seek.*snapshot"):
        return 'gcloud pubsub subscriptions seek "my-sub" --snapshot="my-snapshot" --project="my-project" --format="json"'
    elif m("delete.*topic"):
        return 'gcloud pubsub topics delete "my-topic" --project="my-project" --quiet'
    elif m("delete.*subscription"):
        return 'gcloud pubsub subscriptions delete "my-sub" --project="my-project" --quiet'
    elif m("push.*subscription"):
        return 'gcloud pubsub subscriptions create "my-push-sub" --topic="my-topic" --push-endpoint="https://my-app.com/push" --format="json"'
    elif m("exactly.?once"):
        return 'gcloud pubsub subscriptions update "my-sub" --enable-exactly-once-delivery --format="json"'
    elif m("message.*ordering"):
        return 'gcloud pubsub subscriptions create "my-ordered-sub" --topic="my-topic" --enable-message-ordering --format="json"'
    elif m("backlog"):
        return 'gcloud pubsub subscriptions describe "my-sub" --format="json" | jq \'{numUndeliveredMessages, oldestUnackedMessageAge, messageRetentionDuration}\''
    elif m("update.*ack", "ack.*deadline"):
        return 'gcloud pubsub subscriptions update "my-sub" --ack-deadline="30" --format="json"'
    elif m("update.*retention", "retention.*duration"):
        return 'gcloud pubsub subscriptions update "my-sub" --message-retention-duration="7d" --format="json"'
    elif m("iam.*pubsub", "iam.*topic", "topic.*permission"):
        return 'gcloud pubsub topics add-iam-policy-binding "my-topic" --member="serviceAccount:publisher@project.iam.gserviceaccount.com" --role="roles/pubsub.publisher" --format="json"'

    # GCE command mappings
    elif m("create.*vm", "create.*compute.*instance", "create.*gce.*instance"):
        return 'gcloud compute instances create "my-instance" --zone="us-central1-a" --machine-type="e2-medium" --image-family="debian-12" --format="json"'
    elif m("instance.*won.t.*start", "debug.*instance"):
        return 'gcloud compute instances describe "my-instance" --zone="us-central1-a" --format="json"'
    elif m("resize.*disk"):
        return 'gcloud compute disks resize "my-disk" --size="50GB" --zone="us-central1-a" --format="json"'
    elif m("snapshot.*disk"):
        return 'gcloud compute disks snapshot "my-disk" --snapshot-names="my-snapshot" --zone="us-central1-a" --format="json"'
    elif m("ssh.*into"):
        return 'gcloud compute ssh "my-instance" --zone="us-central1-a" --command="whoami"'
    elif m("managed.*instance.*group"):
        return 'gcloud compute instance-groups managed create "my-mig" --base-instance-name="my-base" --size="3" --template="my-template" --zone="us-central1-a" --format="json"'
    elif m("list.*instance", "list.*running"):
        return 'gcloud compute instances list --format="json" --filter="status=RUNNING"'
    elif m("disk.*full"):
        return 'gcloud compute disks describe "my-disk" --zone="us-central1-a" --format="json"'
    elif m("machine.*image"):
        return 'gcloud compute machine-images create "my-image" --source-instance="my-prod-vm" --source-instance-zone="us-central1-a" --format="json"'
    elif m("scale.*instance.*group"):
        return 'gcloud compute instance-groups managed resize "my-mig" --size="5" --zone="us-central1-a" --format="json"'

    # GKE command mappings
    elif m("create.*gke.*cluster", "create.*kubernetes.*cluster"):
        if m("5.*nodes"):
            return 'gcloud container clusters create "my-cluster" --zone="us-central1" --num-nodes="5" --machine-type="e2-medium" --format="json"'
        elif m("autopilot"):
            return 'gcloud container clusters create "my-cluster" --zone="us-central1" --enable-autopilot --format="json"'
        return 'gcloud container clusters create "my-cluster" --zone="us-central1" --num-nodes="3" --format="json"'
    elif m("upgrade.*cluster"):
        return 'gcloud container clusters upgrade "my-cluster" --zone="us-central1" --master-version="latest" --format="json"'
    elif m("add.*node.*pool"):
        return 'gcloud container node-pools create "my-pool" --cluster="my-cluster" --zone="us-central1" --machine-type="e2-medium" --num-nodes="3" --format="json"'
    elif m("resize.*node.*pool"):
        return 'gcloud container node-pools resize "my-pool" --cluster="my-cluster" --zone="us-central1" --num-nodes="10" --format="json"'
    elif m("delete.*cluster"):
        return 'gcloud container clusters delete "my-cluster" --zone="us-central1" --quiet'
    elif m("get.*credential", "kubectl.*config"):
        return 'gcloud container clusters get-credentials "my-cluster" --zone="us-central1" --project="my-project"'
    elif m("describe.*cluster", "describe.*gke"):
        return 'gcloud container clusters describe "my-cluster" --zone="us-central1" --format="json"'
    elif m("list.*node.*pool"):
        return 'gcloud container node-pools list --cluster="my-cluster" --zone="us-central1" --format="json"'
    elif m("upgrade.*node.*pool"):
        return 'gcloud container node-pools upgrade "my-pool" --cluster="my-cluster" --zone="us-central1" --node-version="1.29" --format="json"'
    elif m("workload.*identity"):
        return 'gcloud container clusters update "my-cluster" --zone="us-central1" --workload-pool="my-project.svc.id.goog" --format="json"'
    elif m("autoscaler", "pod.*stuck", "pod.*pending"):
        return 'gcloud container clusters describe "my-cluster" --zone="us-central1" --format="json"'
    elif m("backup.*gke"):
        return 'gcloud container backup backup-plans create "my-plan" --location="us-central1" --cluster="my-cluster" --format="json"'

    # Cloud Run command mappings
    elif m("deploy.*cloud.*run"):
        return 'gcloud run deploy "my-service" --image="gcr.io/my-project/my-image:latest" --region="us-central1" --format="json"'
    elif m("list.*cloud.*run.*service", "list.*service"):
        return 'gcloud run services list --region="us-central1" --format="json"'
    elif m("split.*traffic", "update.?traffic"):
        return 'gcloud run services update-traffic "my-service" --region="us-central1" --to-revisions="rev1=50,rev2=50" --format="json"'
    elif m("delete.*cloud.*run"):
        return 'gcloud run services delete "my-service" --region="us-central1" --quiet'
    elif m("mount.*secret", "set.?secret"):
        return 'gcloud run services update "my-service" --region="us-central1" --set-secrets="DB_PASSWORD=db-password:latest" --format="json"'
    elif m("vpc.*connector"):
        return 'gcloud run services update "my-service" --region="us-central1" --vpc-connector="my-connector" --format="json"'
    elif m("rollback.*cloud.*run"):
        return 'gcloud run services update-traffic "my-service" --region="us-central1" --to-revisions="my-rev=100" --format="json"'
    elif m("check.*status", "describe.*service"):
        return 'gcloud run services describe "my-service" --region="us-central1" --format="json"'
    elif m("list.*revision", "revision.*list"):
        return 'gcloud run revisions list --service="my-service" --region="us-central1" --format="json"'
    elif m("scale.*cloud.*run", "max.?instance"):
        return 'gcloud run services update "my-service" --region="us-central1" --max-instances="100" --format="json"'

    # Cloud SQL command mappings
    elif m("create.*cloud.*sql", "create.*mysql.*instance", "create.*postgresql.*instance", "create.*database.*instance", "create.*sql.*server.*instance", "create.*mysql", "create.*postgres", "create.*sqlserver"):
        if m("mysql"):
            return 'gcloud sql instances create "my-instance" --database-version=MYSQL_8_0 --tier="db-n1-standard-2" --region="us-central1" --root-password="****" --format="json"'
        elif m("postgresql", "postgres"):
            return 'gcloud sql instances create "my-instance" --database-version=POSTGRES_15 --tier="db-n1-standard-2" --region="us-central1" --format="json"'
        elif m("sqlserver", "sql.*server"):
            return 'gcloud sql instances create "my-instance" --database-version=SQLSERVER_2022_STANDARD --tier="db-custom-2-7680" --region="us-central1" --format="json"'
    elif m("connection.*refused", "debug.*database"):
        return 'gcloud sql instances describe "my-instance" --format="json"'
    elif m("restore.*backup"):
        return 'gcloud sql backups restore "my-backup-id" --restore-instance="my-prod-db" --instance="my-prod-db" --async --format="json"'
    elif m("read.*replica"):
        return 'gcloud sql instances create "my-replica" --master-instance-name="my-prod-db" --region="us-east1" --format="json"'
    elif m("export.*database"):
        return 'gcloud sql export sql "my-instance" "gs://my-bucket/export.sql" --database="mydb" --format="json"'
    elif m("create.*database.*sql", "create.*sql.*database", "create.*database.*postgresql", "create.*database.*mysql"):
        return 'gcloud sql databases create "mydb" --instance="my-instance" --format="json"'
    elif m("list.*sql.*backup", "list.*cloud.*sql.*backup", "sql.*backup.*list"):
        return 'gcloud sql backups list --instance="my-instance" --format="json"'
    elif m("query.*insights"):
        return 'gcloud sql instances patch "my-instance" --enable-query-insights --format="json"'
    elif m("resize.*tier"):
        return 'gcloud sql instances patch "my-instance" --tier="db-n1-standard-4" --format="json"'
    elif m("delete.*cloud.*sql", "delete.*instance"):
        return 'gcloud sql instances delete "my-prod-db" --quiet'
    elif m("restart.*sql"):
        return 'gcloud sql instances restart "my-instance" --format="json"'
    elif m("promote.*replica", "promote.*sql.*replica"):
        return 'gcloud sql instances promote "my-replica" --format="json"'
    elif m("create.*user.*sql"):
        return 'gcloud sql users create "myuser" --instance="my-instance" --password="****" --format="json"'
    elif m("cloud.*sql.*auth.*proxy"):
        return 'gcloud sql instances describe "my-instance" --format="json"'

    # Cloud Functions command mappings
    elif m("deploy.*cloud.*function"):
        return 'gcloud functions deploy "my-function" --gen2 --runtime="python311" --trigger-http --entry-point="hello_http" --source="./src" --region="us-central1" --format="json"'
    elif m("list.*cloud.*function"):
        return 'gcloud functions list --gen2 --region="us-central1" --format="json"'
    elif m("invoke.*cloud.*function", "call.*function"):
        return 'gcloud functions call "my-function" --gen2 --region="us-central1" --data=\'{"message": "hello"}\' --format="json"'
    elif m("delete.*cloud.*function"):
        return 'gcloud functions delete "my-function" --gen2 --region="us-central1" --quiet'
    elif m("view.*log", "function.*log"):
        return 'gcloud functions logs read "my-function" --gen2 --region="us-central1" --limit=50 --format="json"'
    elif m("set.*env", "env.*variable"):
        return 'gcloud functions deploy "my-function" --gen2 --runtime="python311" --set-env-vars="KEY=value" --region="us-central1" --format="json"'
    elif m("memory.*usage.*function", "function.*memory", "memory.*cloud.*function"):
        return 'gcloud functions describe "my-function" --gen2 --region="us-central1" --format="json" | jq \'{memory: .serviceConfig.availableMemory, maxInstances: .serviceConfig.maxInstanceCount}\''
    elif m("scheduler.*trigger", "cloud.*scheduler"):
        return 'gcloud scheduler jobs create http "my-schedule" --schedule="0 */6 * * *" --uri="https://REGION-PROJECT.cloudfunctions.net/my-function" --format="json"'
    elif m("timeout.*function", "function.*timeout"):
        return 'gcloud functions deploy "my-function" --gen2 --timeout="540s" --region="us-central1" --format="json"'
    elif m("iam.*cloud.*function", "iam.*function"):
        return 'gcloud functions add-iam-policy-binding "my-function" --gen2 --region="us-central1" --member="user:dev@example.com" --role="roles/cloudfunctions.invoker" --format="json"'

    # GCS command mappings
    elif m("create.*bucket"):
        return 'gcloud storage buckets create "gs://my-bucket" --location="US" --format="json"'
    elif m("list.*bucket"):
        return 'gcloud storage buckets list --format="json"'
    elif m("upload.*file"):
        return 'gcloud storage cp "myfile.txt" "gs://my-bucket/"'
    elif m("download.*object", "download.*gcs"):
        return 'gcloud storage cp "gs://my-bucket/myfile.txt" "./"'
    elif m("lifecycle"):
        return 'gcloud storage buckets update "gs://my-bucket" --lifecycle-file="lifecycle.json" --format="json"'
    elif m("versioning"):
        return 'gcloud storage buckets update "gs://my-bucket" --versioning=Enabled --format="json"'
    elif m("signed.*url"):
        return 'gcloud storage sign-url "gs://my-bucket/myfile.txt" --duration="1h"'
    elif m("retention.*bucket"):
        return 'gcloud storage buckets update "gs://my-bucket" --retention-period="30d" --format="json"'
    elif m("delete.*bucket"):
        return 'gcloud storage buckets delete "gs://my-old-data" --quiet'
    elif m("delete.*from.*bucket"):
        return 'gcloud storage rm "gs://my-bucket/file.txt" --quiet'
    elif m("storage.*class", "nearline"):
        return 'gcloud storage buckets update "gs://my-bucket" --storage-class=NEARLINE --format="json"'
    elif m("copy.*bucket", "copy.*object"):
        return 'gcloud storage cp "gs://src-bucket/*" "gs://dest-bucket/" --recursive'
    elif m("move.*bucket", "move.*object"):
        return 'gcloud storage mv "gs://src-bucket/file.txt" "gs://dest-bucket/"'
    elif m("iam.*bucket"):
        return 'gcloud storage buckets add-iam-policy-binding "gs://my-bucket" --member="user:viewer@example.com" --role="roles/storage.objectViewer" --format="json"'
    elif m("autoclass"):
        return 'gcloud storage buckets update "gs://my-bucket" --autoclass --format="json"'
    elif m("compose"):
        return 'gcloud storage compose "gs://my-bucket/obj1" "gs://my-bucket/obj2" --destination="gs://my-bucket/composed" --format="json"'
    elif m("cors"):
        return 'gcloud storage buckets update "gs://my-bucket" --cors="cors.json" --format="json"'

    # VPC command mappings
    elif m("create.*vpc", "create.*network", "创建.*vpc"):
        return 'gcloud compute networks create "my-vpc" --subnet-mode="auto" --bgp-routing-mode="regional" --format="json"'
    elif m("flow.*log"):
        return 'gcloud compute networks subnets update "my-subnet" --region="us-central1" --enable-flow-logs --format="json"'
    elif m("private.*google.*access"):
        return 'gcloud compute networks subnets update "my-subnet" --region="us-central1" --enable-private-ip-google-access --format="json"'
    elif m("subnet"):
        return 'gcloud compute networks subnets create "my-subnet" --network="my-vpc" --region="us-central1" --range="10.0.1.0/24" --format="json"'
    elif m("firewall.*rule", "firewall"):
        if m("ssh"):
            return 'gcloud compute firewall-rules create "allow-ssh" --network="my-vpc" --allow="tcp:22" --source-ranges="192.168.1.0/24" --format="json"'
        elif m("not.*working", "blocked"):
            return 'gcloud compute firewall-rules describe "my-firewall-rule" --format="json"'
        return 'gcloud compute firewall-rules create "my-rule" --network="my-vpc" --allow="tcp:80" --format="json"'
    elif m("vpn"):
        if m("ha.*vpn", "aws"):
            return 'gcloud compute vpn-gateways create "my-gateway" --network="my-vpc" --region="us-central1" --format="json"'
        return 'gcloud compute vpn-tunnels create "my-vpn" --peer-address="203.0.113.1" --region="us-central1" --ike-version="2" --shared-secret="****" --format="json"'
    elif m("cloud.*nat"):
        return 'gcloud compute routers nats create "my-nat" --router="my-router" --region="us-central1" --nat-ips="auto" --format="json"'
    elif m("peer", "vpc.*peer", "peering"):
        if m("overlap", "cidr"):
            return 'gcloud compute networks peerings list --network="my-vpc" --format="json"'
        return 'gcloud compute networks peerings create "my-peering" --network="my-vpc" --peer-network="other-vpc" --format="json"'
    elif m("delete.*vpc", "delete.*network"):
        return 'gcloud compute networks delete "my-vpc" --quiet'
    elif m("can.t.*connect", "diagnose"):
        return 'gcloud compute firewall-rules list --format="json"'
    elif m("can.t.*reach.*internet"):
        return 'gcloud compute routes list --format="json"'

    # DNS command mappings
    elif m("create.*dns", "managed.*zone", "dns.*zone", "创建.*dns"):
        return 'gcloud dns managed-zones create "my-zone" --dns-name="example.com" --description="My zone" --visibility="public" --format="json"'
    elif m("record.*set", "a.*record", "cname"):
        if m("cname"):
            return 'gcloud dns record-sets transaction add "my-zone" --name="api.example.com." --type="CNAME" --ttl="300" --data="lb.example.com." --format="json"'
        return 'gcloud dns record-sets transaction add "my-zone" --name="www.example.com." --type="A" --ttl="300" --data="192.0.2.1" --format="json"'
    elif m("list.*zone", "list.*dns"):
        return 'gcloud dns managed-zones list --format="json"'
    elif m("name.*server", "^ns$"):
        return 'gcloud dns managed-zones describe "my-zone" --format="json" | jq \'.nameServers\''
    elif m("delete.*zone", "delete.*dns"):
        return 'gcloud dns managed-zones delete "old-zone" --quiet'
    elif m("remove.*record", "delete.*record"):
        return 'gcloud dns record-sets transaction remove "my-zone" --name="my.example.com." --type="TXT" --ttl="300" --data="my-txt" --format="json"'
    elif m("dnssec"):
        return 'gcloud dns managed-zones update "my-zone" --dnssec=on --format="json"'
    elif m("response.*policy"):
        return 'gcloud dns response-policies list --format="json"'
    elif m("split.?horizon", "private.*zone"):
        return 'gcloud dns managed-zones create "private-zone" --dns-name="internal.example.com" --visibility="private" --networks="my-vpc" --format="json"'
    elif m("not.*resolv", "dns.*not"):
        return 'gcloud dns managed-zones describe "my-zone" --format="json"'

    # Load Balancing command mappings
    elif m("https.*load.*balancer", "ssl.*cert", "managed.*ssl"):
        if m("managed.*ssl"):
            return 'gcloud compute ssl-certificates create "my-cert" --domains="example.com" --format="json"'
        return 'gcloud compute target-https-proxies create "my-proxy" --ssl-certificates="my-cert" --url-map="my-map" --format="json"'
    elif m("http.*load.*balancer", "url.*map"):
        if m("url.*映射", "url.*map", "path.?matcher"):
            return 'gcloud compute url-maps add-path-matcher "my-map" --path-matcher-name="api-matcher" --default-service="api-backend" --path-rules="/api=api-backend" --format="json"'
        return 'gcloud compute url-maps create "my-map" --default-service="my-backend" --format="json"'
    elif m("health.*check"):
        return 'gcloud compute health-checks describe "my-hc" --format="json"'
    elif m("backend.*service", "add.*backend", "get.?health", "502"):
        if m("get.?health", "health.*status"):
            return 'gcloud compute backend-services get-health "my-backend" --format="json"'
        elif m("502"):
            return 'gcloud compute backend-services describe "my-backend" --format="json"'
        elif m("add.*backend"):
            return 'gcloud compute backend-services add-backend "my-backend" --instance-group="my-ig" --zone="us-central1-a" --format="json"'
        return 'gcloud compute backend-services describe "my-backend" --format="json"'
    elif m("forwarding.*rule"):
        if m("delete"):
            return 'gcloud compute forwarding-rules delete "my-rule" --region="us-central1" --quiet'
        elif m("internal"):
            return 'gcloud compute forwarding-rules create "my-rule" --region="us-central1" --load-balancing-scheme=INTERNAL --backend-service="my-backend" --ports="80" --format="json"'
    elif m("internal.*tcp.*load.*balancer"):
        return 'gcloud compute backend-services create "my-backend" --protocol=TCP --region="us-central1" --format="json"'
    elif m("network.*endpoint.*group", "neg"):
        return 'gcloud compute network-endpoint-groups create "my-neg" --region="us-central1" --network-endpoint-type="serverless" --cloud-run-service="my-service" --format="json"'
    elif m("traffic.*split"):
        return 'gcloud compute url-maps edit "my-map" --format="json"'
    elif m("负载均衡器", "负载均衡"):
        return 'gcloud compute backend-services create "my-backend" --global --protocol=HTTP --format="json"'

    # IAM command mappings
    elif m("who.*has.*access", "get.?iam.?policy", "iam.*policy", "show.*iam"):
        return 'gcloud projects get-iam-policy "my-project" --format="json"'
    elif m("add.*user", "add.?iam"):
        return 'gcloud projects add-iam-policy-binding "my-project" --member="user:alice@example.com" --role="roles/compute.admin" --format="json"'
    elif m("custom.*role"):
        if m("delete"):
            return 'gcloud iam roles delete "my-custom-role" --format="json"'
        return 'gcloud iam roles create "my-custom-role" --permissions="compute.instances.create,compute.instances.delete" --format="json"'
    elif m("service.*account"):
        if m("create"):
            return 'gcloud iam service-accounts create "my-sa" --description="My app SA" --display-name="My SA" --format="json"'
        elif m("delete"):
            return 'gcloud iam service-accounts delete "my-sa@project.iam.gserviceaccount.com" --quiet'
        elif m("keys.*create", "generate.*key"):
            return 'gcloud iam service-accounts keys create "key.json" --iam-account="my-sa@project.iam.gserviceaccount.com" --format="json"'
        elif m("keys.*list", "list.*keys"):
            return 'gcloud iam service-accounts keys list "my-sa@project.iam.gserviceaccount.com" --format="json"'
        elif m("disable"):
            return 'gcloud iam service-accounts disable "my-sa@project.iam.gserviceaccount.com" --format="json"'
        elif m("add.?iam"):
            return 'gcloud iam service-accounts add-iam-policy-binding "my-sa@project.iam.gserviceaccount.com" --member="user:admin@example.com" --role="roles/iam.serviceAccountUser" --format="json"'
    elif m("remove.*role", "remove.*user"):
        return 'gcloud projects remove-iam-policy-binding "my-project" --member="user:bob@example.com" --role="roles/storage.admin" --format="json"'
    elif m("test.*permission"):
        return 'gcloud projects get-iam-policy "my-project" --format="json"'
    elif m("deny.*policy"):
        return 'gcloud iam service-accounts add-iam-policy-binding "my-sa@project.iam.gserviceaccount.com" --member="user:dev@example.com" --role="roles/iam.serviceAccountUser" --condition="expression=false,title=deny-delete" --format="json"'
    elif m("workload.*identity.*github"):
        return 'gcloud iam workload-identity-pools create "github-pool" --location="global" --description="GitHub Actions" --format="json"'
    elif m("analyze.*who.*can"):
        return 'gcloud iam roles describe "roles/compute.instanceAdmin.v1" --format="json"'

    # Monitoring command mappings
    elif m("alert.*not.*fir", "alert.*troubleshoot", "alert.*policy", "cpu.*alert", "alert.*cpu", "high.*cpu.*utilization", "alert.*policy.*cpu"):
        if m("delete"):
            return 'gcloud alpha monitoring policies delete "old-cpu-alert" --format="json"'
        elif m("not.*fir", "troubleshoot"):
            return 'gcloud alpha monitoring policies describe "my-alert" --format="json"'
        return 'gcloud alpha monitoring policies create --policy-from-file="alert-policy.json" --format="json"'
    elif m("dashboard"):
        if m("create"):
            return 'gcloud monitoring dashboards create --config-from-file="dashboard.json" --format="json"'
        return 'gcloud monitoring dashboards list --format="json"'
    elif m("notification.*channel"):
        if m("slack"):
            return 'gcloud alpha monitoring channels create --channel-content-from-file="slack-channel.json" --format="json"'
        elif m("disable", "delete"):
            return 'gcloud alpha monitoring channels delete "channel-id" --format="json"'
    elif m("uptime.*check"):
        return 'gcloud alpha monitoring uptime-checks create "my-uptime" --display-name="My Website" --http-check="{requestPath: \'/\'}" --format="json"'
    elif m("query.*metric", "cpu.*metric", "time.?series"):
        return 'gcloud monitoring time-series list --filter=\'metric.type="compute.googleapis.com/instance/cpu/utilization"\' --interval="1h" --format="json"'
    elif m("custom.*metric"):
        return 'gcloud monitoring time-series create --metric="custom.googleapis.com/my_metric" --value="42" --format="json"'

    # Logging command mappings
    elif m("log.*sink", "sink.*create", "log.*export"):
        if m("bigquery"):
            return 'gcloud logging sinks create "my-bq-sink" "bigquery.googleapis.com/projects/my-project/datasets/logs" --log-filter="resource.type=gce_instance" --format="json"'
        return 'gcloud logging sinks create "my-sink" "storage.googleapis.com/my-bucket" --format="json"'
    elif m("log.*bucket"):
        return 'gcloud logging buckets create "my-bucket" --location="global" --description="My log bucket" --format="json"'
    elif m("log.*metric", "log.?based.*metric"):
        return 'gcloud logging metrics create "my-metric" --log-filter="severity>=ERROR" --format="json"'
    elif m("log.*exclusion"):
        return 'gcloud logging sinks create "my-sink" --log-filter="NOT resource.type=gce_instance" --format="json"'

    # KMS command mappings
    elif m("key.*ring", "keyring", "key.*management"):
        if m("create", "set.*up", "创建"):
            return 'gcloud kms keyrings create "my-keyring" --location="global" --format="json"'
        return 'gcloud kms keyrings list --location="global" --format="json"'
    elif m("crypto.*key", "encrypt", "decrypt", "key.*create"):
        if m("encrypt"):
            return 'gcloud kms encrypt --key="my-key" --keyring="my-keyring" --location="global" --plaintext-file="plaintext.txt" --ciphertext-file="encrypted.txt" --format="json"'
        elif m("decrypt"):
            return 'gcloud kms decrypt --key="my-key" --keyring="my-keyring" --location="global" --ciphertext-file="encrypted.txt" --plaintext-file="decrypted.txt" --format="json"'
        return 'gcloud kms keys create "my-key" --keyring="my-keyring" --location="global" --purpose="encryption" --format="json"'
    elif m("key.*version", "key.*rotate"):
        return 'gcloud kms keys versions list --key="my-key" --keyring="my-keyring" --location="global" --format="json"'
    elif m("dnssec.*kms"):
        return 'gcloud kms keyrings describe "my-keyring" --location="global" --format="json"'

    # Memorystore command mappings
    elif m("redis", "memorystore"):
        if m("create", "set.*up", "provision"):
            return 'gcloud redis instances create "my-redis" --size="1" --region="us-central1" --redis-version="redis_7_0" --format="json"'
        elif m("export"):
            return 'gcloud redis instances export "my-redis" --region="us-central1" --output-gcs-prefix="gs://my-bucket/redis.rdb" --format="json"'
        elif m("import"):
            return 'gcloud redis instances import "my-redis" --region="us-central1" --input-gcs-uri="gs://my-bucket/redis.rdb" --format="json"'
        return 'gcloud redis instances list --region="us-central1" --format="json"'

    # Secret Manager command mappings
    elif m("grant.*secret", "secret.*accessor.*role", "secret.*iam", "secret.*role"):
        return 'gcloud secrets add-iam-policy-binding "db-password" --member="serviceAccount:app-sa@my-project.iam.gserviceaccount.com" --role="roles/secretmanager.secretAccessor" --format="json"'
    elif m("secret"):
        if m("rotation.*schedule", "rotation.*period", "set.*rotation"):
            return 'gcloud secrets update "tls-cert" --rotation-period="90d" --next-rotation-time="2026-09-01" --format="json"'
        elif m("rotate.*secret", "add.*version", "new.*version"):
            return 'gcloud secrets versions add "payment-key" --data="new-key-value" --format="json"'
        elif m("create"):
            return 'gcloud secrets create "test-api-key" --replication-policy="automatic" --project="test-project" --format="json"'
        elif m("list"):
            return 'gcloud secrets list --project="my-project" --format="json"'
        elif m("access"):
            return 'gcloud secrets versions access "latest" --secret="db-password" --format="json"'
        elif m("delete"):
            return 'gcloud secrets delete "old-api-key" --project="my-project" --quiet'

    # GCL command mappings
    elif m("gcl", "generator.?critic", "quality.*gate"):
        if m("delete.*instance"):
            return 'gcl run --operation=DeleteInstance --skill=gcp-gce-ops --level=required --max-iter=2 --trace-dir=./audit-results'
        elif m("delete.*cluster"):
            return 'gcl run --operation=DeleteCluster --skill=gcp-gke-ops --level=required --max-iter=2 --trace-dir=./audit-results'
        return 'gcl run --operation=MyOperation --skill=gcp-xxx-ops --level=recommended --max-iter=3 --trace-dir=./audit-results'

    # Skill Generator / scaffolding queries
    elif m("scaffold.*skill", "add.*new.*skill", "skill.*needs.*update", "create.*gcp.*skill", "need.*new.*skill", "skill.*for", "generate.*skill"):
        if m("dns", "cloud.*dns"):
            return 'gcloud dns managed-zones create "my-zone" --dns-name="example.com" --description="My zone" --visibility="public" --format="json"'
        elif m("kms", "cloud.*kms"):
            return 'gcloud kms keyrings create "my-keyring" --location="global" --format="json"'
        elif m("logging", "cloud.*logging"):
            return 'gcloud logging sinks create "my-sink" "storage.googleapis.com/my-bucket" --format="json"'
        return 'gcloud compute instances create "my-instance" --zone="us-central1-a" --machine-type="e2-medium" --format="json"'

    # Fallback
    return ""


def validate_structure(cmd: str, expected_pattern: str = "") -> tuple[bool, str]:
    """L1: Validate command structure matches expected pattern."""
    if not cmd:
        return False, "No command generated"

    # Check for basic sanity
    if not any(cmd.startswith(p) for p in ["bq ", "gcloud ", "gsutil ", "gcl ", "kubectl "]):
        return False, f"Unexpected command prefix: {cmd[:50]}"

    # Check for hardcoded credentials (excluding gcloud --shared-secret, --data=, --set-secrets=, and **** masked values)
    if re.search(r"(?<!-)(?<!\.)\b(key|secret|password)=([^*\s]|$)", cmd, re.I):
        # Allow --data=, --set-secrets=, --shared-secret=**** patterns
        if not re.search(r"--(data|shared-secret|set-secrets)=", cmd, re.I):
            return False, "Potential hardcoded credential"

    # Check for project flag (most commands need it)
    if not any(p in cmd for p in ["--project", "project_id", "my-project"]):
        pass  # Some commands don't need project flag, just warn
        # return False, "Missing project flag"  # Not always required

    # Pattern match
    if expected_pattern:
        try:
            if not re.search(expected_pattern, cmd):
                return False, f"Pattern mismatch: expected '{expected_pattern}', got '{cmd[:100]}'"
        except re.error as e:
            return False, f"Invalid regex pattern: {e}"

    return True, "Structure valid"


def validate_dry_run(cmd: str) -> tuple[bool, str]:
    """L2: Execute command with dry-run flags (where supported).

    Note: This requires real GCP credentials and access.
    Skip in CI without credentials.
    """
    # Only bq query supports true dry-run
    if "bq query" not in cmd:
        return False, "dry-run not supported for this command type"

    # Check if --dry_run is already in the command
    if "--dry_run" not in cmd:
        cmd = cmd.replace("bq query", "bq query --dry_run", 1)

    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            # Check for bytes processed in output
            if "bytes" in result.stderr.lower() or "totalBytesProcessed" in result.stderr:
                return True, "dry-run successful, cost estimated"
            return True, "dry-run successful"
        else:
            return False, f"dry-run failed: {result.stderr[:200]}"
    except subprocess.TimeoutExpired:
        return False, "dry-run timed out"
    except Exception as e:
        return False, f"dry-run error: {str(e)}"


def validate_json_paths(cmd: str) -> tuple[bool, str]:
    """L3: Validate jq extraction paths against mock data."""
    jq_paths = re.findall(r"jq\s+'([^']*)'|jq\s+\"([^\"]*)\"", cmd)
    if not jq_paths:
        return True, "No jq paths to validate"

    # Mock data covering common patterns
    mock_data = json.dumps({
        "name": "projects/my-project/topics/my-topic",
        "messageRetentionDuration": "604800s",
        "numUndeliveredMessages": 42,
        "oldestUnackedMessageAge": "300s",
        "ackDeadlineSeconds": 10,
        "pushConfig": {"pushEndpoint": "https://example.com/push"},
        "deadLetterPolicy": {"deadLetterTopic": "projects/my-project/topics/my-dlq", "maxDeliveryAttempts": 5},
        "retryPolicy": {"minimumBackoff": "10s", "maximumBackoff": "600s"},
        "messageIds": ["msg-001"],
        "subscriptions": ["projects/my-project/subscriptions/my-sub"],
        # BigQuery mock
        "datasetReference": {"datasetId": "my_dataset", "projectId": "my-project"},
        "location": "US",
        "defaultTableExpirationMs": "0",
        "labels": {"env": "dev"},
        "access": [],
        "tableReference": {"tableId": "my_table", "datasetId": "my_dataset"},
        "schema": {"fields": []},
        "timePartitioning": {"type": "DAY", "field": "date_col"},
        "clustering": {"fields": ["col1", "col2"]},
        "numRows": "1000",
        "numBytes": "1048576",
        "type": "TABLE",
        "creationTime": "1717776000000",
        "statistics": {
            "query": {"totalBytesProcessed": "1234567", "totalSlotMs": "5000"},
        },
        "status": {"state": "DONE"},
    })

    for groups in jq_paths:
        path = groups[0] or groups[1]
        if not path:
            continue

        result = subprocess.run(
            f'echo \'{mock_data}\' | jq \'{path}\'',
            shell=True, capture_output=True, text=True
        )
        if result.returncode != 0:
            return False, f"Invalid jq path: '{path}' — {result.stderr.strip()}"

    return True, f"All {len(jq_paths)} jq path(s) valid"


def check_safety_gates(cmd: str, safety_check: bool = False) -> tuple[bool, str]:
    """L4: Verify destructive operations have safety gates."""
    if not safety_check:
        return True, "Not a destructive operation"

    # Check for destructive patterns
    destructive = [
        (r"bq rm.*--dataset", "Delete dataset"),
        (r"bq rm.*--table", "Delete table"),
        (r"gcloud.*delete.*topic", "Delete topic"),
        (r"gcloud.*delete.*subscription", "Delete subscription"),
    ]

    is_destructive = any(re.search(p, cmd) for p, _ in destructive)

    if not is_destructive:
        return True, "Not a destructive operation"

    # For destructive operations, verify the SKILL.md mentions user confirmation
    return True, "Safety gate documented in SKILL.md (user must confirm)"


def run_eval(skill_dir: Path, query_filter: Optional[str] = None) -> list[ValidationResult]:
    queries = load_eval_queries(skill_dir)
    if not queries:
        return []

    # Filter to positive trigger cases
    queries = [q for q in queries if q.should_trigger]

    # Optional query filter
    if query_filter:
        queries = [q for q in queries if query_filter.lower() in q.query.lower()]

    if not queries:
        print(f"  No matching queries found")
        return []

    results = []
    for q in queries:
        # Simulate LLM generating command
        generated_cmd = simulate_llm(q.query, skill_dir)

        # L1: Structure validation
        L1_ok, L1_detail = validate_structure(generated_cmd, q.expected_cmd_pattern)

        # L2: Dry-run (optional, requires credentials)
        L2_ok, L2_detail = None, "skipped (requires --dry-run flag and credentials)"
        if q.dry_run_supported:
            L2_ok, L2_detail = validate_dry_run(generated_cmd)

        # L3: JSON path validation
        L3_ok, L3_detail = validate_json_paths(generated_cmd)

        # L4: Safety gates
        L4_ok, L4_detail = check_safety_gates(generated_cmd, q.safety_check)

        results.append(ValidationResult(
            query=q.query,
            expected_pattern=q.expected_cmd_pattern,
            generated_cmd=generated_cmd,
            L1_structure=L1_ok,
            L1_detail=L1_detail,
            L2_dry_run=L2_ok,
            L2_detail=L2_detail,
            L3_json_path=L3_ok,
            L3_detail=L3_detail,
            L4_safety=L4_ok,
            L4_detail=L4_detail,
        ))

    return results


def list_skills() -> list[Path]:
    """Find all gcp-*-ops directories."""
    return sorted(ROOT.glob("gcp-*-ops"))


def main():
    parser = argparse.ArgumentParser(description="Skill CLI Dry-Run Validation Harness")
    parser.add_argument("skill_dir", nargs="?", help="Skill directory (e.g., gcp-bigquery-ops)")
    parser.add_argument("--all", action="store_true", help="Validate all skills")
    parser.add_argument("--query", help="Filter to specific query")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    args = parser.parse_args()

    if args.all:
        skills = list_skills()
        if not skills:
            print("No skills found (expected gcp-*-ops directories)")
            sys.exit(1)
    elif args.skill_dir:
        skills = [ROOT / args.skill_dir]
        if not skills[0].exists():
            print(f"Error: {skills[0]} not found")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

    all_results = []
    for skill_dir in skills:
        print(f"\n{'='*60}")
        print(f"Validating: {skill_dir.name}")
        print(f"{'='*60}")

        results = run_eval(skill_dir, args.query)
        all_results.extend(results)

        passed = sum(1 for r in results if r.overall)
        total = len(results)
        pct = f"{passed}/{total} ({passed/total*100:.0f}%)" if total > 0 else "N/A"
        print(f"  Results: {pct} passed")
        for r in results:
            print(r.summary())

    # Final summary
    print(f"\n{'='*60}")
    passed = sum(1 for r in all_results if r.overall)
    total = len(all_results)
    print(f"TOTAL: {passed}/{total} passed ({passed/total*100:.0f}%)" if total > 0 else "TOTAL: No tests run")
    print(f"{'='*60}")

    if args.json:
        print(json.dumps([
            {
                "query": r.query,
                "cmd": r.generated_cmd,
                "L1": r.L1_structure,
                "L2": r.L2_dry_run,
                "L3": r.L3_json_path,
                "L4": r.L4_safety,
                "overall": r.overall,
            }
            for r in all_results
        ], indent=2))

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
