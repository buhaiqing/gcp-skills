# AIOps + FinOps + SecOps 三维度批判性反思审计报告

> 审计对象：`gcp-skills` 仓库（27 个 GCP 产品 skill）
> 分析方法：11 个深度审计 Agent（AIOps×5 / FinOps×3 / SecOps×3）并行审计 + Plan Agent 交叉维度聚合
> 核心原则：批判性反思 —— 区分**真实痛点**（数据丢失 / 安全洞 / 浪费支出）与**伪需求**（YAGNI）

---

## 1. 执行摘要

- **最危险缺口 — 无门控的破坏性自动化**：`gcp-gcs-ops`  shipped 了一个无 dry-run/确认门控的 `gsutil -m rm -r` 批量删除脚本（`gcp-gcs-ops/references/advanced/aiops-storage-anomaly.md:252-263`）；`gcp-pubsub-ops` 的"Auto-Cancel"会误 ack 正常在途消息（`gcp-pubsub-ops/references/advanced/aiops-pubsub-anomaly.md:255-273`）；`armor-ops` 缺 GCL `rubric.md` 安全门，错误的 WAF 规则可静默 blackhole 生产流量。**三个独立的 P0 数据丢失/可用性漏洞**。
- **最大结构性不一致 — 模板真空**：仅 ~6/27 skill 有任何 AIOps runbook，~13/27 有 FinOps 文件，GCL 安全门（`rubric.md`+`prompt-templates.md`）在 armor-ops / composer-ops / 大多数 skill 中缺失 —— 意味着每次修复都是手工定制而非 copy-paste。
- **最高 ROI 修复 — 可复用模板三件套**：`self-healing-runbook.md` + `finops-template.md` + `rubric.md`+`prompt-templates.md`，创建一次后让 Wave 2-4 变成机械式脚手架。

---

## 2. 三维度评分矩阵

评分键：0=缺失 / 1=薄（仅段落）/ 2=部分 / 3=单文件好模式 / 4=多文件进阶 / 5=成熟+门控。"n/a"=不在该维度范围。三重暴露=三维均 ≤1。

| Skill | AIOps | FinOps | SecOps | 三重暴露 |
|-------|-------|--------|--------|----------|
| **armor-ops** | 0 | 1 | 0 | **是** |
| **terraform-ops** | 0 | 3 | 0 | **是** |
| **filestore** | 0 | 0 | 0 | **是** |
| **composer-ops** | 0 | 1 | 0 | **是** |
| gcs-ops | 2 | 3 | 3 | 否（AIOps P0） |
| pubsub-ops | 2 | 3 | n/a | AIOps P0 |
| cloudsql-ops | 2 | 3 | 3 | 否 |
| bigquery-ops | 3 | 4 | 3 | 否 |
| gce-ops | 2 | 0 | 3 | 否 |
| gke-ops | 3 | 0 | 3 | 否 |
| lb-ops | 0 | 0 | 1 | AIOps+FinOps 缺口 |
| cloudrun-ops | 0 | 0 | n/a | AIOps+FinOps 缺口 |
| cloudfunctions-ops | 0 | 0 | n/a | AIOps+FinOps 缺口 |
| dns-ops | 0 | 1 | 0 | AIOps+SecOps 缺口 |
| cdn-ops | 0 | 3 | n/a | AIOps 缺口 |
| vpc-ops | 0 | 1 | 1 | AIOps 缺口 |
| iam-ops | n/a | 1 | 4 | 否 |
| kms-ops | n/a | 1 | 4 | 否 |
| secretmanager-ops | n/a | 1 | 4 | 否 |
| monitoring-ops | 1 | 1 | 0 | SecOps 缺口 |
| logging-ops | 1 | 1 | 0 | SecOps 缺口 |
| billing-ops | 3 | 4 | n/a | 否 |
| cloudbuild-ops | 0 | 3 | 0 | AIOps+SecOps 缺口 |
| memorystore-ops | 0 | 0 | n/a | AIOps+FinOps 缺口 |
| securitycenter-ops | 1 | n/a | 2 | AIOps 缺口 |
| （跨维度文档） | 1 | 1 | 1 | 薄覆盖 10/27 链路 |

