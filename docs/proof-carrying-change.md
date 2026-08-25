# Proof-Carrying Software Change Infra：A-CFX 的底层逻辑

A-CFX 不是“自动修 Bug”的包装，也不是一个只做日志问答的 Debug Bot。它要解决的是企业软件研发里的真实断点：事故发生后，根因判断、补丁生成、验证、审批、PR、审计和复盘经常散落在不同工具里，导致 AI 即使给出一个看似合理的补丁，也很难被研发组织放心合并和复用。

因此 A-CFX 的底层逻辑是 **Proof-Carrying Software Change Infra（带证明的软件变更基础设施）**：任何由 Agent 参与的软件变更，都必须带着可回放证据进入研发协作流。

## 一条主链

```text
事故证据
  -> 反事实证明根因
  -> 缺陷基因验证补丁
  -> RiskGate 审批
  -> GitHub PR / 证据护照
  -> Skill / 故障资产沉淀
```

| 环节 | 解决的问题 | A-CFX 的实现 |
|---|---|---|
| 事故证据 | 日志、Trace、Git、配置、依赖和流量证据分散，无法形成共同事实 | EvidenceFusion 与 ChangeTimeline 把多源事实写入 Incident State |
| 反事实证明根因 | “时间上相关”经常被误认为“因果上成立” | CounterfactualReplay 在平行版本中撤销可疑变更并重放事故 |
| 缺陷基因验证补丁 | 补丁只修原始样例，容易二次事故 | FaultGenome 生成同源变体，PatchTournament 用均值、最差场景、风险和成本排序 |
| RiskGate 审批 | 自动化系统越权发布，高风险动作不可控 | RiskGate 对中高风险动作阻断，保留 approved / blocked 状态和回滚点 |
| GitHub PR / 证据护照 | 代码 diff 缺少因果、验证、风险和回滚证据，难以进入企业审批 | EvidencePassport 与 GitHub Issue/PR 模拟链路输出 PR 正文、checks、diff 和审计事件 |
| Skill / 故障资产沉淀 | 事故复盘停留在文档里，无法复用 | SkillForge 产出可评测 Skill 候选、故障基因包和证据模板 |

## 为什么这个逻辑更有创意

大多数软件修复 Agent 的默认叙事是“发现问题 → 生成补丁”。A-CFX 把重点从“补丁生成”前移到“因果证明”，后移到“审批、审计和资产沉淀”。这让项目从一个单点 Agent，升级为一个面向组织研发流程的 Agent Infra。

它的创意不是多加几个工具名，而是把每个工具放到证明链里的固定位置：

- AgentTeams 负责任务拆解、角色编排、上下文传递和状态追踪。
- 云 Skills / MCP 负责把云资源、Git、CI、日志、配置中心和工单系统变成可治理动作。
- Nacos 负责 Agent、Skill、Prompt、配置和服务发现治理。
- Higress 负责统一入口、鉴权、路由、限流和观测。
- PolarDB for PostgreSQL 与 UnifiedModel 负责长记忆、RAG、向量索引、审计日志和实体关系查询。
- RocketMQ 负责反事实实验、补丁验证、审批等待、证据归档等异步事件。
- LoongSuite / AgentScope Studio / AgentLoop 负责 Trace、Log、Metrics、评测、成本和可靠性闭环。

## 为什么商业价值更强

企业不会因为一个 Agent “可能会修代码”就让它直接改生产系统，但会为“让每个 PR 自动带上可审查证据”付费。A-CFX 的商业落点因此更贴近真实采购：

1. **研发组织**：把事故处理、PR 审查、发布审批和复盘打通，减少 MTTR、误修复和二次事故。
2. **云厂商 / DevOps 平台**：作为 APM、CI/CD、配置中心、工单系统和 AI 网关的增值模块。
3. **高审计行业**：把 AI 修复输出变成可审批、可回滚、可追责的合规材料。
4. **生态市场**：故障基因包、证据护照模板和可评测 Skill 可以开源共建，也可以行业化商业分发。

一句话总结：A-CFX 卖的不是“AI 帮你改一行代码”，而是“每次高风险软件变更都能自带证据、审批、回滚和复用资产”。
