---
name: cloudbuild-troubleshooting
description: Cloud Build diagnostics, error taxonomy, and recovery actions

<!---
load_condition: "[构建失败或报错时加载]"
token_cost_estimate: "~1400 tokens"
dependencies: []
--->
---

# Troubleshooting — Cloud Build

## Diagnostic Flow

1. Describe build/trigger/worker pool with `--format=json`.
2. Capture sanitized status, failure info, timing, service account, log URL, source, images/artifacts, and worker pool.
3. Read logs with redaction; identify first failing step and exact error line.
4. Classify using the error taxonomy below.
5. Recommend the smallest safe fix. Do not mutate IAM/triggers/worker pools without approval.

## Error Taxonomy

| Code / Symptom | Likely Cause | Recovery |
|----------------|--------------|----------|
| `PERMISSION_DENIED: cloudbuild.builds.create` | Operator lacks build editor/builder role | HALT — grant least-privilege Cloud Build role |
| Build step `denied: Permission ... artifactregistry` | Build service account lacks repo writer/reader | Add target repo role to build SA; retry only if idempotent |
| `failed to fetch source` / repo not found | Trigger source connection, branch, or repo mapping invalid | Verify trigger source, Git app/OAuth connection, branch regex |
| `invalid build: invalid image name` | Bad image/artifact name or substitution expansion | Fix config/substitution; validate with dry parsing |
| `generic::invalid_argument` for substitutions | Missing required `_VAR` or invalid key format | Provide `_UPPERCASE` substitutions; avoid secret literals |
| `TIMEOUT` | Build exceeded configured timeout or hung step | Increase timeout or fix long-running step; inspect logs |
| `EXPIRED` / queue TTL exceeded | No capacity, quota, or private pool unavailable | Check worker pool state/quota; retry after capacity restored |
| `RESOURCE_EXHAUSTED` | Build quota/concurrency/CPU/disk limit reached | Backoff, reduce parallelism, request quota |
| `UNAVAILABLE` / transient internal error | Cloud Build or dependency transient issue | Retry with exponential backoff if build is idempotent |
| `NOT_FOUND: build/trigger/workerPool` | Wrong project/region/ID or deleted resource | Verify project, region, ID; treat delete target as success only after confirmed |
| `ALREADY_EXISTS` trigger/worker pool | Duplicate create without idempotency check | Describe existing resource and update if desired state differs |
| `FAILED_PRECONDITION: worker pool` | Pool updating/deleting, bad network, or unsupported region | Wait for stable state; verify region/network config |
| Logs unavailable / `logUrl` inaccessible | Missing logging/storage permission or retention/log bucket issue | Check `logsBucket`, Cloud Logging viewer, retention, bucket IAM |
| Docker build cannot pull base image | Network, auth, Artifact Registry/Docker Hub rate limit | Configure auth/cache/private pool egress; retry carefully |
| `secretEnv`/Secret Manager access denied | Build SA lacks secret accessor or version missing | Grant secret accessor for exact secret/version; do not print secret |

## Build Failure Diagnosis Commands

```bash
gcloud builds describe "{{user.build_id}}" --project="{{user.project}}" --format=json
gcloud builds log "{{user.build_id}}" --project="{{user.project}}"
```

Sanitize logs before reporting; prefer short evidence snippets over full logs:

```bash
python3 - <<'PY'
import re, sys
text = sys.stdin.read()
patterns = [
    (r'Authorization:\s*Bearer\s+[A-Za-z0-9._~+/-]+=*', 'Authorization: Bearer ****'),
    (r'(?i)(access_token|refresh_token|id_token)\s*[:=]\s*["\']?[^"\'\s,}]+', r'\1=****'),
    (r'(?i)(password|passwd|pwd|secret|token|api[_-]?key|private[_-]?key)\s*[:=]\s*["\'][^"\']+["\']', r'\1="****"'),
    (r'(?i)(password|passwd|pwd|secret|token|api[_-]?key|private[_-]?key)\s*[:=]\s*\S+', r'\1=****'),
    (r'-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----', '-----BEGIN PRIVATE KEY-----****-----END PRIVATE KEY-----'),
]
for pat, repl in patterns:
    text = re.sub(pat, repl, text, flags=re.S)
sys.stdout.write(text)
PY
```

## Trigger Diagnosis

```bash
gcloud builds triggers describe "{{user.trigger_id}}" \
  --project="{{user.project}}" \
  --region="{{user.region}}" \
  --format=json
gcloud builds triggers run "{{user.trigger_id}}" \
  --branch="{{user.branch_name}}" \
  --project="{{user.project}}" \
  --region="{{user.region}}" \
  --format=json
```

Use the same project, region, and trigger ID for pre-update/pre-delete describe and post-mutation validation. Regional repository/connection triggers require `--region`; global/classic triggers may omit it after local help verification. Check source block, branch/tag regex, substitutions, service account, included config path, and approval settings if present.

## Worker Pool Diagnosis

```bash
gcloud builds worker-pools describe "{{user.worker_pool}}" \
  --region="{{user.region}}" \
  --project="{{user.project}}" \
  --format=json
```

Inspect state, machine type, disk, network, peered project/VPC, private egress, DNS, and firewall. If builds are stuck `QUEUED`, compare pool state with build `createTime/startTime`.

## Recovery Rules

| Situation | Rule |
|-----------|------|
| Non-idempotent build step may deploy/delete | Do not retry without user approval |
| Permission fix needed | Explain exact principal + role + resource; delegate broad IAM changes |
| Trigger delete/update needed | Require exact trigger ID and GCL review |
| Worker pool delete/update needed | Require exact pool ID, region, and GCL review |
| Transient platform failure | Retry with backoff only after confirming build idempotency |
