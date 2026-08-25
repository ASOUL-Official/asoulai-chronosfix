# 12 例合成评测结果

运行日期：2026-08-25

```powershell
python evaluate.py --output output/evaluation
```

> 所有样例均为确定性合成回放。以下结果用于描述当前模拟器的能力边界，不代表真实生产准确率。

## 汇总

| 指标 | 结果 | 正确解读 |
|---|---:|---|
| 总样例 | 12 | 9 Golden、2 Badcase、1 Insufficient Evidence |
| Golden 达成 | 9/9 | 当前建模范围内的诊断结果 |
| 受支持诊断准确率 | 9/9（100%） | 只覆盖模拟器明确建模且期望诊断的 9 例 |
| 整体达成预期 | 10/12（83.33%） | 包含 2 个未支持漏诊的保守总口径 |
| 预期拒答 | 1 | `conflicting-counterfactuals` |
| 正确拒答 | 1/1 | 相同干预无法区分来源时安全拒答 |
| 未支持 Badcase | 2 | 均 abstain，但没有命中已知真实原因，不计成功 |
| 状态分布 | correct=9、incorrect=0、abstain=3 | 两个未支持 Badcase 仍保留为未达预期 |

## 逐例结果

| 场景 | 类型 | 模型边界 | 期望 | 观测主因 | 状态 | 达成预期 |
|---|---|---|---|---|---|---|
| `api-timeout-amplifier` | Golden | supported | H-POOL | H-POOL | correct | yes |
| `cache-warmup-burst` | Golden | supported | H-POOL | H-POOL | correct | yes |
| `checkout-timeout` | Golden | supported | H-POOL | H-POOL | correct | yes |
| `code-latency-regression-primary` | Golden | supported | H-CODE | H-CODE | correct | yes |
| `config-drift-before-peak` | Golden | supported | H-POOL | H-POOL | correct | yes |
| `dependency-regression-primary` | Golden | supported | H-DEPENDENCY | H-DEPENDENCY | correct | yes |
| `downstream-jitter` | Golden | supported | H-POOL | H-POOL | correct | yes |
| `payment-client-slowdown` | Golden | supported | H-POOL | H-POOL | correct | yes |
| `recovery-spike` | Golden | supported | H-POOL | H-POOL | correct | yes |
| `code-regression-unmodeled` | Badcase | unsupported | H-CODE | - | abstain | no |
| `queue-backlog-unmodeled` | Badcase | unsupported | H-QUEUE | - | abstain | no |
| `conflicting-counterfactuals` | Insufficient Evidence | supported | abstain | - | abstain | yes |

## 为什么 Badcase 的 abstain 仍不算成功

两个 Badcase 的真实原因已知，但当前模拟器没有对应因果变量。系统没有强行归因是较安全的行为，却仍然没有完成正确诊断，因此 `expectation_met=no`。它们被排除在“受支持诊断准确率”之外，但保留在 12 例整体结果里。

## 可辨识性仲裁

`conflicting-counterfactuals` 中，两个来源假设映射到相同干预，单次回放无法区分具体来源。评测器会将结果降级为 `indeterminate` 并安全拒答，因此正确拒答为 1/1。这个机制只解决“相同干预不可辨识”的冲突；缺失来源级证据时仍不会生成补丁或进入发布链路。

机器可读结果由评测命令生成，文档中的数字不作为唯一证据。
