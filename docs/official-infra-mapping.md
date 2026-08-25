# 官方推荐 Agent Infra 映射

A-CFX 的原则不是堆叠工具，而是把“带证明的软件变更链”映射为可替换、可治理、可审计的 Agent Infra。当前复赛包采用本地确定性引擎交付可复现 Demo，同时给出迁移到官方推荐基础设施的接口边界。

统一主线：

```text
事故证据 -> 反事实证明根因 -> 缺陷基因验证补丁 -> RiskGate 审批 -> GitHub PR / 证据护照 -> Skill / 故障资产沉淀
```

参考链接：

- AgentTeams / Hiclaw：https://hiclaw.io/
- 阿里云云 Skills：https://skills.aliyun.com/
- Nacos：https://nacos.io/
- Higress：https://higress.io/
- PolarDB for PostgreSQL：https://openpolardb.com/home
- UnifiedModel：https://alibaba.github.io/UnifiedModel/
- RocketMQ：https://rocketmq.apache.ac.cn/
- LoongSuite：https://alibaba.github.io/loongsuite-go/
- AgentScope Studio：https://github.com/agentscope-ai/agentscope-studio
- AgentLoop：https://help.aliyun.com/zh/cms/cloudmonitor-2-0/agentloop-overview

## 总体映射

| 官方能力 | 在 A-CFX 中的职责 | 当前实现 | 复赛/决赛接入方式 | 可替换性与迁移成本 |
|---|---|---|---|---|
| AgentTeams（原 Hiclaw） | 多 Agent 角色编排、任务拆解、上下文共享、人类可见协作、状态追踪 | `agentteams/chronosfix-team.yaml` + `agentteams-run.json` | Manager=Incident Commander；Workers=7 个职能 Agent；Matrix Room=Repair Cockpit 证据房间 | 已按 Manager/Worker/Shared State 建模，迁移成本为协议适配 |
| 阿里云云 Skills 门户 | 云资源操作 Skill 的发现、安装、鉴权、HITL、安全边界 | 本地 9 个 Skill + 云 Skills 映射表 | 将 Nacos/Higress/PolarDB/RocketMQ/CloudMonitor 操作封装为云 Skills，风险动作走 HITL | 只替换 Skill 执行后端，输入输出 Schema 不变 |
| Nacos | Agent、Skill、Prompt、配置、服务发现和运行时治理中心 | 文档定义 registry 与 governance schema | 管理 AgentSpec、SkillSpec、PromptTemplate、ConfigPolicy、MCP Endpoint | 本地 JSON Registry 可迁移到 Nacos namespace/group/dataId |
| Higress | 模型、Agent 服务、MCP 工具、外部 API 的统一网关 | 等价 Tool Adapter 合约 | 统一鉴权、路由、限流、Fallback、Token 观测、MCP 代理 | 适配器从本地函数切换为 HTTP/MCP 网关调用 |
| PolarDB for PostgreSQL | 长记忆、RAG、向量索引、审计日志、Trace 存储 | `proof-bundle.json`、`trace.jsonl`、`engineering-metrics.json` | 表结构：incidents、evidence、traces、skills、passports；pgvector 存 embeddings | 文件存储到数据库，查询接口保持统一 |
| UnifiedModel | Issue、Commit、Trace、Config、Patch、Passport 的统一实体关系层 | `state_to_unified_model_entities()` 输出对象图草案 | 将 Incident→Evidence→Hypothesis→Patch→Skill 建成可查询 object graph | 不绑定单库，GraphStore Provider 可替换 |
| RocketMQ | Agent 间事件、异步实验、任务状态流转、可靠通知 | 本地同步流程 + `agentteams-run.json` 事件顺序 | Topic：incident.created、hypothesis.ready、experiment.done、riskgate.waiting、passport.ready | 同步函数改为事件发布/消费，业务 Schema 不变 |
| LoongSuite | 业务服务自动埋点与 OpenTelemetry 采集 | Demo 使用合成 Trace | 接入真实 Go 服务后自动采集 HTTP/DB/日志指标 | 仅影响采集侧，不改变 Agent 流程 |
| AgentScope Studio | 本地 Agent 调试、Trace 可视化、评估视图 | Repair Cockpit 可视化证据房间 | 将 trace/log/metrics 导入 Studio 进行开发调试与评估 | 可与 AgentLoop 并行或替换 |
| AgentLoop | Agent 全栈观测、审计、评估、实验和持续优化 | `trace.jsonl`、`run-log.jsonl`、`evaluation-report.md` | 上报 Agent/Skill/MCP/RAG/LLM Span、成本、质量评估、审批事件 | 遵循 Trace/Log/Metrics 结构，后端可替换 |

## AgentTeams 五点映射

| 指南核验点 | A-CFX 映射 |
|---|---|
| 角色编排 | Human=Release Owner；Manager=Incident Commander；Workers=Timeline/Hypothesis/Universe/Patch/Verifier/Auditor/Skill Curator |
| 任务拆解 | Commander 按 Evidence → Counterfactual Proof → Fault Genome → RiskGate → PR / Passport → SkillForge 拆解 |
| 上下文传递 | Incident State 作为共享状态；每个 Skill 只读或写入明确字段 |
| 协同执行 | 当前为确定性顺序执行，复赛接 RocketMQ 后可让 Hypothesis、Replay、Patch Scoring 并行 |
| 状态追踪 | trace_id/span_id、agent、skill、status、payload 写入 trace；agentteams-run 记录任务与状态 |

