# 真实 GitHub Issue / PR 协作证据

本项目已经补充一条真实 GitHub 协作链路，用来证明 A-CFX 的本地 GitHub Issue / PR 模拟产物可以迁移到公开仓库的真实研发流程。

## Live artifacts

| 类型 | 链接 | 状态 |
|---|---|---|
| GitHub Issue | https://github.com/ASOUL-Official/asoulai-chronosfix/issues/1 | Open |
| GitHub PR | https://github.com/ASOUL-Official/asoulai-chronosfix/pull/2 | Open |
| Demo branch | `demo/live-proof-carrying-pr-20260825` | Created from `main` |
| PR commit | `3b9d3dafdae7b9990430423f7134d2644c8a2c24` | Documentation-only |

## 这条 PR 证明什么

它不是为了改变核心代码，而是作为一个低风险、可检查的 live artifact，证明 A-CFX 能把下面这条链落到真实 GitHub 协作流：

```text
事故证据
  -> 反事实证明根因
  -> 缺陷基因验证补丁
  -> RiskGate 审批
  -> GitHub PR / 证据护照
  -> Skill / 故障资产沉淀
```

## PR 证据护照

| 声明 | 内容 |
|---|---|
| 需求声明 | 复赛/决赛需要证明本地模拟的 Issue / PR 链路可以进入真实研发协作流 |
| 因果声明 | 本地 `github-issue.md`、`github-pr.md`、checks、diff、audit 可映射为真实 GitHub Issue / PR |
| 验证声明 | 已创建公开 Issue #1、PR #2、demo 分支和 documentation-only commit |
| 风险声明 | PR 只新增文档，不修改运行时代码、测试、部署配置或提交成品 |
| 回滚声明 | 可关闭 PR、删除分支，或在合并后 revert 文档 |
| 审计声明 | Issue / PR 的创建时间、作者、分支、commit、正文均由 GitHub 留痕 |

## 答辩话术

复赛工程包同时提供两层证据：第一层是本地可复现的 GitHub Issue / PR 模拟产物，便于无账号运行；第二层是公开仓库中的真实 Issue #1 和 PR #2，证明这套证据护照可以进入标准代码评审流程。决赛阶段只需要把当前本地 `github_flow.py` 从模拟写文件替换为 GitHub API 写入，即可形成真实端到端闭环。
