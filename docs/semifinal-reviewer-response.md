# 复赛评委反馈闭环

项目正式名称：**AsoulAI ChronosFix（A-CFX）：软件故障时间机器**  
定位：**让每一次软件变更都携带可验证的证据。**

本页只记录可验证状态。`implemented` 表示仓库中有代码、测试或运行产物；`designed` 表示接口与迁移方案已定义但尚无外部执行证据；`requires-input` 表示必须取得授权数据、账号或运行环境后才能完成。

## 1. 评委建议与当前闭环

### 复赛新增：Manager 按证据自由组合 Agent

复赛版把“固定角色清单”升级为“可治理能力池 + 运行时选择”。AgentTeams 资源层声明 8 个 Worker，保证身份、权限和 Skill 边界完整；本地 Manager 每次读取事件、假设、候选补丁和证据缺口后，选择最小充分组合，并把 `decision_id`、理由、依赖和停止边界写入 `agent_plan_recommended` 事件。主场景选择 7 个 Worker 完成闭环；证据冲突 / 不足场景只选择 3 个 Worker，并在 `PatchTournament / RiskGate` 前拒答。证据见 `src/chronosfix/runtime/recommender.py`、`evidence/local-controller-evidence.json` 和 `coordination.json`。

这意味着 8 个 Worker 不是每次都强制同时启动，而是 AgentTeams 的可复用能力池；不同证据输入会产生不同 Agent / Skill 组合。当前证据仍是本地 Controller 的可回放实现，不冒充官方 AgentTeams Controller / Matrix 运行轨迹。

| 评委建议 | 状态 | 本轮证据 | 下一道门槛 |
|---|---|---|---|
| 新证据动态调整任务 | implemented | `src/chronosfix/dynamic.py`、`coordination.json` 的 `task_registered/evidence_observed` | AgentTeams Matrix 实际消息记录 |
| 多个修复方案竞争 | implemented | PatchTournament 对所有候选运行相同强制故障族并排名 | 接真实 CI/沙箱运行候选补丁 |
| 共享状态更新 | implemented | 单调 `revision`、event log、task graph、attempts | PolarDB/RocketMQ 持久化与并发冲突测试 |
| 人工暂停/恢复 | implemented | `human_pause`、revision checkpoint、`approval_invalidated`、`human_resume` | 对接企业审批或 AgentTeams Human |
| Worker 失败重派 | implemented | Timeline/Verifier 首次 timeout 注入，按 capability 重派备用 Worker | Controller lease/heartbeat 实测 |
| Skill 可发现/加载 | implemented | 9 个独立 `agentteams/skills/*/SKILL.md` + `skill_registry.py` | 在真实 Worker workspace 加载并调用 |
| 防重复执行 | implemented | evidence event 去重、task idempotency key、lost-ack replay | RocketMQ 重复投递/重启恢复实测 |
| 统一可观测 | implemented locally | 18 个业务 Span + 独立协调事件、run/trace/revision 关联 | AgentLoop/Studio 或 OTLP 外部导入 |
| 异常注入 | implemented locally | Repair Cockpit 提供新证据、Worker timeout/崩溃、重复 evidence、stale approval、权限拒绝、人工暂停/恢复与 retry exhausted 的可点击本地模拟 | 决赛接真实沙箱进程、租约和外部权限系统 |
| 权限控制 | implemented contract | L0-L3、只读/隔离/人工审批、fail-closed | 云 RAM、GitHub App、沙箱账号实测 |
| 真实工具沙箱 | designed | deterministic simulator 与 local draft 只证明隔离契约 | 接容器化仓库/CI 沙箱，不写生产 |
| 版本、灰度、回滚 | rollback implemented; rollout designed | machine-readable rollback 往返验证；部署策略文档 | 真实 staging canary 与自动回滚证据 |
| SLO、容量、长期运维 | locally measured/designed | P99、失败率、容量变体；生产部署策略 | 长期压测、SLO burn-rate 和运维值班数据 |
| 真实事故对照 | requires-input | 当前全部 fixture 明确标记为确定性合成 | 公开 postmortem 重建或已授权脱敏事故 |

## 2. 动态协同事件模型

每次运行生成 `coordination.json`：

1. Incident Commander 注册任务和依赖，不直接执行所有能力。
2. Scheduler 根据 dependency 和 capability 选择 Worker，并发语义由可运行任务集合表示。
3. 新证据先按 evidence kind 计算受影响 DAG 闭包：因果、补丁和 RiskGate 相关节点进入增量重算，未受影响的事故上下文节点复用；若出现未映射信号，再动态插入 `agent-08-skill-curator`。
4. Worker 首次超时产生 `task_failed`，随后产生 `task_reassigned` 并转给备用 Worker。
5. 重复 evidence event 产生 `evidence_deduplicated`，不会修改 state revision。
6. lost-ack task replay 使用相同 idempotency key，产生 `task_deduplicated`，不再调用 handler。
7. 中风险补丁产生 `human_pause`；暂停后若有新证据，旧 revision 的审批产生 `approval_invalidated`。
8. 只有绑定最新 revision 的审批产生 `human_resume`，才允许后续 RiskGate 继续。
9. `incremental_recompute_started` 明确写出 `affected_task_ids`、`reused_task_ids` 和 `new_task_ids`；`task_invalidated` 逐节点记录失效原因，证明没有整条流水线重跑。

这套证据是 AgentTeams Matrix 的本地兼容控制面，不声称 Controller 已执行。

## 3. 真实事故同题对照模板

数据只能来自公开事故报告或已授权、脱敏的内部事故。每个事故应同时保存人工 baseline 和 A-CFX run，禁止只展示系统一侧。

| 阶段 | 人工 baseline 要记录 | A-CFX 要记录 |
|---|---|---|
| 收集证据 | 信息源、查询步骤、首次形成可用时间线的耗时 | evidence source、缺口、timeline revision |
| 定位问题 | 假设提出顺序、验证动作、被否定原因、首次正确定位时间 | task/event/attempt、反事实结果、拒答条件 |
| 验证修复 | 候选数、测试范围、回滚准备、漏测项 | patch ranking、mandatory variants、rollback check |
| 异常影响 | 误修次数、复发、超时升级、业务/SLO 影响 | fail-closed、reassign、stale approval、SLO watch |
| 结果 | MTTA/MTTD/MTTR、审计材料完整度 | 同口径指标及证据文件链接 |

没有真实测量前，PPT、Demo 和 README 不得声称生产 MTTR 降幅、准确率或商业 ROI。

## 4. 下一阶段优先级

本轮新增 `evidence/release-manifest.json`，将源码指纹、Demo 数据、主场景证据、PPT/PDF 与提交包输入统一绑定；校验入口为 `scripts/validate_release_manifest.py`。

P0：在 AgentTeams Controller/Matrix 跑一次动态任务图，保存 Worker load Skill、失败重派和 Human 恢复记录。  
P1：选择一个公开事故或授权脱敏事故，完成上述人工 baseline 对照。  
P1：把一个候选补丁放进容器化 Git/CI 沙箱，演示 canary、SLO burn-rate、回滚。  
P2：用 RocketMQ/PolarDB 替换本地 event log，验证重复投递、并发 revision 和 checkpoint 恢复。  
P2：将 Trace 导入 AgentLoop/AgentScope Studio 或标准 OTLP 后端。
