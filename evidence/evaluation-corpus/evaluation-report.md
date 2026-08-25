# ChronosFix Golden / Badcase 评测报告

> 口径：本报告由 `python -m chronosfix.evaluation` 从场景 Ground Truth 自动生成；
> 数据为确定性合成回放，不代表真实生产环境准确率。

## 汇总

- 总样例：12。
- 样例构成：Golden 9，Badcase 2，Insufficient Evidence 1；其中评测专用夹具 3。
- 当前模拟器可支持的诊断样例：9，正确 9，限定口径准确率 100.0%。
- 预期拒答样例：1，正确拒答 1，拒答成功率 100.0%。
- 当前模型不支持样例：2；未达到理想预期 2，错误强行归因 0。
- 应拒答却仍给出主因的样例：0；这些样例按失败保留，不计入成功数。
- 状态分布：correct=9，incorrect=0，abstain=3。

## 逐例结果

| 场景 | 类型 | 执行范围 | 模型边界 | 期望 | 观测主因 | 状态 | 达成期望 |
|---|---|---|---|---|---|---|---|
| `api-timeout-amplifier` | golden | pipeline-and-evaluation | supported | H-POOL | H-POOL | correct | yes |
| `cache-warmup-burst` | golden | pipeline-and-evaluation | supported | H-POOL | H-POOL | correct | yes |
| `checkout-timeout` | golden | pipeline-and-evaluation | supported | H-POOL | H-POOL | correct | yes |
| `code-latency-regression-primary` | golden | pipeline-and-evaluation | supported | H-CODE | H-CODE | correct | yes |
| `config-drift-before-peak` | golden | pipeline-and-evaluation | supported | H-POOL | H-POOL | correct | yes |
| `dependency-regression-primary` | golden | pipeline-and-evaluation | supported | H-DEPENDENCY | H-DEPENDENCY | correct | yes |
| `downstream-jitter` | golden | pipeline-and-evaluation | supported | H-POOL | H-POOL | correct | yes |
| `code-regression-unmodeled` | badcase | evaluation-only-counterfactual | unsupported | H-CODE | - | abstain | no |
| `conflicting-counterfactuals` | insufficient-evidence | evaluation-only-counterfactual | supported | abstain | - | abstain | yes |
| `queue-backlog-unmodeled` | badcase | evaluation-only-counterfactual | unsupported | H-QUEUE | - | abstain | no |
| `payment-client-slowdown` | golden | pipeline-and-evaluation | supported | H-POOL | H-POOL | correct | yes |
| `recovery-spike` | golden | pipeline-and-evaluation | supported | H-POOL | H-POOL | correct | yes |

## 结果解释

- `correct`：系统给出的主因集合与 Ground Truth 完全一致。
- `incorrect`：系统给出了主因，但与 Ground Truth 不一致，或在应拒答时强行归因。
- `abstain`：没有可辨识的假设达到主因阈值；相同干预对应多个来源假设时会安全拒答。
- `supported_diagnosis_accuracy` 只覆盖模拟器实际建模的容量与依赖延迟变量。
- `evaluation-only-counterfactual` 夹具只运行反事实分类，不进入补丁、RiskGate 或 PR 流水线。
- `code_version`、队列深度当前不进入容量方程；相关 Badcase 会如实显示为已知漏诊，并排除在受支持口径准确率之外。
- 证据冲突夹具要求拒答；相同干预无法区分来源时由可辨识性仲裁降级为 `indeterminate`。

## 已知边界

- `code-regression-unmodeled`：status=abstain，expectation_met=no；仅运行反事实分类评测，不进入补丁竞赛、RiskGate 或 PR 流水线；结果不得表述为已支持代码根因诊断。
- `conflicting-counterfactuals`：status=abstain，expectation_met=yes；本夹具验证可辨识性仲裁：两个来源假设映射到相同干预时降级为 indeterminate；未加入来源级证据前不得自动放行补丁。
- `queue-backlog-unmodeled`：status=abstain，expectation_met=no；code_version 仅作为不影响容量方程的评测哨兵；本夹具不声称已实现 RocketMQ 队列根因回放。

## 机器可读证据

- `evaluation-summary.json`：完整口径、汇总和逐例结果。
- `evaluation-cases.csv`：可导入表格或评测平台的逐例记录。
- 本文件：由同一次运行生成的可读摘要。
