# AsoulAI ChronosFix（A-CFX）复赛 PPT 大纲

本版 PPT/PDF 共 19 页，按最新版复赛要求重做：统一使用“Proof-Carrying Software Change Infra（带证明的软件变更基础设施）”作为底层逻辑，突出 Demo 可运行性、AgentTeams 工程实现、样例输入输出、日志/Trace/指标/评测、官方 Infra 映射、权限审批、失败处理、回滚审计、开放计划和商业价值。

## 1. 封面

- 队伍：AsoulAI。
- 作品：AsoulAI ChronosFix（A-CFX）。
- 方向三：软件研发全流程协同。
- 复赛定位：Demo 实现与工程验证。

## 2. 底层逻辑

- A-CFX 不是自动修 Bug，而是带证明的软件变更基础设施。
- 事故证据 → 反事实证明根因 → 缺陷基因验证补丁 → RiskGate 审批 → GitHub PR / 证据护照 → Skill / 故障资产沉淀。

## 3. 场景闭环

- 一次订单故障被转化为 PR 证据护照、缺陷基因包、可复用 Skill 三类研发质量资产。
- 强调“先证明根因，再交付补丁”。

## 4. 完整场景链路

- 输入：Issue、Trace、配置、Git、合成订单数据。
- 执行：多 Agent 协作、反事实实验、补丁竞赛、RiskGate。
- 输出：proof-report、proof-bundle、Trace、Metrics、审计记录。

## 5. AgentTeams 映射

- 以 AgentTeams / Hiclaw 为协同设计基点。
- 逐项说明角色编排、任务拆解、上下文传递、协同执行和状态追踪。

## 6. Agent 与 Skill 设计

- Incident Analyst、Causal Lab、Patch Strategist、RiskGate。
- Skill 作为可复用工程动作，Agent 负责判断、编排和证据解释。

## 7. 样例输入输出

- 给出 incident_id、故障症状、可疑变更和审批输入。
- 给出 root cause、patch、status、evidence 输出。

## 8. 创新点一：反事实根因证明

- 平行版本撤销可疑变更并重放事故。
- 用因果证据替代日志猜测。

## 9. 创新点二：缺陷基因与补丁竞赛

- 一次事故繁殖为一族同源变体。
- 多个补丁候选按通过率、风险和成本竞争。

## 10. 创新点三：RiskGate 与证据护照

- 高风险写操作不越权。
- 补丁附带因果、验证、风险、回滚和缺口声明。

## 11. 日志 / Trace / Metrics

- 展示 trace.jsonl、run-log.jsonl、engineering-metrics.json、evaluation-report.md。
- 强调自动化测试、Demo 与 AgentTeams 入口可重放。

## 12. 官方 Infra 映射

- AgentTeams、云 Skills、Nacos、Higress、PolarDB、UnifiedModel、RocketMQ、AgentLoop。
- 说明不堆叠工具，而是讲清必要性、接口契约、权限边界和替换成本。

## 13. 云 Skills / Nacos / Higress

- 云 Skills：鉴权、编排、端到端体验。
- Nacos：Agent、Skill、Prompt、配置治理。
- Higress：统一入口、鉴权、路由、限流、Trace 注入。

## 14. PolarDB / UnifiedModel / RAG

- PolarDB for PostgreSQL：向量、长记忆、Trace、审计。
- UnifiedModel：统一事故、AgentRun、SkillCall、证据护照、补丁候选实体。
- RAG：历史事故、Runbook、相似故障基因检索。

## 15. RocketMQ / 可观测闭环

- RocketMQ 事件模型：incident.created、hypothesis.ready、riskgate.waiting 等。
- LoongSuite、AgentScope Studio 或 AgentLoop 用于 Trace、评估、成本与质量闭环。

## 16. 仓库可复现路径

- 自动化测试。
- 核心 Demo。
- AgentTeams 风格入口。
- 无审批失败处理分支。

## 17. 商业价值

- 面向中大型研发组织、云厂商 / DevOps 平台、生态市场。
- 收费形态：SaaS、私有化、云市场插件、Skill 市场、审计合规模块。

## 18. 开放计划与下一步

- 已开放核心代码、AgentTeams 配置、Skill 规格、样例证据。
- 合规边界：Apache-2.0、合成数据、当前不调用商业 API。
- 决赛增强：真实 Git/CI/Nacos 接入、历史事故 RAG、AgentLoop 观测评估。

## 19. 结束页

- 总结：让软件修复从经验猜测升级为可证明、可审批、可回放、可复用的软件变更基础设施。