**确认三重暴露（三维均 ≤1）：** armor-ops、terraform-ops、filestore、composer-ops。
gcs-ops 非三重暴露（FinOps=3、SecOps=3），但携带 AIOps P0 破坏性操作。

---

## 3. 跨维度联动分析

### 3.1 三维度全失败的 skill
证据确认恰好四个：
- **armor-ops**（AIOps 0，FinOps 1 薄段落，SecOps 0 — 无 rubric.md/prompt-templates.md，无 WAF blackhole 门控）
- **terraform-ops**（AIOps 0 — 手工 drift 检测，FinOps 3，SecOps 0 — 无 IaC 安全扫描）
- **filestore**（AIOps 0，FinOps 0，SecOps 0 — 三轴完全无覆盖）
- **composer-ops**（AIOps 0，FinOps 1 薄，SecOps 0 — 缺 rubric.md/prompt-templates.md）

这些是仓库的盲点：单个 skill 可同时引发数据丢失、浪费支出、安全洞，且无任何安全网。

### 3.2 共同根因
缺失的 **`rubric.md` + `prompt-templates.md` GCL 安全门** 是共同促成因素：
- armor-ops 无门阻断坏 WAF 规则（SecOps blackhole）**且** 无 AIOps 修复 playbook（异常无人处理）
- terraform-ops 无门阻断破坏性 `terraform destroy`/`apply`（AIOps 数据丢失风险）**且** 无 SecOps IaC 扫描

一个结构件的缺失因而跨维度复合放大，而非孤立失败。

### 3.3 复合风险
一维度 P0 + 另一维度缺门控 = 灾难性：
- gcs-ops 有 P0 无门控批量删除（AIOps），但其 SecOps 姿态"仅" 3 — 若攻击者窃取凭证（他处 SecOps 缺口）即可零摩擦触发无门控删除
- pubsub-ops 误 ack（P0 AIOps）位于无 self-healing runbook 的 skill，消息丢失静默且不可恢复
- armor-ops WAF blackhole（P0 SecOps）无 GCL 门，坏规则直达生产无 critic 检查点

---

## 4. 批判性反思：真实痛点 vs 伪需求

### 4.1 真实痛点（必须修）
- **数据丢失** — gcs 无门控 `gsutil -m rm -r`（`aiops-storage-anomaly.md:252-263`）；pubsub 误 ack 正常消息（`aiops-pubsub-anomaly.md:255-273`）。摧毁用户数据无可恢复，ship-blocking。
- **安全洞** — armor-ops WAF 可 blackhole 合法生产流量且无 GCL 门（缺 rubric.md/prompt-templates.md）。静默可用性损失。
- **浪费支出** — 高成本 compute skill（gce、gke、lb、cloudrun、cloudfunctions、memorystore、filestore）**零** FinOps 参考；这些最大支出项无优化指导。
- **未处理失败** — 全部 5 个 data skill（gcs、cloudsql、pubsub、bigquery、filestore）缺 `self-healing-runbook.md`；cloudsql 无效 filter 命令（`aiops-query-insights.md:86-102,132-159`）返回空 = 静默 AIOps 失败。

### 4.2 伪需求 / YAGNI（降级优先级）
- 给 **dns-ops、kms-ops、secretmanager-ops、monitoring-ops、logging-ops** 加完整 AIOps 自修复 — 这些从不跑自主循环，边际价值不抵维护面。薄 well-architected 段落可接受。
- 给全部 27 链路写跨 skill blast-radius 文档 — 仅 10/27 覆盖，但扩到 27 的 ROI 低于 P0/P1 门控；放 Wave 4 做脚手架，非手工编写。
- 给真正低成本、低流量 skill（dns、kms、secretmanager）逐个写 `finops-*.md` — 支出微不足道，共享模板懒应用即够。

