# 官方推荐 Agent Infra 映射与证据等级

A-CFX 不按组件数量包装完成度，而是区分“本地已测试、离线校验、dry-run、接口设计、待部署”。

## 总表

| 官方能力 | A-CFX 职责 | 当前证据等级 | 当前证据 | 下一步 |
|---|---|---|---|---|
| AgentTeams | 角色编排、任务拆解、上下文、人类协作、状态追踪 | formal-spec offline-validated | v1beta1 Manager/8 Worker/Team/Human + 校验 JSON | 安装 Controller，保存 Matrix/Worker 运行证据 |
| 云 Skills | 云资源只读查询与受控操作 | interface-tested + dry-run | 官方 `alibabacloud-sls-query` 适配器 | 用只读 RAM Profile 查询真实 SLS |
| Nacos | Agent/Skill/Prompt/策略/Endpoint 治理 | interface-design | namespace/group/dataId 规划 | 部署轻量 Registry 并验证版本/回滚 |
| Higress | 模型、Agent、MCP/Skill 统一入口 | interface-design | 鉴权、路由、限流、fallback 策略 | 代理一个真实工具并注入 Trace |
| PolarDB for PostgreSQL | 长记忆、RAG、Trace 与审计存储 | migration-design | JSON/JSONL 数据模型与候选表结构 | 迁移历史事故/Passport，验证权限与索引 |
| UnifiedModel | Incident/Evidence/Hypothesis/Patch/Skill 关系模型 | local object graph draft | 本地实体转换 | 接统一查询 Provider |
| RocketMQ | 异步实验、审批等待、可靠通知 | event-contract design | Topic、幂等与重试契约 | 实际发布/消费一个实验事件 |
| LoongSuite | 真实服务埋点 | not integrated | 无 | 接真实服务的 HTTP/DB Trace |
| AgentScope Studio | 本地 Agent 调试和可视化 | not integrated | Repair Cockpit 不是 Studio 证据 | 导入 Agent Trace |
| AgentLoop | Agent 观测、评估与持续优化 | schema-compatible plan | trace/log/metrics/evaluation 文件 | 实际上报并保存观测页面 |

## AgentTeams

正式清单：

- apiVersion：`agentteams.io/v1beta1`；
- 1 Manager；
- 8 Worker；
- 1 Team，通过 `workerMembers` 关联；
- 1 Human；
- 唯一 Team Leader：`chronosfix-incident-commander`；
- 上游版本固定为 AgentTeams `v1.2.3` / commit `223ddc2b8073e4c8b93bcbb15e1d717f196c04d9`。

`agentteams/run_chronosfix_team.py` 运行的是本地确定性内核，输出 `agentteams_runtime_executed=false`。Controller/Matrix 尚未安装，因此不能声称真实 Runtime 已完成。

## 官方云 Skill

当前选用官方 `alibabacloud-sls-query`，固定来源 commit `4dc1013ec2564f85fd07e5b5945b2d34ceca7eff`。

| 设计项 | 当前实现 |
|---|---|
| 操作 | `GetIndex`、`GetLogsV2` |
| 权限 | `log:GetIndex`、`log:GetLogStoreLogs` |
| 时间窗 | 最长 24 小时 |
| 凭据 | 只读取已有 Aliyun CLI Profile；密钥不进入 Agent 上下文 |
| 审计 | 请求参数、User-Agent、执行模式写入 JSON |
| fallback | 云不可用时保留合成证据并标记 simulated |
| 当前模式 | dry-run；没有真实云查询 |

## Nacos 治理模型（待部署）

| 对象 | DataId 示例 | 内容 |
|---|---|---|
| Team Spec | `agentteams/chronosfix-team.yaml` | 角色与拓扑 |
| Agent Spec | `agents/release-auditor.yaml` | 身份、Skill、权限 |
| Skill Spec | `skills/riskgate.yaml` | Schema、策略、失败处理 |
| Prompt | `prompts/hypothesis-contract.md` | 假设与证据规范 |
| Policy | `policies/change-risk.yaml` | 阈值、审批与回滚 |

当前没有 Nacos 运行截图、Endpoint 或 API 调用记录。

## Higress 策略（待部署）

- 真实凭据保留在网关或平台侧，Agent 只持 consumer identity；
- Git/CI/Log/Config/Ticket 按工具域路由；
- 反事实和补丁竞赛限制并发；
- 工具失败写 evidence gap，不能降级为虚构成功；
- 记录时延、失败率、调用主体和 trace correlation。

当前没有 Higress 实际路由或插件执行证据。

## 数据与事件（待部署）

本地 `IncidentState`、`proof-bundle.json`、`trace.jsonl` 和 `run-manifest.json` 作为最小可验证数据层。生产候选：

- PolarDB 表：incidents、evidence_items、agent_traces、evidence_passports、skill_candidates；
- UnifiedModel 关系：Incident → Evidence → Hypothesis → Patch → Passport/Skill；
- RocketMQ Topics：incident.created、timeline.ready、hypothesis.ready、experiment.done、riskgate.waiting、passport.ready；
- 幂等键使用 incident/run/span，失败进入 retry 与 evidence gap。

这些均为迁移设计，尚无部署与压测结果。

## 可替换性

核心契约保留 input/output schema、permission scope、evidence level、idempotency、retry 和 audit 字段。替换组件时主要迁移执行后端与存储 Provider；鉴权、数据搬迁、运维与回归测试仍有实际成本，不能笼统写成“零成本替换”。

参考链接：

- AgentTeams（原 Hiclaw）：<https://hiclaw.io/>
- 云 Skills：<https://skills.aliyun.com/>
- Nacos：<https://nacos.io/>
- Higress：<https://higress.io/>
- PolarDB for PostgreSQL：<https://openpolardb.com/home>
- UnifiedModel：<https://alibaba.github.io/UnifiedModel/>
- RocketMQ：<https://rocketmq.apache.ac.cn/>
- LoongSuite：<https://alibaba.github.io/loongsuite-go/>
- AgentScope Studio：<https://github.com/agentscope-ai/agentscope-studio>
- AgentLoop：<https://help.aliyun.com/zh/cms/cloudmonitor-2-0/agentloop-overview>
