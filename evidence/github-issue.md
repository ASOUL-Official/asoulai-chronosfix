# [SEV-2] 订单创建接口在午间流量下出现高失败率与长尾延迟

> 本文件是本地可复现的 GitHub Issue 草案，不代表已写入远端仓库。

仓库：`ASOUL-Official/asoulai-chronosfix`
本地草案编号：`#42`
场景：`scenarios/checkout-timeout/scenario.json`
标签：incident, agentteams, needs-riskgate, local-draft, sev-2, checkout-timeout

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

- [ ] 反事实实验必须提供可复查的主因证据。
- [ ] 选中变更必须通过全部必选验证检查。
- [ ] PR 必须绑定场景、精确 changes、rollback_changes 与 RiskGate 决策。
- [ ] 缺少检查、回滚或必要人工审批时，PR 必须保持 draft。

## 关联证据

- `trace.jsonl`
- `run-log.jsonl`
- `proof-bundle.json`
- `proof-report.md`
- `run-manifest.json`
- `github-pr.md`
