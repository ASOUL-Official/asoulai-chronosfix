# 复赛部署、运行与验证说明

A-CFX 核心闭环使用 Python 标准库实现，保证评委在无外部 API、无闭源模型、无云账号的情况下也能复现实验。云 Skills、Nacos、Higress、PolarDB、RocketMQ、AgentLoop 等生产化组件以接口契约方式说明，可在复赛/决赛继续接入。

## 1. 环境要求

| 项目 | 要求 |
|---|---|
| Python | 3.10+ |
| 系统 | Windows / macOS / Linux |
| 依赖 | Python 标准库，无必须安装的第三方包 |
| 网络 | 本地运行不需要网络；在线 Demo 使用 GitHub Pages |
| 数据 | 合成事故数据，不含真实企业数据或个人信息 |

## 2. 一键运行核心 Demo

```powershell
cd D:\1\全球AI大赛\chronosfix
python demo.py --approve --output evidence
```

运行成功后会输出：

- `evidence/trace.jsonl`
- `evidence/run-log.jsonl`
- `evidence/engineering-metrics.json`
- `evidence/proof-bundle.json`
- `evidence/proof-report.md`
- `evidence/agentteams-run.json`
- `evidence/evaluation-report.md`
- `evidence/github-issue.md`
- `evidence/github-pr.md`
- `evidence/github-pr-diff.patch`
- `evidence/github-pr-checks.json`
- `evidence/github-review-audit.jsonl`

## 3. 运行 AgentTeams 风格代码包

```powershell
cd D:\1\全球AI大赛\chronosfix
python agentteams/run_chronosfix_team.py --approve --output output/agentteams-latest
```

该入口会读取同一个事故样例，并输出 Manager/Worker、共享状态、上下文传递、审批门禁和产物列表。

## 4. 验证风险阻断分支

不传 `--approve`：

```powershell
python demo.py --output output/no-approval
```

预期结果：

- 进程返回码为 `2`；
- `approval` 为 `blocked-awaiting-human`；
- RiskGate Span 出现在 `trace.jsonl`；
- 证明中风险补丁不会无人值守发布。

## 5. 自动化测试

```powershell
python -m unittest discover -s tests -p "test_*.py" -q
```

覆盖内容：

- 连接池恢复可以消除基线故障；
- 反事实实验证明 `H-POOL` 是主因；
- 补丁竞赛选择 `P-RESTORE-POOL`；
- Evidence Passport、Fault Genome、Skill Candidate 均生成；
- 未审批时 RiskGate 阻断交付。

## 6. 在线 Demo

在线地址：

```text
https://asoul-official.github.io/asoulai-chronosfix/
```

本地打开：

```powershell
start repair-cockpit\index.html
```

Demo 重点展示：

- 时间线证据；
- 反事实平行宇宙；
- 缺陷基因实验室；
- 补丁竞赛；
- 证据护照；
- Skill 自进化；
- 复赛工程验证；
- GitHub Issue / PR 模拟链路；
- 官方推荐 Infra 映射。

## 7. 第三方依赖、商业 API 与数据授权

| 项目 | 当前复赛包披露 |
|---|---|
| 第三方依赖 | 核心 Python Demo 无第三方依赖；PPT/Demo 构建工具仅用于产物制作 |
| 商业 API | 当前核心运行不调用商业 API |
| 闭源模型 | 当前核心运行不依赖闭源模型 |
| 数据来源 | 自造合成故障样例 |
| 授权边界 | 不含真实用户数据、企业生产日志或密钥 |
| 云产品权限 | 生产接入时采用 RAM 最小权限、只读优先、高风险 HITL |

## 8. 复赛验收建议

评委可按以下顺序复现：

1. 读 README 的“评审快速使用”。
2. 运行 `python -m unittest discover -s tests -q`。
3. 运行 `python demo.py --approve --output evidence`。
4. 查看 `evidence/evaluation-report.md`。
5. 查看 `evidence/agentteams-run.json` 和 `evidence/trace.jsonl`。
6. 查看 `evidence/github-issue.md`、`evidence/github-pr.md`、`evidence/github-pr-diff.patch` 和 `evidence/github-pr-checks.json`。
7. 打开在线 Demo 或本地 `repair-cockpit/index.html`。
8. 查看复赛 PPT/PDF 中的工程证据页。
