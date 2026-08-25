# 复赛 Demo 视频脚本

建议视频时长控制在 3-5 分钟，评委能在不跑代码的情况下看到完整闭环、异常处理和工程证据。

## 0. 开场 15 秒

画面：打开在线 Demo 首页。

讲法：

> 我们是 AsoulAI，作品是 AsoulAI ChronosFix（A-CFX）：软件故障时间机器。它解决的是软件研发全流程协同里的线上故障修复问题：不是让 AI 看日志猜原因，而是让多 Agent 用反事实实验证明根因，再让补丁带着证据护照进入发布审批。

## 1. 场景输入 30 秒

画面：展示时间线与指标卡。

讲法：

> 样例是订单创建接口在 10:16 后失败率升高。系统接收 Issue、Git、依赖、配置、流量、告警等证据，Incident Commander 将任务拆给不同职能 Agent。这里可以看到基线失败率 48.72%、P99 606.96ms、Trace Span 15 个。

## 2. AgentTeams 协作 45 秒

画面：切到“复赛工程验证 / Infra Mapping”区域或展示 `agentteams-run.json`。

讲法：

> A-CFX 以 AgentTeams 为协同基点：Manager 是 Incident Commander，Workers 分别负责时间线、假设、反事实实验、补丁、验证、审计和 Skill 沉淀。所有中间结论都写入 Incident State，并通过 trace_id/span_id 追踪。

## 3. 反事实根因证明 45 秒

画面：点击平行宇宙实验室的 H-CODE、H-DEPENDENCY、H-POOL。

讲法：

> 系统不会直接下结论，而是把每个假设变成可证伪实验。撤销代码提交，失败率不变，所以代码不是主因；回退依赖，失败率下降但不归零，所以它只是放大因素；恢复连接池，失败率从 48.7% 降到 0%，因此连接池缩容被证明为主因。

## 4. 缺陷基因与补丁竞赛 45 秒

画面：展示缺陷基因实验室与补丁竞赛。

讲法：

> A-CFX 不只修原始样例，还把事故繁殖成 8 个同源故障变体，包括高流量、下游抖动、恢复尖峰和隐性配置漂移。四个补丁进入竞赛，最终选择恢复连接池并增加容量验证门禁，因为它在平均失败率、最差失败率、风险和成本之间综合最优。

## 5. 风险边界与证据护照 45 秒

画面：展示证据护照与 RiskGate 分支。

讲法：

> 中高风险动作必须经过 RiskGate。没有 `--approve` 时，Demo 会返回 `blocked-awaiting-human`，证明系统不会无人值守发布。审批通过后，Evidence Passport 会生成需求、因果、验证、风险、回滚和缺口声明，形成可审计交付材料。

## 6. 工程证据 45 秒

画面：展示仓库文件：`trace.jsonl`、`run-log.jsonl`、`engineering-metrics.json`、`evaluation-report.md`。

讲法：

> 复赛包提供可运行代码、样例输入输出、日志、Trace、指标和自动化验证。评委可以本地运行单元测试，也可以运行 AgentTeams 风格入口，生成完整证据链。

## 7. 官方 Infra 映射 30 秒

画面：展示 Demo 的官方基座映射区域或 PPT 架构页。

讲法：

> 生产化时，A-CFX 映射到官方推荐 Agent Infra：AgentTeams 负责协作，云 Skills 负责云资源操作，Nacos 做 Agent/Skill/Prompt 治理，Higress 做模型与工具统一网关，PolarDB 与 UnifiedModel 做记忆和实体关系，RocketMQ 做事件流转，AgentLoop 或 AgentScope Studio 做观测评估。

## 8. 收尾 15 秒

画面：回到商业价值飞轮。

讲法：

> A-CFX 的商业价值是把事故复盘从一次性成本变成研发质量资产：故障基因包、证据护照模板和可复用 Skill 可以在团队、行业和云市场中持续复用。

