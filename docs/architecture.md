# 技术架构

ChronosFix 采用四层结构：Agent 协同层、Skill 能力层、工具适配层、证据治理层。

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

## MCP 与等价集成契约

初赛 Demo 为了可运行性，使用本地 JSON 和确定性模拟器实现工具适配。复赛迁移时，每个外部系统按同一套契约封装：

| 工具 | 协议 | 核心输入 | 核心输出 | 权限 | 审计 |
|---|---|---|---|---|---|
| Git Adapter | MCP / CLI | repo、commit、path、diff range | diff、blame、commit metadata | 只读；修复分支可写需授权 | 记录 commit range 和调用人 |
| CI Adapter | MCP / HTTP | branch、test target、env | test result、logs、coverage | 触发测试，不直发生产 | 记录 job id 和结果 |
| Log/Trace Adapter | MCP / HTTP | service、time window、query | logs、spans、metrics | 只读脱敏 | 记录 query 和 trace id |
| Config Adapter | MCP / HTTP | key、environment、version | config diff、rollback point | 修改需审批 | 记录审批与回滚点 |
| Ticket Adapter | MCP / HTTP | incident id、status、report | issue、PR、comment | 写入报告需授权 | 记录外部链接 |

## 可观测性

Demo 输出轻量 Trace：

- `trace_id`：单次事故链路。
- `span_id`：每个 Agent/Skill 调用。
- `agent`：负责的职能 Agent。
- `skill`：调用能力。
- `status`：ok、approved 或 blocked。
- `payload`：输入输出摘要、指标和证据。

当前增强版会记录 15 段 Trace，覆盖 EvidenceFusion、ChangeTimeline、BaselineReplay、HypothesisContract、CounterfactualReplay、FaultGenome、PatchTournament、RiskGate、EvidencePassport、SkillForge 和 ProofReport。

## 上下文与 RAG 计划

初赛实现三类上下文能力：

- Incident State：保存任务状态、证据索引、假设、实验、故障变体、补丁排名和证据护照。
- 轨迹可观测：Trace 可回放每个决策。
- 证据报告：proof-bundle 可进入知识库。

复赛增加历史事故 RAG 和 Runbook RAG，用于检索相似故障、既往修复、组件约束和发布策略。
