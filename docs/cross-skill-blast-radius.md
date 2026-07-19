# Cross-Skill Blast Radius — 跨域关联排障地图

> **Purpose:** 在 27 个 `gcp-*-ops` skill 的孤立 `aiops-*.md` 之上，提供跨域依赖 / blast-radius / 降级顺序的全局视图。当单点变更或故障沿上游→下游扩散时，本文件给出关联排障的入口与告警锚点。
> **Version:** 1.0.0
> **Last Updated:** 2026-07-19
> **Scope:** 仅基于已核查的 10 个 aiops 文档锚点（vpc / iam / billing / cloudbuild / gcs / bigquery / gke / cloudsql / pubsub / securitycenter）。未列锚点的产品（LB / GCE / CDN / DNS）暂无独立 aiops 文档，其关联排障回退到最近的锚点 skill，详见各链路「回退」标注。

---

## 使用约定

- **Blast radius（影响边界）**：上游资源变更后，下游哪些产品会同步出现异常。
- **关联告警**：用 `gcloud logging` / `gcloud monitoring` 查询，可引用各 skill 的 aiops 文档做根因定位。
- **降级顺序**：先保认证与数据平面可用性，后弃可延迟的分析/成本类能力。
- 所有链路均映射到 `docs/error-taxonomy.md` 的根因维度（如 `PERMISSION_DENIED` / `UNAVAILABLE` / `FAILED_PRECONDITION`）。

---

## 链路 1：VPC → GKE / GCE（网络层）

### 拓扑（上游 → 下游）

```
VPC (防火墙规则 / 子网 / Cloud NAT / 路由)
   ├──► GKE 集群 (节点池网络、Pod CIDR、NEG 后端)
   └──► GCE 实例 (网卡子网、防火墙 ingress/egress、外部 IP)
```

> **回退说明**：LB / GCE 暂无独立 aiops 文档。GCE 实例的网络异常排障回退到 `gcp-vpc-ops` 的子网与防火墙章节；GKE 有独立锚点。

### Blast radius

| 上游变更 | 影响边界 | 典型 error-taxonomy 维度 |
|----------|----------|--------------------------|
| 防火墙规则误删 / deny 收紧 | GKE Pod 出向失败、GCE SSH/健康检查中断 | `UNAVAILABLE` (Network) |
| 子网 CIDR 耗尽 / 扩容冲突 | 新 GKE 节点 / GCE 实例无法分配 IP | `FAILED_PRECONDITION` (Config) |
| Cloud NAT 网关删除 | 无外部 IP 的 GCE/GKE 出向流量全断 | `UNAVAILABLE` (Network) |
| 路由表变更 | 跨子网 / 跨 VPC 连通性中断 | `UNAVAILABLE` (Network) |

### 关联告警规则示例

```bash
# 1. VPC 连接失败率突增（回源 aiops-network-anomaly.md §Log-Based Anomaly Detection）
gcloud logging read \
  "resource.type=gce_subnetwork AND jsonPayload.bytes_sent > 0 AND jsonPayload.reporter=dropped" \
  --project="$CLOUDSDK_CORE_PROJECT" --limit=50 --format=json

# 2. GKE 节点 NotReady 与网络策略关联（回源 aiops-gke-anomaly.md §Node Pool Anomaly Detection）
gcloud logging read \
  "resource.type=gke_cluster AND jsonPayload.reason=FailedScheduling" \
  --project="$CLOUDSDK_CORE_PROJECT" --freshness=1h --format=json

# 3. 防火墙变更审计（回源 aiops-iam-anomaly.md §Role Binding Drift 同构的 audit 思路）
gcloud logging read \
  "protoPayload.methodName=\"v1.compute.firewalls.patch\" OR protoPayload.methodName=\"v1.compute.firewalls.delete\"" \
  --project="$CLOUDSDK_CORE_PROJECT" --freshness=24h --format=json
```

### 降级顺序建议

