# ChronosFix 复赛评测报告

## 1. 自动化验证摘要

- 事故样例：INC-2026-0816-001 / 订单创建接口在午间流量下出现高失败率与长尾延迟
- Run ID：run-cd233db619aa4b7fa4f6248727b0f874
- Agent/Skill Trace Span：18
- 流水线步骤完成率（由 Trace 推导）：100.0%
- 根因假设数：3
- 反事实实验数：3
- 故障基因变体数：8
- 补丁候选数：4
- 选中补丁最差失败率：6.2%
- 质量门禁：passed
- 发布决策：approved
- 回滚验证：通过

## 2. 复赛验收点覆盖

| 验收点 | 证据 |
|---|---|
| AgentTeams 等价编排证据 | `agentteams/chronosfix-team.yaml`、`agentteams-run.json`（非 Controller Runtime 证据） |
| 样例输入输出 | `scenarios/checkout-timeout/scenario.json`、`proof-bundle.json` |
| 日志与 Trace | `run-log.jsonl`、`trace.jsonl` |
| Metrics | `engineering-metrics.json` |
| 风险审批 | `RiskGate` Span 与 evidence passport 风险声明 |
| 回滚审计 | machine-readable rollback_changes、回滚验证结果与 proof-report |
| GitHub Issue/PR 本地草案链路 | `github-issue.md`、`github-pr.md`、`github-pr-diff.patch`、`github-pr-checks.json`、`github-review-audit.jsonl` |
| 完整性绑定 | `run-manifest.json` 与 Evidence Passport SHA-256 摘要 |
| Skill 复用 | `SkillForge` 输出 3 个 Skill Candidate |
| 动态协同控制面 | `coordination.json`：任务图、state revision、证据驱动插入、Worker 重派、幂等去重、暂停/恢复 |

## 3. 失败处理分支

运行 `python demo.py --output output/no-approval` 时不传 `--approve`，健康但中风险的补丁会返回 `blocked-awaiting-human`。若任一强制变体、回滚或执行检查失败，则优先返回 `blocked-quality-gate`，人工不能覆盖质量失败。动态控制面会在同一次运行中注入一次 Worker 超时并重派，重复 evidence 事件去重，并记录 revision 绑定的暂停/恢复。

## 4. 开放 / 开源复现

项目使用 Python 标准库实现核心闭环，Apache-2.0 协议开放，评委可用 README 中的一键命令复现实验。
