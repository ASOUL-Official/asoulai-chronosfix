# ChronosFix 复赛评测报告

## 1. 自动化验证摘要

- 事故样例：INC-2026-0816-001 / 订单创建接口在午间流量下出现高失败率与长尾延迟
- Agent/Skill Trace Span：15
- 工具/Skill 成功率：100.0%
- 根因假设数：3
- 反事实实验数：3
- 故障基因变体数：8
- 补丁候选数：4
- 选中补丁最差失败率：6.2%
- 审批状态：approved

## 2. 复赛验收点覆盖

| 验收点 | 证据 |
|---|---|
| AgentTeams 编排 | `agentteams/chronosfix-team.yaml`、`agentteams-run.json` |
| 样例输入输出 | `scenarios/checkout-timeout/scenario.json`、`proof-bundle.json` |
| 日志与 Trace | `run-log.jsonl`、`trace.jsonl` |
| Metrics | `engineering-metrics.json` |
| 风险审批 | `RiskGate` Span 与 evidence passport 风险声明 |
| 回滚审计 | selected patch rollback contract 与 proof-report |
| Skill 复用 | `SkillForge` 输出 3 个 Skill Candidate |

## 3. 失败处理分支

运行 `python demo.py --output output/no-approval` 时不传 `--approve`，RiskGate 会返回 `blocked-awaiting-human`，证明中风险补丁不会无人值守发布。

## 4. 开放 / 开源复现

项目使用 Python 标准库实现核心闭环，Apache-2.0 协议开放，评委可用 README 中的一键命令复现实验。
