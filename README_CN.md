# GCP Skills

> Google Cloud Platform 的 Agent 可解析操作手册 — 结构化、AI 代理可执行的云资源管理技能集合。

[**English Version**](README.md)

---

## 概述

`gcp-skills` 是一个 **Skills Farm**（技能农场）—— 一套为 AI 代理设计的、生产级的云资源运维操作手册集。每个技能是一个独立的目录，告诉 Agent **何时**行动、**执行前检查**什么、**如何**通过 `gcloud` CLI 或 SDK 执行、以及**如何**从失败中恢复。

基于 [Agent Skill OpenSpec](https://agentskills.io/specification) 构建，并遵循 [`AGENTS.md`](AGENTS.md) 中的规范。本仓库强制执行严格的质量门禁，包括 Token 效率、凭据安全，以及 **Generator-Critic-Loop (GCL)** 对抗性质量门禁。

---

## 仓库结构

```
gcp-skills/
├── gcp-[product]-ops/          # 每个 GCP 产品一个技能目录
│   ├── SKILL.md                # 入口文件：触发条件、变量约定、执行概览
│   ├── references/             # 深度内容：命令、错误码、监控、评估
│   │   ├── core-concepts.md
│   │   ├── api-sdk-usage.md
│   │   ├── gcloud-usage.md
│   │   ├── troubleshooting.md
│   │   ├── monitoring.md
│   │   ├── integration.md
│   │   ├── well-architected-assessment.md
│   │   ├── idempotency-checklist.md
│   │   ├── rubric.md               # GCL 评分标准（required/recommended 技能）
│   │   └── prompt-templates.md     # GCL 生成器 + 评审模板（required/recommended）
│   └── assets/
│       ├── example-config.yaml
│       └── eval_queries.json
├── gcp-skill-generator/         # 元技能：从 GCP API 规范生成新技能
│   └── references/
│       ├── gcp-skill-template.md
│       ├── gcl-rollout-spec.md
│       └── ...
├── gcp-gcl-runner-ops/          # 跨技能 GCL 执行器（第二阶段）
│   └── scripts/
│       ├── gcl_runner.py
│       ├── gcl_runner_test.py
│       └── README.md
├── AGENTS.md                    # 主规范 — 请先阅读此文
├── REQUIREMENTS.md              # 完整需求和架构文档
├── README.md                    # 本文件（英文版）
├── README_CN.md                 # 中文版
├── .env.example
├── docker-compose.yaml
└── Dockerfile
```

### 标准技能目录

```
gcp-[product]-ops/
├── SKILL.md
├── references/
│   ├── core-concepts.md
│   ├── api-sdk-usage.md
│   ├── gcloud-usage.md              # sdk-only 技能可省略
│   ├── troubleshooting.md
│   ├── integration.md
│   ├── monitoring.md
│   ├── well-architected-assessment.md  # 必须
│   ├── idempotency-checklist.md
│   ├── rubric.md                       # GCL：required/recommended
│   └── prompt-templates.md            # GCL：required/recommended
├── assets/
│   ├── example-config.yaml
│   └── eval_queries.json
└── scripts/                            # 可选
```

---

## 现有技能

| 技能目录 | 产品 | 状态 |
|----------------|---------|:----:|
| [`gcp-gce-ops`](gcp-gce-ops/SKILL.md) | Compute Engine（虚拟机实例、磁盘、快照、MIG） | ✅ 已发布 |
| [`gcp-lb-ops`](gcp-lb-ops/SKILL.md) | Cloud Load Balancing（转发规则、后端服务、URL 映射、NEG、SSL 证书） | ✅ 已发布 |
| [`gcp-logging-ops`](gcp-logging-ops/SKILL.md) | Cloud Logging（日志存储桶、视图、接收器、指标、排除规则） | ✅ 已发布 |
| [`gcp-kms-ops`](gcp-kms-ops/SKILL.md) | Cloud KMS（密钥环、加密密钥、密钥版本、加密/解密） | ✅ 已发布 |
| [`gcp-memorystore-ops`](gcp-memorystore-ops/SKILL.md) | Memorystore for Redis（实例、扩容、导出/导入、故障转移） | ✅ 已发布 |
| [`gcp-cloudbuild-ops`](gcp-cloudbuild-ops/SKILL.md) | Cloud Build（构建、触发器、私有工作池、诊断） | ✅ 已发布 |
| [`gcp-billing-ops`](gcp-billing-ops/SKILL.md) | Cloud Billing（结算账号、预算、导出、项目关联、定价） | ✅ 已发布 |
| [`gcp-vpc-ops`](gcp-vpc-ops/SKILL.md) | VPC（网络、子网、防火墙规则、VPN、Cloud NAT、对等连接） | ✅ 已发布 |
| [`gcp-gke-ops`](gcp-gke-ops/SKILL.md) | Google Kubernetes Engine（集群、节点池、工作负载、IAM） | ✅ 已发布 |
| [`gcp-cloudsql-ops`](gcp-cloudsql-ops/SKILL.md) | Cloud SQL（MySQL/PostgreSQL/SQL Server 实例、备份） | ✅ 已发布 |
| [`gcp-gcs-ops`](gcp-gcs-ops/SKILL.md) | Cloud Storage（存储桶、对象、生命周期、IAM） | ✅ 已发布 |
| [`gcp-iam-ops`](gcp-iam-ops/SKILL.md) | Cloud IAM（角色、策略、服务账号、工作负载身份） | ✅ 已发布 |
| [`gcp-dns-ops`](gcp-dns-ops/SKILL.md) | Cloud DNS（区域、记录、策略、健康检查） | ✅ 已发布 |
| [`gcp-pubsub-ops`](gcp-pubsub-ops/SKILL.md) | Cloud Pub/Sub（主题、订阅、架构、快照） | ✅ 已发布 |
| [`gcp-cloudrun-ops`](gcp-cloudrun-ops/SKILL.md) | Cloud Run（服务、修订版、流量分配） | ✅ 已发布 |
| [`gcp-cloudfunctions-ops`](gcp-cloudfunctions-ops/SKILL.md) | Cloud Functions（函数、触发器、源代码仓库） | ✅ 已发布 |
| [`gcp-monitoring-ops`](gcp-monitoring-ops/SKILL.md) | Cloud Monitoring（指标、仪表板、告警策略） | ✅ 已发布 |
| [`gcp-bigquery-ops`](gcp-bigquery-ops/SKILL.md) | BigQuery（数据集、表、查询、作业） | ✅ 已发布 |
| [`gcp-secretmanager-ops`](gcp-secretmanager-ops/SKILL.md) | Secret Manager（密钥、版本、IAM） | ✅ 已发布 |
| [`gcp-cdn-ops`](gcp-cdn-ops/SKILL.md) | Cloud CDN（源站、缓存策略、签名 URL） | ✅ 已发布 |
| [`gcp-securitycenter-ops`](gcp-securitycenter-ops/SKILL.md) | Security Command Center（发现、来源、静音规则） | ✅ 已发布 |
| [`gcp-filestore-ops`](gcp-filestore-ops/SKILL.md) | Cloud Filestore（实例、文件共享、备份、快照、NFS） | ✅ 已发布 |
| [`gcp-gcl-runner-ops`](gcp-gcl-runner-ops/SKILL.md) | GCL Runner（跨技能 Generator-Critic-Loop 执行） | ✅ 已发布 |
| [`gcp-terraform-ops`](gcp-terraform-ops/SKILL.md) | Terraform（初始化、规划、应用、销毁、状态管理） | ✅ 已发布 |

完整路线图请参见 [AGENTS.md 附录 A](AGENTS.md#appendix-a-gcp-product--directory-mapping-planned)。

---

## 快速开始

### 前置条件

```bash
# 1. gcloud CLI
gcloud version

# 2. 服务账号密钥
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# 3. 设置项目
export CLOUDSDK_CORE_PROJECT=my-gcp-project

# 4. 验证
gcloud auth application-default print-access-token --quiet &>/dev/null && echo "✅ 认证通过"
```

### 使用技能

技能由兼容的 AI Agent 运行时（Claude Code、Cursor、Harness AI Agent 等）自动加载。Agent 读取 `SKILL.md` 的 `description` 字段来匹配用户请求。

**示例：**
```
用户："在 us-central1-a 创建一个虚拟机实例"
Agent 加载 gcp-gce-ops → 执行 gcloud compute instances create（含预检）→ 验证 → 报告结果
```

### 运行评测查询

每个技能附带 `assets/eval_queries.json`——约 20 条测试查询，用于验证触发准确性：

```bash
# 手动评测示例
cat gcp-gce-ops/assets/eval_queries.json | python3 -m json.tool
```

---

## 质量门禁

### 五大核心标准

| # | 标准 | 说明 |
|---|------|------|
| 1 | **边界明确** | 精确的 SHOULD/SHOULD NOT 触发条件 + 委托规则 |
| 2 | **结构化 I/O** | `{{env.*}}`（永不询问）、`{{user.*}}`（一次询问）、`{{output.*}}`（从 API 解析） |
| 3 | **步骤明确** | 每个操作都有：预检 → 执行 → 验证 → 恢复 |
| 4 | **失败策略完备** | ≥10 个产品特有错误码；HALT 与重试分离 |
| 5 | **职责单一** | 一个产品一个资源模型；跨产品委托而非重复 |

### Generator-Critic-Loop (GCL) 对抗性质量门禁

GCL 是运行时执行质量的对抗性检查。每个破坏性操作都由独立的 Critic 按量化评分标准打分，防止静默失败。

| 等级 | max_iter | 关键风险 |
|-------|:--------:|----------|
| **required** | 2 | 数据销毁、不可逆操作、生产流量影响 |
| **recommended** | 3 | 资源删除、配置变更 |
| **optional** | 5 | 只读审计、诊断 |

### 更新后自检

每次技能更新触发强制性两轮自检：
- **R1**：结构合规（元数据、触发条件、变量、Token 效率）
- **R2**：内容验证（链接完整性、去重、错误码、TODO.md 同步）

详情请见 [`AGENTS.md §11`](AGENTS.md#11-post-update-self-review-mandatory) 和 [`docs/post-update-self-review.md`](docs/post-update-self-review.md)。

---

## Token 效率

技能遵循 8 条规则（TE-1 至 TE-8），在保持 Agent 可执行性的同时最小化 Token 消耗：

| 规则 | 要点 | 节省量 |
|------|------|--------|
| **TE-1** | API 查询 > 静态表格 | ~200-500/文件 |
| **TE-2** | 省略不必要的文档说明 | ~100-200/函数 |
| **TE-3** | 紧凑错误表（≤3 列） | ~300-500/文件 |
| **TE-4** | JSON Paths 集中声明 | ~50-100/文件 |
| **TE-5** | YAML Anchors | ~200-400/文件 |
| **TE-6** | 消除跨文件重复 | 视情况而定 |
| **TE-7** | 专业内容放入 `advanced/` 层级 | ~3,000-8,000/文件 |
| **TE-8** | 引用深度 ≤ 2 层 | ~100-500/文件 |

---

## 开发指南

### 创建新技能

使用 [`gcp-skill-generator`](gcp-skill-generator/SKILL.md) 元技能：

```
"生成 gcp-gke-ops，用于 Google Kubernetes Engine，操作：create, describe, modify, delete"
```

生成器会自动搭建目录、填充所有参考文件，并根据 P0/P1 检查清单进行验证。

### P0 质量检查清单

- [ ] Trigger & Scope：包含 SHOULD/SHOULD NOT
- [ ] 变量：`{{env.*}}` vs `{{user.*}}` — 无秘密字面量
- [ ] 每个操作：预检 → 执行 → 验证 → 恢复
- [ ] 错误分类：≥10 个错误码，HALT 与重试分离
- [ ] 所有破坏性操作的安全门
- [ ] 应用 Token 效率规则（TE-1 至 TE-8）
- [ ] 自愈框架：≥3 个恢复路径
- [ ] GCL rubric + 提示模板（`required`/`recommended` 技能）
- [ ] Well-Architected 评估（五大支柱）
- [ ] 评测查询（≥20 条）用于触发准确性
- [ ] 所有内部链接有效

---

## 诊断日志标准

所有远程脚本使用结构化日志格式：

```
[HH:MM:SS] [PHASE] key=value
```

阶段：`DIAG` / `INSTALL` / `EXEC` / `RESULT` / `WARN` / `ERROR` / `SUMMARY`

完整规范见 [`docs/diagnostic-logging-standard.md`](docs/diagnostic-logging-standard.md)。

---

## 安全

- **永不输出凭据**：在日志中用 `****` 替换访问令牌和服务账号密钥
- **通过环境变量传递密码**：使用 `MYSQL_PWD` / `PGPASSWORD`，而非 `-p<password>`
- **删除操作**：必须获得明确的资源标识符确认
- **IAM 预览**：在应用策略变更前使用 dry-run 预览
- **Python SDK**：通过 `GOOGLE_APPLICATION_CREDENTIALS` 自动读取凭据 — 默认安全
- **Go SDK**：禁止 `fmt.Println(config)` 和 `log.Printf("%+v", ...)` — 可能泄漏服务账号密钥

---

## 相关项目

- [Google Cloud SDK & gcloud CLI](https://cloud.google.com/sdk/gcloud)
- [Google Cloud Client Libraries (Go)](https://pkg.go.dev/cloud.google.com/go)
- [Agent Skills Open Specification](https://agentskills.io/specification)
- [Google Cloud Architecture Framework](https://cloud.google.com/architecture/framework)

---

## 许可证

MIT 许可证 — 请参见 [LICENSE](LICENSE) 文件。

---

## 贡献指南

1. 阅读 [`AGENTS.md`](AGENTS.md) — 所有约定的唯一权威来源
2. 阅读仓库文档中的完整架构规范
3. 使用 [`gcp-skill-generator`](gcp-skill-generator/SKILL.md) 搭建新技能
4. 每次更新后运行两轮自检
5. 合并前通过 GCL 对抗性审查

---

> **有问题？** 提交 Issue 或查阅 [`docs/`](docs/) 中的详细规范。