# 复赛参赛指南对照矩阵

本矩阵依据最新版《赛道一：新智基座丨Agent Infra》指南整理，目标是让评委能快速判断 AsoulAI ChronosFix（A-CFX）是否具备可运行、可验证、可审计和可持续演进能力。

## 1. 复赛必交材料

| 复赛材料 | 指南要求 | A-CFX 对应交付 | 状态 |
|---|---|---|---|
| 更新版项目方案 PPT/PDF | 更新场景闭环、架构、Skill、风险边界与落地计划 | `submission/ChronosFix_复赛方案.pptx`、`submission/ChronosFix_复赛方案.pdf` | 已完成 |
| 可执行 AgentTeams 代码包 | 运行入口、依赖说明、配置文件、样例输入输出和运行证据 | `agentteams/chronosfix-team.yaml`、`agentteams/run_chronosfix_team.py`、`evidence/agentteams-run.json` | 已补强 |
| 可运行 Demo / Demo 视频 | 展示完整场景链路、Agent 协作、工具调用、异常处理与技术亮点 | 在线 Demo、`repair-cockpit/`、`docs/demo-video-script.md` | 已补强 |

## 2. 更新版方案内容要求

| 指南要求 | A-CFX 设计 | 证据文件 |
|---|---|---|
| 场景与方案更新 | 从“事故修复 Demo”升级为“研发质量资产平台”：故障时间机器、缺陷基因、证据护照、Skill 飞轮 | `README.md`、`docs/business-value.md` |
| 完整场景链路 | Issue/日志/Trace/Git/配置 → AgentTeams 拆解 → 反事实实验 → 补丁竞赛 → RiskGate → Evidence Passport → SkillForge | `demo.py`、`evidence/proof-report.md` |
| 样例输入输出 | 样例输入为订单接口超时事故，输出为 proof-bundle、proof-report、trace、metrics、AgentTeams transcript | `scenarios/checkout-timeout/scenario.json`、`evidence/` |
| 日志 / Trace / 指标 | Trace 记录 Agent/Skill 调用；Log 记录事件与权限范围；Metrics 记录根因、补丁、变体、成功率和耗时 | `evidence/trace.jsonl`、`evidence/run-log.jsonl`、`evidence/engineering-metrics.json` |
| GitHub Issue / PR 链路 | 事故进入 Issue，选中补丁形成 PR 草案，并附带 diff、checks、RiskGate 状态和审计事件 | `docs/github-issue-pr-flow.md`、`evidence/github-issue.md`、`evidence/github-pr.md` |
| 评测结果 | 自动化测试覆盖主因证明、审批阻断、补丁选择、Skill 沉淀 | `tests/test_pipeline.py`、`evidence/evaluation-report.md` |
| 自动化验证证据 | 一键运行单元测试与 AgentTeams 风格 Demo | `docs/deployment-and-verification.md` |
| Skill 工程实现 | 9 个核心 Skill，具备输入、输出、安全边界、复用价值和版本演进策略 | `docs/skill-specs.md` |
| 工具 / MCP / RAG / 可观测集成 | 当前使用等价契约与本地证据；复赛说明迁移到 MCP、云 Skills、Nacos、Higress、PolarDB、RocketMQ、AgentLoop 的接口 | `docs/official-infra-mapping.md`、`docs/interface-schema.md` |
| 接口 Schema / 数据流 | 定义 Incident、Trace、Tool Adapter、Skill、Evidence Passport、EventBus Schema | `docs/interface-schema.md` |
| 部署配置 | Python 标准库可复现；在线 Demo 通过 GitHub Pages 发布；复赛提供 AgentTeams 风格入口 | `README.md`、`docs/deployment-and-verification.md` |
| 失败处理 | RiskGate 无审批时阻断；工具契约定义 timeout/retry/idempotency/degrade | `tests/test_pipeline.py`、`docs/interface-schema.md` |
| 权限 / 审批 / 回滚 / 审计 | 只读分析自动化；模拟/测试隔离；中高风险动作人工审批；每个补丁必须有回滚契约 | `docs/safety-and-audit.md`、`evidence/proof-report.md` |
| 开放 / 开源计划 | Apache-2.0；开放核心代码、Skill 规格、样例数据、接口契约、运行报告 | `LICENSE`、`docs/open-source-compliance.md` |

## 3. 多 Agent 闭环八项核验

| 闭环环节 | A-CFX 实现 |
|---|---|
| 任务输入 | `scenario.json` 输入 Issue、Git、依赖、配置、流量与告警证据 |
| 任务拆解 | Incident Commander 将任务拆给 Timeline、Hypothesis、Universe、Patch、Verifier、Auditor、Skill Curator |
| 上下文传递 | Incident State 承载 timeline、hypotheses、experiments、variants、patch scores、approval、passport |
| 工具调用 | 本地等价工具契约模拟 Git/CI/Log/Trace/Config/Ticket；新增 GitHub Issue/PR API 等价输出；后续迁移 MCP |
| 结果验证 | CounterfactualReplay 与 PatchTournament 形成可复验数值 |
| 执行证据沉淀 | trace、log、metrics、proof-bundle、proof-report、agentteams-run、github issue/pr/checks/audit |
| 审批与回滚 | RiskGate 阻断未审批中风险补丁；EvidencePassport 写入 rollback claims |
| 经验沉淀 | SkillForge 输出 ConnectionPoolCapacityGuard、CounterfactualConfigReplay、ProofCarryingPatch |

## 4. 复赛风险清单与应对

| 可能扣分点 | 应对 |
|---|---|
| 只有 PPT、缺少 PoC | 仓库可运行，包含测试、Demo、Trace、Metrics、运行报告 |
| AgentTeams 只提名词 | 提供 AgentTeams YAML 与 `run_chronosfix_team.py`，输出 `agentteams-run.json` |
| 云 Skills 使用不清楚 | 在 `official-infra-mapping.md` 说明云 Skills 的鉴权、HITL、安全、编排和迁移 |
| 工具集成不可判断 | `interface-schema.md` 给出协议、鉴权、Schema、失败处理、审计与 MCP 迁移成本 |
| 研发协作流不真实 | 新增 `github-issue-pr-flow.md` 与 `evidence/github-*`，展示 Issue、PR、diff、checks、audit 的可迁移链路 |
| RAG 不足 | 明确实现共享状态、轨迹可观测、证据链持久化，并规划 PolarDB/pgvector 历史事故 RAG |
| 隐私/数据授权不清 | 当前样例为合成数据；真实企业数据接入时默认脱敏、最小权限、审计留痕 |
