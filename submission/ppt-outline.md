# AsoulAI ChronosFix（A-CFX）初赛 PPT 大纲

本版 PPT 按官方《初赛方案 PPT 内容框架模板》重做，共 19 页，覆盖 P0 一页纸速览、目录、七个核心章节和团队提交物。视觉上采用“官方章节分隔 + 白底内容页 + 评分维度显性标注”的结构，避免只讲创意而漏掉官方评分项。

## 1. 封面

- AsoulAI ChronosFix / A-CFX：软件故障时间机器。
- 方向三：软件研发全流程协同。
- 副标题：把线上事故沉淀为可复用 Skill、故障基因包和证据护照。

## 2. P0 · 一页纸速览

- 项目名称、问题与场景、核心方案、创新差异、开放复用价值、当前进展。
- 明确 A-CFX 不是普通 Debug Bot，而是研发质量资产平台。

## 3. 目录

- 按官方模板组织：场景价值、方案总览、多 Agent、Skill、工程验证与安全、开源计划、落地进展、团队与提交物。

## 4. 第一章 · 场景与价值

- 对应评分维度：场景价值与行业可复制性 25%。

## 5. 场景与价值内容页

- 目标用户：中大型研发组织、平台工程团队、云厂商 DevOps / AIOps 产品线。
- 痛点：故障窗口内代码、配置、依赖、流量同时变化，AI 总结无法证明因果。
- 可复制价值：订单、支付、网关、库存、配置治理等场景都可迁移。
- Demo 指标：48.72% 基线失败率、606.96ms P99、8 个故障基因变体、12 条证据护照声明。

## 6. 第二章 · 方案总览

- 对应官方建议：用一张架构图讲清端到端流程和关键技术选型。

## 7. 方案总览内容页

- 官方参考 Baseline：OpsPilot Zero。
- A-CFX 对齐：AgentTeams、7 职能 Agent、Skill、MCP/Adapter、Trace、RiskGate。
- A-CFX 增强：从运维自愈迁移到软件研发全流程协同，新增反事实证明、故障基因、证据护照和质量资产飞轮。

## 8. 第三章 · 多 Agent 协同设计

- 对应评分维度：多 Agent 协同与自主闭环能力 25%。

## 9. 多 Agent 协同内容页

- 7 个职能 Agent：Commander、Timeline、Hypothesis、Universe、Patch、Verifier、Auditor。
- 共享 Incident State、反事实实验裁决冲突、高风险动作由 RiskGate 阻断。

## 10. 第四章 · Skill 工程体系

- 对应评分维度：Skill 工程体系与生态复用 25%。

## 11. Skill 工程体系内容页

- 9 个 Skill：EvidenceFusion、ChangeTimeline、CounterfactualReplay、FaultGenome、PatchTournament、RiskGate、EvidencePassport、ProofReport、SkillForge。
- 强调输入输出、失败处理、复用边界和生命周期管理。

## 12. 第五章 · 工程落地、运行验证与安全可审计

- 对应评分维度：工程落地与安全可审计 20%。

## 13. 工程验证与安全内容页

- 可运行 Demo、Repair Cockpit、15 段 Trace、proof-bundle、proof-report。
- 中高风险补丁必须人工审批；每个补丁携带回滚策略与缺口声明。

## 14. 第六章 · 开放 / 开源计划

- 对应评分维度：开放 / 开源贡献 5%。

## 15. 开源开放与原创性边界

- 公开仓库统一使用 AsoulAI ChronosFix / A-CFX，避免与 GitHub 泛 Chronos / debugging-first 类项目混淆。
- 差异化：A-CFX 是多 Agent 事故实验闭环，不是单点调试模型或自动补丁脚本。

## 16. 第七章 · 落地计划与进展

- 对应官方建议：当前进展、里程碑、落地计划与风险控制。

## 17. 落地计划内容页

- 初赛已完成：本地 Demo、Repair Cockpit、官方模板版 PPT、公开仓库、测试与证据链。
- 复赛增强：真实 Git / CI、日志 Trace 适配器、历史事故 RAG、AgentTeams 部署、更多故障回放集。
- 决赛展示：现场故障回放、多团队 Skill 复用、审计证据导出、商业化插件样机。

## 18. 第八章 · 团队介绍

- 队伍：AsoulAI。
- 说明提交入口和可验证材料。

## 19. 团队与提交物

- 队伍名称、作品名称、代码仓库、在线 Demo、PPT、500 字简介、evidence 证据目录。
- 总结：让软件修复从经验猜测升级为可回放、可审计、可复用、可商业化的研发质量资产闭环。
