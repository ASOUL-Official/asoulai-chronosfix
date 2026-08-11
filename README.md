# ChronosFix：软件故障时间机器

队伍名称：**AsoulAI**

ChronosFix 是面向 GOAI 新智基座 Agent Infra「方向三：软件研发全流程协同」的初赛方案与可运行 Demo。它解决的不是“让 AI 看日志猜原因”，而是把线上故障修复升级为一条可回放、可验证、可审计、可复用的多 Agent 实验闭环。

一句话：ChronosFix 让研发团队在事故发生后，自动重建时间线，在多个平行版本里撤销代码、配置、依赖等可疑变更，用反事实实验证明真正根因，再让补丁带着证据护照进入发布审批。

## 核心创意

1. **故障时间机器**
   多 Agent 不直接下结论，而是把事故前后的 Git、依赖、配置、流量、告警证据拼成时间线；每个根因假设都必须在隔离平行宇宙中被撤销、重放、证伪或证实。

2. **缺陷基因实验室**
   系统从一个已证明的故障中繁殖出一组同源变体，例如边界流量、恢复期尖峰、下游抖动、隐性配置漂移。补丁必须通过这组“故障家族”而不是只修原始样例。

3. **证据护照**
   每个候选补丁都携带需求声明、因果声明、验证声明、风险声明、回滚声明和缺口声明。没有证据护照的补丁不能被标记为可发布。

4. **Skill 自进化工坊**
   一次事故处理完成后，系统会把有效经验蒸馏成可复用 Skill 候选，例如连接池容量守卫、反事实配置回放、带证明补丁生成器，让团队越用越强。

## 初赛交付内容

- `demo.py`：可运行的反事实故障分析 Demo。
- `scenarios/checkout-timeout/scenario.json`：订单接口故障样例，包含 Git、依赖、配置、流量与告警证据。
- `src/chronosfix`：多 Agent 编排内核与可复用 Skill 实现。
- `tests/test_pipeline.py`：自动化测试，覆盖根因证明、故障变体、补丁选择、证据护照、Skill 沉淀和人工审批门禁。
- `evidence`：Demo 输出，包括 `trace.jsonl`、`proof-bundle.json` 和 `proof-report.md`。
- `repair-cockpit`：可直接打开的 Repair Cockpit 修复驾驶舱，用交互页面展示时间线、平行宇宙、缺陷基因、补丁竞赛、证据护照和 Skill 自进化。
- `docs`：Agent Identity、Skill 工程体系、架构、安全审计、开源合规和赛题要求映射。
- `submission`：初赛作品简介、PPT 大纲与提交清单。
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

ChronosFix 的本地 Demo 使用确定性执行内核模拟 AgentTeams 协同流程；复赛阶段可迁移到 AgentTeams Manager-Workers 架构：

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
