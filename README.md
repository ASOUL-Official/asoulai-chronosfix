# AsoulAI ChronosFix（A-CFX）：带证明的软件变更基础设施

队伍名称：**AsoulAI**

AsoulAI ChronosFix（A-CFX）是面向 GOAI 新智基座 Agent Infra「方向三：软件研发全流程协同」的复赛工程验证方案与可运行 Demo。它的底层逻辑不是“让 AI 自动修 Bug”，而是构建一套 **Proof-Carrying Software Change Infra（带证明的软件变更基础设施）**：每一次软件变更进入 PR、审批和发布链路前，都必须携带可回放、可验证、可审计、可复用的证据。

一句话：A-CFX 把线上事故转化为一条带证明的软件变更链：**事故证据 → 反事实证明根因 → 缺陷基因验证补丁 → RiskGate 审批 → GitHub PR / 证据护照 → Skill / 故障资产沉淀**。它让研发团队不是“相信 AI 的结论”，而是审查 AI 交付的证据。

## 底层逻辑：Proof-Carrying Software Change Infra

A-CFX 的核心判断是：企业不是缺少一个会生成补丁的 Agent，而是缺少一套能把“事故、代码、验证、审批、审计、复盘资产”串起来的软件变更基础设施。

```text
事故证据
  -> 反事实证明根因
  -> 缺陷基因验证补丁
  -> RiskGate 审批
  -> GitHub PR / 证据护照
  -> Skill / 故障资产沉淀
```

这条链把所有创新点收束到一个可评审、可落地、可商业化的主线上：

- **事故证据**：从 Issue、Git、依赖、配置、流量、告警、Trace 中抽取同一时间窗口的事实。
- **反事实证明根因**：在平行版本里撤销可疑变更并重放事故，把“时间相关”变成“因果可证”。
- **缺陷基因验证补丁**：从已证明根因繁殖同源故障变体，逼补丁修一类问题，而不是只修原始样例。
- **RiskGate 审批**：中高风险动作必须人类确认，系统保留 blocked、approved、rollback 和 evidence gap。
- **GitHub PR / 证据护照**：补丁不只给 diff，还携带因果、验证、风险、回滚、缺口声明，可直接进入研发协作流。
- **Skill / 故障资产沉淀**：把事故复盘蒸馏为可评测 Skill、故障基因包和证据模板，形成组织级质量资产飞轮。

完整设计说明见 [`docs/proof-carrying-change.md`](docs/proof-carrying-change.md)。

## 评审快速使用

如果从 GitHub 首页进入，建议按下面顺序查看：

