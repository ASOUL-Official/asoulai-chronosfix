# 技术架构与证据边界

ChronosFix 用一条带证明的软件变更链组织本地工程实现与 Agent Infra 迁移接口：

```text
Issue / Alert / Git / Config / Trace
  -> Incident State
  -> 可证伪假设与反事实干预
  -> 故障族与补丁竞赛
  -> quality_gate
  -> named human approval
  -> local GitHub draft + Evidence Passport
  -> Skill Candidate + run manifest
```

## 分层架构

| 层 | 当前实现 | 生产化映射 |
|---|---|---|
| 协同层 | 本地确定性 orchestrator；AgentTeams-compatible transcript；增量因果重计算 | AgentTeams Manager/Worker/Team/Human/Matrix |
| Skill 层 | 9 个核心本地 Skill + 官方 SLS 只读 Adapter；完整性/评测为辅助模块 | AgentTeams Worker Skill / 企业 Skill Registry |
| 工具层 | 本地场景文件、GitHub local-draft、官方 SLS Skill dry-run | 云 Skills、MCP、Git/CI/Log/Config/Ticket Adapter |
| 治理与网关 | 契约和策略说明 | Nacos、Higress |
| 数据层 | Incident State、JSON/JSONL、SHA-256 manifest | PolarDB for PostgreSQL、UnifiedModel |
| 事件层 | 本地顺序执行与事件日志 | RocketMQ |
| 可观测层 | 18 Span Trace、结构化日志、实测 duration、派生指标 | LoongSuite、AgentScope Studio、AgentLoop |

其他官方组件目前是接口映射，不是部署证据。

新证据到达时，Controller 按证据信号计算 DAG 影响闭包：只让时间线、假设、反事实、补丁验证和 RiskGate 等相关节点失效并重算，复用未受影响的事故上下文；新能力节点单独记录为 `new_task_ids`。

## AgentTeams 正式资源

`agentteams/runtime/chronosfix-resources.yaml` 使用 `agentteams.io/v1beta1`，包含：

- 1 Manager；
- 8 Worker，其中 Incident Commander 为唯一 `team_leader`；
- 1 Team，通过 `workerMembers` 关联成员；
- 1 Human，作为具名 Release Owner。

资源已经离线校验，结果为 `evidence/agentteams-manifest-validation.json`。AgentTeams Controller / Matrix 尚未安装和执行；`agentteams-run.json` 是本地确定性内核生成的兼容映射证据，不是真实 Runtime 轨迹。

## Agent 协作映射

| 环节 | Worker | 共享状态 |
|---|---|---|
| 证据融合与时间线 | Timeline Analyst | events、timeline、evidence index |
| 假设契约 | Hypothesis Scientist | hypotheses、interventions、拒答条件 |
| 反事实与故障族 | Universe Builder | experiments、classifications、variants |
| 补丁契约 | Patch Engineer | changes、rollback_changes |
| 对抗验证 | Adversarial Verifier | patch scores、mandatory variant results |
| 门禁与护照 | Release Auditor | quality gate、approval record、passport |
| 资产沉淀 | Skill Curator | skill candidates |
| 总体协调 | Incident Commander | run status、最终报告、人工升级 |

## RiskGate 状态模型

质量与人工审批是两个正交维度：

```text
quality_gate = passed
AND (risk low OR named human approval valid)
=> release_ready = true
```

质量门禁检查：

- 是否证明至少一个主因；
- 所有强制变体是否健康；
- 是否存在 missing claims；
- 是否有机器可读回滚且实际恢复基线；
- 所有 required checks 是否执行并有退出码或 run ID 等结果证据。

中高风险审批记录包含 approver、reason、timestamp、policy_version 和 input_digest。人工不能覆盖 `blocked-quality-gate`。

## Trace、指标与完整性

主场景当前生成 18 个 Span。每条 Span 包含：

- `timestamp`、`started_at`、`ended_at`；
- `duration_ms` 与 `duration_kind`；
- `run_id`、`trace_id`、`span_id`、`parent_span_id`；
- incident、agent、skill、status、payload。

`engineering-metrics.json.elapsed_ms` 来自本地 wall-clock 实测；步骤完成率和证据覆盖率分别标记为 derived。因为本地运行没有调用外部工具，`external_tool_success_rate` 为 null，而不是虚构 100%。

`run-manifest.json` 使用 SHA-256 绑定场景、补丁 changes、rollback_changes、审批输入摘要和主要证据文件。它提供完整性检测，不等同于密码学签名或远程不可抵赖存证。

## 12 例评测边界

- 9 个 pipeline Golden：受支持诊断 9/9。
- 2 个 evaluation-only Badcase：当前变量未建模，均 abstain，但不计成功。
- 1 个 Insufficient Evidence：通过可辨识性仲裁正确拒答 1/1。
- 整体达成预期 10/12。

这些均为合成回放，不能外推生产准确率。

## 外部工具契约

真实系统按相同输入/输出与权限模型接入：

| 工具 | 当前证据 | 生产权限 |
|---|---|---|
| Git / GitHub | local-draft + documentation-only Issue #1/PR #2 | 分支、PR、Checks 分权；合并禁用 |
| CI | 本地 validation checks 带执行结果 | 只触发测试，不直发生产 |
| SLS | 官方 `alibabacloud-sls-query` dry-run | RAM GetIndex/GetLogsV2 只读 |
| 配置中心 | Schema/Adapter 契约 | 读取自动，回滚必须 HITL |
| 发布系统 | RiskGate 本地门禁 | 具名审批、回滚与审计 |

详细 Schema 见 `docs/interface-schema.md`。
