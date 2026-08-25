# 官方组件部署策略：不是全量堆叠，而是分阶段证明

结论：**全部部署当然最完整，但复赛/决赛前不一定最优。** 推荐按“最小闭环 → 真实协作流 → 治理与观测 → 规模化数据层”的顺序推进。

## 全量部署的成本

| 组件 | 部署复杂度 | 最容易卡的点 | 是否建议复赛前强接 |
|---|---:|---|---|
| AgentTeams | 高 | Docker/K8s、Matrix、对象存储、模型凭证 | 不建议，放决赛增强 |
| 云 Skills | 中 | 账号鉴权、RAM 权限、官方 Skill 可用性 | 文档映射优先 |
| Nacos | 中 | 配置模型、命名空间、权限和变更审计 | 可做轻量 demo，但非必须 |
| Higress | 中高 | 网关路由、鉴权、模型/工具代理、Trace 注入 | 决赛前可重点接 |
| PolarDB for PostgreSQL | 中 | 云资源、表结构、pgvector、权限边界 | 可用本地 PostgreSQL 替代验证 |
| UnifiedModel | 中 | 实体建模与查询接口 | 文档和 object graph 先行 |
| RocketMQ | 中 | Topic、Consumer、幂等、重试 | 可用本地事件日志替代 |
| LoongSuite / AgentScope Studio / AgentLoop | 中 | Trace schema 对齐、上报凭证、评估面板 | 决赛前优先接 AgentLoop/Studio |

## 推荐部署顺序

### P0：当前复赛包，保持稳定

- Python 标准库 Demo。
- AgentTeams 风格入口。
- Repair Cockpit 在线 Demo。
- 7 个场景评测集。
- Trace、Log、Metrics、GitHub PR 草案、Evidence Passport。

目标：保证评委一定能跑。

### P1：真实研发协作流

优先做真实 GitHub Issue / PR / Checks 的最小闭环。

原因：这比全量部署 Nacos/Higress/RocketMQ 更能证明方向三“软件研发全流程协同”的商业价值。

需要：

- GitHub 账号权限或 token。
- 一个演示分支。
- 一个不会影响主项目的 demo PR。

### P2：网关与治理

接 Higress / Nacos 的轻量演示：

- Higress：把 LLM、Agent 服务、MCP 工具统一入口讲清楚。
- Nacos：管理 AgentSpec、SkillSpec、Prompt、风险阈值。

目标：回答“生产环境怎么治理、鉴权、路由、限流、回滚”。

### P3：数据层与观测

接 PolarDB / AgentLoop / AgentScope Studio：

- PolarDB：历史事故、Trace、Evidence Passport、Skill Candidate。
- AgentLoop/Studio：Agent 推理轨迹、成本、质量、失败分支。

目标：回答“如何持续优化质量、成本、可靠性”。

## 我的建议

如果时间紧，只做这三件最划算：

1. **保留当前稳定提交包**，不要让重组件破坏可运行性。
2. **补真实 GitHub PR 或手动可验证 PR 证据**，增强方向三真实性。
3. **准备 AgentTeams runtime 接入路线图**，诚实说明复赛是等价实现，决赛接真实 runtime。

这比临时全量部署 8 个组件更稳，也更符合“不是堆工具，而是讲清必要性、边界和迁移成本”的评审口径。
