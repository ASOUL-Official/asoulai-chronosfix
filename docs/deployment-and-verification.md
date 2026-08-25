# 部署、运行与验证说明

A-CFX 核心流水线使用 Python 标准库，支持离线复现。AgentTeams 清单校验需要 PyYAML；真实 AgentTeams Controller、真实 SLS 查询及其他云组件不属于默认本地运行。

## 1. 环境

| 项目 | 要求 |
|---|---|
| Python | 3.10+ |
| 系统 | Windows / macOS / Linux |
| 核心依赖 | Python 标准库 |
| 网络 | 核心流水线和评测不需要网络 |
| 数据 | 合成事故数据，不含企业生产数据或密钥 |

所有命令均从仓库根目录运行，不依赖提交者机器的绝对路径。

## 2. 自动化测试

```powershell
python -m unittest discover -s tests -p "test_*.py" -q
```

测试覆盖场景 Schema、RiskGate fail-closed、具名审批、PR 草案一致性、回滚、run manifest/哈希、Trace 唯一性、12 例评测和官方 SLS Skill dry-run。

## 3. 主场景证据运行

```powershell
python demo.py --approve --approver "AsoulAI Release Owner" --approval-reason "Semifinal evidence review" --output evidence
```

主要输出：

- `trace.jsonl`、`run-log.jsonl`、`engineering-metrics.json`；
- `proof-bundle.json`、`proof-report.md`；
- `agentteams-run.json`、`evaluation-report.md`；
- `github-issue.*`、`github-pr.*`、diff、checks、audit；
- `run-manifest.json`。

主场景当前为 18 个 Span。每次运行的 `run_id` 和 `trace_id` 唯一，因此重新运行后哈希和时间值会变化，这是预期行为。

## 4. 未审批与质量失败

未提供审批：

```powershell
python demo.py --output output/no-approval
```

若质量通过但风险为 medium，预期：

- `quality_gate=passed`；
- `release_decision=blocked-awaiting-human`；
- 退出码 2。

仅传 `--approve` 也不够；必须提供 `--approver`。具名审批记录还会保存理由、时间、策略版本和输入摘要。

如果强制变体、回滚或 required check 失败，则：

- `quality_gate=failed`；
- `release_decision=blocked-quality-gate`；
- 人工审批不能覆盖失败质量。

## 5. 12 例评测

```powershell
python evaluate.py --output output/evaluation
```

生成 JSON、CSV、Markdown 三种结果。当前可信口径：

- 9/9 受支持诊断正确；
- 10/12 整体达成预期；
- 1/1 证据冲突正确拒答；
- 2 个未支持 Badcase 如实保留为漏诊；
- 数据全部为合成回放。

## 6. AgentTeams 材料

运行本地兼容入口：

```powershell
python agentteams/run_chronosfix_team.py --approve --approver "AsoulAI Release Owner" --approval-reason "Semifinal evidence review" --output output/agentteams-latest
```

它运行本地确定性内核，输出中明确记录 `agentteams_runtime_executed=false`。

离线校验正式资源：

```powershell
python agentteams/runtime/validate_resources.py agentteams/runtime/chronosfix-resources.yaml
```

正式资源使用 `agentteams.io/v1beta1`，但 Controller / Matrix 尚未安装与执行。不要把清单验证或本地 transcript 表述为真实 Runtime 运行。

## 7. 官方 SLS Skill dry-run

```powershell
python cloud_skill_demo.py --output evidence/cloud-skill-sls-dry-run.json
```

该命令只生成官方 `alibabacloud-sls-query` 的 GetIndex/GetLogsV2 调用计划和权限边界，不访问真实云。真实执行需要：

- 已安装 Aliyun CLI；
- 已配置只读 RAM Profile；
- 已提供 SLS Project 与 Logstore；
- 显式选择 cloud-read-only 执行。

当前没有真实 SLS 查询成功证据。

## 8. GitHub 与在线 Demo

在线 Demo：<https://asoul-official.github.io/asoulai-chronosfix/>。

核心流水线生成的 `github-*` 文件是 local-draft，不写 GitHub API。公开 Issue #1 / PR #2 是 documentation-only 迁移证据，不证明自动修复 PR 或真实 Check Run。Pages 页面是静态演示，事实以可重放 evidence 为准。

## 9. 建议验收顺序

1. 运行完整测试。
2. 运行主场景和未审批分支。
3. 检查 `run-manifest.json`、Trace、RiskGate、回滚与 hashes。
4. 运行 12 例评测并查看失败样例。
5. 核对 AgentTeams v1beta1 清单及其 Controller 未运行边界。
6. 核对官方 SLS Skill dry-run。
7. 最后打开 Repair Cockpit 与 PPT/PDF。
