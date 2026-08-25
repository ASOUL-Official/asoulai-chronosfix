# [SEV-2] 订单创建接口在午间流量下出现高失败率与长尾延迟

仓库：`ASOUL-Official/asoulai-chronosfix`  
Issue：`#42`  
标签：incident, sev-2, checkout, agentteams, needs-riskgate

## 影响

- 路由：`/api/order/create`
- 基线失败率：48.7%
- 基线 P99：606.96ms
- 严重等级：SEV-2

## 事故证据

- `commit` / `git:a91c7e`：为订单请求增加关联日志
- `dependency` / `lockfile:payment-client@2.0`：支付客户端升级，重试路径平均延迟增加
- `configuration` / `config:db.pool.maxSize`：数据库连接池从 24 调整为 8
- `traffic` / `metric:checkout.rps`：午间活动流量升至 120 RPS
- `incident` / `alert:checkout-5xx`：订单创建失败率和 P99 延迟同时升高

## 验收条件

- [ ] 反事实实验必须证明主因，而不是只给日志总结。
- [ ] 候选补丁必须通过缺陷基因变体回归。
- [ ] PR 必须包含 RiskGate 状态、回滚契约和证据护照链接。
- [ ] 中高风险变更无人工审批时必须保持 blocked-awaiting-human。

## 关联证据

- `trace.jsonl`
- `run-log.jsonl`
- `proof-bundle.json`
- `proof-report.md`
- `github-pr.md`
