# 安全边界与审计

ChronosFix 的核心规则是：**人工可以接受风险，不能批准失败质量。**

## 风险与质量分离

| 维度 | 检查内容 | 失败状态 |
|---|---|---|
| 质量门禁 | 主因、强制变体、missing claims、回滚、required checks | `blocked-quality-gate` |
| 风险审批 | 风险等级、具名审批人、理由、时间、策略版本、输入摘要 | `blocked-awaiting-human` |

只有 `quality_gate=passed` 且审批条件满足，`release_ready` 才能为 true。

## 风险等级

| 等级 | 动作 | 当前策略 |
|---|---|---|
| L0 | 读取本地场景、日志、Git/Trace 摘要 | 自动 |
| L1 | 隔离回放、生成故障变体、生成草案 | 自动 |
| L2 | 测试配置、修复分支、触发 CI | 策略检查；真实外部写入尚未接入 |
| L3 | 共享/生产配置或发布 | 必须具名人工审批；当前不执行 |

主场景选中补丁风险为 medium，因此需要具名审批。命令行 `--approve` 必须同时提供 `--approver`；审批记录包含 reason、timestamp、policy_version 和 input_digest。匿名、bot、system 等主体不能作为有效人类审批人。

## 质量门禁

以下任一条件失败都会 fail-closed：

- 未证明 primary cause；
- 强制变体失败或缺失；
- 存在任何未处理的 missing claim；
- 缺少 rollback contract；
- rollback changes 不能恢复场景基线；
- required check 未执行、失败或缺少 exit code/run ID 等结果证据。

低风险可以不要求人工审批，但仍必须通过质量门禁。

## 回滚

每个 Patch Candidate 都需要：

- `changes`；
- 字段集合一致的 `rollback_changes`；
- rollback 值与场景 baseline 一致；
- 人类可读回滚说明；
- 本地往返验证结果。

这证明本地状态契约可回退，不等同于已经在生产环境演练回滚。

## 可辨识性与拒答

`intervention_effect_score` 只描述确定性干预效果，不是统计置信度。若多个来源假设映射到同一干预，系统将其标记为 `indeterminate` 并拒答；没有来源级证据时不生成发布结论。

## 审计产物

- `trace.jsonl`：run/trace/span、父子关系、实测时间和 payload；
- `run-log.jsonl`：决策、权限范围和失败处理；
- `proof-bundle.json` / `proof-report.md`：实验、补丁、门禁和声明；
- `github-review-audit.jsonl`：local-draft 协作事件；
- `run-manifest.json`：场景、补丁、回滚、审批与产物 SHA-256。

SHA-256 用于发现本地文件漂移，不是数字签名、可信时间戳或远程不可抵赖审计。

## 外部系统边界

- GitHub local-draft 不具有外部写权限；
- 公开 Issue #1/PR #2 为 documentation-only；
- 官方 SLS Skill 当前仅 dry-run；
- AgentTeams Controller/Matrix 未运行；
- Nacos、Higress、PolarDB、RocketMQ、AgentLoop 尚未部署。

真实接入必须使用最小权限、凭据隔离、调用审计和显式撤销/回滚。
