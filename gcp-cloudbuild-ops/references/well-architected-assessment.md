---
name: cloudbuild-well-architected-assessment
description: Google Cloud Architecture Framework assessment for Cloud Build operations

<!---
load_condition: "[架构评审时加载]"
token_cost_estimate: "~700 tokens"
dependencies: []
--->
---

# Well-Architected Assessment — Cloud Build

## Pillar Summary

| Pillar | Controls | Evidence |
|--------|----------|----------|
| Security | Least-privilege build/trigger SAs, secret redaction, explicit delete confirmation, private pool network review | IAM checks, sanitized traces, trigger/pool config |
| Stability | Build state validation, retry/cancel rules, trigger source validation, worker pool capacity checks | Build status/timing, trigger describe, pool state |
| Cost | Timeout/machine/disk review, private pool sizing, artifact/log retention awareness | Build config, workerConfig, logs/artifacts output |
| Efficiency | Idempotent trigger/pool reconciliation, centralized substitutions, reusable configs | Diff of current vs desired resource |
| Performance | Step parallelism, caching, regional pools, queue/runtime monitoring | Build timing, queue delay, worker pool region |

## Security

| Check | Method | Target |
|-------|--------|--------|
| Build SA least privilege | Describe build/trigger service account | No broad editor unless justified |
| Secret handling | Inspect substitutions/log snippets | No plaintext secrets in command/log output |
| Trigger mutation safety | Show source/branch/config/SA and run GCL | Approved CI/CD impact |
| Worker pool network | Review networkConfig | Intended VPC/private egress only |
| Auditability | Preserve sanitized command/result | Trace supports review |

## Stability

- Validate build terminal state and failure info before declaring success.
- Use retries only for transient failures and only when build side effects are safe.
- Treat queued/expired builds as capacity or worker pool symptoms.
- For trigger updates, confirm branch/tag regex and source connection before relying on automation.

## Cost

- Review build timeout, machine type, disk size, and private pool worker config.
- Avoid unnecessary retry loops; failed retries can consume build minutes.
- Recommend artifact/log retention cleanup via appropriate product skills when storage cost is root cause.

## Efficiency

- Prefer config files under version control.
- Reconcile existing triggers/pools instead of create/delete churn.
- Centralize substitutions and avoid duplicated build logic.
- Use `--format=json` and centralized JSON paths for reliable parsing.

## Performance

- Compare queue duration (`startTime-createTime`) and runtime (`finishTime-startTime`).
- Use regional/private pools near dependencies when network latency matters.
- Recommend layer/cache optimization for repeated Docker builds.
- Split independent steps with `waitFor` where build config supports it.
