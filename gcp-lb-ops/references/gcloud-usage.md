# gcloud — Cloud Load Balancing CLI

## Install and config
- Install: see [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
- **CRITICAL Credentials:** Set `GOOGLE_APPLICATION_CREDENTIALS` or run `gcloud auth login`

## Conventions (agent execution)
- Always use `--format=json` for machine-parseable output
- Use `jq` for field extraction from JSON output
- All LB create/modify/delete operations are synchronous — no long-running operation polling needed (except SSL certificate provisioning)
- Use `--global` flag for global resources (external HTTP(S) LB); use `--region=` for regional resources

## CLI vs API Coverage Gap

| Operation (REST API) | Available via `gcloud`? | Notes |
|----------------------|-------------------------|-------|
| Create forwarding rule | ✅ Yes | `gcloud compute forwarding-rules create` |
| Describe forwarding rule | ✅ Yes | `gcloud compute forwarding-rules describe` |
| List forwarding rules | ✅ Yes | `gcloud compute forwarding-rules list` |
| Delete forwarding rule | ✅ Yes | `gcloud compute forwarding-rules delete` |
| Create backend service | ✅ Yes | `gcloud compute backend-services create` |
| Add backend to service | ✅ Yes | `gcloud compute backend-services add-backend` |
| Remove backend from service | ✅ Yes | `gcloud compute backend-services remove-backend` |
| Update backend service | ✅ Yes | `gcloud compute backend-services update` |
| Describe backend service | ✅ Yes | `gcloud compute backend-services describe` |
| List backend services | ✅ Yes | `gcloud compute backend-services list` |
| Delete backend service | ✅ Yes | `gcloud compute backend-services delete` |
| Get backend health | ✅ Yes | `gcloud compute backend-services get-health` |
| Create URL map | ✅ Yes | `gcloud compute url-maps create` |
| Update URL map | ✅ Yes | `gcloud compute url-maps update / add-path-matcher / remove-path-matcher` |
| Describe URL map | ✅ Yes | `gcloud compute url-maps describe` |
| List URL maps | ✅ Yes | `gcloud compute url-maps list` |
| Delete URL map | ✅ Yes | `gcloud compute url-maps delete` |
| Create health check | ✅ Yes | `gcloud compute health-checks create {http|https|tcp|ssl|grpc}` |
| Describe health check | ✅ Yes | `gcloud compute health-checks describe` |
| List health checks | ✅ Yes | `gcloud compute health-checks list` |
| Delete health check | ✅ Yes | `gcloud compute health-checks delete` |
| Create target proxy | ✅ Yes | `gcloud compute target-{http|https|tcp|ssl|grpc}-proxies create` |
| Describe target proxy | ✅ Yes | `gcloud compute target-{http|https|tcp|ssl|grpc}-proxies describe` |
| Create SSL certificate | ✅ Yes | `gcloud compute ssl-certificates create` (managed + self-managed) |
| Describe SSL certificate | ✅ Yes | `gcloud compute ssl-certificates describe` |
| Create NEG | ✅ Yes | `gcloud compute network-endpoint-groups create` |
| Add NEG endpoints | ✅ Yes | `gcloud compute network-endpoint-groups update` |
| Describe NEG | ✅ Yes | `gcloud compute network-endpoint-groups describe` |
| List NEGs | ✅ Yes | `gcloud compute network-endpoint-groups list` |
| Delete NEG | ✅ Yes | `gcloud compute network-endpoint-groups delete` |
| Update backend bucket | No full support | Use `gcloud compute backend-buckets` (limited) |
| Update SSL policy | ✅ Yes | `gcloud compute ssl-policies create/update/delete` |

**Conclusion**: `gcloud` CLI covers 95%+ of Load Balancing operations. SDK fallback (Python/Go) is only needed for edge cases or scripting complex multi-step workflows.

## Command Map

### Forwarding Rules

| Goal | Example `gcloud` invocation | Notes |
|------|---------------------------|-------|
| Create (global ext. HTTPS) | `gcloud compute forwarding-rules create my-rule --load-balancing-scheme=EXTERNAL_MANAGED --target-https-proxy=my-proxy --ports=443 --global` | JSON output |
| Create (regional int. TCP) | `gcloud compute forwarding-rules create my-rule --load-balancing-scheme=INTERNAL_MANAGED --backend-service=my-bs --region=us-central1 --ports=ALL` | JSON output |
| Describe | `gcloud compute forwarding-rules describe my-rule --global` | JSON output |
| List | `gcloud compute forwarding-rules list --global` | JSON output |
| Delete | `gcloud compute forwarding-rules delete my-rule --global` | Confirm interactively |

### Backend Services

| Goal | Example `gcloud` invocation | Notes |
|------|---------------------------|-------|
| Create (global, HTTP) | `gcloud compute backend-services create my-bs --protocol=HTTP --health-checks=my-hc --global` | JSON output |
| Add backend | `gcloud compute backend-services add-backend my-bs --instance-group=my-mig --instance-group-zone=us-central1-a --global` | JSON output |
| Get health | `gcloud compute backend-services get-health my-bs --global` | JSON output |
| Update | `gcloud compute backend-services update my-bs --timeout=60s --global` | JSON output |
| Delete | `gcloud compute backend-services delete my-bs --global` | Confirm |

### URL Maps

| Goal | Example `gcloud` invocation | Notes |
|------|---------------------------|-------|
| Create | `gcloud compute url-maps create my-map --default-service=my-bs --global` | JSON output |
| Add path matcher | `gcloud compute url-maps add-path-matcher my-map --default-service=my-bs --path-matcher-name=api --path-rules="/api=api-bs" --global` | JSON output |
| Add host rule | `gcloud compute url-maps add-host-rule my-map --hosts="api.example.com" --path-matcher-name=api --global` | JSON output |
| Describe | `gcloud compute url-maps describe my-map --global` | JSON output |
| List | `gcloud compute url-maps list --global` | JSON output |
| Validate | `gcloud compute url-maps validate --source=<file> --global` | Validate inline YAML/JSON |

### Health Checks

| Goal | Example `gcloud` invocation | Notes |
|------|---------------------------|-------|
| Create HTTP | `gcloud compute health-checks create http my-hc --port=80 --request-path=/healthz` | JSON output |
| Create HTTPS | `gcloud compute health-checks create https my-hc --port=443 --request-path=/healthz` | JSON output |
| Create TCP | `gcloud compute health-checks create tcp my-hc --port=3306` | JSON output |
| Create gRPC | `gcloud compute health-checks create grpc my-hc --port=8080` | JSON output |
| Describe | `gcloud compute health-checks describe my-hc` | JSON output |
| List | `gcloud compute health-checks list` | JSON output |

### SSL Certificates

| Goal | Example `gcloud` invocation | Notes |
|------|---------------------------|-------|
| Create (managed) | `gcloud compute ssl-certificates create my-cert --domains="example.com" --global` | 5-10 min provisioning |
| Create (self-managed) | `gcloud compute ssl-certificates create my-cert --certificate=cert.pem --private-key=key.pem --global` | Instant |
| Describe | `gcloud compute ssl-certificates describe my-cert --global` | Check managed.status |
| List | `gcloud compute ssl-certificates list --global` | JSON output |
| Delete | `gcloud compute ssl-certificates delete my-cert --global` | Confirm |

### NEGs

| Goal | Example `gcloud` invocation | Notes |
|------|---------------------------|-------|
| Create (zonal, VM) | `gcloud compute network-endpoint-groups create my-neg --network-endpoint-type=GCE_VM_IP_PORT --zone=us-central1-a --network=default --default-port=80` | JSON output |
| Create (serverless) | `gcloud compute network-endpoint-groups create my-neg --network-endpoint-type=SERVERLESS --region=us-central1 --cloud-run-service=my-service` | JSON output |
| Describe | `gcloud compute network-endpoint-groups describe my-neg --zone=us-central1-a` | JSON output |
| List | `gcloud compute network-endpoint-groups list --zone=us-central1-a` | JSON output |
| List endpoints | `gcloud compute network-endpoint-groups list-network-endpoints my-neg --zone=us-central1-a` | JSON output |