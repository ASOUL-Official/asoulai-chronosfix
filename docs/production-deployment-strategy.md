# 官方组件分阶段部署策略

原则：先补能改变证据等级的集成，不为“组件数量”牺牲核心闭环稳定性。

## 当前基线

| 能力 | 当前状态 |
|---|---|
| 核心流水线 | 本地可运行、自动化测试、Trace/manifest/回滚证据 |
| 评测 | 12 个合成样例；9/9 受支持诊断、10/12 整体、1/1 冲突拒答 |
| AgentTeams | v1beta1 正式资源离线校验；Controller 未安装 |
| 云 Skill | 官方 SLS 只读 Skill dry-run；未查真实云 |
| GitHub | local-draft；Issue #1/PR #2 documentation-only |
| Nacos/Higress/PolarDB/RocketMQ/观测 | 接口设计，尚未部署 |

## P1：真实外部证据

优先完成两个最小闭环：

1. **真实只读 SLS 查询**
   - 提供专用 Project/Logstore；
   - 使用最小 RAM Policy；
   - 保存成功、权限拒绝、超时三种证据；
   - 不把 AccessKey 写入仓库或 Agent 上下文。

2. **真实低风险 GitHub PR + CI**
   - GitHub App/PAT 分权；
   - 由真实 selected patch 生成隔离分支；
   - CI 实际运行并回传 commit SHA、job/check URL；
   - PR 保持 draft，合并由人工和保护规则决定。

这两项能把 dry-run/local-draft 提升为 external execution evidence。

## P2：AgentTeams Controller

前置条件：

- 用户明确授权安装器创建/管理容器、卷和管理员配置；
- 可用模型 API Key 或模型网关；
- 独立演示环境；
- 回滚/清理方案。

验收证据：

- Controller 版本与状态；
- 资源 apply 结果；
- Team Active、Worker 状态；
- Matrix 协作记录；
- Worker Skill 调用；
- 最终 run/trace/门禁结果；
- 失败和人工审批分支。

在这些证据产生前，只使用“formal-spec offline-validated”。

## P3：治理与网关

- Nacos 托管 Agent/Skill/Prompt/Policy 版本，并演示更新与回滚；
- Higress 统一代理至少一个工具，演示鉴权、限流、失败和 Trace correlation；
- 所有写动作走具名审批，不能把网关成功等同于业务质量通过。

## P4：数据、事件与观测

- PolarDB/UnifiedModel 保存 Incident、Evidence、Trace、Passport 和 Skill；
- RocketMQ 驱动实验与审批等待，验证幂等、重复投递和死信；
- AgentLoop/AgentScope Studio 导入真实 Agent Trace；
- LoongSuite 接一个真实服务，区分服务 Trace 与 Agent Trace。

## 部署复杂度与取舍

| 组件 | 主要成本 | 迁移失败时保底 |
|---|---|---|
| AgentTeams | Controller、Matrix、存储、模型凭据 | 本地确定性 engine + 明确 runtime=false |
| 云 Skills | RAM、CLI、资源目标 | dry-run + 合成证据 |
| GitHub/CI | Token、分支保护、Check API | local-draft |
| Nacos/Higress | 命名空间、鉴权、网关策略 | 版本化本地配置 |
| PolarDB/RocketMQ | 云资源、Schema、可靠性运维 | JSON/JSONL 与顺序事件日志 |
| AgentLoop/Studio | Trace 映射、上报凭据 | 本地 Trace/报告 |

“全部部署”只有在每个组件都有实际调用、权限、失败和观测证据时才更完整；仅启动空组件不会增加有效完成度。
