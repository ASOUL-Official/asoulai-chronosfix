# Agent Identity 清单

| Agent | Role | Capabilities | Inputs | Outputs | Dependencies | Decision Boundary | Trace |
|---|---|---|---|---|---|---|---|
| Incident Commander | 任务指挥与状态编排 | 拆解任务、调度 Agent、合并结论、升级人工审批、触发 SkillForge | Issue、告警、证据包、运行状态 | 任务计划、最终结论、审批请求、Skill 候选 | 全部 Agent 与 Incident State | 只读分析可自主调度；中高风险执行需人工确认 | 记录任务状态、关键决策和最终报告 |
| Timeline Analyst | 时间线分析 | 融合 Git、日志、Trace、配置和流量事件，按时间排序 | 多源事件 | 事件时间线、证据索引 | EvidenceFusion、ChangeTimeline | 不直接修改代码或配置 | 记录证据来源、缺口和事件排序 |
| Hypothesis Scientist | 假设生成 | 生成可证伪根因假设和最小干预方案 | 时间线、故障指标、历史上下文 | 假设列表、干预契约 | Incident State | 只能提出实验，不直接判定根因 | 记录假设、依据和所需证据 |
| Universe Builder | 平行版本实验 | 创建反事实状态，撤销代码/依赖/配置变化并重放故障；从主因繁殖故障基因变体 | 假设契约、基线状态、种子场景 | 实验结果、因果置信度、故障变体族 | CounterfactualReplay、FaultGenome | 只在隔离环境实验，不触碰生产 | 记录每个平行版本、故障变体的输入输出和分类 |
| Patch Engineer | 补丁生成 | 生成候选补丁、成本、风险和回滚策略 | 已证明根因、系统约束 | 补丁候选、回滚方案 | PatchTournament | 可生成方案；执行需门禁 | 记录候选补丁和取舍 |
| Adversarial Verifier | 对抗验证 | 在故障基因变体上评测补丁，按正确性、风险、成本排序 | 补丁候选、故障变体 | 排名、失败率、P99、健康状态 | PatchTournament | 可淘汰候选补丁；不能绕过审批 | 记录每个补丁在每个场景的结果 |
| Release Auditor | 发布审计 | 风险分级、人工审批、证据护照、回滚检查、审计归档 | 选中补丁、风险、验证结果 | 审批结果、证据护照、审计记录、发布建议 | RiskGate、EvidencePassport、ProofReport | 中高风险必须人工确认 | 记录审批人、时间、风险等级、回滚状态和证据声明 |

## 协作原则

- 每个 Agent 只对自己的专业边界负责，最终状态由 Incident Commander 汇总。
- 每个关键结论必须落入 Trace，方便复盘。
- 每个候选补丁必须经过 Verifier 和 Auditor，不能由 Patch Engineer 直接发布。
- SkillForge 只生成候选 Skill，不能绕过人工评审自动注册新能力。
