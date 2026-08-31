# GitHub Issue / PR 草案链路

ChronosFix 将事故证据、选中补丁、回滚和门禁结果转换为 GitHub 风格的草案。默认链路仍是离线 local-draft；只有显式传入 `--write-github` 且提供令牌时，才会发布一个只包含证据文件的 external-evidence-draft Draft PR。

## 1. 本地产物

运行：

```powershell
python demo.py --approve --approver "AsoulAI Release Owner" --approval-reason "Semifinal evidence review" --output evidence
```

生成：

| 文件 | 内容 |
|---|---|
| `github-issue.md/json` | 从 scenario、事故事件和影响信息生成的 Issue 草案 |
| `github-pr.md/json` | 根因、实际 changes、rollback、门禁和证据护照 |
| `github-pr-diff.patch` | 从 selected patch 的 changes/rollback changes 派生 |
| `github-pr-checks.json` | 本地执行检查、RiskGate、具名审批结果 |
| `github-review-audit.jsonl` | local-draft 审计事件 |

当前实现不使用固定 checkout 场景或固定补丁：分支、场景路径、changes 和 rollback 均从本次 Incident State 派生。缺少 scenario、selected patch 或执行检查时，PR 保持 `draft/pending`；失败检查或失败门禁使其保持 `draft/blocked`。

## 2. 受控外部 Draft PR

先完成本地运行并通过 RiskGate：

```powershell
python demo.py --approve --approver "AsoulAI Release Owner" --approval-reason "Semifinal evidence review" --output evidence
```

查看计划（不联网）：

```powershell
python scripts/github_draft_pr.py --output evidence
```

确认令牌只存在于本机环境变量后，显式开启写入：

```powershell
$env:GITHUB_TOKEN = "<fine-grained-token-or-github-app-token>"
python scripts/github_draft_pr.py --output evidence --write-github
```

适配器只会：

- 以 `chronosfix/...-external-<run_id>` 创建隔离分支；
- 提交 `.chronosfix/runs/<run_id>/` 下的证据文件；
- 创建 `draft=true` 的 PR；
- 将 PR URL、commit SHA、GitHub request ID 写入 `github-write-result.json` 和 `run-manifest.json`。

适配器不会写 `main`、修改业务源码、创建 Check Run、合并 PR 或发布生产。重复执行同一 `run_id` 会复用已存在的开放 Draft PR。令牌永远不会写入结果文件。

## 3. Checks 的准确含义

`github-pr-checks.json` 是本地检查汇总，检查项必须携带实际执行证据（例如 exit code 或 run ID），不能只写 `success` 字符串。它尚未通过 GitHub Checks API 创建在线 Check Run，也没有虚构 commit SHA。

## 4. RiskGate 与审批

PR readiness 同时受以下条件约束：

- `quality_gate=passed`；
- 中高风险具名审批有效；
- selected patch 与 diff 一致；
- rollback changes 存在并验证；
- required checks 有真实本地执行结果。

人工只能批准风险，不能把失败质量改成通过。

## 5. 公开 GitHub 边界

公开协作证据：

- [Issue #1](https://github.com/ASOUL-Official/asoulai-chronosfix/issues/1)
- [PR #2](https://github.com/ASOUL-Official/asoulai-chronosfix/pull/2)
- 分支：`demo/live-proof-carrying-pr-20260825`
- commit：`3b9d3dafdae7b9990430423f7134d2644c8a2c24`

PR #2 是 **documentation-only**。它证明团队能把证据护照说明带入公开仓库的 Issue/PR 评审流程，但不证明：

- 程序已经调用 GitHub API；
- Agent 自动提交了真实修复代码；
- GitHub Actions 已运行修复测试；
- 已创建真实 Check Run；
- PR 已合并或发布生产。

## 6. 真实迁移所需权限

| 动作 | 候选权限 | 默认策略 |
|---|---|---|
| 创建 Issue | `issues:write` | 只写事故协作说明 |
| 创建修复分支 | `contents:write` | 仅隔离分支 |
| 创建 PR | `pull_requests:write` | 默认 draft |
| 写 Check Run | `checks:write` | 只能回传真实 CI 结果 |
| 合并 | 不授予 Agent | 人工与仓库保护规则决定 |
| 生产发布 | 不属于 GitHub draft Adapter | 进入独立发布审批 |

真实接入后需要保存 API request ID、repository、branch、commit SHA、Check Run URL 和权限主体，并纳入 run manifest。
