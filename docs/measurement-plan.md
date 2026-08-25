# A-CFX 实测方案：从 Demo 指标走向决赛硬证据

复赛阶段已经有自动化测试、Trace、Metrics、Proof Report 和 7 个故障回放场景。决赛前如果要把“商业价值”变成更硬的证据，建议按下面四层实测。

## 1. 正确性实测

目标：证明系统不是“看起来会分析”，而是真的能把主因和放大因素区分开。

| 指标 | 计算方式 | 当前可落地证据 |
|---|---|---|
| 根因命中率 | primary-cause 是否与预设专家结论一致 | 7 个 `scenarios/*/scenario.json` |
| 误归因率 | 被证伪的代码/依赖是否被错误标为主因 | `CounterfactualReplay` 结果 |
| 证据完整度 | 是否生成因果、验证、风险、回滚、缺口声明 | `evidence_passport` |

推荐命令：

```powershell
python -m unittest discover -s tests -p "test_*.py" -q
```

## 2. 变更可信度实测

目标：证明补丁不是“能过原始样例”，而是能抗同源变体。

| 指标 | 计算方式 | 当前可落地证据 |
|---|---|---|
| 平均失败率 | PatchTournament 中所有故障变体的平均 failure_rate | `proof-bundle.json` |
| 最差失败率 | 所有变体中的最大 failure_rate | `engineering-metrics.json` |
| 回滚完整度 | 每个补丁是否含 rollback contract | `github-pr.md` / Evidence Passport |
| PR 可审查度 | PR 是否带 diff、checks、RiskGate、审计事件 | `github-pr-checks.json` |

## 3. 工程效率实测

目标：量化它对研发组织的价值。

建议用“人工 baseline vs A-CFX”对比：

| 指标 | 人工 baseline | A-CFX 口径 |
|---|---|---|
| MTTA | 从告警到定位候选根因的时间 | 从 scenario 输入到 primary-cause 输出 |
| MTTR 代理 | 从告警到生成可审查修复方案的时间 | 从 scenario 输入到 GitHub PR 草案 |
| PR 材料准备时间 | 人工写根因、验证、风险、回滚说明耗时 | Evidence Passport 自动生成耗时 |
| 复盘沉淀率 | 复盘是否转成可复用资产 | SkillForge 产出的 Skill 候选数 |

复赛演示里可以先用“代理指标”表述：当前确定性 Demo 以 span 数估算链路耗时，决赛接真实 Git/CI 后换成真实 wall-clock。

## 4. 商业 ROI 实测

目标：把商业价值从“逻辑成立”变成“可采购指标”。

建议做一个小规模实测表：

| ROI 项 | 实测方式 |
|---|---|
| 减少故障定位时间 | 选 5-10 个历史事故，让同学/队友人工定位，再用 A-CFX 跑，比较耗时 |
| 降低误修复 | 设置包含干扰项的 Badcase，看系统是否拒绝错误根因 |
| 节省审计材料时间 | 对比人工写 PR 根因/验证/回滚说明 vs 自动 Evidence Passport |
| 资产复用 | 统计一个故障基因包能否覆盖多个相邻场景 |

## 决赛前最推荐补的实测

如果时间有限，只做三件事：

1. 录一张表：7 个场景的 primary-cause、selected_patch、worst_failure_rate、trace_spans。
2. 做 3 个 Badcase：代码变更靠近事故但不是根因，验证系统不会误判。
3. 用 1 个真实开源仓库的小 PR，手动模拟 Issue → PR → checks → Evidence Passport。

这样能回答评委最可能问的三句话：

- “你怎么证明不是 AI 猜的？”
- “你怎么证明补丁不会只过一个样例？”
- “你怎么证明它能进入真实研发流程？”
