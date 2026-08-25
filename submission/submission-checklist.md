# 复赛提交清单

队伍名称：**AsoulAI**

## 必交材料

- [x] 更新版复赛项目方案 PPT：`submission/ChronosFix_复赛方案.pptx`
- [x] 更新版复赛项目方案 PDF：`submission/ChronosFix_复赛方案.pdf`
- [x] 可执行 AgentTeams 代码包：`agentteams/chronosfix-team.yaml`、`agentteams/run_chronosfix_team.py`
- [x] 可运行 Demo：`demo.py`
- [x] 在线 / 本地 Repair Cockpit：`repair-cockpit/index.html`
- [x] Demo 视频脚本：`docs/demo-video-script.md`
- [x] 复赛指南对照矩阵：`docs/semifinal-guide-matrix.md`
- [x] 500 字以内作品简介：`submission/work-intro-500.txt`
- [x] 评审入口说明：`提交入口说明.md`

## 方案完整度材料

- [x] 最新参赛指南要求映射：`docs/semifinal-guide-matrix.md`
- [x] 官方推荐 Agent Infra 映射：`docs/official-infra-mapping.md`
- [x] 带证明的软件变更基础设施底层逻辑：`docs/proof-carrying-change.md`
- [x] 真实 AgentTeams runtime 接入判断：`docs/agentteams-runtime-integration.md`
- [x] 官方组件分阶段部署策略：`docs/production-deployment-strategy.md`
- [x] 决赛实测方案：`docs/measurement-plan.md`
- [x] 接口 Schema、数据流与等价 MCP 契约：`docs/interface-schema.md`
- [x] 部署、运行与验证说明：`docs/deployment-and-verification.md`
- [x] GitHub Issue / PR 模拟链路：`docs/github-issue-pr-flow.md`
- [x] 真实 GitHub Issue / PR 协作证据：`docs/live-github-collaboration-evidence.md`、Issue #1、PR #2
- [x] Agent 身份与分工：`docs/agent-identity.md`
- [x] Skill 工程体系：`docs/skill-specs.md`
- [x] 创新层设计：`docs/innovation-layer.md`
- [x] 商业价值与产业化设计：`docs/business-value.md`
- [x] 官方 OpsPilot Zero 参考基线对齐与增强说明：`docs/official-baseline.md`
- [x] 架构说明：`docs/architecture.md`
- [x] 安全与审计：`docs/safety-and-audit.md`
- [x] 开源合规计划：`docs/open-source-compliance.md`
- [x] 避免 GitHub 泛 Chronos 项目混淆的 A-CFX 命名边界：`docs/originality-check.md`

## 可验证产物

- [x] 故障场景数据：`scenarios/checkout-timeout/scenario.json`
- [x] 扩展故障回放评测集：`docs/evaluation-corpus.md`、`scenarios/*/scenario.json`
- [x] 7 场景实测汇总：`docs/evaluation-corpus-results.md`
- [x] 自动化测试：`tests/test_pipeline.py`
- [x] Trace：`evidence/trace.jsonl`
- [x] 结构化日志：`evidence/run-log.jsonl`
- [x] 工程 Metrics：`evidence/engineering-metrics.json`
- [x] AgentTeams 运行转录：`evidence/agentteams-run.json`
- [x] 复赛评测报告：`evidence/evaluation-report.md`
- [x] GitHub Issue：`evidence/github-issue.md`
- [x] GitHub PR 草案：`evidence/github-pr.md`
- [x] GitHub PR Diff：`evidence/github-pr-diff.patch`
- [x] GitHub PR Checks：`evidence/github-pr-checks.json`
- [x] GitHub 审计事件：`evidence/github-review-audit.jsonl`
- [x] 证据包：`evidence/proof-bundle.json`
- [x] 证明报告：`evidence/proof-report.md`

## 当前 Demo 已覆盖

- [x] 7 个职能 Agent。
- [x] 9 个可复用 Skill。
- [x] 3 个根因假设。
- [x] 3 组反事实平行实验。
- [x] 8 个缺陷基因变体。
- [x] 7 个可运行事故场景。
- [x] 4 个补丁候选竞赛。
- [x] 1 个证据护照。
- [x] 3 个 Skill 候选沉淀。
- [x] 16 段 Trace Span。
- [x] 1 个可交互修复驾驶舱。
- [x] 1 条 Proof-Carrying Software Change Chain。
- [x] 1 条研发质量资产商业飞轮。
- [x] 中风险补丁人工审批门禁。

## 复赛增强路线

- [x] 将本地 Skill 映射为 AgentTeams Worker Skill。
- [x] 补齐官方云 Skills、Nacos、Higress、PolarDB、UnifiedModel、RocketMQ、AgentLoop 映射。
- [x] 增加日志、Metrics、AgentTeams transcript 和复赛评测报告。
- [x] 增加 GitHub Issue / PR 模拟链路，补齐真实研发协作流证据。
- [x] 增加“事故证据 → 反事实根因 → 缺陷基因 → RiskGate → PR 证据护照 → Skill 沉淀”的统一底层逻辑。
- [x] 增加部署复现和失败处理说明。
- [ ] 决赛接入真实 Git 仓库与 PR。
- [ ] 决赛接入 CI、压测和日志 Trace 平台。
- [ ] 决赛接入配置中心与发布审批系统。
- [ ] 决赛增加历史故障 RAG 与 Runbook 检索。
- [ ] 决赛建立多项目故障回放评测集。
