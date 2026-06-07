# Well-Architected Assessment — Cloud Run

Mapped to the [Google Cloud Architecture Framework](https://cloud.google.com/architecture/framework) five pillars.

## 2.1 Security

| Recommendation | Implementation | Priority |
|----------------|----------------|----------|
| **IAM Authentication** | Deploy with `--no-allow-unauthenticated`; use `roles/run.invoker` | P0 |
| **Secret Management** | Mount secrets via `--set-secrets` from Secret Manager | P0 |
| **VPC Isolation** | Attach VPC connector (`--vpc-connector`) for private network access | P0 |
| **Ingress Restriction** | Use `--ingress=internal` or `internal-and-cloud-load-balancing` | P0 |
| **Service Identity** | Use dedicated SA per service (`--service-account`) | P1 |
| **CMEK Encryption** | Configure customer-managed encryption keys for data at rest | P1 |
| **Container Image Scanning** | Enable Artifact Registry vulnerability scanning | P1 |
| **Cloud Audit Logs** | All Cloud Run API calls logged to Cloud Audit Logs | P2 |

## 2.2 Stability

| Recommendation | Implementation | Priority |
|----------------|----------------|----------|
| **Multi-Region** | Deploy identical services in multiple regions; use Cloud Run multi-region (global) | P0 |
| **Traffic Splitting** | Use canary deployments: route small % to new revision, increase gradually | P0 |
| **Revision Rollback** | Shift traffic back to previous stable revision | P0 |
| **Min Instances** | Set `min-instances > 0` for critical services to avoid cold-start failures | P1 |
| **Health Checks** | Ensure container responds on configured port within timeout | P1 |
| **Request Timeout Tuning** | Set appropriate `--timeout` (default 300s, max 3600s) | P1 |
| **Dead Letter Queues** | For async processing, handle failures with retry + DLQ patterns | P2 |
| **Circuit Breakers** | Implement client-side retries with backoff for downstream dependencies | P2 |

### Emergency Recovery Runbook

| Scenario | Recovery Action |
|----------|-----------------|
| New revision breaking | `gcloud run services update-traffic NAME --to-revisions=PREV_REV=100` |
| Service unresponsive | Check `.status.conditions`; review logs; redeploy previous image |
| Traffic spike causing errors | Increase `max-instances` or `concurrency` |
| Secret rotation failure | Update secret version; redeploy with new `--set-secrets` |

## 2.3 Cost

| Recommendation | Implementation | Savings Impact |
|----------------|----------------|----------------|
| **Scale to Zero** | `min-instances=0` for non-critical / low-traffic services | High |
| **Right-Size CPU/Memory** | Match allocation to actual usage (monitor metrics first) | Medium |
| **Concurrency Tuning** | Higher concurrency = fewer instances = lower cost | Medium |
| **Committed Use** | Use 1-year or 3-year committed use discounts for steady workloads | High |
| **Execution Environment** | Use gen2 for better price/performance on new services | Low |
| **Container Optimization** | Use slim base images, multi-stage builds | Low |

### Cost Estimation

> **TE-1**: Query actual usage instead of hardcoding estimates:
> ```bash
> gcloud monitoring metrics read "run.googleapis.com/billing_billable_instance_time" \
>   --aggregation="alignmentPeriod=86400s,crossSeriesReducer=REDUCE_SUM" \
>   --interval="P30D" --format=json
> ```

| Component | Pricing Model | Notes |
|-----------|---------------|-------|
| Requests | $0.40 per 1M requests | First 2M/month free |
| Compute | $0.000024 per vCPU-second | Billed per 100ms increment |
| Memory | $0.0000025 per GiB-second | Billed per 100ms increment |
| Networking | Standard GCP egress rates | Ingress free |
| Idle scaling | Billed while min-instances running | Set to 0 to avoid |

## 2.4 Efficiency

| Recommendation | Implementation | Impact |
|----------------|----------------|--------|
| **CI/CD Integration** | Cloud Build triggers on container registry push | High |
| **Container Image Optimization** | Multi-stage builds, distroless images, layer caching | Medium |
| **Concurrency Tuning** | Match concurrency to workload type (CPU-bound: low, I/O-bound: high) | High |
| **Cold Start Mitigation** | `min-instances > 0`, smaller images, faster startup code | Medium |
| **Service Mesh** | Use Cloud Run with Anthos Service Mesh for advanced routing | Low |

## 2.5 Performance

| Recommendation | Implementation | Impact |
|----------------|----------------|--------|
| **Cold Start Mitigation** | `min-instances > 0`, CPU always-on (`--cpu-throttling=false`) | High |
| **CPU Allocation** | Higher CPU for compute-intensive workloads | Medium |
| **Memory Allocation** | Sufficient memory to avoid OOM kills | Medium |
| **Connection Pooling** | Reuse HTTP/gRPC connections to backend services | High |
| **Response Caching** | Use Cloud CDN or in-memory caching for repeated responses | High |
| **Geographic Proximity** | Deploy in region closest to users | Medium |

### Performance Baseline Metrics

| Metric | Good | Warning | Critical |
|--------|------|---------|----------|
| P50 Latency | < 100ms | 100-500ms | > 500ms |
| P99 Latency | < 500ms | 500ms-2s | > 2s |
| Cold Start Time | < 200ms | 200ms-2s | > 2s |
| Error Rate | < 0.1% | 0.1-1% | > 1% |
| CPU Utilization | 40-70% | 70-85% | > 85% |
| Memory Utilization | 40-70% | 70-85% | > 85% |
