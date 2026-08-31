# 官方复赛要求逐条审计

审计对象：AsoulAI ChronosFix（A-CFX）复赛提交版

审计日期：2026-08-26

依据：最新版《赛道一：新智基座丨Agent Infra》参赛指南第 6、8、9、10、11、12 章及附录 A/B；官方 PPT 模板；仓库、提交包、公开 GitHub、在线 Demo 和本地验收证据。

## 结论先行

当前版本可以作为复赛提交包，核心闭环已经可本地复现、可验证、可审计，在线 Repair Cockpit 可运行，公开仓库可访问，自动化验收链已通过。

必须如实披露的边界：

- AgentTeams Controller / Matrix 尚未安装和执行；当前 transcript 是 `compatible mapping evidence`，不是 Controller 运行轨迹。
- 官方 `alibabacloud-sls-query` 已完成适配器契约测试和 dry-run；没有真实 SLS 查询成功证据。
- Nacos、Higress、PolarDB for PostgreSQL、UnifiedModel、RocketMQ、LoongSuite、AgentScope Studio、AgentLoop 当前为接口映射、数据模型和迁移设计，未宣称已经部署。
- 没有知识库 RAG；依据指南的四项上下文能力要求，已实现共享状态管理和轨迹可观测，满足“至少两项”的替代路径。
- 在线 Demo 是静态证据驾驶舱；绿色状态只代表离线合成验证通过，不代表真实云资源或生产发布执行。

## 复赛必交材料

| 官方要求 | 当前证据 | 状态 | 评审时准确表述 |
|---|---|---|---|
| 更新版项目方案 PPT/PDF | `submission/ChronosFix_复赛方案.pptx`、`submission/ChronosFix_复赛方案.pdf` | 已完成 | 复赛版已更新场景闭环、架构、Skill、风险边界、评测和落地计划；所有外部执行边界已单独标注 |
| 可执行 AgentTeams 代码包 | `agentteams/run_chronosfix_team.py`、`agentteams/runtime/chronosfix-resources.yaml`、`agentteams/runtime/validate_resources.py`、依赖锁和样例输出 | 部分完成 | 提供本地可执行入口、正式 v1beta1 资源声明和离线校验；真实 Controller / Matrix 执行留待决赛接入 |
| 可运行 Demo / Demo 视频 | 在线 Repair Cockpit、`repair-cockpit/index.html`、`docs/demo-video-script.md` | 已完成 | 可运行完整离线场景链路，包含通过、无人审批阻断、质量门禁失败、证据不足和 Badcase 分支 |
| 样例输入输出、日志、Trace、Metrics | `scenarios/`、`evidence/run-log.jsonl`、`evidence/trace.jsonl`、`evidence/engineering-metrics.json` | 已完成 | 产物由同一 `run_id` 绑定，Metrics 区分 measured / derived |
| 评测结果和自动化验证证据 | `evidence/evaluation-report.md`、`evidence/evaluation-corpus/`、`scripts/run_semifinal_acceptance.py` | 已完成 | 12 个合成场景、61 项测试、严格 JSON/JSONL、Schema、资源校验和 CI 验收均可重跑 |

## 技术要求逐条核对

### 1. AgentTeams 多 Agent 协同（必选）

- 角色编排：1 Manager、8 Worker、1 Team、1 Human，正式声明位于 `agentteams/runtime/chronosfix-resources.yaml`。8 个 Worker 是可治理能力池，不是每次运行都强制全量启动；Manager 会按当前证据选择最小充分子集。
- 任务拆解与上下文：`IncidentState` 的状态分区、`run_id` / `trace_id` / `parent_span_id` 和 Worker 写入边界见 `docs/agent-identity.md`、`docs/interface-schema.md`。
- 协同执行与状态追踪：本地入口 `agentteams/run_chronosfix_team.py` 生成兼容 transcript、Trace、日志和证据护照。
- 自主组合证据：`src/chronosfix/runtime/recommender.py` 依据事件、假设、候选补丁和证据缺口生成 `agent_plan_recommended`；Golden 运行选择 7 个 Worker，冲突 / 证据不足运行只选择 3 个并在 `PatchTournament / RiskGate` 前停止，结果落在 `evidence/local-controller-evidence.json`。
- 证据等级：`evidence/agentteams-manifest-validation.json` 是离线资源校验；`evidence/agentteams-run.json` 明确 `agentteams_runtime_executed=false`。
- 状态：部分完成。可以证明资源设计、状态契约和本地闭环，不能把它表述为真实 Runtime 已运行。

### 2. Agent Identity 清单（必需）