## 云 Skills 接入策略

| Skill 类别 | 当前本地 Skill | 云 Skills / 官方 Skill 映射 | 鉴权与风险 |
|---|---|---|---|
| 云资源查询 | EvidenceFusion、ChangeTimeline | SLS 查询、CloudMonitor、资源中心、Nacos 查询类 Skills | 只读 RAM Policy；结果脱敏 |
| 配置治理 | CounterfactualConfigReplay、RiskGate | Nacos 配置读取/回滚、Higress 路由/限流策略 Skills | 修改类动作必须 HITL 确认 |
| 数据与记忆 | ProofReport、EvidencePassport | PolarDB/OSS/日志服务写入 Skills | 写入证据库，禁止写生产配置 |
| 发布验证 | PatchTournament | CI/CD、测试平台、灰度验证 Skills | 触发测试不直发生产 |
| 资产沉淀 | SkillForge | 云 Skills 门户 Skill Forge / 私有 Skill Registry | 候选 Skill 需人工评审与回放评测 |

## Nacos 治理模型

| Registry 对象 | Nacos DataId 示例 | 内容 |
|---|---|---|
| AgentTeams Spec | `agentteams/chronosfix-team.yaml` | 角色、拓扑、共享状态、升级策略 |
| AgentSpec | `agents/release-auditor.yaml` | Agent 身份、可用 Skill、权限边界 |
| SkillSpec | `skills/riskgate.yaml` | 输入输出、调用条件、失败处理、版本 |
| PromptTemplate | `prompts/hypothesis-contract.md` | 假设生成与证据等级规范 |
| ConfigPolicy | `policies/config-change-risk.yaml` | 哪些配置变更需要审批、回滚点和白名单 |

## Higress 网关策略

| 策略 | A-CFX 设计 |
|---|---|
| 统一入口 | LLM、Agent 服务、MCP Server、云 Skills 全部经 Higress 暴露 |
| 鉴权 | Agent 只持有 consumer token；真实云凭证留在网关/平台侧 |
| 路由 | Git/CI/Log/Config/Ticket 按工具域路由；模型 API 按任务类型路由 |
| 限流 | 高成本反事实实验和 PatchTournament 设置并发上限 |
| Fallback | 模型调用失败时降级到规则评估；工具失败时进入证据缺口声明 |
| 观测 | 记录 Token、时延、失败率、工具命中率和审计事件 |

## PolarDB / UnifiedModel 数据层

| 数据对象 | 存储表/图节点 | 索引 |
|---|---|---|
| Incident | `incidents` / `Incident` | incident_id、service、time_window |
| Evidence | `evidence_items` / `ChangeEvent` | source、timestamp、embedding |
| Trace Span | `agent_traces` / `TraceSpan` | trace_id、span_id、agent、skill |
| Passport | `evidence_passports` / `EvidencePassport` | patch_id、approval、risk_level |
| Skill Candidate | `skill_candidates` / `Skill` | name、version、reuse_target、embedding |

RAG 最小实现选型：共享状态管理、轨迹可观测、证据链持久化已经完成；知识库 RAG 计划使用 PolarDB for PostgreSQL + pgvector 存储历史事故、Runbook 和故障基因包。

## RocketMQ 事件模型

| Topic | Producer | Consumer | 可靠性策略 |
|---|---|---|---|
| `incident.created` | Commander | Timeline Analyst | 事件幂等键为 incident_id |
| `timeline.ready` | Timeline Analyst | Hypothesis Scientist | 至少一次投递，重复事件按 span_id 去重 |
| `hypothesis.ready` | Hypothesis Scientist | Universe Builder | 每个 hypothesis_id 独立消费 |
| `experiment.done` | Universe Builder | Patch Engineer / Verifier | 失败进入 retry 与 evidence gap |
| `riskgate.waiting` | Release Auditor | Human Release Owner | 保留待审批状态与超时提醒 |
| `passport.ready` | Release Auditor | Skill Curator / Ticket Adapter | 持久化证据并写回工单 |

## 可观测映射

| 数据 | 当前产物 | AgentLoop / AgentScope Studio 映射 |
|---|---|---|
| Trace | `trace.jsonl` | Agent/Skill/MCP/RAG/LLM Span |
| Log | `run-log.jsonl` | 决策依据、失败原因、权限校验、审批事件 |
| Metrics | `engineering-metrics.json` | 端到端耗时、工具成功率、补丁成功率、成本代理指标 |
| Evaluation | `evaluation-report.md` | Golden/Badcase 回放、规则评估、Agent-as-Judge 扩展 |

## 替代方案披露

当前复赛包未直接依赖商业 API 或闭源模型，核心闭环使用合成数据和 Python 标准库复现。推荐组件采用“接口兼容优先”的迁移方案：本地 JSON/JSONL 是可验证最小实现，云上组件用于生产化治理、规模化存储、真实工具接入和观测优化。
