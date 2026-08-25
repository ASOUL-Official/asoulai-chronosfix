# fix(checkout-timeout): 恢复连接池 24 并增加容量验证门禁

> 本文件是本地可复现的 GitHub PR 草案，不代表已创建远端分支或 PR。

本地草案编号：`#43`
关联 Issue：`#42`
场景：`scenarios/checkout-timeout/scenario.json`
分支：`chronosfix/inc-2026-0816-001-checkout-timeout-p-restore-pool` → `main`
状态：`ready-for-review`
RiskGate：`approved` / quality=`passed`

## 准入状态

- 结论：`ready`
- 缺失证据：none
- 失败证据：none

## 根因证明

- 主因假设：`H-POOL` / 连接池缩容造成服务容量不足
- 基线失败率：48.7%
- 反事实失败率：0.0%
- 干预效果分：100.0%（确定性回放效果比例，不是统计置信度）

## 变更合同

- 选中补丁：`P-RESTORE-POOL` / 恢复连接池 24 并增加容量验证门禁
- changes：`{"pool_size": 24}`
- rollback_changes：`{"pool_size": 8}`
- 回滚说明：恢复 db.pool.maxSize=8 配置快照

## 变更文件

- `changes/chronosfix/checkout-timeout/p-restore-pool.json`

## 已记录的验证检查

- `counterfactual-replay`：success（executed=True）
- `fault-gene-suite`：success（executed=True）
- `rollback-contract`：success（executed=True）

## 证据护照摘录

### 因果声明

- 连接池缩容造成服务容量不足: 反事实撤销后失败率 48.7% -> 0.0%，干预效果分 100.0%
- 支付客户端升级放大请求占用时间: 单独撤销后失败率 33.3%，判定为放大因素

### 回滚声明

- 恢复 db.pool.maxSize=8 配置快照
- 机器可验证回滚字段: {'pool_size': 8}。

## 合并策略

- 缺证据即保持 draft：是
- 需要全部必选检查通过：是
- 需要回滚合同与 rollback_changes：是
- 需要证据护照：是
