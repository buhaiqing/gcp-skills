# Monitoring — Google Cloud Composer

## Key Metrics

| Metric | Description | Threshold |
|--------|-------------|-----------|
| `composer.googleapis.com/environment/worker_count` | Number of active workers | — |
| `composer.googleapis.com/environment/dag_count` | Number of DAGs | — |
| `composer.googleapis.com/environment/running_task_count` | Running tasks | — |
| `composer.googleapis.com/environment/pending_task_count` | Pending tasks | > 100 (alert) |
| `composer.googleapis.com/environment/failed_task_count` | Failed tasks | > 0 (alert) |
| `composer.googleapis.com/environment/cpu_usage` | CPU utilization | > 80% (alert) |
| `composer.googleapis.com/environment/memory_usage` | Memory utilization | > 80% (alert) |
| `composer.googleapis.com/environment/disk_usage` | Disk utilization | > 80% (alert) |

## Cloud Monitoring Setup

### Dashboard Metrics

```yaml
# Environment health overview
- type: composer.googleapis.com/environment/worker_count
  view: FULL
- type: composer.googleapis.com/environment/dag_count
  view: FULL
- type: composer.googleapis.com/environment/running_task_count
  view: FULL
```

### Alert Policies

```yaml
# Alert on high failure rate
alertPolicy:
  displayName: "High Task Failure Rate"
  conditions:
    - displayName: "Failed tasks > 5%"
      conditionThreshold:
        filter: "resource.type=\"composer_environment\""
        comparison: COMPARISON_GT
        thresholdValue: 0.05
        duration: "300s"
```

## Airflow Metrics

| Metric | Description |
|--------|-------------|
| `airflow_dag_run_duration` | DAG execution time |
| `airflow_task_duration` | Task execution time |
| `airflow_task_failure_rate` | Task failure percentage |
| `airflow_dag_schedule_delay` | DAG scheduling delay |

## Logging

Enable verbose logging for debugging:

```bash
gcloud composer environments update {{user.environment_name}} \
  --project="{{env.CLOUDSDK_CORE_PROJECT}}" \
  --region={{user.region}} \
  --airflow-configs=core-evaluate_python_native_operators=true
```

## Cost & Performance Metrics

| Metric | Description |
|--------|-------------|
| Worker utilization | CPU/Memory usage |
| DAG parse time | Time to load DAGs |
| Scheduler heartbeat | Scheduler health |
| Webserver response time | UI responsiveness |