`docs/agent-identity.md` 逐个写明 Name、Role、Capabilities、Inputs、Outputs、Dependencies、DecisionBoundary 和 Trace；高风险动作升级到 Human，失败采用 fail-closed。

### 3. Skill 工程体系（必选）

`docs/skill-specs.md` 提供 9 个业务 Skill 和 1 个官方 SLS 只读适配器，覆盖输入输出、调用条件、依赖、失败处理、权限、复用价值、版本和评测关系。Skill 不是一次性提示词；新版本采用“候选 → 评测 → 人审 → 发布 → 监控 → 回滚”生命周期。

### 4. 工具 / MCP 等价集成契约

当前核心执行使用本地适配器和确定性场景文件；`docs/interface-schema.md`、`docs/architecture.md` 和 `docs/official-infra-mapping.md` 为每个外部工具给出协议入口、参数/返回 Schema、鉴权、错误、重试、幂等、审计、降级和 MCP 迁移成本。没有把接口设计冒充已部署 MCP Server。

### 5. RAG / 上下文增强替代路径

指南允许在 Agent 记忆、知识库 RAG、共享状态管理、轨迹可观测四项中至少实现两项。本版本明确不声称知识库 RAG，已实现：

1. 共享状态管理：`IncidentState`、状态分区、审批和回滚状态；
2. 轨迹可观测：18 个 Trace Span、结构化 Log、Metrics、Evidence Passport 和 SHA-256 manifest。

PolarDB/pgvector 历史事故 RAG 是生产化路线，不是当前运行证据。

### 6. 可观测

已完成本地 Trace / Log / Metrics 和离线评测；`docs/measurement-plan.md` 定义了质量、性能、成本、可靠性指标。LoongSuite、AgentScope Studio、AgentLoop 的真实上报未接入，当前仅提供兼容数据模型和迁移计划。

### 7. Schema、数据流与工程结构

`schemas/scenario.schema.json`、`docs/interface-schema.md`、`docs/architecture.md`、`pyproject.toml`、`scripts/` 和 `tests/` 共同覆盖输入输出、数据流、部署入口、依赖、失败处理与验证方式。

### 8. 权限、审批、回滚、审计

- SLS 适配器限制为 `GetIndex` / `GetLogsV2`，查询窗口不超过 24 小时，凭据不进入 Agent 上下文或证据文件；
- `RiskGate` 将 `quality_gate`、`human_approval` 和 `release_decision` 分离，具名审批不能覆盖质量失败；
- 回滚契约要求恢复完整基线状态；
- Trace、结构化日志、审计事件、审批摘要和 manifest 提供可回放证据。

证据：`docs/safety-and-audit.md`、`evidence/github-review-audit.jsonl`、`evidence/run-manifest.json`。

### 9. 评测口径

- 9 个 Golden：9/9 命中当前模拟器支持范围内的 Ground Truth；
- 1 个冲突/证据不足：1/1 正确拒答；
- 2 个未建模 Badcase：如实保留为已知漏诊；
- 全部样例：10/12 达成预期，不能写成 12/12；
- 所有数据为确定性合成回放，不代表生产准确率、MTTR 或商业 ROI。

### 10. 开放 / 开源规范

`LICENSE`、`THIRD_PARTY_NOTICES.md`、`SBOM.json`、`docs/open-source-compliance.md` 和 `docs/originality-check.md` 已披露 Apache-2.0、第三方依赖、商业 API / 闭源模型边界、合成数据授权、复现方式和后续维护计划。当前不提交密钥，不包含真实企业日志或用户数据。

## 公开链接复核

- 代码仓库：<https://github.com/ASOUL-Official/asoulai-chronosfix>
- 在线 Demo：<https://asoul-official.github.io/asoulai-chronosfix/>
- 公开 Issue #1：协作证据文档迁移；不等同于自动修复执行。
- 公开 PR #2：协作证据文档迁移；不等同于真实 AgentTeams Runtime 或生产发布。
- 公开 PR #3：真实 GitHub Actions 工程验收（Python 3.10 / 3.11 / 3.12 和验收 Artifact）；不等同于真实 AgentTeams Runtime 或云端查询。

## 提交前最后检查

- [x] README、PPT/PDF、Demo 和提交入口的作品名称统一为“带证明的软件变更基础设施”；
- [x] 不把 dry-run、offline-validated、compatible mapping 或 local-draft 写成真实生产执行；
- [x] 通过分支、无人审批阻断分支、质量门禁失败分支、Badcase 和证据不足分支均可验证；
- [x] 重新生成提交 ZIP 与 SHA-256 manifest 后，再运行一键复赛验收器；
- [ ] 决赛阶段：接入真实 AgentTeams Controller / Matrix、真实只读 SLS、生产 CI / 发布系统和历史事故 RAG。
