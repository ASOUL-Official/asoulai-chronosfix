# 7 场景端到端实测结果

运行日期：2026-08-25

运行命令：

```powershell
python -m unittest discover -s tests -p "test_*.py" -q
```

自动化测试已覆盖全部 `scenarios/*/scenario.json`，每个场景均执行完整 Proof-Carrying Software Change Chain。

## 汇总结果

| 场景 | Incident | 证明主因 | 选中补丁 | 最差失败率 | Trace Span | 审批 |
|---|---|---|---|---:|---:|---|
| `api-timeout-amplifier` | INC-2026-0825-007 | H-POOL | P-RESTORE-POOL | 27.93% | 16 | approved |
| `cache-warmup-burst` | INC-2026-0825-006 | H-POOL | P-RESTORE-POOL | 22.78% | 16 | approved |
| `checkout-timeout` | INC-2026-0816-001 | H-POOL | P-RESTORE-POOL | 6.25% | 16 | approved |
| `config-drift-before-peak` | INC-2026-0825-002 | H-POOL | P-RESTORE-POOL | 0.00% | 16 | approved |
| `downstream-jitter` | INC-2026-0825-005 | H-POOL | P-RESTORE-POOL | 22.04% | 16 | approved |
| `payment-client-slowdown` | INC-2026-0825-003 | H-POOL | P-RESTORE-POOL | 31.86% | 16 | approved |
| `recovery-spike` | INC-2026-0825-004 | H-POOL | P-ADAPTIVE-GUARD | 14.20% | 16 | approved |

## 解读

- 7 个场景都能通过反事实实验把 `H-POOL` 证明为 primary-cause。
- 6 个场景选择 `P-RESTORE-POOL`，说明恢复容量并增加门禁是多数事故族的低风险方案。
- `recovery-spike` 选择 `P-ADAPTIVE-GUARD`，说明补丁竞赛不是固定答案，而会在恢复尖峰类场景中选择更强的保护方案。
- 每个场景均保留 16 段 Trace，覆盖 GitHub Issue / PR 链路和 ProofReport。
- 每个场景均生成 proof-bundle、proof-report、GitHub Issue/PR 草案、checks 和审计事件。

## 当前局限

这组实测仍属于合成故障回放集，不等同于真实企业历史事故。它的作用是验证工程闭环、证据结构和评测口径。决赛阶段建议加入 3-5 个真实开源仓库 issue 或脱敏事故样例，形成更强的 ROI 证据。