1. **先保**：恢复防火墙 allow 规则与 Cloud NAT（恢复出向连通性，保住数据平面）。
2. **次保**：扩容子网 / 修复路由（恢复新实例调度能力）。
3. **后弃**：非关键的 VPC Flow Logs 采样率下调（省成本，不阻断业务）。

### 锚点链接

- [gcp-vpc-ops AIOps](gcp-vpc-ops/references/advanced/aiops-network-anomaly.md)
- [gcp-gke-ops AIOps](gcp-gke-ops/references/advanced/aiops-gke-anomaly.md)

---

## 链路 2：GCS → DNS → BigQuery（存储 / 数据回源层）

### 拓扑（上游 → 下游）

```
GCS bucket (对象访问 / 回源源站)
   ├──► DNS 解析 (bucket 自定义域名、CDN 回源 Host)
   └──► BigQuery (外部表 / 加载作业读取 GCS 对象)
```

> **回退说明**：CDN / DNS 暂无独立 aiops 文档。DNS 解析异常排障回退到 GCS 访问日志（确认请求是否到达 bucket）与 VPC（确认 egress 连通性）；BigQuery 有独立锚点。

### Blast radius

| 上游变更 | 影响边界 | 典型 error-taxonomy 维度 |
|----------|----------|--------------------------|
| GCS IAM / ACL 收紧 | BigQuery 外部表加载失败、CDN 回源 403 | `PERMISSION_DENIED` (Permission) |
| GCS bucket 删除 / 重命名 | BigQuery load job `NOT_FOUND`、回源 404 | `NOT_FOUND` (Resource State) |
| DNS 记录变更 / TTL 生效 | 自定义域名访问短暂中断、回源 Host 解析失败 | `UNAVAILABLE` (Network) |
| GCS 生命周期策略误删 | 热数据被转冷，读取延迟上升 | `FAILED_PRECONDITION` (Config) |

### 关联告警规则示例

```bash
# 1. GCS 未授权访问 / 403 突增（回源 aiops-storage-anomaly.md §Access Pattern Anomalies）
gcloud logging read \
  "resource.type=gcs_bucket AND jsonPayload.protocolStatusCode=403" \
  --project="$CLOUDSDK_CORE_PROJECT" --freshness=1h --format=json

# 2. BigQuery 加载作业因 GCS 对象缺失失败（回源 aiops-bigquery-anomaly.md §Job Failure Pattern Detection）
gcloud logging read \
  "resource.type=bigquery_resource AND protoPayload.methodName=jobservice.jobinsert AND jsonPayload.error.code=NOT_FOUND" \
  --project="$CLOUDSDK_CORE_PROJECT" --freshness=6h --format=json

# 3. DNS 解析失败（回退 VPC egress 连通性核查，无独立 aiops 锚点）
gcloud dns record-sets list --zone="$ZONE" --project="$CLOUDSDK_CORE_PROJECT"
```

### 降级顺序建议

1. **先保**：恢复 GCS IAM binding（保住 BigQuery 加载与回源读取，数据平面优先）。
2. **次保**：回滚 DNS 记录变更（恢复自定义域名访问）。
3. **后弃**：暂停 BigQuery 外部表增量分析作业（延迟可接受，不阻断核心读写）。

### 锚点链接

- [gcp-gcs-ops AIOps](gcp-gcs-ops/references/advanced/aiops-storage-anomaly.md)
- [gcp-bigquery-ops AIOps](gcp-bigquery-ops/references/advanced/aiops-bigquery-anomaly.md)
- [gcp-vpc-ops AIOps](gcp-vpc-ops/references/advanced/aiops-network-anomaly.md)（DNS 回退）

---

## 链路 3：IAM → 多产品（认证 / 授权层）

### 拓扑（上游 → 下游）

```
IAM (角色绑定 / Service Account / Workload Identity)
   ├──► Cloud SQL (SA 认证、IAM DB 认证)
   ├──► GCS (bucket IAM binding)
   ├──► BigQuery (dataset / job 权限)
   └──► 其余依赖该身份的 gcp-*-ops 服务
```

