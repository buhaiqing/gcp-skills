# Core Concepts — Google Cloud Composer

## Architecture Overview

Cloud Composer is a managed Apache Airflow service that runs on GKE:

```
Cloud Composer Environment
├── Airflow Webserver (UI)
├── Airflow Scheduler
├── Airflow Workers (GKE pods)
├── Cloud SQL (metadata)
├── Cloud Storage (DAGs, plugins, logs)
└── GKE Cluster (underlying infrastructure)
```

## Key Concepts

| Concept | Description |
|---------|-------------|
| **Environment** | Complete Airflow installation with all components |
| **DAG** | Directed Acyclic Graph — workflow definition |
| **Operator** | Atomic unit of work in a DAG |
| **Sensor** | Waits for a condition to be met |
| **Connection** | Configuration for external systems |
| **Variable** | Key-value pair for runtime configuration |
| **Pool** | Resource slot management for task execution |
| **Queue** | Celery queue for task routing |

## Environment States

| State | Description |
|-------|-------------|
| `CREATING` | Environment being provisioned |
| `RUNNING` | Environment ready for use |
| `UPDATING` | Environment being modified |
| `DELETING` | Environment being removed |
| `ERROR` | Environment in error state |
| `WAITING_FOR_WORKER` | Worker node provisioning |

## Airflow Versions

| Composer Version | Airflow Version | Python Version |
|------------------|-----------------|----------------|
| Composer 2.9.x | Airflow 2.9.x | 3.11, 3.12 |
| Composer 2.8.x | Airflow 2.8.x | 3.11 |
| Composer 2.7.x | Airflow 2.7.x | 3.11 |
| Composer 2.6.x | Airflow 2.6.x | 3.8, 3.9, 3.10 |

## Environment Sizes

| Size | Workers | CPU | Memory |
|------|---------|-----|--------|
| Small | 3-6 | 2 vCPU | 7.5 GB |
| Medium | 6-9 | 4 vCPU | 15 GB |
| Large | 9-12 | 8 vCPU | 30 GB |

## Quotas and Limits

| Resource | Default Limit |
|----------|---------------|
| Environments per project | 5 |
| DAGs per environment | No limit |
| Variables per environment | No limit |
| Connections per environment | No limit |
| PyPI packages | No limit |

## Regions and Availability

- Environments are regional resources
- Each environment runs in a single region
- Multi-region requires multiple environments
- GKE cluster provides high availability within region

## Dependency Graph

```
Cloud Composer Environment
    ↑
GKE Cluster (managed)
    ↑
VPC Network (shared)
    ↑
Cloud SQL (metadata database)
    ↑
Cloud Storage (DAGs, logs)
```

## Airflow Concepts

### DAGs

```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

with DAG(
    'example_dag',
    start_date=datetime(2024, 1, 1),
    schedule_interval='@daily',
    catchup=False,
) as dag:
    
    task1 = PythonOperator(
        task_id='task1',
        python_callable=my_function,
    )
```

### Connections

```python
# Airflow connection types
conn_id = 'my_database'
conn_type = 'postgres'
host = 'database.example.com'
port = 5432
schema = 'mydb'
```

### Variables

```python
# Airflow variables
from airflow.models import Variable
value = Variable.get('my_key', default_var='default')
```
