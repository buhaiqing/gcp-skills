# Enhanced Self-Healing Framework for CLI Installation

> **Purpose:** 定义增强的 CLI 安装异常处理和自愈能力框架，确保在各种异常场景下都能自动恢复或提供明确的降级路径。
> **Version:** 1.0.0
> **Last Updated:** 2026-06-07
> **Status:** MANDATORY — 所有生成的 Skill 必须遵循此自愈框架

---

## 1. 核心设计原则

### 1.1 自愈能力成熟度模型

| 等级 | 名称 | 特征 |
|------|------|------|
| L1 | 基础重试 | 固定次数重试，无错误分类 |
| L2 | 智能重试 | 错误分类，针对性重试策略 |
| L3 | 多路径自愈 | 多种自愈路径，自动选择最优方案 |
| L4 | 预防性自愈 | 预检异常，提前规避 |
| L5 | 自学习自愈 | 历史数据分析，优化自愈策略 |

### 1.2 自愈决策树

```
[异常发生]
    │
    ├── Step 1: 错误分类
    │   网络异常 / 权限异常 / 资源异常 / 配置异常 / 未知异常
    │
    ├── Step 2: 选择自愈路径
    │   根据错误类型选择对应的自愈策略
    │
    ├── Step 3: 执行自愈
    │   尝试自愈操作，记录结果
    │
    ├── Step 4: 验证
    │   检查自愈是否成功
    │
    ├── Step 5: 降级（如自愈失败）
    │   执行降级路径，明确告知用户
```

---

## 2. 错误分类体系

### 2.1 gcloud CLI 安装错误

| 错误类型 | 检测方法 | 自愈路径 |
|----------|----------|----------|
| 网络超时 | `curl` 返回 > 30s | 切换镜像源，重试 |
| 磁盘空间不足 | `df -h` 显示 < 100MB | 清理 `/tmp`，重试 |
| 权限不足 | `/usr/local` 不可写 | 使用 `sudo` 或安装到 `~/bin` |
| 依赖缺失 | Python 版本 < 3.8 | 安装 Python 依赖 |
| 架构不匹配 | `uname -m` 不识别 | 手动选择架构 |

### 2.2 Go Runtime JIT 下载错误

| 错误类型 | 检测方法 | 自愈路径 |
|----------|----------|----------|
| 网络超时 | `curl` 返回 > 30s | 切换下载镜像 |
| 下载损坏 | 校验和错误 | 重新下载 |
| 版本不兼容 | `go version` 检查 | 降级至 1.21 |
| 架构不匹配 | 解压失败 | 自动检测架构 |

---

## 3. 降级路径

| 主路径 | 降级路径 1 | 降级路径 2 |
|--------|-----------|-----------|
| gcloud CLI | Cloud Console API (REST) | Go SDK (JIT) |
| Go JIT SDK | Python SDK (google-cloud-*) | `curl` REST API calls |

### 用户指导模板

```markdown
### 安装失败处理

如果 `gcloud` 安装失败，请尝试以下方法之一：

1. **使用 Cloud Shell**: 所有 GCP 操作可在 `https://shell.cloud.google.com` 完成
2. **使用 REST API**: `curl -H "Authorization: Bearer $(gcloud auth print-access-token)"`
3. **使用 Docker Image**: `docker run google/cloud-sdk:latest gcloud ...`
```