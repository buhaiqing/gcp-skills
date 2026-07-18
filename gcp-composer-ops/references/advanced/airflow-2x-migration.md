# Airflow 2.x Migration Guide

## Table of Contents

- [Overview](#overview)
- [TaskGroup Migration](#taskgroup-migration)
- [Sensor Changes](#sensor-changes)
- [PythonVirtualenvOperator Migration](#pythonvirtualenvoperator-migration)
- [HA Cluster Migration](#ha-cluster-migration)
- [Breaking Changes Summary](#breaking-changes-summary)
- [Migration Validation](#migration-validation)

---

## Overview

This guide covers migrating from Airflow 1.x to Airflow 2.x in Cloud Composer environments, focusing on TaskGroup patterns, sensor retirement, operator changes, and HA configuration.

## TaskGroup Migration

### TaskGroup vs Old TaskInstance Grouping

Airflow 2.x introduces TaskGroup for organizing tasks visually and logically, replacing the informal grouping patterns used in 1.x.

### Migration: Informal Groups to TaskGroup

**Before (Airflow 1.x pattern)**

```python
# Informal naming convention for grouping
with dag:
    # ETL tasks
    etl_extract = PythonOperator(task_id='etl_extract', python_callable=extract)
    etl_transform = PythonOperator(task_id='etl_transform', python_callable=transform)
    etl_load = PythonOperator(task_id='etl_load', python_callable=load)

    # Reporting tasks
    report_generate = PythonOperator(task_id='report_generate', python_callable=generate_report)
    report_send = PythonOperator(task_id='report_send', python_callable=send_report)

    etl_extract >> etl_transform >> etl_load >> report_generate >> report_send
```

**After (Airflow 2.x TaskGroup)**

```python
from airflow.utils.task_group import TaskGroup

with dag:
    with TaskGroup(group_id='etl') as etl_group:
        extract = PythonOperator(task_id='extract', python_callable=extract)
        transform = PythonOperator(task_id='transform', python_callable=transform)
        load = PythonOperator(task_id='load', python_callable=load)

        extract >> transform >> load

    with TaskGroup(group_id='reporting') as reporting_group:
        generate = PythonOperator(task_id='generate', python_callable=generate_report)
        send = PythonOperator(task_id='send', python_callable=send_report)

        generate >> send

    etl_group >> reporting_group
```

### TaskGroup with DAG Reference

```python
from airflow.utils.task_group import TaskGroup

with DAG(dag_id='main_dag', start_date=datetime(2026, 1, 1)) as dag:
    with TaskGroup(group_id='stage1') as stage1:
        t1 = PythonOperator(task_id='task1', python_callable=func1)
        t2 = PythonOperator(task_id='task2', python_callable=func2)
        t1 >> t2

    with TaskGroup(group_id='stage2') as stage2:
        t3 = PythonOperator(task_id='task3', python_callable=func3)
        t4 = PythonOperator(task_id='task4', python_callable=func4)
        t3 >> t4

    stage1 >> stage2
```

### TaskGroup and XCom

```python
# XCom works across TaskGroups via task_id
with TaskGroup(group_id='etl') as etl_group:
    extract = PythonOperator(task_id='extract', python_callable=extract)

    transform = PythonOperator(
        task_id='transform',
        python_callable=transform,
        op_args=[extract.output],  # Access via task_id, not group_id
    )

    extract >> transform
```

---

## Sensor Changes

### Smart Sensor Retirement

Airflow 2.x retires the Smart Sensor service (deprecated). Tasks that relied on Smart Sensors must be migrated to standard sensors or TaskFlow patterns.

### Migration: Smart Sensor to Standard Sensor

**Before (Airflow 1.x with Smart Sensor)**

```python
# Smart sensor pattern (Airflow 1.x)
from airflow.operators.sensors import HttpSensor

# Smart sensor would batch-check multiple HttpSensors
check_api = HttpSensor(
    task_id='check_api',
    http_conn_id='api',
    endpoint='status',
    smart_sensor=True,  # Deprecated in 2.x
)
```

**After (Airflow 2.x standard sensor)**

```python
from airflow.providers.http.sensors.http import HttpSensor

check_api = HttpSensor(
    task_id='check_api',
    http_conn_id='api',
    endpoint='status',
    timeout=300,
    poke_interval=60,
    mode='reschedule',  # Use reschedule mode for efficiency
)
```

### Sensor Mode Options

| Mode | Description | Use Case |
|------|-------------|----------|
| `poke` | Continuously runs sensor (default) | Fast checks, short timeouts |
| `reschedule` | Releases worker between checks | Long-running sensors, saves resources |
| `smart_sensor` | **Removed in 2.x** | Use `reschedule` instead |

### Common Sensor Migrations

| 1.x Pattern | 2.x Migration |
|-------------|---------------|
| `smart_sensor=True` | Use `mode='reschedule'` |
| `sensors.SqlSensor` | `providers.http.sensors.sql.SqlSensor` |
| `sensors.HdfsSensor` | `providers.hadoop.sensors.hdfs.HdfsSensor` |
| `sensors.HivePartitionSensor` | `providers.apache.hive.sensors.hive.HivePartitionSensor` |

---

## PythonVirtualenvOperator Migration

### PythonVirtualenvOperator Changes

Airflow 2.x deprecates `PythonVirtualenvOperator` in favor of `PythonOperator` with virtualenv support or `PythonDecoratorOperator` (TaskFlow).

### Migration: PythonVirtualenvOperator to PythonOperator

**Before (Airflow 1.x)**

```python
from airflow.operators.virtualenv import PythonVirtualenvOperator

venv_task = PythonVirtualenvOperator(
    task_id='venv_task',
    python_callable=my_function,
    requirements=['pandas', 'numpy'],
    system_site_packages=False,
    dag=dag,
)
```

**After (Airflow 2.x TaskFlow)**

```python
from airflow.decorators import dag, task

@dag(start_date=datetime(2026, 1, 1))
def my_dag():
    @task
    def venv_task():
        import pandas  # Declared at runtime
        import numpy
        my_function()

    venv_task()
```

**After (Airflow 2.x with venv support)**

```python
from airflow.operators.python import PythonOperator

venv_task = PythonOperator(
    task_id='venv_task',
    python_callable=my_function,
    # Use virtualenv_args for venv support
    virtualenv_method='auto',
    dag=dag,
)
```

### Requirements via PythonOperator

```python
from airflow.operators.python import PythonOperator

# Install requirements inline
task_with_deps = PythonOperator(
    task_id='process_data',
    python_callable=process_data,
    # For Composer, use pypi_packages environment variable instead
)
```

### Composer-Specific: PyPI Packages

In Cloud Composer, manage dependencies via environment-level PyPI packages rather than per-task virtualenv:

```bash
# Update Composer environment with required packages
gcloud composer environments update ENVIRONMENT_NAME \
  --region=REGION \
  --update-pypi-packages-from-file=requirements.txt
```

---

## HA Cluster Migration

### High Availability Configuration

Airflow 2.x introduces better HA patterns for schedulers and web servers.

### Multi-Threaded Scheduler (vs Multi-Process)

**Airflow 1.x**: Used multiprocessing for parallelism
**Airflow 2.x**: Uses multithreading by default

```yaml
# airflow.cfg for Airflow 2.x
[scheduler]
# Number of scheduler threads
num_runs = 2
scheduler_heartbeat_sec = 5

# Use LocalExecutor for local testing
# Use CeleryExecutor for distributed
executor = CeleryExecutor
```

### Web Server HA

```bash
# Scale web servers (Cloud Composer specific)
gcloud composer environments update ENVIRONMENT_NAME \
  --region=REGION \
  --web-server-extra-config '{"web_server_visible": true}'
```

### Database HA (PostgreSQL)

```python
# connections.yaml for HA PostgreSQL
- conn_id: postgres_ha
  conn_type: postgres
  host: primary-host.internal
  port: 5432
  login: airflow_user
  password: '{{ env.POSTGRES_PASSWORD }}'
  schema: airflow
  extra:
    sslmode: require
    target_session_attrs: read-write
```

### Executor Migration

| 1.x Executor | 2.x Migration | Notes |
|--------------|---------------|-------|
| `SequentialExecutor` | `SequentialExecutor` | No change |
| `LocalExecutor` | `LocalExecutor` | Thread-based now |
| `CeleryExecutor` | `CeleryExecutor` | Use `CeleryKubernetesExecutor` for mixed |
| `MesosExecutor` | **Removed** | Migrate to KubernetesExecutor |

### KubernetesExecutor Migration

```yaml
# airflow.cfg for KubernetesExecutor
[kubernetes]
# Enable KubernetesExecutor
pod_template_file = /opt/airflow/pod_template.yaml
namespace = airflow
worker_container_repository = us-docker.pkg.dev/airflow-repo/composer
worker_container_tag = latest
delete_worker_pods = False
```

---

## Breaking Changes Summary

### Operator Changes

| 1.x | 2.x | Action |
|-----|-----|--------|
| `airflow.operators.PythonOperator` | `airflow.operators.python.PythonOperator` | Update imports |
| `airflow.operators.BashOperator` | `airflow.operators.bash.BashOperator` | Update imports |
| `airflow.operators.Sensors` | `airflow.providers.*.sensors.*` | Move to providers |
| `airflow.operators.subdag_operator.SubDagOperator` | `airflow.operators.subdag.SubDagOperator` | Update import |
| `airflow.operators.dagrun_operator` | `airflow.operators.dagrun_operator` | Provider-based |

### CLI Changes

| 1.x Command | 2.x Command |
|-------------|-------------|
| `airflow test` | `airflow tasks test` |
| `airflow run` | `airflow tasks run` |
| `airflow clear` | `airflow tasks clear` |
| `airflow list_dags` | `airflow dag list` |

### Config Changes

| Parameter | Change |
|-----------|--------|
| `sql_alchemy_pool_size` | Default changed from 5 to 5 |
| `sql_alchemy_pool_recycle` | Default changed from 3600 to 1800 |
| `web_server_host` | No default change |
| `rowsecurity` | Renamed to `access_control` |

### API Changes

| 1.x | 2.x |
|-----|-----|
| `/api/experimental/` | `/api/v1/` (stable API) |
| `DAG.get_instance` | `DAG.get_dagrun` |
| `TI.xcom_pull()` | `TI.xcom_pull()` (same, but context-based preferred) |

---

## Migration Validation

### Pre-Migration Checklist

| Check | Command |
|-------|---------|
| Validate DAG syntax | `airflow dags list` |
| Check for deprecated operators | `grep -r "airflow.operators" dags/` |
| Review custom sensors | `grep -r "smart_sensor" dags/` |
| Test in dev environment | Deploy to non-production Composer |

### Post-Migration Validation

```bash
# List DAGs and verify parsing
airflow dags list

# Test specific DAG
airflow tasks test DAG_ID TASK_ID EXECUTION_DATE

# Check DAG bag
airflow dagbag dump

# Verify connections
airflow connections list
```

### Composer-Specific Validation

```bash
# Check Composer environment version
gcloud composer environments describe ENVIRONMENT_NAME \
  --region=REGION \
  --format="value(config.airflowVersion)"

# Verify Airflow UI access
curl -s "https://$(gcloud composer environments describe ENVIRONMENT_NAME \
  --region=REGION \
  --format='value(config.webServerNetworkUri')" | head
```

---

## See Also

- [Airflow 2.0 Migration Guide](https://airflow.apache.org/docs/apache-airflow/stable/upgrading-to-2.html)
- [TaskGroup Documentation](https://airflow.apache.org/docs/apache-airflow/stable/concepts/taskgroups.html)
- [PythonVirtualenvOperator](https://airflow.apache.org/docs/apache-airflow/stable/_api/airflow/operators/python/index.html)
- [Cloud Composer Version Details](https://cloud.google.com/composer/docs/concepts/versioning)
