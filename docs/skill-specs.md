# Skill 工程体系

ChronosFix 把软件故障处理拆成 9 个可复用 Skill。每个 Skill 都有稳定输入、输出、安全边界和失败处理，方便后续迁移到 AgentTeams Worker、MCP 工具、阿里云云 Skills 或企业内部平台。

| Skill 名称 | 类型 | 使用场景 | 输入 | 输出 | 安全边界 | 复用价值 |
|---|---|---|---|---|---|---|
| EvidenceFusion | 自定义 Skill | 故障进入后融合多源证据 | Issue、日志、Trace、Git、配置事件 | Incident State、证据索引 | 只读访问，敏感字段脱敏 | 可用于运维、安全、客服事件分析 |
| ChangeTimeline | 自定义 Skill | 重建故障前后事件序列 | ChangeEvent 列表 | 排序后的时间线 | 不执行外部变更 | 可用于发布复盘和事故复盘 |
| CounterfactualReplay | 自定义 Skill | 验证根因假设 | Baseline State、Hypothesis Intervention | 失败率、P99、因果置信度 | 只在隔离环境回放 | 可用于性能回退、依赖升级、配置变更分析 |
| FaultGenome | 创新 Skill | 从已证明根因繁殖故障变体 | Baseline、实验结果、种子场景 | 同源缺陷变体族 | 只生成测试场景，不发布变更 | 可把一次事故变成一组回归测试资产 |
| PatchTournament | 自定义 Skill | 比较多个修复方案 | PatchCandidate、故障变体 | 补丁排名、平均/最差失败率、风险成本分 | 只产出建议，不直接发布 | 可用于自动修复、代码评审和发布前验证 |
| RiskGate | 安全 Skill | 中高风险动作前审批 | 选中补丁、风险分、审批状态 | approved 或 blocked-awaiting-human | 未审批时阻断执行 | 可用于运维、安全、FinOps 等高风险动作 |
| EvidencePassport | 创新 Skill | 为补丁生成发布证明 | Incident State、选中补丁、Trace | 需求、因果、验证、风险、回滚、缺口声明 | 缺少关键声明时不得标记可发布 | 让自动修复具备可解释、可审计、可追责能力 |
| SkillForge | 创新 Skill | 从事故中沉淀可复用 Skill | 已完成事故、证据护照、故障变体 | Skill 候选、Schema、评测案例、安全边界 | 只生成候选，不自动上线新 Skill | 建立“事故变资产”的组织学习闭环 |
| ProofReport | 自定义 Skill | 产出证据化 PR/报告 | Incident State、Metrics、Trace | proof-report.md、proof-bundle.json | 不包含密钥或原始敏感数据 | 可用于审计、复盘和知识库沉淀 |

## 生命周期设计

- **版本**：每个 Skill 使用语义化版本；输入输出 Schema 发生兼容性变更时提升 minor，不兼容时提升 major。
- **发布**：初赛以本地 Python Skill 交付；复赛封装为 AgentTeams Worker Skill、云 Skills 映射和 MCP 工具说明。
- **评估**：以故障回放集统计根因准确率、补丁通过率、误判率、人工审批命中率和证据护照完整率。
- **回滚**：Skill Registry 保留上一个稳定版本；如果新版本误判率上升，回退到前一版本。
- **沉淀**：SkillForge 会把一次事故的有效处理模式输出为 Skill Candidate，进入人工评审和回放评测后再注册。

## 云 Skills 门户映射

| A-CFX Skill | 云 Skills 接入方式 | 鉴权 | 编排位置 | 失败处理 |
|---|---|---|---|---|
| EvidenceFusion | 调用 SLS、CloudMonitor、资源中心、Nacos 只读 Skills 获取证据 | RAM 只读策略 | Commander / Timeline | 证据缺失时写入 missing evidence，不强判主因 |
| CounterfactualReplay | 调用配置读取、沙箱环境、CI 触发类 Skills | 沙箱或测试环境权限 | Universe Builder | 沙箱不可用时降级为本地模拟并标注证据等级 |
| RiskGate | 接入云 Skills HITL 协作平台 | 人工确认 + 操作审计 | Release Auditor | 未审批返回 `blocked-awaiting-human` |
| EvidencePassport | 写入工单、知识库、审计存储类 Skills | 写证据库权限，不写生产配置 | Release Auditor | 缺少因果/验证/回滚声明时禁止可发布 |
| SkillForge | 对接云 Skills 门户 / Skill Forge 共建流程 | 仅生成候选，发布需人工评审 | Skill Curator | 新 Skill 不自动上线，必须回放评测 |

## 复赛必填字段覆盖

| 字段 | 覆盖方式 |
|---|---|
| Skill 名称 | 上表与 9 个核心 Skill 清单 |
| 用途 | 每个 Skill 的使用场景 |
| 输入与输出 | 表格与关键契约示例 |
| 调用条件 | 由 AgentTeams 任务拆解和 incident state 触发 |
| 依赖工具 | MCP/Adapter/云 Skills 映射 |
| 失败处理机制 | 证据缺口、重试、降级、RiskGate 阻断 |
| 安全边界 | 只读优先、隔离实验、中高风险人工审批 |
| 复用价值 | 故障基因包、证据护照、Skill Candidate |
| 多 Agent 关系 | 每个 Skill 绑定 Manager/Worker 角色 |

## 关键 Skill 契约示例

### FaultGenome

```json
{
  "input": ["baseline", "primary_cause", "seed_mutations"],
  "output": ["fault_variants"],
  "safety": "仅生成测试变体，不修改生产系统",
  "evaluation": "选中补丁必须在全部变体上满足健康阈值"
}
```

### EvidencePassport

```json
{
  "input": ["selected_patch", "counterfactual_experiments", "patch_scores", "approval"],
  "output": ["requirement_claims", "causal_claims", "verification_claims", "risk_claims", "rollback_claims", "missing_claims"],
  "safety": "缺少因果、验证、风险或回滚声明时，不允许自动发布"
}
```

### SkillForge

```json
{
  "input": ["resolved_incident", "fault_variants", "evidence_passport"],
  "output": ["skill_candidates"],
  "safety": "只生成候选 Skill，需要人工评审和回放评测后才能注册"
}
```
