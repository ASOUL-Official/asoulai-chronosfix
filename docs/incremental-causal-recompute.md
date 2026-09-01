# 增量因果重计算

## 目标

新证据出现后，ChronosFix 不整条重跑流水线，而是由 Manager 根据证据类型计算 DAG 影响闭包：只让受影响的因果结论、补丁验证和 RiskGate 审批失效；未受影响的共享事故上下文继续复用。

## 运行语义

1. `evidence_observed` 写入新的 evidence digest，并递增共享状态 `revision`。
2. Controller 按 `evidence.kind` 选择起始 Agent 集合：SLO、配置、依赖、流量、提交和事故事实会影响时间线、假设、反事实、补丁、对抗验证和 RiskGate；运行时拓扑等未知能力信号只触发 SkillForge，不强行改写已有因果结论。
3. 沿 DAG 依赖向下计算影响闭包，写出 `incremental_recompute_started`，其中包含：
   - `affected_task_ids`：已有结果需要失效并重算的节点；
   - `reused_task_ids`：本次继续复用的已完成节点；
   - `new_task_ids`：因新能力而新增的节点。
4. 每个已有受影响节点写入 `task_invalidated`，并保留旧 attempt；重算使用新的 attempt 编号，不覆盖历史执行证据。
5. 新证据会让已批准的 approval 变为 `STALE`，RiskGate 必须绑定最新 `revision` 后才能恢复。

## 可复核证据

`evidence/local-controller-evidence.json` 的 `dynamic_evidence.incremental_recompute` 展示一次现场运行：6 个因果/补丁/门禁节点增量重算、1 个事故上下文节点复用、1 个 SkillForge 新节点插入；对应事件流包含失效原因和 attempt=2 的重新执行记录。

该实现是本地 Controller 的真实子进程执行证据；官方 AgentTeams Controller / Matrix 仍保持待接入边界，不将本地实现冒充官方运行时。
