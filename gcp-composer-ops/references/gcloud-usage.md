# gcloud — Google Cloud Composer CLI

## Install and config

- Install: see [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
- **CRITICAL Credentials:** Set `GOOGLE_APPLICATION_CREDENTIALS` or run `gcloud auth login`

## Conventions (agent execution)

- Always use `--format=json` for machine-parseable output
- Use `jq` for field extraction from JSON output
- Long-running operations return immediately; poll via describe

## CLI vs API coverage gap

| Operation (REST API) | Available via `gcloud`? | Notes |
|------------------------|-------------------------|-------|
| Create Environment | yes | `gcloud composer environments create` |
| Describe Environment | yes | `gcloud composer environments describe` |
| Update Environment | yes | `gcloud composer environments update` |
| Delete Environment | yes | `gcloud composer environments delete` |
| List Environments | yes | `gcloud composer environments list` |
| List Operations | yes | `gcloud composer operations list` |
| Get Operation | yes | `gcloud composer operations describe` |
| Run Airflow CLI | yes | `gcloud composer environments run` |
| Import DAGs | yes | `gcloud composer environments storage dags import` |
| Export DAGs | yes | `gcloud composer environments storage dags export` |

## Command map

| Goal | Example `gcloud` invocation | Notes |
|------|------------------------------|-------|
| Create Environment | `gcloud composer environments create my-env --project={{env.CLOUDSDK_CORE_PROJECT}} --region={{user.region}} --environment-size=small --airflow-version=2.9.3 --format=json` | Long-running |
| Describe Environment | `gcloud composer environments describe my-env --project={{env.CLOUDSDK_CORE_PROJECT}} --region={{user.region}} --format=json` | Returns state |
| Update Environment | `gcloud composer environments update my-env --project={{env.CLOUDSDK_CORE_PROJECT}} --region={{user.region}} --environment-size=medium --format=json` | Long-running |
| Delete Environment | `gcloud composer environments delete my-env --project={{env.CLOUDSDK_CORE_PROJECT}} --region={{user.region}} --quiet` | With confirmation |
| List Environments | `gcloud composer environments list --project={{env.CLOUDSDK_CORE_PROJECT}} --format=json` | All environments |
| Run Airflow CLI | `gcloud composer environments run my-env --project={{env.CLOUDSDK_CORE_PROJECT}} --region={{user.region}} dags list` | Execute airflow command |
| Import DAGs | `gcloud composer environments storage dags import --environment=my-env --project={{env.CLOUDSDK_CORE_PROJECT}} --region={{user.region}} --source=gs://bucket/dags/` | From GCS |
