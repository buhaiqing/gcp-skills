# Cross-Skill Blast Radius — 跨域关联排障地图

> **Purpose:** 在 27 个 `gcp-*-ops` skill 的孤立 `aiops-*.md` 之上，提供跨域依赖 / blast-radius / 降级顺序的全局视图。当单点变更或故障沿上游→下游扩散时，本文件给出关联排障的入口与告警锚点。
> **Version:** 1.0.0
> **Last Updated:** 2026-07-19
> **Scope:** 覆盖全部 27 个 `gcp-*-ops` skill 的跨域关联。已核查锚点（vpc / iam / billing / cloudbuild / gcs / bigquery / gke / cloudsql / pubsub / securitycenter）有独立 aiops 文档；其余产品（gce / lb / logging / kms / memorystore / dns / cloudrun / cloudfunctions / monitoring / secretmanager / cdn / securitycenter / filestore / gcl-runner / terraform / armor / composer）暂无独立 aiops 文档，其关联排障回退到最近的锚点 skill，详见各链路「回退」标注。

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

## 链路 4：LB / CDN / Armor（边缘 / 流量层）

### 拓扑（上游 → 下游）

```
LB (转发规则 / 后端服务 / NEG / SSL 证书)
   ├──► CDN (缓存策略、回源 Host、签名 URL)
   ├──► Armor (安全策略、WAF 规则、DDoS 防护)
   └──► GCE / GKE 后端 (实例组 / NEG 健康检查)
```

> **回退说明**：LB / CDN / Armor 暂无独立 aiops 文档。LB 后端异常排障回退到 `gcp-gce-ops` / `gcp-gke-ops` 的健康检查章节；CDN 回源异常回退到 `gcp-gcs-ops`（回源源站）；Armor 策略误杀排障回退到 `gcp-vpc-ops` 防火墙章节。

### Blast radius

| 上游变更 | 影响边界 | 典型 error-taxonomy 维度 |
|----------|----------|--------------------------|
| LB 后端服务摘除 / NEG 清空 | CDN 回源 502、Armor 转发目标不可达 | `UNAVAILABLE` (Network) |
| SSL 证书过期 / 误删 | 全站 TLS 握手失败、CDN 回源 525 | `FAILED_PRECONDITION` (Config) |
| Armor 安全策略误配（deny 过宽） | 合法流量被 403，LB 转发被拦截 | `PERMISSION_DENIED` (Permission) |
| CDN 缓存策略误清 | 回源压力骤增、源站限流 `RATE_LIMITED` | `RATE_LIMITED` (Rate Limit) |

### 降级顺序建议

1. **先保**：恢复 LB 后端健康（保住数据平面入口）。
2. **次保**：回滚 Armor 过宽 deny 规则（恢复合法流量）。
3. **后弃**：下调 CDN 日志采样率（省成本，不阻断业务）。

### 锚点链接

- [gcp-vpc-ops AIOps](gcp-vpc-ops/references/advanced/aiops-network-anomaly.md)（Armor 回退）
- [gcp-gcs-ops AIOps](gcp-gcs-ops/references/advanced/aiops-storage-anomaly.md)（CDN 回源）
- [gcp-gke-ops AIOps](gcp-gke-ops/references/advanced/aiops-gke-anomaly.md)（NEG 后端）

---

## 链路 5：Pub/Sub → Cloud Run / Cloud Functions / BigQuery（事件 / 数据管道层）

### 拓扑（上游 → 下游）

```
Pub/Sub (topic / subscription / schema / sink)
   ├──► Cloud Run (push 订阅触发服务)
   ├──► Cloud Functions (trigger 触发函数)
   └──► BigQuery (subscription sink 写入表)
```

> **回退说明**：Cloud Run / Cloud Functions 暂无独立 aiops 文档。函数/服务调用失败排障回退到 `gcp-logging-ops`（调用日志）与 `gcp-monitoring-ops`（延迟/错误率指标）；BigQuery sink 有独立锚点。

### Blast radius