> 依据 `docs/error-taxonomy.md` §2 Permission / §8 Authentication：IAM 角色或 SA 变更会沿身份依赖波及所有消费该 principal 的服务。

### Blast radius

| 上游变更 | 影响边界 | 典型 error-taxonomy 维度 |
|----------|----------|--------------------------|
| SA 禁用 / 密钥删除 | 依赖该 SA 的服务全部 `AUTH_FAILED` | `AUTH_FAILED` (Auth) |
| 角色绑定误删 | Cloud SQL / GCS / BigQuery 等 `PERMISSION_DENIED` | `PERMISSION_DENIED` (Permission) |
| 条件绑定 / 组织策略收紧 | 跨项目访问被拒、Workload Identity 联邦失败 | `PERMISSION_DENIED` (Permission) |
| IAM 策略 etag 冲突 | `setIamPolicy` 并发失败 `ABORTED` | `ABORTED` (Dependency) |

### 关联告警规则示例

```bash
# 1. IAM 权限拒绝跨产品聚合（回源 aiops-iam-anomaly.md §Privilege Escalation Detection）
gcloud logging read \
  "protoPayload.status.code=7" \
  --project="$CLOUDSDK_CORE_PROJECT" --freshness=1h --format=json | \
  jq -r '.[] | "\(.protoPayload.resourceName)\t\(.protoPayload.principalEmail)"' | sort | uniq -c | sort -rn

# 2. SA 密钥老化（回源 aiops-iam-anomaly.md §Service Account Key Anomalies）
gcloud iam service-accounts keys list \
  --iam-account="$SA_EMAIL" --project="$CLOUDSDK_CORE_PROJECT" \
  --format=json | jq -r '.[] | select(((now - (.validAfterTime|fromdateiso8601))/86400) > 90) | .name'

# 3. Cloud SQL IAM DB 认证失败（回源 aiops-query-insights.md §Connection Pool Monitoring）
gcloud logging read \
  "resource.type=cloudsql_database AND textPayload=~\"permission denied\"" \
  --project="$CLOUDSDK_CORE_PROJECT" --freshness=1h --format=json
```

### 降级顺序建议

1. **先保**：恢复被删的角色绑定 / 重新启用 SA（保住所有下游认证，全局影响最大）。
2. **次保**：轮换并重新分发 SA 密钥（恢复数据平面写入）。
3. **后弃**：暂停 IAM 策略漂移审计的自动修复（避免并发 `ABORTED`，人工复核后再开）。

### 锚点链接

- [gcp-iam-ops AIOps](gcp-iam-ops/references/advanced/aiops-iam-anomaly.md)
- [gcp-cloudsql-ops AIOps](gcp-cloudsql-ops/references/advanced/aiops-query-insights.md)
- [gcp-gcs-ops AIOps](gcp-gcs-ops/references/advanced/aiops-storage-anomaly.md)
- [gcp-bigquery-ops AIOps](gcp-bigquery-ops/references/advanced/aiops-bigquery-anomaly.md)
- [docs/error-taxonomy.md](error-taxonomy.md)（Permission / Authentication 维度）

---

## 与其他 AIOps 资产的关系

| 资产 | 作用 | 链接 |
|------|------|------|
| 错误分类（根因维度） | 跨域链路中的 error-taxonomy 维度映射来源，统一自愈决策 | [docs/error-taxonomy.md](error-taxonomy.md) |
| 闭环反馈（GCL 反馈） | 跨域排障结论回流到 GCL 评分与知识库，形成检测→处置→反馈闭环 | [gcp-gcl-runner-ops/trace_feedback.py](gcp-gcl-runner-ops/trace_feedback.py) |
| 各产品孤立 aiops | 本文件的下游锚点，提供单产品根因定位与告警细节 | 见各链路「锚点链接」 |

> 本文件不重建 error-taxonomy，仅引用其维度编码；不修改任何 skill 目录文件，仅作为 `docs/` 下的全局关联层。
