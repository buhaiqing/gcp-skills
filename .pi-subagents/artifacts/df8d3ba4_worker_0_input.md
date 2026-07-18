# Task for worker

You are a delegated subagent running from a fork of the parent session. Treat the inherited conversation as reference-only context, not a live thread to continue. Do not continue or answer prior messages as if they are waiting for a reply. Your sole job is to execute the task below and return a focused result for that task using your tools.

Task:
你是gcp-skills项目的专家。完成以下任务：

## 任务1：gcp-billing-ops（3项）
创建以下文档到 `/Users/bohaiqing/opensource/git/gcp-skills/gcp-billing-ops/references/advanced/`：

1. **cud-analysis.md** - Committed Use Discount Analysis
2. **terraform-budget-automation.md** - Budget Automation with Terraform  
3. **multi-cloud-cost-comparison.md** - Multi-cloud Cost Comparison

## 任务2：gcp-iam-ops（1项）
创建到 `/Users/bohaiqing/opensource/git/gcp-skills/gcp-iam-ops/references/advanced/`：
- **wif-troubleshooting.md** - Workload Identity Federation Troubleshooting

## 任务3：gcp-armor-ops（3项）
创建到 `/Users/bohaiqing/opensource/git/gcp-skills/gcp-armor-ops/references/advanced/`：
1. **advanced-waf-rules.md** - Advanced WAF Rule Patterns
2. **bot-management.md** - Bot Management Deep-Dive
3. **adaptive-protection.md** - Adaptive Protection Tuning

## 执行步骤
1. 先查看 `/Users/bohaiqing/opensource/git/gcp-skills/gcp-bigquery-ops/references/advanced/` 下现有文档格式
2. 按该格式创建上述文档，每个至少50行
3. 更新 `/Users/bohaiqing/opensource/git/gcp-skills/TODO.md` 把这些任务的 Status 从 ⬜ 改为 ✅

完成后输出：创建的文件列表

## Acceptance Contract
Acceptance level: checked
Completion is not accepted from prose alone. End with a structured acceptance report.

Criteria:
- criterion-1: Implement the requested change without widening scope

Required evidence: changed-files, tests-added, commands-run, residual-risks, no-staged-files

Finish with a fenced JSON block tagged `acceptance-report` in this shape:
Use empty arrays when no items apply; array fields contain strings unless object entries are shown.
`criteriaSatisfied[].status` must be exactly one of: satisfied, not-satisfied, not-applicable.
`commandsRun[].result` must be exactly one of: passed, failed, not-run.
`manualNotes` and `notes` are optional strings; an empty string means no note and does not satisfy `manual-notes` evidence.
```acceptance-report
{
  "criteriaSatisfied": [
    {
      "id": "criterion-1",
      "status": "satisfied",
      "evidence": "specific proof"
    }
  ],
  "changedFiles": [
    "src/file.ts"
  ],
  "testsAddedOrUpdated": [
    "test/file.test.ts"
  ],
  "commandsRun": [
    {
      "command": "command",
      "result": "passed",
      "summary": "short result"
    }
  ],
  "validationOutput": [
    "validation output or concise summary"
  ],
  "residualRisks": [
    "none"
  ],
  "noStagedFiles": true,
  "diffSummary": "short description of the diff",
  "reviewFindings": [
    "blocker: file.ts:12 - issue found, or no blockers"
  ],
  "manualNotes": "anything else the parent should know"
}
```