| 上游变更 | 影响边界 | 典型 error-taxonomy 维度 |
|----------|----------|--------------------------|
| topic 删除 / 重命名 | 订阅者 `NOT_FOUND`、Cloud Run/Functions 触发中断 | `NOT_FOUND` (Resource State) |
| subscription 推送端点不可达 | Cloud Run 重试堆积、消息积压 `UNAVAILABLE` | `UNAVAILABLE` (Network) |
| schema 变更不兼容 | 消息校验失败、Functions 解析异常 `INVALID_ARGUMENT` | `INVALID_ARGUMENT` (Config) |
| BigQuery sink IAM 收紧 | 订阅写入表 `PERMISSION_DENIED` | `PERMISSION_DENIED` (Permission) |

### 降级顺序建议

1. **先保**：恢复 topic / subscription（保住事件管道，数据平面优先）。
2. **次保**：修复 Cloud Run / Functions 端点可达性（恢复消费）。
3. **后弃**：暂停 BigQuery sink 增量分析（延迟可接受）。

### 锚点链接

- [gcp-bigquery-ops AIOps](gcp-bigquery-ops/references/advanced/aiops-bigquery-anomaly.md)
- [gcp-logging-ops AIOps](gcp-logging-ops/references/advanced/aiops-logging-anomaly.md)（回退）
- [gcp-monitoring-ops AIOps](gcp-monitoring-ops/references/advanced/aiops-monitoring-anomaly.md)（回退）

---

## 链路 6：KMS / Secret Manager → 加密资源（密钥 / 机密层）

### 拓扑（上游 → 下游）

```
KMS (key ring / crypto key / version)
   ├──► GCS (CMEK 加密 bucket)
   ├──► Cloud SQL (CMEK 实例)
   └──► Secret Manager (secret / version)
Secret Manager
   ├──► Cloud Run / Cloud Functions (挂载机密)
   └──► Composer (connection 密码)
```

> **回退说明**：KMS / Secret Manager 暂无独立 aiops 文档。密钥禁用导致加密资源不可读排障回退到对应资源 skill（GCS / Cloud SQL）；机密挂载失败回退到 `gcp-logging-ops`。

### Blast radius

| 上游变更 | 影响边界 | 典型 error-taxonomy 维度 |
|----------|----------|--------------------------|
| KMS key version 禁用 / 销毁 | CMEK bucket / 实例读取 `PERMISSION_DENIED` 或 `FAILED_PRECONDITION` | `FAILED_PRECONDITION` (Config) |
| Secret version 禁用 / 删除 | Cloud Run / Functions 启动拉取机密失败 `NOT_FOUND` | `NOT_FOUND` (Resource State) |
| KMS key 轮转 | 旧密文短暂不可解密、依赖服务重试 `UNAVAILABLE` | `UNAVAILABLE` (Network) |
| Secret IAM 收紧 | Composer connection 取密 `PERMISSION_DENIED` | `PERMISSION_DENIED` (Permission) |

### 降级顺序建议

1. **先保**：重新启用 KMS key version / Secret version（恢复加密资源可读）。
2. **次保**：恢复 Secret IAM binding（恢复服务机密挂载）。
3. **后弃**：暂停非关键 CMEK 审计扫描。

### 锚点链接

- [gcp-gcs-ops AIOps](gcp-gcs-ops/references/advanced/aiops-storage-anomaly.md)（CMEK）
- [gcp-cloudsql-ops AIOps](gcp-cloudsql-ops/references/advanced/aiops-query-insights.md)（CMEK）
- [gcp-logging-ops AIOps](gcp-logging-ops/references/advanced/aiops-logging-anomaly.md)（机密挂载回退）

---

## 链路 7：Composer → GCS / Pub/Sub / BigQuery（编排层）

### 拓扑（上游 → 下游）

```
Composer (Airflow environment / DAG / connection / PyPI)
   ├──► GCS (DAG bucket / 数据落地)
   ├──► Pub/Sub (operator 发布消息)
   └──► BigQuery (operator 执行查询 / 写入)
```

> **回退说明**：Composer 暂无独立 aiops 文档。DAG 失败排障回退到 `gcp-gcs-ops`（DAG bucket）、`gcp-pubsub-ops`、`gcp-bigquery-ops` 各自锚点；环境创建失败回退到 `gcp-vpc-ops`（私有 IP / 子网）。

### Blast radius

