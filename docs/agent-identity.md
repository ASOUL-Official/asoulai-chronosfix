# Agent Identity 与执行边界

ChronosFix 的正式 AgentTeams 资源包含 **1 个 Manager、8 个 Worker、1 个 Team、1 个 Human**。其中 Incident Commander 是 Team Leader，其余 7 个 Worker 负责专业任务。

8 个 Worker 构成可治理能力池，而不是固定的全量执行队列。Manager 会读取当前证据和目标，在每次运行生成最小充分的 Agent / Skill 组合；例如 Golden 主场景选择 7 个 Worker，证据冲突或不足场景只选择 Incident Commander、Timeline Analyst、Hypothesis Scientist 三个 Worker，并在补丁前拒答。组合决策以 `agent_plan_recommended` 事件和 `decision_id` 固化，便于复盘和审计。

> 当前证据边界：以下身份已经写入 `agentteams.io/v1beta1` 资源并通过离线结构校验；本地确定性流水线也按相同职责生成 AgentTeams-compatible transcript。AgentTeams Controller / Matrix 尚未执行，因此不能把本地 transcript 称为真实 Worker 对话。

| 身份 | AgentTeams 资源 | 职责 | 关键输出 | 决策边界 |
|---|---|---|---|---|
| ChronosFix Manager | Manager | 接收人类任务、选择 Team、要求 Team Leader 返回 run/trace/门禁状态 | 任务入口与 Team 委派 | 不自行生成事故结论，不绕过 RiskGate |
| Incident Commander | Worker / `team_leader` | 拆解任务、维护 Incident State、合并可引用结论、触发人工升级 | 任务计划、最终报告、审批请求 | 只汇总 Worker 证据；不能伪造或覆盖失败检查 |
| Timeline Analyst | Worker | 融合 Issue、Git、日志、Trace、配置和流量事实 | 时间线、证据索引、缺口 | 只读优先；推断必须与事实分开 |
| Hypothesis Scientist | Worker | 生成可证伪假设、最小干预和拒答条件 | 假设契约 | 只提出实验，不直接发布根因结论 |
| Universe Builder | Worker | 在隔离状态中执行反事实重放并生成故障族 | 实验结果、分类、故障变体 | 未建模变量标注 unsupported，不触碰生产 |
| Patch Engineer | Worker | 从场景候选中构造补丁与机器可读回滚契约 | `changes`、`rollback_changes` | 本地只生成草案，不执行生产变更 |
| Adversarial Verifier | Worker | 在所有强制变体上验证补丁，并运行 Golden/Badcase 评测 | 变体结果、失败率、评测报告 | 失败样例必须保留，不能从分母静默删除 |
| Release Auditor | Worker | 分离质量门禁与风险审批，检查回滚、执行证据和完整性 | `quality_gate`、`human_approval`、Evidence Passport | 人工只能批准风险，不能将失败质量改成通过 |
| Skill Curator | Worker | 将通过验证的处理模式整理为 Skill Candidate | Skill 候选、版本与安全边界 | 只生成候选，不自动注册或上线 |
| AsoulAI Release Owner | Human | 对中高风险补丁作具名风险接受 | 审批人、理由、时间、策略版本、输入摘要 | 无权绕过质量门禁 |

## 上下文与追踪

本地流水线使用 `IncidentState` 传递 timeline、hypotheses、experiments、variants、patch scores、gate result、approval record、passport 和 GitHub draft。每次运行生成唯一 `run_id` 与 `trace_id`；主场景当前记录 18 个 Span，并包含父子关系、开始/结束时间和实测 duration。

正式资源：`agentteams/runtime/chronosfix-resources.yaml`。
离线校验：`evidence/agentteams-manifest-validation.json`。
真实接入状态：`agentteams/runtime/runtime-status.md`。
