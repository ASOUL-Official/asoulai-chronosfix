# 官方参考 Baseline 对照

> 结论：官方规范文件未提供必须继承的代码仓库型 baseline；在《新智基座 Agent Infra 赛道》说明中，官方给出了作品示例 Demo：**OpsPilot Zero——面向千行百业云上与自建 IDC 业务故障的零人工运维多 Agent 排查与自愈系统**。ChronosFix 将其作为“官方参考 Baseline”，并在方向三“软件研发全流程协同”上做场景迁移与创新增强。

## 官方参考 Baseline：OpsPilot Zero

官方示例强调的基线能力包括：

- 以 AgentTeams 作为多 Agent 协同编排层。
- 用 7 个职能 Agent 覆盖告警归并、任务拆解、根因候选、数据建议、计划、执行、验证。
- 将专家经验封装为 Skill，包括告警归并、Runbook/RAG、根因分析、风险控制、恢复验证、复盘沉淀等。
- 通过 MCP/适配器接入 Nacos、K8s、网关、工单、知识库等外部系统。
- 使用 Incident State、AgentLoop Trace、审计记录和安全边界保证可回放、可验证、可审计。
- 初赛边界以 Mock 数据、工具接口、核心 Skill Schema、根因/计划/验证报告为可信 Demo，复赛再接入真实系统。

## ChronosFix 对齐官方 Baseline 的部分

| 官方参考 Baseline 能力 | ChronosFix 对齐方式 | 证据位置 |
|---|---|---|
| AgentTeams 编排层 | 提供 1 Manager、8 Worker、1 Team、1 Human 的 v1beta1 资源声明，明确共享状态与升级策略 | `agentteams/runtime/chronosfix-resources.yaml` |
| 8 个 Worker 职能 | Commander、Timeline、Hypothesis、Universe、Patch、Verifier、Auditor、Curator 覆盖诊断、验证、发布和沉淀 | `docs/agent-identity.md` |
| Skill 工程化 | 9 个业务 Skill + 1 个官方 SLS Skill Adapter，带输入输出、安全边界、失败处理和复用价值 | `docs/skill-specs.md` |
| MCP/适配器契约 | 当前实现本地适配器与 SLS 只读 dry-run；Git、CI、配置中心、工单保留等价契约和迁移边界 | `docs/architecture.md` |
| 可观测与审计 | 输出 18 段 Trace、proof-bundle、proof-report、PR 草案、Evidence Passport 和 Run Manifest | `evidence/trace.jsonl` |
| 安全边界 | RiskGate 阻断中高风险无人值守发布，保留回滚与人工审批 | `docs/safety-and-audit.md` |
| 可演示初赛闭环 | 本地 Demo + Repair Cockpit + PPT + 评审入口说明 | `demo.py`、`repair-cockpit/index.html` |

## ChronosFix 在官方 Baseline 上的增强

| 增强点 | 相比官方示例的差异化价值 |
|---|---|
| 软件研发全流程协同 | 从运维故障自愈迁移到 Issue、Git、依赖、配置、CI、发布审批和复盘的研发闭环，更贴合方向三。 |
| 带证明的软件变更链 | 不只给 RCA 结论，而是把事故证据、反事实根因、缺陷基因验证、RiskGate、GitHub PR / 证据护照和 Skill 沉淀串成可审查链路。 |
| 故障时间机器 | 用“撤销可疑变更—重放事故—比较指标”的反事实实验把相关性变成因果证据。 |
| 缺陷基因实验室 | 从一个已证明故障繁殖 8 个同源变体，避免补丁只修单一样例，提升回归防护和评测价值。 |
| PR 证据护照 | 每个补丁必须携带需求、因果、验证、风险、回滚和缺口声明，能进入 GitHub PR、变更单和发布审批。 |
| 研发质量资产平台 | 把事故复盘沉淀为故障基因包、证据护照模板、可评测 Skill，形成可复用、可分发、可商业化的资产飞轮。 |

## 放入提交物的方式

- 复赛 PPT 用同一闭环展示对官方示例能力的继承，并把重点落到方向三的 PR 与变更治理。
- Repair Cockpit 直接展示 AgentTeams 边界、因果证明、三态门禁和评测证据，不声称真实 Runtime 已运行。
- README、评审入口和赛题要求矩阵保留官方参考 Baseline 的可追溯说明。

## 来源

- 本地官方规范 PDF：`6e21b053-f18b-4857-83e2-835bd96d5434.pdf`，第 22-35 页“作品示例 DEMO / OpsPilot Zero”。
- 本地官方模板 PDF：`2e567d1a-99c1-45ce-8a0f-3d36d11f3314.pdf`，用于初赛 PPT 内容框架。
