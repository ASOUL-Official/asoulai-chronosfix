# GitHub Issue / PR 模拟链路

A-CFX 复赛包新增一条可复现的研发协作链路：把事故证据转成 GitHub Issue，把选中补丁转成 PR 草案，并附带补丁 diff、检查结果、RiskGate 状态和审计日志。当前本地实现以本仓库 evidence 文件形式模拟真实接入后的 API 输出；在用户授权后，项目也补充了真实 GitHub Issue / PR live artifact，用于证明该链路可以进入公开仓库协作流。

## Live GitHub 证据

- Issue #1：https://github.com/ASOUL-Official/asoulai-chronosfix/issues/1
- PR #2：https://github.com/ASOUL-Official/asoulai-chronosfix/pull/2
- Demo branch：`demo/live-proof-carrying-pr-20260825`

这条 PR 是 documentation-only，不修改运行时代码，作为低风险 live artifact 保留给评委检查。完整说明见 `docs/live-github-collaboration-evidence.md`。

## 1. 链路目标

复赛评审常见疑问是：多 Agent 找到根因后，如何进入真实研发流程？本链路回答这个问题：

```text
Incident Evidence
  -> GitHub Issue #42
  -> AgentTeams 分析与反事实证明
  -> Patch Tournament 选出 P-RESTORE-POOL
  -> GitHub PR #43 草案
  -> PR checks / RiskGate / Evidence Passport
  -> 人工审批、回滚契约、审计事件
```

## 2. 生成方式

运行：

```powershell
python demo.py --approve --output evidence
```

会生成以下文件：

| 文件 | 作用 |
|---|---|
| `evidence/github-issue.md` | 面向研发协作的 Issue 正文 |
| `evidence/github-issue.json` | Issue API 等价结构 |
| `evidence/github-pr.md` | PR 描述，包含根因证明、验证结果、回滚策略 |
| `evidence/github-pr.json` | PR API 等价结构 |
| `evidence/github-pr-diff.patch` | 模拟补丁 diff，包含配置、测试和证据护照文件 |
| `evidence/github-pr-checks.json` | 单测、反事实回放、故障基因、RiskGate、证据护照检查 |
| `evidence/github-review-audit.jsonl` | Issue、分支、PR、RiskGate 审计事件 |

## 3. 权限边界

| 动作 | 当前复赛包 | 真实接入时权限 |
|---|---|---|
| 创建 Issue | 本地生成 `github-issue.*` | `issues:write`，只写事故协作说明 |
| 创建分支 | 本地生成分支名和 diff | `contents:write` 到隔离修复分支 |
| 创建 PR | 本地生成 `github-pr.*` | `pull_requests:write`，默认 draft |
| 写检查结果 | 本地生成 `github-pr-checks.json` | `checks:write`，不绕过 CI |
| 合并 PR | 当前不执行 | 必须人工审批、检查通过、回滚契约存在 |
| 生产发布 | 当前不执行 | 交给发布系统和人工审批链路 |

## 4. 和 AgentTeams / Trace 的关系

新链路会出现在 `trace.jsonl` 与 `agentteams-run.json` 中：

- Agent：`patch-engineer`
- Skill：`GitHubIssuePrFlow`
- 写入状态：`github_issue`、`github_pr`、`pr_checks`、`review_audit`
- 权限范围：`dev-collaboration-write-draft`

这说明 A-CFX 不是在证明报告之后“手工编 PR”，而是把研发协作输出纳入同一条 AgentTeams 可观测链路。

## 5. 可迁移到真实 GitHub 的接口

当前文件可直接映射到 GitHub API：

| 本地文件 | GitHub API |
|---|---|
| `github-issue.json` | `POST /repos/{owner}/{repo}/issues` |
| `github-pr.json` | `POST /repos/{owner}/{repo}/pulls` |
| `github-pr-diff.patch` | `git apply` 或 Contents API / Git Data API |
| `github-pr-checks.json` | `POST /repos/{owner}/{repo}/check-runs` |
| `github-review-audit.jsonl` | 审计日志 / SIEM / AgentLoop |

真实接入成本主要在鉴权、分支写入、检查回传和合并策略绑定；核心数据结构已经在复赛包中给出。
