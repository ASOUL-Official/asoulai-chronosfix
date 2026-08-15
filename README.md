# AsoulAI ChronosFix（A-CFX）：软件故障时间机器

队伍名称：**AsoulAI**

AsoulAI ChronosFix（A-CFX）是面向 GOAI 新智基座 Agent Infra「方向三：软件研发全流程协同」的初赛方案与可运行 Demo。它解决的不是“让 AI 看日志猜原因”，而是把线上故障修复升级为一条可回放、可验证、可审计、可复用的多 Agent 实验闭环。

一句话：A-CFX 让研发团队在事故发生后，自动重建时间线，在多个平行版本里撤销代码、配置、依赖等可疑变更，用反事实实验证明真正根因，再让补丁带着证据护照进入发布审批；更进一步，它把每次事故沉淀成可复用、可审计、可分发的“研发质量资产”。

## 评审快速使用

如果从 GitHub 首页进入，建议按下面顺序查看：

1. **在线 Demo**：打开 [AsoulAI ChronosFix Repair Cockpit](https://asoul-official.github.io/asoulai-chronosfix/)，直接查看时间线、反事实实验、官方 Baseline 对照、原创性边界、补丁竞赛、证据护照和商业价值飞轮。
2. **初赛方案 PPT**：查看 [`submission/ChronosFix_初赛方案.pptx`](submission/ChronosFix_初赛方案.pptx)，这是按官方初赛 PPT 内容框架重做的 19 页版本，覆盖 P0 速览、目录、场景价值、方案总览、多 Agent、Skill、工程验证、安全审计、开源计划、落地进展和团队提交物。
3. **500 字作品简介**：查看 [`submission/work-intro-500.txt`](submission/work-intro-500.txt)，可直接用于官方提交入口。
4. **官方 Baseline 对照**：查看 [`docs/official-baseline.md`](docs/official-baseline.md)，说明本方案如何对齐官方 OpsPilot Zero 示例，并在方向三上增强。
5. **原创性与命名边界**：查看 [`docs/originality-check.md`](docs/originality-check.md)，说明 A-CFX 如何避免与 GitHub 泛 Chronos / debugging-first 类项目混淆。
6. **可验证输出**：查看 [`evidence/proof-report.md`](evidence/proof-report.md)、[`evidence/proof-bundle.json`](evidence/proof-bundle.json) 和 [`evidence/trace.jsonl`](evidence/trace.jsonl)。

本地复现只需要 Python 标准库：

```powershell
git clone https://github.com/ASOUL-Official/asoulai-chronosfix.git
cd asoulai-chronosfix
python -m unittest discover -s tests -p "test_*.py" -q
python demo.py --approve --output evidence
```

如果只想看可视化演示，也可以直接打开：

```text
repair-cockpit/index.html
```

## 官方参考 Baseline

官方规范文件未提供必须继承的代码仓库型 baseline，但在 Agent Infra 赛道说明中给出了作品示例 Demo：**OpsPilot Zero——面向千行百业云上与自建 IDC 业务故障的零人工运维多 Agent 排查与自愈系统**。A-CFX 将它作为官方参考 Baseline：对齐其 AgentTeams、7 职能 Agent、Skill 工程化、MCP/适配器、Incident State、AgentLoop Trace、安全审计和初赛 Mock Demo 边界；同时把场景从运维故障自愈迁移到方向三的软件研发全流程协同，并新增反事实根因证明、缺陷基因实验室、证据护照和研发质量资产飞轮。

详细对照见 `docs/official-baseline.md`。

## 原创性与命名边界

公开展示统一使用 **AsoulAI ChronosFix（A-CFX）**，避免与 GitHub 上泛 Chronos / debugging-first 类项目混淆。A-CFX 的核心差异不是单点调试模型或自动补丁脚本，而是“反事实根因证明 + 故障基因实验室 + 证据护照 + Skill 飞轮”的研发质量资产闭环。详见 `docs/originality-check.md`。

## 核心创意

1. **故障时间机器**
   多 Agent 不直接下结论，而是把事故前后的 Git、依赖、配置、流量、告警证据拼成时间线；每个根因假设都必须在隔离平行宇宙中被撤销、重放、证伪或证实。

2. **缺陷基因实验室**
   系统从一个已证明的故障中繁殖出一组同源变体，例如边界流量、恢复期尖峰、下游抖动、隐性配置漂移。补丁必须通过这组“故障家族”而不是只修原始样例。

3. **证据护照**
   每个候选补丁都携带需求声明、因果声明、验证声明、风险声明、回滚声明和缺口声明。没有证据护照的补丁不能被标记为可发布。

4. **Skill 自进化工坊**
   一次事故处理完成后，系统会把有效经验蒸馏成可复用 Skill 候选，例如连接池容量守卫、反事实配置回放、带证明补丁生成器，让团队越用越强。

5. **研发质量资产交易所**
   事故不再只是成本中心。A-CFX 会把一次修复沉淀为三类资产：故障基因包、证据护照模板和可评测 Skill。企业内部可在多个研发团队复用，开源社区可沉淀行业样例，云厂商或平台方可把它变成面向 CI/CD、AIOps、DevSecOps 的 Agent Infra 增值能力。

## 商业价值与落地模式

A-CFX 的商业命题是：把线上事故处理从“专家临场救火”升级为“可复用质量资产生产线”。它面向三类付费场景：

- **中大型研发组织**：接入 Git、CI、日志、Trace、配置中心和工单系统，减少故障定位时间、降低误修复风险，并把复盘沉淀成跨团队复用的 Skill。
- **云厂商与 DevOps 平台**：作为 Agent Infra 插件能力嵌入 APM、CI/CD、配置中心、工单和发布平台，为客户提供“带证据的自动修复”。
- **开源与生态市场**：开放故障回放集、MCP 适配器模板和 Skill 规格，让社区贡献行业故障基因包，形成越用越强的数据与能力飞轮。

可收费形态包括团队版 SaaS、企业私有化部署、云市场插件、故障基因包/Skill 市场和高风险行业的审计合规模块。核心护城河不是单个模型，而是持续积累的反事实事故数据、补丁验证结果、证据护照和可复用 Skill 资产库。

## 初赛交付内容

- `demo.py`：可运行的反事实故障分析 Demo。
- `scenarios/checkout-timeout/scenario.json`：订单接口故障样例，包含 Git、依赖、配置、流量与告警证据。
- `src/chronosfix`：多 Agent 编排内核与可复用 Skill 实现。
- `tests/test_pipeline.py`：自动化测试，覆盖根因证明、故障变体、补丁选择、证据护照、Skill 沉淀和人工审批门禁。
- `evidence`：Demo 输出，包括 `trace.jsonl`、`proof-bundle.json` 和 `proof-report.md`。
- `repair-cockpit`：可直接打开的 Repair Cockpit 修复驾驶舱，用交互页面展示时间线、平行宇宙、缺陷基因、补丁竞赛、证据护照和 Skill 自进化。
- `docs`：官方参考 Baseline 对照、Agent Identity、Skill 工程体系、架构、安全审计、开源合规、商业化设计和赛题要求映射。
- `submission`：初赛作品简介、官方模板版 PPT 大纲与提交清单。
- `LICENSE`：Apache-2.0 开源协议。

## 快速运行

```powershell
cd D:\1\全球AI大赛\chronosfix
C:\Users\liuzhanxian\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest discover -s tests -v
C:\Users\liuzhanxian\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe demo.py --approve --output evidence
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
- 证据链：15 个 Trace Span，覆盖证据融合、时间线、反事实实验、故障基因、补丁竞赛、风险门禁、证据护照和 Skill Forge。

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

## 开源计划

初赛提交方案与可运行最小闭环；复赛补齐真实 Git 仓库适配器、CI 适配器、日志 Trace 适配器、配置中心 MCP Server、AgentTeams 部署说明和更多故障回放集。项目计划采用 Apache-2.0 协议开放核心代码、Skill 规格、MCP Schema、样例数据与评测脚本。