| 上游变更 | 影响边界 | 典型 error-taxonomy 维度 |
|----------|----------|--------------------------|
| DAG bucket 删除 / IAM 收紧 | DAG 同步失败、任务 `NOT_FOUND` / `PERMISSION_DENIED` | `NOT_FOUND` (Resource State) |
| Composer connection 密码失效 | BigQuery / Pub/Sub operator 认证 `AUTH_FAILED` | `AUTH_FAILED` (Auth) |
| PyPI 包冲突 / 环境重建失败 | 所有 DAG 调度中断 `FAILED_PRECONDITION` | `FAILED_PRECONDITION` (Config) |
| 私有环境子网 CIDR 耗尽 | 环境创建 `INSUFFICIENT_CIDR` 失败 | `FAILED_PRECONDITION` (Config) |

### 降级顺序建议

1. **先保**：恢复 DAG bucket IAM / connection 密码（恢复调度与下游写入）。
2. **次保**：重建 PyPI 依赖（恢复 DAG 执行）。
3. **后弃**：暂停非关键 DAG 回填作业。

### 锚点链接

- [gcp-gcs-ops AIOps](gcp-gcs-ops/references/advanced/aiops-storage-anomaly.md)
- [gcp-bigquery-ops AIOps](gcp-bigquery-ops/references/advanced/aiops-bigquery-anomaly.md)
- [gcp-pubsub-ops AIOps](gcp-pubsub-ops/references/advanced/aiops-pubsub-anomaly.md)
- [gcp-vpc-ops AIOps](gcp-vpc-ops/references/advanced/aiops-network-anomaly.md)（私有环境回退）

---

## 链路 8：Monitoring / Logging / Security Center（观测 / 安全层）

### 拓扑（上游 → 下游）

```
Monitoring (metric / dashboard / alert policy)
   ├──► Logging (log-based metric / sink / exclusion)
   └──► Security Center (finding / mute rule / source)
```

> **回退说明**：Monitoring / Logging / Security Center 暂无独立 aiops 文档（Security Center 有锚点）。告警/日志管道异常排障回退到 `gcp-logging-ops` 与 `gcp-monitoring-ops`；安全发现误报回退到 `gcp-securitycenter-ops`。

### Blast radius

| 上游变更 | 影响边界 | 典型 error-taxonomy 维度 |
|----------|----------|--------------------------|
| Logging sink 删除 | Monitoring 日志指标断流、告警静默 `NOT_FOUND` | `NOT_FOUND` (Resource State) |
| Alert policy 误删 | 下游故障无告警、MTTR 上升 | `FAILED_PRECONDITION` (Config) |
| Log exclusion 过宽 | 安全相关日志被丢弃、Security Center 漏检 | `FAILED_PRECONDITION` (Config) |
| Mute rule 过宽 | 真实发现被静默 `PERMISSION_DENIED`（误判） | `PERMISSION_DENIED` (Permission) |

### 降级顺序建议

1. **先保**：恢复 Logging sink（保住指标与告警数据源）。
2. **次保**：回滚过宽 exclusion / mute rule（恢复检测覆盖）。
3. **后弃**：暂停非关键 dashboard 刷新。

### 锚点链接

- [gcp-securitycenter-ops AIOps](gcp-securitycenter-ops/references/advanced/aiops-security-anomaly.md)
- [gcp-logging-ops AIOps](gcp-logging-ops/references/advanced/aiops-logging-anomaly.md)（回退）
- [gcp-monitoring-ops AIOps](gcp-monitoring-ops/references/advanced/aiops-monitoring-anomaly.md)（回退）

---

## 链路 9：Memorystore / Filestore / Cloud SQL（数据层）

### 拓扑（上游 → 下游）

```
Memorystore (Redis instance / failover)
   ├──► GCE / GKE (应用缓存客户端)
Filestore (instance / file share / NFS)
   ├──► GCE / GKE (挂载 NFS 的工作负载)
Cloud SQL (instance / replica / backup)
   ├──► Cloud Run / GKE (应用数据库连接)
   └──► Composer (connection 数据源)
```

> **回退说明**：Memorystore / Filestore 暂无独立 aiops 文档。Redis 故障排障回退到 `gcp-gce-ops` / `gcp-gke-ops` 客户端连接章节；Filestore 挂载失败回退到 `gcp-vpc-ops`（NFS 端口 / 防火墙）；Cloud SQL 有独立锚点。

### Blast radius

