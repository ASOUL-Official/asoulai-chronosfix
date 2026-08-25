# 技术架构

ChronosFix 复赛版采用七层结构：AgentTeams 协同层、Skill 能力层、云 Skills / MCP 工具层、AI 治理控制面、AI 网关层、Agent 数据层、证据可观测层。当前代码包用本地确定性引擎交付可运行 Demo，同时按官方推荐工具链定义可迁移接口。

它的架构目标不是“自动修 Bug”，而是支撑一条 **Proof-Carrying Software Change Chain（带证明的软件变更链）**：事故证据 → 反事实证明根因 → 缺陷基因验证补丁 → RiskGate 审批 → GitHub PR / 证据护照 → Skill / 故障资产沉淀。

## 端到端链路

```text
Issue / Alert / Log / Trace / Git / Config
              |
              v
Incident Commander 拆解任务与维护共享状态
              |
              v
Timeline Analyst 构建故障时间线
              |
              v
Hypothesis Scientist 生成可证伪假设
              |
              v
Universe Builder 创建平行版本、反事实重放、故障基因繁殖
              |
              v
Patch Engineer 生成候选补丁与回滚契约
              |
              v
Adversarial Verifier 在故障基因族上进行补丁竞赛
              |
              v
Release Auditor 执行风险门禁、证据护照与审计归档
              |
              v
SkillForge 将成功经验沉淀为可复用 Skill 候选
```

从软件变更视角看，上面的 Agent 流程对应六个可审查交付物：

| 证明链环节 | 关键交付物 |
|---|---|
| 事故证据 | timeline、evidence index、impact metrics |
| 反事实证明根因 | hypothesis contracts、counterfactual experiment result |
| 缺陷基因验证补丁 | fault variants、patch tournament ranking、regression result |
| RiskGate 审批 | risk score、approval state、rollback contract |
| GitHub PR / 证据护照 | PR draft、checks、diff、Evidence Passport |
| Skill / 故障资产沉淀 | skill candidates、fault gene package、proof template |

## AgentTeams 映射

| AgentTeams 能力 | ChronosFix 映射 |
|---|---|
| Manager | Incident Commander |
| Worker | Timeline、Hypothesis、Universe、Patch、Verifier、Auditor |
| Team | ChronosFix Incident Response Team |
| Human | 研发负责人或值班 SRE，负责中高风险审批 |
| Matrix Room | 故障协作房间，全员可见每个 Agent 的结论和证据 |
| Shared File System / Object Storage | Trace、proof-bundle、proof-report、实验产物和回放数据 |
| Higress AI Gateway / MCP | Git、CI、日志、配置中心、工单和知识库工具入口 |

### 角色、任务、上下文、执行、状态五点

| 指南核验点 | 当前可验证实现 |
|---|---|
| 角色编排 | `agentteams/chronosfix-team.yaml` 定义 Human、Manager 和 7 个 Worker |
| 任务拆解 | `agentteams/run_chronosfix_team.py` 输出 AgentTeams 风格任务拆解 |
| 上下文传递 | Incident State 承载 timeline、hypotheses、experiments、variants、patch scores、approval、passport |
| 协同执行 | Demo 串联 9 个 Skill；生产接 RocketMQ 后可将反事实实验和补丁评分并行化 |
| 状态追踪 | `trace.jsonl`、`run-log.jsonl`、`agentteams-run.json` 记录 trace_id、span_id、agent、skill、status、payload |

## 官方推荐基础设施映射

| 基础设施 | ChronosFix 职责 | 复赛说明 |
|---|---|---|
| 阿里云云 Skills | 云资源操作、HITL、官方 Skill 发现与安装 | 本地 Skill 可迁移为云 Skills；高风险配置回滚走人工确认 |
| Nacos | AgentSpec、SkillSpec、Prompt、配置策略、MCP Endpoint Registry | `official-infra-mapping.md` 定义 namespace/group/dataId |
| Higress | LLM、Agent 服务、MCP Server、云 Skills 的统一入口 | 统一鉴权、路由、限流、Fallback、Token 观测 |
| PolarDB for PostgreSQL | 长记忆、RAG、审计日志、Trace、向量索引 | 复赛以 JSON/JSONL 最小实现，生产接表结构和 pgvector |
| UnifiedModel | Incident、Evidence、Patch、Skill 的实体关系层 | `engineering.py` 提供 object graph 草案 |
| RocketMQ | 事件驱动、异步任务、Agent 间消息和可靠通知 | 定义 incident/timeline/hypothesis/experiment/riskgate/passport Topics |
| LoongSuite / AgentScope Studio / AgentLoop | Trace、Log、Metrics、评估、审计回放 | 当前输出可导入观测系统的结构化证据 |

## MCP 与等价集成契约

当前可运行 Demo 为了复现稳定性，使用本地 JSON 和确定性模拟器实现工具适配。迁移到真实系统时，每个外部系统按同一套契约封装：

| 工具 | 协议 | 核心输入 | 核心输出 | 权限 | 审计 |
|---|---|---|---|---|---|
| Git Adapter | MCP / CLI | repo、commit、path、diff range | diff、blame、commit metadata | 只读；修复分支可写需授权 | 记录 commit range 和调用人 |
| CI Adapter | MCP / HTTP | branch、test target、env | test result、logs、coverage | 触发测试，不直发生产 | 记录 job id 和结果 |
| Log/Trace Adapter | MCP / HTTP | service、time window、query | logs、spans、metrics | 只读脱敏 | 记录 query 和 trace id |
| Config Adapter | MCP / HTTP | key、environment、version | config diff、rollback point | 修改需审批 | 记录审批与回滚点 |
| Ticket Adapter | MCP / HTTP | incident id、status、report | issue、PR、comment | 写入报告需授权 | 记录外部链接 |

完整 Schema 见 `docs/interface-schema.md`。

## 可观测性

Demo 输出复赛工程证据：

- `trace_id`：单次事故链路。
- `span_id`：每个 Agent/Skill 调用。
- `agent`：负责的职能 Agent。
- `skill`：调用能力。
- `status`：ok、approved 或 blocked。
- `payload`：输入输出摘要、指标和证据。
- `run-log.jsonl`：结构化记录权限范围、审批事件和失败处理。
- `engineering-metrics.json`：记录 Tool 成功率、补丁最差失败率、审批门禁、回滚契约和 Trace Schema。
- `evaluation-report.md`：汇总自动化验证、复赛验收点和失败分支。

当前增强版会记录 16 段 Trace，覆盖 EvidenceFusion、ChangeTimeline、BaselineReplay、HypothesisContract、CounterfactualReplay、FaultGenome、PatchTournament、RiskGate、EvidencePassport、GitHub Issue/PR、SkillForge 和 ProofReport。

## 上下文与 RAG 计划

当前复赛包实现三类上下文能力：

- Incident State：保存任务状态、证据索引、假设、实验、故障变体、补丁排名和证据护照。
- 轨迹可观测：Trace 可回放每个决策。
- 证据报告：proof-bundle 可进入知识库。

复赛最小实现已覆盖指南中 RAG/上下文增强的三项：共享状态管理、轨迹可观测、证据链持久化。决赛阶段增加历史事故 RAG 和 Runbook RAG，用 PolarDB for PostgreSQL + pgvector 检索相似故障、既往修复、组件约束和发布策略。
