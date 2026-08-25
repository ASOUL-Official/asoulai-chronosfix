# 赛题要求对照矩阵

| 赛题要求 | ChronosFix 对应设计 | 复赛证据 |
|---|---|---|
| 对齐官方参考 Baseline | 官方未提供代码仓库型 baseline；本方案以 OpsPilot Zero 示例为参考基线，对齐 AgentTeams、7 职能 Agent、Skill、MCP/适配器、Trace、审计和 Mock Demo 边界 | `docs/official-baseline.md` |
| 真实企业场景 | 软件研发全流程中的线上故障定位、根因验证、补丁生成、发布审批、回滚与复盘 | `scenarios/checkout-timeout/scenario.json` |
| 商业价值与行业复制 | 将事故复盘沉淀为故障基因包、证据护照模板和可复用 Skill，可服务研发组织、云厂商、DevOps 平台和高审计行业 | `docs/business-value.md` |
| 底层逻辑清晰 | 以带证明的软件变更链统一事故证据、反事实根因、缺陷基因、RiskGate、GitHub PR、证据护照和 Skill 沉淀 | `docs/proof-carrying-change.md` |
| 至少 3 个不同职能 Agent | 7 个 Agent：Commander、Timeline、Hypothesis、Universe、Patch、Verifier、Auditor | `docs/agent-identity.md` |
| AgentTeams 为协同基座 | Manager-Workers、共享 Incident State、透明协作房间、人类审批、Worker Skill 分工 | `agentteams/chronosfix-team.yaml` |
| 多 Agent 闭环 | 证据输入、任务拆解、上下文传递、工具调用、反事实实验、补丁竞赛、风险审批、证据沉淀、Skill 沉淀 | `evidence/trace.jsonl` |
| Skill 必选 | 9 个核心 Skill：EvidenceFusion、ChangeTimeline、CounterfactualReplay、FaultGenome、PatchTournament、RiskGate、EvidencePassport、SkillForge、ProofReport | `docs/skill-specs.md` |
| MCP 或等价契约 | 当前使用本地适配器；生产迁移为 Git/CI/日志/配置中心/工单 MCP Server | `docs/architecture.md` |
| RAG/上下文增强 | 当前实现 Incident State、证据索引、Trace 回放；后续接入历史事故、Runbook 与代码知识库检索 | `evidence/proof-bundle.json` |
| 可观测性 | 每个 Agent/Skill 调用记录 trace_id、span_id、status 和 payload | `evidence/trace.jsonl` |
| 安全边界 | 中风险补丁需要人工审批；所有变更必须带回滚策略和审计记录 | `src/chronosfix/skills/risk_gate.py` |
| 开放/开源 | 开放核心代码、Skill 规格、MCP Schema、样例故障和评测脚本 | `docs/open-source-compliance.md` |
| 复赛工程验证 | 提供 AgentTeams 风格入口、日志、Trace、Metrics、评测报告、部署验证说明和 Demo 视频脚本 | `agentteams/run_chronosfix_team.py`、`docs/semifinal-guide-matrix.md` |
| 官方推荐 Infra 映射 | 映射 AgentTeams、云 Skills、Nacos、Higress、PolarDB、UnifiedModel、RocketMQ、LoongSuite/AgentScope/AgentLoop | `docs/official-infra-mapping.md` |

## 创新点与完整度增强

| 创新点 | 解决的问题 | 为什么比普通多 Agent 更强 | 可验证产物 |
|---|---|---|---|
| 故障时间机器 | AI 只看日志容易猜错根因 | 用反事实撤销实验把“相关性”变成“因果证据” | `CounterfactualReplay`、`proof-bundle.json` |
| 缺陷基因实验室 | 补丁只修单个样例，容易回归 | 从一个事故繁殖出 8 个同源变体，逼补丁通过对抗测试 | `FaultGenome`、补丁竞赛结果 |
| PR 证据护照 | AI 参与的修复缺少发布可信度 | 补丁必须携带需求、因果、验证、风险、回滚、缺口声明，并进入 PR checks | `EvidencePassport`、`proof-report.md`、`github-pr.md` |
| Skill 自进化工坊 | 事故经验复盘后沉睡在文档里 | 自动蒸馏成下次可复用 Skill 候选，形成组织记忆 | `SkillForge`、Skill 候选清单 |
| 研发质量资产交易所 | 事故处理通常只是一次性成本 | 将故障基因、证据护照和 Skill 变成可复用、可分发、可商业化资产 | `docs/business-value.md`、Repair Cockpit 商业飞轮 |

## 评分维度覆盖

| 评分维度 | 权重 | ChronosFix 设计重点 |
|---|---:|---|
| 场景价值与行业可复制性 | 25% | 面向所有拥有线上服务、代码仓库、CI 和配置中心的研发组织，可复制到微服务、移动端、数据平台和基础设施项目；商业上可作为 SaaS、私有化、云市场插件和 Skill/故障基因市场 |
| 多 Agent 协同与自主闭环能力 | 25% | 多假设竞争、反事实实验、故障基因繁殖、补丁竞赛和审批门禁天然需要多 Agent 协作 |
| Skill 工程体系与生态复用 | 25% | 每个能力沉淀为可复用 Skill；事故结束后再生成 Skill 候选，形成“用一次，强一次”的自进化机制 |
| 工程落地、运行验证与安全可审计 | 20% | Demo 已可运行，输出 Trace、指标、证据护照、证明报告和审批事件 |
| 开放/开源贡献 | 5% | 计划开源核心框架、样例数据、Skill 规格、MCP 适配器模板和评测脚本 |
