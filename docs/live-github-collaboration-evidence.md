# GitHub Issue #1 / PR #2：documentation-only 证据

本项目保留一组公开 GitHub 协作对象，用于让评委核验仓库身份、Issue/PR 表达和 Evidence Passport 的迁移形式。

| 类型 | 链接/标识 | 边界 |
|---|---|---|
| Issue | https://github.com/ASOUL-Official/asoulai-chronosfix/issues/1 | 公开协作说明 |
| PR | https://github.com/ASOUL-Official/asoulai-chronosfix/pull/2 | documentation-only |
| Branch | `demo/live-proof-carrying-pr-20260825` | 从 main 创建 |
| Commit | `3b9d3dafdae7b9990430423f7134d2644c8a2c24` | 只修改文档 |

## 它能证明什么

- 团队控制并公开了目标仓库；
- Issue/PR 可以承载因果、验证、风险、回滚和审计说明；
- 本地 `github-*` 草案在结构上可以映射到公开协作对象；
- GitHub 自身保留作者、时间、分支、commit 和讨论记录。

## 它不能证明什么

- `github_flow.py` 已经调用 GitHub API；
- Agent 已自动生成并提交运行时代码修复；
- PR #2 的 diff 来自主场景 selected patch；
- GitHub Actions 已运行反事实、故障族或回滚检查；
- `github-pr-checks.json` 已写成在线 Check Run；
- 已完成合并、灰度或生产发布。

因此，提交材料统一称其为“documentation-only 迁移证据”，而不是“真实端到端自动修复”。

## 与本地证据的关系

本地流水线生成的 Issue/PR/diff/checks/audit 是每次运行派生的 local-draft；它们具有 scenario、selected patch、rollback、RiskGate 和 run ID。公开 Issue #1/PR #2 是另一层低风险人工创建证据，二者不能互相替代。

真实端到端接入需要新增 GitHub App/PAT 最小权限、真实修复分支、真实 CI、Check Run URL 和外部写入审计。

## PR #3：真实工程验收证据

为验证当前复赛增强，我们另建了真实工程分支和 PR：

| 类型 | 链接/标识 | 结果 |
|---|---|---|
| PR | https://github.com/ASOUL-Official/asoulai-chronosfix/pull/3 | 已合并 |
| Branch | `demo/live-engineering-gate-20260826` | 从复赛 main 创建 |
| Commit | `3821f7ac7289f7d990b9eb5f78f19f85c68bf5f4` | 一键验收器与 Schema 验证器 |
| Merge commit | `9d80acc38135644bbdf49253e4d1e34779c4bae1` | 已进入 main |

PR #3 的 GitHub Actions 在 Python 3.10、3.11、3.12 上全部通过，并上传 `chronosfix-semifinal-acceptance-*` Artifact。当前本地复赛验收器包含 14 项自动检查和 35 项关键断言：

- 57 项测试、严格 JSON/JSONL、公开 Draft 2020-12 Schema；
- AgentTeams v1beta1 清单（1 Manager、8 Worker、1 Team、1 Human）；
- 已审批分支 `approved` 与无人审批分支 `blocked-awaiting-human`；
- 12 场景、9/9 支持范围诊断、1/1 正确拒答、10/12 达成预期；
- 明确记录 AgentTeams Runtime 未执行、云 Skill 为 dry-run、评测数据为合成数据。

PR #3 证明真实 GitHub 分支、CI 和 Artifact 证据链已经跑通；它仍不等同于真实 AgentTeams Controller、真实云日志或生产发布执行。