| 上游变更 | 影响边界 | 典型 error-taxonomy 维度 |
|----------|----------|--------------------------|
| Memorystore 故障转移 / 实例删除 | 应用缓存击穿、GKE Pod 连接 `UNAVAILABLE` | `UNAVAILABLE` (Network) |
| Filestore 实例删除 / 配额满 | GCE 挂载点 IO 错误 `STORAGE_FULL` / `NOT_FOUND` | `STORAGE_FULL` (Resource State) |
| Cloud SQL 主实例删除 / 只读切换 | 应用连接 `UNAVAILABLE`、Composer DAG 失败 | `UNAVAILABLE` (Network) |
| Cloud SQL 存储满 | 写入 `STORAGE_FULL`、备份 `BACKUP_FAILED` | `STORAGE_FULL` (Resource State) |

### 降级顺序建议

1. **先保**：恢复 Cloud SQL 主实例 / Memorystore（保住应用数据平面）。
2. **次保**：扩容 Filestore / Cloud SQL 存储（恢复写入）。
3. **后弃**：暂停非关键备份保留策略。

### 锚点链接

- [gcp-cloudsql-ops AIOps](gcp-cloudsql-ops/references/advanced/aiops-query-insights.md)
- [gcp-gke-ops AIOps](gcp-gke-ops/references/advanced/aiops-gke-anomaly.md)
- [gcp-vpc-ops AIOps](gcp-vpc-ops/references/advanced/aiops-network-anomaly.md)（Filestore NFS 回退）

---

## 链路 10：Cloud Build / Terraform（交付 / IaC 层）

### 拓扑（上游 → 下游）

```
Cloud Build (build / trigger / worker pool)
   ├──► GCS (构建产物 / 源码 tarball)
   ├──► Artifact Registry / Container (镜像推送)
   └──► Cloud Run / GKE (部署目标)
Terraform (plan / apply / destroy / state)
   ├──► 任意 gcp-*-ops 资源 (声明式创建/变更)
   └──► GCS (remote state bucket)
```

> **回退说明**：Cloud Build / Terraform 暂无独立 aiops 文档。构建失败排障回退到 `gcp-logging-ops`（构建日志）与 `gcp-gcs-ops`（产物）；Terraform state 冲突回退到 `gcp-gcs-ops`（remote state bucket）与 `gcp-iam-ops`（state 锁 IAM）。

### Blast radius

| 上游变更 | 影响边界 | 典型 error-taxonomy 维度 |
|----------|----------|--------------------------|
| 构建产物 bucket 删除 | 部署拉取镜像/包 `NOT_FOUND` | `NOT_FOUND` (Resource State) |
| 私有 worker pool 子网耗尽 | 构建排队失败 `FAILED_PRECONDITION` | `FAILED_PRECONDITION` (Config) |
| Terraform remote state 锁冲突 | `apply` 并发 `ABORTED` | `ABORTED` (Dependency) |
| Terraform 误 `destroy` 资源 | 下游服务 `NOT_FOUND`（需 HALT 人工确认） | `NOT_FOUND` (Resource State) |

### 降级顺序建议

1. **先保**：恢复 remote state bucket / 释放 state 锁（恢复 IaC 可控性）。
2. **次保**：恢复构建产物 bucket（恢复部署链路）。
3. **后弃**：暂停非关键 nightly 构建。

### 锚点链接

- [gcp-gcs-ops AIOps](gcp-gcs-ops/references/advanced/aiops-storage-anomaly.md)
- [gcp-logging-ops AIOps](gcp-logging-ops/references/advanced/aiops-logging-anomaly.md)（构建日志回退）
- [gcp-iam-ops AIOps](gcp-iam-ops/references/advanced/aiops-iam-anomaly.md)（state 锁回退）

---

## 与其他 AIOps 资产的关系

| 资产 | 作用 | 链接 |
|------|------|------|
| 错误分类（根因维度） | 跨域链路中的 error-taxonomy 维度映射来源，统一自愈决策 | [docs/error-taxonomy.md](error-taxonomy.md) |
| 闭环反馈（GCL 反馈） | 跨域排障结论回流到 GCL 评分与知识库，形成检测→处置→反馈闭环 | [gcp-gcl-runner-ops/trace_feedback.py](gcp-gcl-runner-ops/trace_feedback.py) |
| 各产品孤立 aiops | 本文件的下游锚点，提供单产品根因定位与告警细节 | 见各链路「锚点链接」 |

> 本文件不重建 error-taxonomy，仅引用其维度编码；不修改任何 skill 目录文件，仅作为 `docs/` 下的全局关联层。
