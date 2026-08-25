# Proof-Carrying Software Change Infra：底层逻辑

ChronosFix 解决的是“AI 结论怎样安全进入研发协作流”，而不只是“怎样生成补丁”。任何变更草案都必须携带可回放的因果、验证、风险、审批、回滚和完整性证据。

```text
事故证据
  -> 反事实干预
  -> 可辨识性仲裁
  -> 故障族验证
  -> 质量门禁
  -> 具名风险审批
  -> PR 本地草案 / Evidence Passport
  -> Skill Candidate / run manifest
```

## 六个环节

| 环节 | 交付物 | 当前实现边界 |
|---|---|---|
| 事故证据 | timeline、evidence index、baseline | 合成 scenario |
| 反事实证明 | hypothesis、intervention、effect score、classification | 确定性模拟；effect score 非统计置信度 |
| 故障族验证 | mandatory variants、patch ranking | 本地合成回放 |
| 质量与审批 | quality gate、具名 approval record | fail-closed；未接企业审批系统 |
| PR 与护照 | changes、rollback、checks、claims、hashes | local-draft；Issue #1/PR #2 仅 documentation-only |
| 资产沉淀 | skill candidates、evaluation fixtures | 候选资产，不自动上线 |

## 反事实不等于置信度

`intervention_effect_score` 表示确定性回放中干预带来的相对失败率改善。它不能解释为真实世界因果概率或统计显著性。当不同来源假设使用相同干预而无法区分时，可辨识性仲裁将结果降级为 `indeterminate` 并拒答。

## 质量不能被人类批准覆盖

RiskGate 检查主因、全部强制变体、missing claims、机器可读回滚和 required checks。中高风险另需具名人类审批。人工审批只代表风险接受，不会把 `blocked-quality-gate` 改成通过。

## 证据完整性

每次运行生成唯一 run/trace；主场景当前有 18 个 Span。端到端耗时和 Span duration 为本地实测，派生指标另行标记。`run-manifest.json` 用 SHA-256 绑定输入、补丁、回滚、审批和主要产物，便于发现证据漂移。

## 当前完成度

- 核心确定性流水线：已实现并测试；
- 12 例合成评测：9/9 受支持诊断，10/12 整体达成，1/1 冲突拒答；
- AgentTeams：v1beta1 正式资源离线校验，Controller 未运行；
- 官方 SLS Skill：契约测试 + dry-run，真实云查询未完成；
- GitHub：本地 PR 草案，公开 Issue #1/PR #2 为 documentation-only；
- 其他云组件：接口与迁移设计，未部署。

## 商业假设

候选价值是降低从事故到可审查变更材料的协作成本，而不是直接替代发布负责人。是否缩短 MTTR、减少误修或产生 ROI，需要通过真实事故、人类 baseline 和客户试点测量；当前不把这些目标写成已实现结果。
