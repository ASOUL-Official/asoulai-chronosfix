# fix(checkout): 恢复连接池 24 并增加容量验证门禁

PR：`#43`  
关联 Issue：`#42`  
分支：`chronosfix/inc-2026-0816-001-restore-pool` → `main`  
RiskGate：`approved`

## 根因证明

- 主因假设：`H-POOL` / 连接池缩容造成服务容量不足
- 基线失败率：48.7%
- 反事实失败率：0.0%
- 因果置信度：100.0%

## 变更摘要

- 选中补丁：`P-RESTORE-POOL` / 恢复连接池 24 并增加容量验证门禁
- 风险分：0.3
- 成本分：0.15

## 变更文件

- `configs/checkout-prod.yaml`
- `tests/test_checkout_capacity_guard.py`
- `docs/incidents/INC-2026-0816-001-evidence-passport.md`

## 验证结果

- 单元测试：passed
- 反事实回放：passed
- 缺陷基因变体：8
- 补丁候选数：4
- 最差失败率：6.2%
- Trace Span：16

## 证据护照摘录

### 因果声明

- 连接池缩容造成服务容量不足: 反事实撤销后失败率 48.7% -> 0.0%，因果置信度 100.0%
- 支付客户端升级放大请求占用时间: 单独撤销后失败率 33.3%，判定为放大因素

### 回滚声明

- 恢复 db.pool.maxSize=8 配置快照

## 合并策略

- 需要人工审批：是
- 需要全部检查通过：是
- 需要回滚契约：是
- 需要证据护照：是