---

## 5. 优先级矩阵

### P0 — Ship-blocking（任何发布前必修）
| ID | 发现 | 证据 (file:line) |
|----|------|------------------|
| P0-1 | 无门控 `gsutil -m rm -r` 批量删除（数据丢失风险，无 dry-run/门控） | `gcp-gcs-ops/references/advanced/aiops-storage-anomaly.md:252-263` |
| P0-2 | "Auto-Cancel" 误 ack 正常在途 pubsub 消息（消息丢失） | `gcp-pubsub-ops/references/advanced/aiops-pubsub-anomaly.md:255-273` |
| P0-3 | armor-ops WAF 规则可 blackhole 生产流量且无 GCL 安全门（缺 rubric.md/prompt-templates.md） | SecOps 证据：armor-ops 缺 rubric.md + prompt-templates.md |

### P1 — 高优先级（下一发布）
| ID | 发现 | 证据 |
|----|------|------|
| P1-1 | 高成本 skill（gce、gke、lb、cloudrun、cloudfunctions、memorystore、filestore）**缺** `finops-*.md` | FinOps Wave 2：high-cost "ALL MISSING" |
| P1-2 | 全部 5 个 data skill（gcs、cloudsql、bigquery、pubsub、filestore）**缺** `self-healing-runbook.md` | AIOps Data wave |
| P1-3 | terraform-ops **零** AIOps 覆盖（手工 drift 检测，无门） | AIOps Ops wave |
| P1-4 | cloudsql 无效 filter 命令（解析/返回空 = 静默失败） | `gcp-cloudsql-ops/references/advanced/aiops-query-insights.md:86-102,132-159` |
| P1-5 | filestore 三重暴露（0/0/0）— 无 AIOps/FinOps/SecOps | 评分矩阵 |

### P2 — 中优先级（一致性 / 加固）
| ID | 发现 | 证据 |
|----|------|------|
| P2-1 | 8 个低成本 skill（dns、kms、secretmanager、monitoring、logging、composer、armor、securitycenter、billing、terraform）仅依赖薄 well-architected Cost 段落 | FinOps Low-cost wave |
| P2-2 | composer-ops 及大多数非关键 skill 缺 rubric.md+prompt-templates.md | SecOps Network/Compute waves |
| P2-3 | vpc-ops 防火墙异常检测缺失；dns-ops 无 DNS-hijack 检测 | AIOps Infra wave |
| P2-4 | securitycenter/armor 无 AIOps 修复；monitoring/logging 无 secret-leak-in-logs 检测 | AIOps Security/Ops waves |
| P2-5 | cross-skill-blast-radius.md + error-taxonomy.md 仅覆盖 10/27 链路 | 结构性不一致注记 |

---

## 6. 优化路线图（4 Wave，ultrawork 就绪）

### Wave 1 — P0 安全门（Effort: M，3 skill：gcs、pubsub、armor）
- **触及 skill**：gcp-gcs-ops、gcp-pubsub-ops、armor-ops
- **动作**：gcs 删除脚本加 `--dry-run`/确认门控（P0-1）；pubsub auto-cancel 重写为仅针对 DLQ/stuck 消息，绝不碰在途正常消息（P0-2）；armor-ops 编写 `rubric.md` + `prompt-templates.md` GCL 门阻断 drop 超阈值合法流量的 WAF 规则（P0-3）
- **预期**：零无门控破坏性路径；WAF 变更受 critic 门控
- **TDD**：加参考示例单测（dry-run 输出断言、ack 目标过滤测试）

### Wave 2 — 高成本 FinOps + Data AIOps Runbook（Effort: L，~12 skill）
- **触及 skill**：gce、gke、lb、cloudrun、cloudfunctions、memorystore、filestore（FinOps P1-1）；gcs、cloudsql、bigquery、pubsub、filestore（self-healing runbook P1-2）；cloudsql filter fix（P1-4）
- **动作**：从模板实例化 7 个高成本 skill 的 `finops-*.md`；5 个 data skill 加 `self-healing-runbook.md`；修 cloudsql 无效 filter
- **预期**：每个高支出 skill 有成本优化指导；每个 data skill 有恢复 runbook
- **TDD**：finops dry_run 阈值测试（镜像 bigquery 好模式）；runbook 步骤验证测试

