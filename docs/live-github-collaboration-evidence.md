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
