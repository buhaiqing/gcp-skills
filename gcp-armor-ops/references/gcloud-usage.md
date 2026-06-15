# gcloud — Google Cloud Armor CLI

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
| Create Security Policy | yes | `gcloud compute security-policies create` |
| Describe Security Policy | yes | `gcloud compute security-policies describe` |
| Update Security Policy | yes | `gcloud compute security-policies update` |
| Delete Security Policy | yes | `gcloud compute security-policies delete` |
| List Security Policies | yes | `gcloud compute security-policies list` |
| Add Rule | yes | `gcloud compute security-policies rules create` |
| Update Rule | yes | `gcloud compute security-policies rules update` |
| Remove Rule | yes | `gcloud compute security-policies rules delete` |
| List Rules | yes | `gcloud compute security-policies rules list` |

## Command map

| Goal | Example `gcloud` invocation | Notes |
|------|------------------------------|-------|
| Create Policy | `gcloud compute security-policies create my-policy --project={{env.CLOUDSDK_CORE_PROJECT}} --format=json` | JSON output |
| Describe Policy | `gcloud compute security-policies describe my-policy --project={{env.CLOUDSDK_CORE_PROJECT}} --format=json` | Returns fingerprint |
| Add Allow Rule | `gcloud compute security-policies rules create 1000 --security-policy=my-policy --expression="true" --action="allow" --format=json` | Priority-based |
| Add Deny Rule | `gcloud compute security-policies rules create 2000 --security-policy=my-policy --expression="evaluatePreconfiguredWaf('xss-v33-stable')" --action="deny-403" --format=json` | Pre-configured WAF |
| Add Rate Limit | `gcloud compute security-policies rules create 3000 --security-policy=my-policy --expression="true" --action="throttle" --rate-limit-threshold-count=1000 --rate-limit-threshold-interval-sec=60 --format=json` | Throttle action |
| List Rules | `gcloud compute security-policies rules list my-policy --project={{env.CLOUDSDK_CORE_PROJECT}} --format=json` | All rules |
| Delete Policy | `gcloud compute security-policies delete my-policy --project={{env.CLOUDSDK_CORE_PROJECT}} --quiet` | With confirmation |