1. **在线 Demo**：打开 [AsoulAI ChronosFix Repair Cockpit](https://asoul-official.github.io/asoulai-chronosfix/)，直接查看时间线、反事实实验、GitHub Issue/PR 模拟链路、官方 Baseline 对照、原创性边界、补丁竞赛、证据护照和商业价值飞轮。
2. **复赛方案 PPT / PDF**：查看 `submission/ChronosFix_复赛方案.pptx` 与 `submission/ChronosFix_复赛方案.pdf`，重点展示完整场景链路、样例输入输出、日志、Trace、指标、评测结果、自动化验证证据、官方 Infra 映射、风险边界与开放计划。
3. **500 字作品简介**：查看 [`submission/work-intro-500.txt`](submission/work-intro-500.txt)，可直接用于官方提交入口。
4. **官方 Baseline 对照**：查看 [`docs/official-baseline.md`](docs/official-baseline.md)，说明本方案如何对齐官方 OpsPilot Zero 示例，并在方向三上增强。
5. **原创性与命名边界**：查看 [`docs/originality-check.md`](docs/originality-check.md)，说明 A-CFX 如何避免与 GitHub 泛 Chronos / debugging-first 类项目混淆。
6. **可验证输出**：查看 [`evidence/proof-report.md`](evidence/proof-report.md)、[`evidence/proof-bundle.json`](evidence/proof-bundle.json)、[`evidence/trace.jsonl`](evidence/trace.jsonl) 和 [`evidence/github-pr.md`](evidence/github-pr.md)。
7. **复赛工程材料**：查看 [`docs/proof-carrying-change.md`](docs/proof-carrying-change.md)、[`docs/semifinal-guide-matrix.md`](docs/semifinal-guide-matrix.md)、[`docs/official-infra-mapping.md`](docs/official-infra-mapping.md)、[`docs/interface-schema.md`](docs/interface-schema.md)、[`docs/deployment-and-verification.md`](docs/deployment-and-verification.md)、[`docs/github-issue-pr-flow.md`](docs/github-issue-pr-flow.md)。

本地复现只需要 Python 标准库：

```powershell
git clone https://github.com/ASOUL-Official/asoulai-chronosfix.git
cd asoulai-chronosfix
python -m unittest discover -s tests -p "test_*.py" -q
python demo.py --approve --output evidence
python agentteams/run_chronosfix_team.py --approve --output output/agentteams-latest
```

如果只想看可视化演示，也可以直接打开：

```text
repair-cockpit/index.html
```

## 官方参考 Baseline

官方规范文件未提供必须继承的代码仓库型 baseline，但在 Agent Infra 赛道说明中给出了作品示例 Demo：**OpsPilot Zero——面向千行百业云上与自建 IDC 业务故障的零人工运维多 Agent 排查与自愈系统**。A-CFX 将它作为官方参考 Baseline：对齐其 AgentTeams、7 职能 Agent、Skill 工程化、MCP/适配器、Incident State、AgentLoop Trace、安全审计和初赛 Mock Demo 边界；同时把场景从运维故障自愈迁移到方向三的软件研发全流程协同，并新增反事实根因证明、缺陷基因实验室、证据护照和研发质量资产飞轮。

详细对照见 `docs/official-baseline.md`。

## 原创性与命名边界

公开展示统一使用 **AsoulAI ChronosFix（A-CFX）**，避免与 GitHub 上泛 Chronos / debugging-first 类项目混淆。A-CFX 的核心差异不是单点调试模型或自动补丁脚本，而是“带证明的软件变更链 + 反事实根因证明 + 故障基因验证 + PR 证据护照 + Skill 飞轮”的研发质量资产闭环。详见 `docs/originality-check.md`。

## 核心创意如何对应证明链

1. **故障时间机器**
   对应“事故证据 → 反事实证明根因”。多 Agent 不直接下结论，而是把事故前后的 Git、依赖、配置、流量、告警证据拼成时间线；每个根因假设都必须在隔离平行宇宙中被撤销、重放、证伪或证实。

2. **缺陷基因实验室**
   对应“缺陷基因验证补丁”。系统从一个已证明的故障中繁殖出一组同源变体，例如边界流量、恢复期尖峰、下游抖动、隐性配置漂移。补丁必须通过这组“故障家族”而不是只修原始样例。

3. **证据护照**
   对应“GitHub PR / 证据护照”。每个候选补丁都携带需求声明、因果声明、验证声明、风险声明、回滚声明和缺口声明。没有证据护照的补丁不能被标记为可发布。

4. **Skill 自进化工坊**
   对应“Skill / 故障资产沉淀”。一次事故处理完成后，系统会把有效经验蒸馏成可复用 Skill 候选，例如连接池容量守卫、反事实配置回放、带证明补丁生成器，让团队越用越强。

5. **研发质量资产交易所**
   事故不再只是成本中心。A-CFX 会把一次修复沉淀为三类资产：故障基因包、证据护照模板和可评测 Skill。企业内部可在多个研发团队复用，开源社区可沉淀行业样例，云厂商或平台方可把它变成面向 CI/CD、AIOps、DevSecOps 的 Agent Infra 增值能力。

## 商业价值与落地模式

A-CFX 的商业命题是：把线上事故处理从“专家临场救火”升级为“带证明的软件变更生产线”。它面向三类付费场景：

- **中大型研发组织**：接入 Git、CI、日志、Trace、配置中心和工单系统，减少故障定位时间、降低误修复风险，并把复盘沉淀成跨团队复用的 Skill。
- **云厂商与 DevOps 平台**：作为 Agent Infra 插件能力嵌入 APM、CI/CD、配置中心、工单和发布平台，为客户提供“带证明的 PR / 变更审批能力”。
- **开源与生态市场**：开放故障回放集、MCP 适配器模板和 Skill 规格，让社区贡献行业故障基因包，形成越用越强的数据与能力飞轮。

可收费形态包括团队版 SaaS、企业私有化部署、云市场插件、故障基因包/Skill 市场和高风险行业的审计合规模块。核心护城河不是单个模型，而是持续积累的反事实事故数据、补丁验证结果、PR 证据护照和可复用 Skill 资产库。

## 复赛交付内容

- `demo.py`：可运行的反事实故障分析 Demo。
- `scenarios/checkout-timeout/scenario.json`：订单接口故障样例，包含 Git、依赖、配置、流量与告警证据。
- `src/chronosfix`：多 Agent 编排内核与可复用 Skill 实现。
- `agentteams/chronosfix-team.yaml`：AgentTeams 编排草案。
- `agentteams/run_chronosfix_team.py`：可执行 AgentTeams 风格入口，输出 Manager/Worker、上下文传递和状态追踪证据。
- `tests/test_pipeline.py`：自动化测试，覆盖根因证明、故障变体、补丁选择、证据护照、Skill 沉淀和人工审批门禁。
- `evidence`：Demo 输出，包括 `trace.jsonl`、`run-log.jsonl`、`engineering-metrics.json`、`agentteams-run.json`、`evaluation-report.md`、`proof-bundle.json`、`proof-report.md`、`github-issue.md`、`github-pr.md`、`github-pr-diff.patch` 和 `github-pr-checks.json`。
- `repair-cockpit`：可直接打开的 Repair Cockpit 修复驾驶舱，用交互页面展示时间线、平行宇宙、缺陷基因、补丁竞赛、证据护照和 Skill 自进化。
- `docs`：复赛指南矩阵、官方 Infra 映射、GitHub Issue/PR 链路、接口 Schema、部署验证、Demo 视频脚本、Agent Identity、Skill 工程体系、架构、安全审计、开源合规、商业化设计。
- `submission`：复赛 PPT/PDF、作品简介、提交清单。
- `LICENSE`：Apache-2.0 开源协议。

## 快速运行

```powershell
cd D:\1\全球AI大赛\chronosfix
C:\Users\liuzhanxian\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest discover -s tests -v
C:\Users\liuzhanxian\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe demo.py --approve --output evidence
C:\Users\liuzhanxian\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe agentteams\run_chronosfix_team.py --approve --output output\agentteams-latest
```

打开可视化驾驶舱：

```powershell
start repair-cockpit\index.html
```

推送到 GitHub 后，仓库内置的 GitHub Pages 工作流会自动发布 `repair-cockpit` 目录，用作在线 Demo。

运行成功后会输出：

- 主要原因：连接池缩容造成服务容量不足。
- 被证伪原因：关联日志代码变更。
- 放大因素：支付客户端升级增加请求占用时间。
- 缺陷基因变体：8 个同源对抗场景。
- 选中补丁：恢复连接池 24 并增加容量验证门禁。
- 证据护照：12 条结构化证据声明。
- Skill 沉淀：3 个可复用 Skill 候选。
- 证据链：16 个 Trace Span，覆盖证据融合、时间线、反事实实验、故障基因、补丁竞赛、风险门禁、证据护照、GitHub Issue/PR 链路和 Skill Forge。
- 复赛工程证据：`run-log.jsonl`、`engineering-metrics.json`、`agentteams-run.json`、`evaluation-report.md`、`github-issue.md`、`github-pr.md`、`github-pr-diff.patch`、`github-pr-checks.json`。

## 已验证指标

- 基线失败率：48.72%。
- 基线 P99：606.96 ms。
- 根因假设：3 个。
- 平行实验：3 组。
- 补丁候选：4 个。
- 对抗变体：8 个。
- 选中补丁平均失败率：1.15%。
- 选中补丁最差失败率：6.25%。
- 审批策略：中高风险补丁必须人工确认，审批后才允许交付。

## AgentTeams 映射

A-CFX 的本地 Demo 使用确定性执行内核模拟 AgentTeams 协同流程；复赛阶段可迁移到 AgentTeams Manager-Workers 架构：

- Manager 对应 `Incident Commander`，负责任务拆解、状态流转、冲突裁决与人工升级。
- Workers 对应 Timeline、Hypothesis、Universe、Patch、Verifier、Auditor 等职能 Agent。
- `FaultGenome` 由 Universe Builder 承担，用于从主因繁殖故障变体。
- `EvidencePassport` 由 Release Auditor 承担，用于生成补丁发布证据。
- `SkillForge` 由 Commander 汇总，用于把事故经验沉淀成可复用 Skill。
- 共享状态对应 Incident State 与证据索引。
- Matrix Room 对应透明协作与人类可见干预。
- Higress/MCP 对应 Git、CI、日志、配置中心和工单系统接入层。
- MinIO/对象存储对应 Trace、报告、实验产物和回放数据沉淀。

相关编排草案见 `agentteams/chronosfix-team.yaml`。

复赛可执行入口：

```powershell
python agentteams/run_chronosfix_team.py --approve --output output/agentteams-latest
```

该入口会生成 `agentteams-run.json`，用于验证角色编排、任务拆解、上下文传递、协同执行和状态追踪。

## GitHub Issue / PR 模拟链路

A-CFX 已新增真实研发协作样机：运行 Demo 后会把事故证据生成 GitHub 风格 Issue，把选中补丁生成 PR 草案，并附带 diff、checks、RiskGate 状态和审计事件。当前为本地可复现模拟，不会主动写入真实 GitHub 账号；真实接入时可映射到 GitHub Issues、Pulls、Checks 和 Git Data API。

核心证据：

- `evidence/github-issue.md`：事故 Issue 正文。
- `evidence/github-pr.md`：PR 描述，包含根因证明、验证结果、回滚策略。
- `evidence/github-pr-diff.patch`：模拟补丁 diff。
- `evidence/github-pr-checks.json`：单测、反事实回放、故障基因、RiskGate 和证据护照检查。
- `evidence/github-review-audit.jsonl`：Issue、分支、PR、RiskGate 审计事件。

详见 `docs/github-issue-pr-flow.md`。

## 官方推荐 Infra 映射

A-CFX 已单独补齐官方推荐工具链说明，重点不是堆叠数量，而是接口契约与迁移边界：

- AgentTeams：多 Agent 协同基点。
- 阿里云云 Skills：云资源操作、HITL、Skill 发现与安装。
- Nacos：Agent、Skill、Prompt、配置和 MCP Endpoint 治理。
- Higress：模型、Agent 服务、MCP 工具和云 Skills 的统一网关。
- PolarDB for PostgreSQL：长记忆、RAG、审计日志和向量索引。
- UnifiedModel：Incident、Evidence、Patch、Skill 的实体关系图。
- RocketMQ：事件驱动、异步任务、可靠通知和执行状态流转。
- LoongSuite / AgentScope Studio / AgentLoop：Trace、Log、Metrics、评估和审计回放。

详见 `docs/official-infra-mapping.md`。

## 开源计划

复赛提交可运行工程材料、AgentTeams 风格入口、在线 Demo、GitHub Issue/PR 模拟链路、复赛 PPT/PDF、接口契约、运行报告和自动化验证证据；决赛继续补齐真实 GitHub API 写入、CI 适配器、日志 Trace 适配器、配置中心 MCP Server、真实历史事故 RAG 和更多故障回放集。项目采用 Apache-2.0 协议开放核心代码、Skill 规格、MCP Schema、样例数据与评测脚本。
