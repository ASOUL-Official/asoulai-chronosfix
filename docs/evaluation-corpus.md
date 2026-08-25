# 故障回放评测集

复赛主 Demo 使用 `scenarios/checkout-timeout/scenario.json` 保持讲解稳定。为了补强决赛前的工程可信度，A-CFX 额外加入 6 个同构事故样例，用于验证同一条 Proof-Carrying Software Change Chain 能覆盖不同触发条件。

统一证明链：

```text
事故证据 -> 反事实证明根因 -> 缺陷基因验证补丁 -> RiskGate 审批 -> GitHub PR / 证据护照 -> Skill / 故障资产沉淀
```

| 场景 | 主要触发 | 评测目的 |
|---|---|---|
| `checkout-timeout` | 午间流量 + 连接池缩容 | 主 Demo，展示完整链路 |
| `config-drift-before-peak` | 隐性配置漂移 | 验证配置中心漂移类事故 |
| `payment-client-slowdown` | 支付依赖变慢 + 容量不足 | 验证依赖升级是放大因素而非唯一根因 |
| `recovery-spike` | 恢复窗口流量尖峰 | 验证恢复/回放任务造成的短时峰值 |
| `downstream-jitter` | 下游服务抖动 | 验证长尾依赖抖动下的补丁鲁棒性 |
| `cache-warmup-burst` | 缓存预热后流量回灌 | 验证缓存恢复期的容量门禁 |
| `api-timeout-amplifier` | API timeout 策略放大请求占用 | 验证超时策略与连接池容量的交互 |

## 当前实测口径

每个场景都会执行完整 pipeline，并检查：

- 至少存在一个被反事实证明的 primary-cause。
- 自动生成 Trace、proof-bundle、proof-report、GitHub Issue/PR 草案、checks 和审计事件。
- Evidence Passport 至少包含因果、验证、风险和回滚声明。
- Trace Span 维持 16 段，说明 GitHub Issue / PR 链路被纳入证据链。

## 后续增强

决赛阶段可继续扩展为三类评测：

1. **Golden Case**：真实历史事故脱敏后转成标准输入，要求证明链输出与专家结论一致。
2. **Badcase**：故意加入相邻但非根因的代码/依赖/配置变更，评测误归因率。
3. **Regression Case**：把故障基因包接入 CI，评测补丁在同源变体上的通过率、最差失败率和回滚完整度。
