# Advanced DAG Patterns

## Table of Contents

- [Overview](#overview)
- [SubDAG Patterns](#subdag-patterns)
- [Cross-DAG Dependencies](#cross-dag-dependencies)
- [Dynamic Task Generation](#dynamic-task-generation)
- [Setup and Teardown Tasks](#setup-and-teardown-tasks)
- [SLA Monitoring](#sla-monitoring)
- [Retry Strategies](#retry-strategies)
- [Sensor Patterns](#sensor-patterns)

---

## Overview

Advanced DAG patterns for production Airflow environments covering SubDAGs, cross-DAG orchestration, dynamic generation, and operational concerns like SLA monitoring and retry strategies.

## SubDAG Patterns

### SubDAG Structure

```python
from airflow.models import DAG
from airflow.operators.subdag import SubDagOperator

def load_subdag_factory(parent_dag_name, child_dag_name, start_date, schedule_interval):
    """Factory for creating load SubDAGs."""
    subdag = DAG(
        dag_id=f"{parent_dag_name}.{child_dag_name}",
        start_date=start_date,
        schedule_interval=schedule_interval,
        catchup=False,
    )

    with subdag:
        from airflow.operators.python import PythonOperator

        def extract(**context):
            # Extract logic
            pass

        def transform(**context):
            # Transform logic
            pass

        def load(**context):
            # Load logic
            pass

        extract_task = PythonOperator(task_id='extract', python_callable=extract, dag=subdag)
        transform_task = PythonOperator(task_id='transform', python_callable=transform, dag=subdag)
        load_task = PythonOperator(task_id='load', python_callable=load, dag=subdag)

        extract_task >> transform_task >> load_task

    return subdag

# In parent DAG
load_subdag = SubDagOperator(
    task_id='etl_load',
    subdag=load_subdag_factory(
        parent_dag_name='parent_etl',
        child_dag_name='etl_load',
        start_date=datetime(2026, 1, 1),
        schedule_interval='@daily',
    ),
    dag=parent_dag,
)
```

### SubDAG Best Practices

| Practice | Rationale |
|----------|-----------|
| Use SubDAGs for reusable task groups | Encapsulate repeatable patterns |
| Limit SubDAG depth to 1 level | Nested SubDAGs reduce visibility |
| Set `shared_dag_id` for same-task SubDAGs | Avoids duplicate execution |
| Monitor SubDAGs via Airflow UI | SubDAG states aggregate to parent |

---

## Cross-DAG Dependencies

### TriggerDagRunOperator

```python
from airflow.operators.dagrun_operator import TriggerDagRunOperator

# Trigger dependent DAG
trigger_downstream = TriggerDagRunOperator(
    task_id='trigger_reporting_dag',
    trigger_dag_id='reporting_dag',
    execution_date='{{ logical_date }}',
    wait_for_completion=True,
    poke_interval=60,
    allowed_states=['success'],
    failed_states=['failed'],
    dag=upstream_dag,
)
```

### ExternalTaskSensor

```python
from airflow.sensors.external_task import ExternalTaskSensor

# Wait for external DAG to complete
wait_for_upstream = ExternalTaskSensor(
    task_id='wait_for_upstream_dag',
    external_dag_id='upstream_dag',
    external_task_id=None,  # Wait for entire DAG
    execution_date_fn=lambda dt: dt,  # Match same logical date
    timeout=7200,  # 2 hours
    poke_interval=300,
    mode='reschedule',
    dag=downstream_dag,
)
```

### Cross-DAG Pattern: Fan-out/Fan-in

```python
# Fan-out: Trigger multiple DAGs
trigger_analytics = TriggerDagRunOperator(
    task_id='trigger_analytics_dags',
    trigger_dag_id='analytics_pipeline',
    conf={'source': 'sales', 'date': '{{ ds }}'},
    dag=main_dag,
)

# Fan-in: Aggregate multiple DAG completions
wait_for_regions = [
    ExternalTaskSensor(
        task_id=f'wait_for_{region}_dag',
        external_dag_id=f'data_processing_{region}',
        external_task_id=None,
        execution_date_fn=lambda dt, r=region: dt,
        dag=aggregator_dag,
    )
    for region in ['us-east', 'us-west', 'eu-central']
]
```

---

## Dynamic Task Generation

### Dynamic TaskFlow API

```python
from airflow.decorators import dag, task

@dag(start_date=datetime(2026, 1, 1), schedule_interval='@daily')
def dynamic_tasks_dag():
    """DAG with dynamically generated tasks."""

    @task
    def get_users():
        # Simulate fetching user list
        return [{'id': 1, 'name': 'alice'}, {'id': 2, 'name': 'bob'}, {'id': 3, 'name': 'charlie'}]

    @task
    def process_user(user):
        return f"Processed {user['name']}"

    @task
    def aggregate(results):
        return f"Aggregated {len(results)} results"

    users = get_users()
    results = process_user.expand(user=users)
    aggregated = aggregate(results=[results])
```

### Dynamic Task Mapping (Airflow 2.3+)

```python
from airflow.decorators import dag, task

@dag(start_date=datetime(2026, 1, 1), schedule_interval='@daily')
def batch_processing_dag():
    """DAG with mapped tasks for batch processing."""

    @task
    def get_files():
        return ['file1.csv', 'file2.csv', 'file3.csv', 'file4.csv']

    @task
    def process_file(filename):
        # Process individual file
        return f"processed_{filename}"

    @task
    def combine_results(files):
        return f"Combined {len(files)} files"

    files = get_files()
    processed = process_file.expand(filename=files)
    combined = combine_results(files=[processed])
```

### Dynamic Task Generation via XCom

```python
from airflow.operators.python import PythonOperator

def generate_tasks(**context):
    """Generate tasks dynamically based on upstream output."""
    ti = context['ti']
    items = ti.xcom_pull(task_ids='fetch_config')

    task_ids = []
    for item in items:
        task_id = f"process_{item['id']}"
        task_ids.append(task_id)
        # Task generation handled via branching or subdag

    context['ti'].xcom_push(key='generated_tasks', value=task_ids)
    return task_ids

fetch_config = PythonOperator(
    task_id='fetch_config',
    python_callable=generate_tasks,
    dag=dag,
)
```

---

## Setup and Teardown Tasks

### Setup/Teardown Pattern (Airflow 2.7+)

```python
from airflow.decorators import dag, task

@dag(start_date=datetime(2026, 1, 1), schedule_interval='@daily')
def data_pipeline():
    """DAG with setup and teardown tasks."""

    @task
    def setup():
        """Initialize resources before pipeline."""
        return {'resources_initialized': True}

    @task
    def extract():
        """Extract data."""
        pass

    @task
    def transform():
        """Transform data."""
        pass

    @task
    def load():
        """Load data."""
        pass

    @task
    def teardown(**context):
        """Cleanup resources after pipeline."""
        pass

    # Define setup/teardown relationship
    setup_task = setup()
    teardown_task = teardown()

    extract_task = extract()
    transform_task = transform()
    load_task = load()

    # Setup runs before main pipeline
    setup_task >> extract_task

    # Teardown runs after main pipeline (on success or failure)
    extract_task >> transform_task >> load_task >> teardown_task

    # Alternative: use trigger_rule
    # extract_task >> transform_task >> load_task
    # [extract_task, transform_task, load_task] >> teardown_task
```

### Cleanup Task with Trigger Rule

```python
from airflow.utils.trigger_rule import TriggerRule

cleanup = PythonOperator(
    task_id='cleanup',
    python_callable=cleanup_resources,
    trigger_rule=TriggerRule.ALL_DONE,  # Run regardless of upstream success/failure
    dag=dag,
)

main_tasks >> cleanup
```

---

## SLA Monitoring

### SLA Miss Callback

```python
from airflow.utils.email import send_email
from airflow.models.slamiss import SlaMiss

def sla_callback(context, slams):
    """Callback when SLA is missed."""
    dag_id = context['dag'].dag_id
    task_id = slams.task_id
    execution_date = slams.execution_date

    subject = f"SLA Miss: {dag_id}.{task_id} @ {execution_date}"
    body = f"""
    DAG: {dag_id}
    Task: {task_id}
    Expected: {slams.dag_id}
    Execution Date: {execution_date}

    Please investigate.
    """

    # Send email notification
    send_email(to=['oncall@example.com'], subject=subject, html_content=body)

# In DAG definition
sla_miss_callback=sla_callback,
slas=[
    SLA(task_id='critical_task', dag=dag, warning_time=timedelta(minutes=30)),
    SLA(task_id='downstream_task', dag=dag, warning_time=timedelta(minutes=45)),
],
```

### SLA Configuration

```python
from airflow.models import SLA

with DAG(
    dag_id='production_etl',
    start_date=datetime(2026, 1, 1),
    schedule_interval='@daily',
    sla_miss_callback=sla_callback,
    default_args={
        'sla': timedelta(minutes=60),  # Default SLA for all tasks
    }
) as dag:
    # Tasks inherit default SLA unless overridden
    task1 = PythonOperator(task_id='task1', python_callable=func1)
    task2 = PythonOperator(task_id='task2', python_callable=func2, sla=timedelta(minutes=30))
```

---

## Retry Strategies

### Exponential Backoff Retry

```python
from airflow.models import DAG
from airflow.operators.python import PythonOperator
from airflow.models.param import Param

default_args = {
    'owner': 'composer',
    'start_date': datetime(2026, 1, 1),
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'retry_exponential_backoff': True,
    'max_retry_delay': timedelta(hours=2),
    'execution_timeout': timedelta(hours=1),
}

dag = DAG(
    dag_id='robust_etl',
    default_args=default_args,
    schedule_interval='@daily',
)
```

### Task-Specific Retry

```python
# High-priority task with aggressive retry
critical_task = PythonOperator(
    task_id='critical_api_call',
    python_callable=call_critical_api,
    retries=5,
    retry_delay=timedelta(seconds=30),
    retry_exponential_backoff=True,
    max_retry_delay=timedelta(minutes=5),
    dag=dag,
)

# Low-priority task with minimal retry
low_priority_task = PythonOperator(
    task_id='non_critical_cleanup',
    python_callable=cleanup,
    retries=1,
    retry_delay=timedelta(minutes=1),
    dag=dag,
)
```

### Retry Policy by Error Type

```python
from airflow.models import DAG
from airflow.operators.python import PythonOperator

def selective_retry(context):
    """Custom retry callback to inspect exception."""
    exception = context.get('exception')
    task_instance = context.get('task_instance')

    if isinstance(exception, ConnectionError):
        # Network issues: retry aggressively
        return True
    elif isinstance(exception, ValueError):
        # Bad input: don't retry
        return False
    elif isinstance(exception, TimeoutError):
        # Timeout: retry with longer delay
        return True

    # Default: use task's own retry settings
    return None

task = PythonOperator(
    task_id='api_task',
    python_callable=call_api,
    retries=3,
    retry_delay=timedelta(minutes=2),
    on_retry_callback=selective_retry,
    dag=dag,
)
```

---

## Sensor Patterns

### ExternalTaskSensor

```python
from airflow.sensors.external_task import ExternalTaskSensor

# Wait for specific task in external DAG
wait_for_task = ExternalTaskSensor(
    task_id='wait_for_aggregation',
    external_dag_id='aggregation_dag',
    external_task_id='aggregate_all',
    execution_date_fn=lambda dt: dt,
    timeout=3600,
    poke_interval=60,
    mode='reschedule',
    dag=downstream_dag,
)
```

### HttpSensor

```python
from airflow.sensors.http_sensor import HttpSensor

check_api = HttpSensor(
    task_id='check_api_available',
    http_conn_id='api_connection',
    endpoint='health',
    request_params={},
    response_check=lambda response: response.status_code == 200,
    poke_interval=60,
    timeout=300,
    dag=dag,
)
```

### SqlSensor

```python
from airflow.sensors.sql import SqlSensor

check_data_ready = SqlSensor(
    task_id='check_data_ready',
    conn_id='datawarehouse',
    sql="SELECT COUNT(*) FROM processed WHERE date = '{{ ds }}' AND status = 'ready'",
    pass_value=True,
    poke_interval=300,
    timeout=3600,
    dag=dag,
)
```

### GCSObjectExistenceSensor

```python
from airflow.providers.google.cloud.sensors.gcs import GCSObjectExistenceSensor

wait_for_file = GCSObjectExistenceSensor(
    task_id='wait_for_input_file',
    bucket='data-bucket',
    object='input/{{ ds }}/data.csv',
    google_cloud_conn_id='google_cloud_default',
    timeout=7200,
    poke_interval=300,
    dag=dag,
)
```

### TimeSensor and BranchDayOfWeekSensor

```python
from airflow.sensors.time_sensor import TimeSensor
from airflow.operators.branch import BranchDateTimeSensor

# Wait until specific time
wait_until_5am = TimeSensor(
    task_id='wait_until_5am',
    target_time=time(5, 0),
    dag=dag,
)

# Branch based on day
branch_day = BranchDateTimeSensor(
    task_id='branch_on_weekday',
    follow_task_ids_if_true='process_weekday',
    follow_task_ids_if_false='process_weekend',
    target_upper=time(18, 0),  # After 6pm
    target_lower=time(6, 0),   # Before 6am
    dag=dag,
)
```

---

## See Also

- [Airflow SubDAGs](https://airflow.apache.org/docs/apache-airflow/stable/concepts.html#subdags)
- [TriggerDagRunOperator](https://airflow.apache.org/docs/apache-airflow/stable/_api/airflow/operators/dagrun_operator/index.html)
- [ExternalTaskSensor](https://airflow.apache.org/docs/apache-airflow/stable/_api/airflow/sensors/external_task/index.html)
- [Dynamic Tasks](https://airflow.apache.org/docs/apache-airflow/stable/concepts/dynamic-task-mapping.html)
- [SLA Monitoring](https://airflow.apache.org/docs/apache-airflow/stable/concepts/sla.html)