### Wave 3 — SecOps GCL 门 + 监控（Effort: M，~6 skill）
- **触及 skill**：composer-ops、terraform-ops、monitoring-ops、logging-ops、securitycenter-ops、vpc-ops、dns-ops
- **动作**：composer/terraform 加 `rubric.md`+`prompt-templates.md`（P2-2）；terraform-ops IaC 安全扫描步（P1-3）；secret-leak-in-logs 检测（P2-4）；vpc 防火墙 + dns-hijack 检测（P2-3）
- **预期**：所有 network/compute 变更 skill 有 GCL 门；盲点 SecOps 覆盖

### Wave 4 — 结构性一致性（模板驱动，Effort: M，repo 全量）
- **触及 skill**：全部 27（脚手架遍扫）
- **动作**：推出 3 个可复用模板；回填薄 well-architected-only skill（P2-1）；blast-radius/error-taxonomy 扩到 27/27（P2-5）
- **预期**：新 AIOps/FinOps/SecOps 内容变 copy-paste；一致性由模板强制

---

## 7. 可复用模板提案（最高 ROI 结构性修复）

三个模板文件，在 `gcp-skill-generator/references/` 或 `docs/` 创建一次，然后每 skill copy：

1. **`self-healing-runbook.md`** — 标准段落：Trigger/Detect → Triage → Automated Remediation（任何破坏性 `gcloud`/`gsutil`/`kubectl` 操作显式 `--dry-run`/确认门）→ Manual Escalation → Post-Mortem。直接关闭 P1-2（data skill）与 P2-4。
2. **`finops-template.md`** — 段落：Cost Drivers → Idle/Waste Detection（`gcloud` 查询）→ Sizing/Commitment 建议 → Dry-Run 阈值门控（镜像 bigquery 好模式）。通过 copy-paste 关闭 P1-1 与 P2-1。
3. **`rubric.md` + `prompt-templates.md`**（GCL 安全门对）— `rubric.md` 定义 critic 维度（Correctness、Safety=0→ABORT、Idempotency、Traceability、Spec Compliance）与 blast-radius 检查；`prompt-templates.md` 提供 Critic/Hallucination-Detector prompt。关闭 P0-3、P1-3、P2-2，门控每个破坏性/WAF/IaC 变更。

**为何最高 ROI**：一旦存在，Wave 2-4 变机械脚手架（copy 模板 → 填 skill 特定命令）而非 20+ 手工编写任务，且 P0 安全门通过 generator 成每个新 skill 的默认部分。

---

## 8. 原子提交策略（执行阶段）

- **按 wave 提交**，非按文件：`wave1/p0-safety-gates`、`wave2/finops-runbooks`、`wave3/secops-gates`、`wave4/templates-scaffold`
- 每提交含相关 skill 目录 + 新/更新模板为一 cohesive 单元
- 模板先独立提交（`chore: add reusable aiops/finops/secops templates`），下游 wave 引用稳定构件
- 每个 P0 修复独立提交，message 含 file:line 便于追溯
- 绝不混 P0 安全修复与无关脚手架

## 9. TDD 导向计划注记

- 每个模板随附 **example/ fixture**（采样 gcloud 输出）供参考验证测试使用
- P0 修复含回归测试：gcs dry-run 断言无门控不执行 `rm`；pubsub 测试断言正常在途消息永不被 ack；armor 门测试断言 blackhole-rule 候选被 critic rubric 拒绝
- FinOps 模板含 dry_run 阈值测试，镜像现有 bigquery 模式
- 每提交门禁：`npx markdownlint-cli2` + `ruff`（有脚本处）
