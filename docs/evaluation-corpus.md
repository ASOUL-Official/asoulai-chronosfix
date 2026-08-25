# Golden / Badcase / Insufficient Evidence 合成评测集

ChronosFix 当前评测集共有 **12 个确定性合成样例**。它用于验证已建模变量、暴露未建模变量和拒答缺陷，不代表真实企业事故准确率。

## 样例构成

| 类型 | 数量 | 执行范围 | 目的 |
|---|---:|---|---|
| Golden | 9 | `pipeline-and-evaluation` | 运行完整本地流水线，并对照 Ground Truth |
| Badcase | 2 | `evaluation-only-counterfactual` | 暴露代码版本、队列积压等当前未建模变量 |
| Insufficient Evidence | 1 | `evaluation-only-counterfactual` | 检查证据冲突时是否正确拒答 |

9 个 Golden 包括原有 7 个容量/配置压力场景，并增加：

- `code-latency-regression-primary`：代码延迟回归为主因；
- `dependency-regression-primary`：依赖延迟回归为主因。

3 个评测专用夹具位于 `scenarios/evaluation-fixtures/`，只执行反事实分类，不进入 PatchTournament、RiskGate 或 PR 流水线：

- `code-regression-unmodeled`：已知真实原因是代码回归，但对应变量未进入当前容量方程；
- `queue-backlog-unmodeled`：已知真实原因是队列积压，但当前模拟器未建模队列深度；
- `conflicting-counterfactuals`：两个来源假设映射到同一干预，无法凭该回放区分来源，理想行为应为拒答。

## Ground Truth 契约

每个样例显式提供：

- `case_type`；
- `model_support`；
- `fixture_scope`；
- `expected_outcome`；
- `known_actual_causes`；
- `expected_primary_causes`；
- `expected_amplifiers`；
- `expected_not_causal`；
- `boundary_note`。

评测器不会从成功样例反推答案，也不会删除失败样例。

## 运行与产物

```powershell
python evaluate.py --output output/evaluation
```

生成：

- `evaluation-summary.json`：口径、汇总和逐例结果；
- `evaluation-cases.csv`：可导入表格或评测平台；
- `evaluation-report.md`：可读报告。

## 指标解释

- **supported diagnosis accuracy**：仅统计模拟器明确支持且期望诊断的样例。
- **overall expectation met**：全部 12 例中满足各自预期的数量。
- **abstention success**：预期拒答样例中实际拒答的数量。
- **unsupported case**：保留为已知边界，不计入受支持准确率，也不包装成成功。
- **unexpected assertion**：应拒答却仍宣称主因，按失败处理。

当前结果见 `docs/evaluation-corpus-results.md`：受支持诊断 9/9，整体达成 10/12，正确拒答 1/1。
