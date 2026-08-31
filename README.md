# AsoulAI ChronosFix（A-CFX）：软件故障时间机器

**让每一次软件变更都携带可验证的证据。**

队伍名称：**AsoulAI**

AsoulAI ChronosFix（A-CFX）面向 GOAI 新智基座 Agent Infra「方向三：软件研发全流程协同」。它不把“AI 给出一个补丁”当作完成，而是要求每次变更进入 PR、审批和发布链路前，携带可回放、可验证、可审计的证据。

```text
事故证据
  -> 反事实证明根因
  -> 故障基因验证补丁
  -> 质量门禁 + 具名人工审批
  -> GitHub PR 本地草案 / 证据护照
  -> Skill / 故障资产沉淀
```

## 当前证据等级（先看这里）

| 能力 | 当前状态 | 不应误解为 |
|---|---|---|
| ChronosFix 核心流水线 | Python 标准库本地可运行，自动生成 Trace、日志、指标、PR 草案和证据包 | 真实生产环境修复结果 |
| 动态协同控制面 | 新证据插入任务、capability 调度、Worker 超时重派、事件/任务幂等、revision checkpoint 和人工暂停/恢复均有 `coordination.json` 证据 | AgentTeams Controller / Matrix 已执行 |
| RiskGate | 质量门禁与人工审批分离；中高风险要求具名审批，人工不能覆盖失败质量检查 | 已接企业发布审批系统 |
| 评测集 | 12 个合成样例：9 Golden、2 Badcase、1 Insufficient Evidence | 真实企业事故准确率 |
| AgentTeams | `agentteams.io/v1beta1` Manager/Worker/Team/Human 正式资源已离线校验 | AgentTeams Controller / Matrix 已执行 |
| 官方云 Skill | `alibabacloud-sls-query` 只读适配器完成契约测试和 dry-run，当前未执行真实云查询 | 真实 SLS 查询已完成 |
| GitHub 协作 | 核心流水线生成本地 Issue/PR/diff/checks 草案；公开 Issue #1 / PR #2 为 documentation-only 迁移证据 | 已由程序写入真实修复 PR 或 GitHub Check Run |
| 其他官方组件 | Nacos、Higress、PolarDB、UnifiedModel、RocketMQ、LoongSuite、AgentScope Studio、AgentLoop 已完成接口映射与迁移边界设计 | 已部署并接入生产 |

逐条参赛要求、证据位置和准确评审表述见 [`docs/official-requirements-audit.md`](docs/official-requirements-audit.md)；运行边界见 [`agentteams/runtime/runtime-status.md`](agentteams/runtime/runtime-status.md)。

## 可复现运行

环境：Python 3.10+，核心闭环不依赖第三方 Python 包，也不需要云账号。

如果要运行公开 Schema、AgentTeams 清单和“一键复赛验收器”，先安装可选验证依赖（`PyYAML` + `jsonschema`）：

```powershell
python -m pip install -e ".[validation]"
```

只运行 `demo.py`、`evaluate.py` 或 57 项单元测试时无需安装这些可选依赖。

```powershell
git clone https://github.com/ASOUL-Official/asoulai-chronosfix.git
cd asoulai-chronosfix
python -m unittest discover -s tests -p "test_*.py" -q
python demo.py --approve --approver "AsoulAI Release Owner" --approval-reason "Semifinal evidence review" --output evidence
python evaluate.py --output output/evaluation
python agentteams/run_chronosfix_team.py --approve --approver "AsoulAI Release Owner" --approval-reason "Semifinal evidence review" --output output/agentteams-latest
python scripts/build_submission_package.py
python scripts/run_semifinal_acceptance.py --output output/semifinal-acceptance
```

验证未审批分支：

```powershell
python demo.py --output output/no-approval
```

预期：若质量检查通过但中风险补丁缺少具名审批，发布决策为 `blocked-awaiting-human`，进程返回码为 `2`。若强制故障变体、回滚或执行证据失败，则状态优先为 `blocked-quality-gate`，即使有人审批也不能放行。

在线 Repair Cockpit：<https://asoul-official.github.io/asoulai-chronosfix/>。它是静态演示界面；可审计事实以命令生成的 `evidence/` 文件为准。

## 当前可验证结果

主场景 `checkout-timeout` 的一次证据运行记录了：

- 基线失败率 48.72%，P99 606.96 ms；
- 3 个假设、3 次反事实干预、8 个强制故障变体、4 个候选补丁；
- 选中补丁 `P-RESTORE-POOL`，最差变体失败率 6.25%；
- 质量门禁 `passed`，具名人工审批后发布决策 `approved`；
- 回滚字段已恢复到场景基线并通过机器校验；
- 18 个 Trace Span，带 `run_id`、`trace_id`、父子关系和实测 duration；
- 6 个动态任务、8 次 Worker attempt、2 次失败重派、2 条去重证据，以及 revision 绑定的人工暂停/恢复；
- 端到端 `elapsed_ms` 为本地 wall-clock 实测；证据覆盖率与步骤完成率明确标记为派生指标；
- `run-manifest.json` 使用 SHA-256 绑定输入场景、补丁、回滚、审批摘要和输出文件。

### 12 例合成评测的准确口径

- Golden：9/9 达成 Ground Truth；这也是**当前模拟器支持范围内**的诊断口径。
- 全部样例：10/12 达成预期，不能写成 12/12。
- Badcase：2 个属于当前未建模根因，系统均未强行归因，但也未命中已知真实原因，因此作为已知漏诊保留。
- Insufficient Evidence：1 个，正确拒答 1/1；可辨识性仲裁在多个来源假设映射到相同干预时降级为 `indeterminate` 并安全拒答。
- 全部数据均为确定性合成回放，不代表生产准确率、真实 MTTR 或商业 ROI。

运行 `python evaluate.py --output output/evaluation` 可生成 `evaluation-summary.json`、`evaluation-cases.csv` 和 `evaluation-report.md`。评测说明见 [`docs/evaluation-corpus.md`](docs/evaluation-corpus.md) 与 [`docs/evaluation-corpus-results.md`](docs/evaluation-corpus-results.md)。

## RiskGate：质量不能被审批覆盖

RiskGate 输出两个独立维度：

- `quality_gate`：主因、强制变体、缺失声明、回滚和执行检查是否成立；
- `human_approval`：中高风险是否由具名人类审批，并记录理由、时间、策略版本和输入摘要。

只有两者同时满足，`release_ready` 才能为 true。布尔参数 `--approve` 不能单独构成有效审批，命令行必须同时提供 `--approver`；审批只接受风险，不能将失败质量改成通过。

## AgentTeams 对齐

仓库提供两层材料：

1. [`agentteams/run_chronosfix_team.py`](agentteams/run_chronosfix_team.py) 调用动态确定性内核并输出 AgentTeams-compatible transcript。核心计算由 task graph 驱动，包含证据触发插入、capability dispatch、失败重派、幂等去重和 revision checkpoint；输出仍明确标记 `agentteams_runtime_executed: false`。
2. [`agentteams/runtime/chronosfix-resources.yaml`](agentteams/runtime/chronosfix-resources.yaml) 使用 `agentteams.io/v1beta1`，包含 1 Manager、8 Worker、1 Team、1 Human；9 个业务 Skill 已拆为运行时可发现的 `agentteams/skills/*/SKILL.md`。离线校验结果见 [`evidence/agentteams-manifest-validation.json`](evidence/agentteams-manifest-validation.json)。

8 个 Worker 是可治理能力池，不是每次运行都强制同时启动。`chronosfix-manager` 读取证据后生成可回放的 Agent / Skill 组合：当前 Golden 主场景选择 7/8 个 Worker，冲突 / 证据不足场景选择 3/8 个并在补丁前拒答；`agent_plan_recommended` 事件、`decision_id` 和停止边界见 `evidence/local-controller-evidence.json`。这证明的是本地 Manager 的证据驱动控制面，不是官方 AgentTeams Controller 已执行。

AgentTeams Controller 尚未安装，因此仓库当前没有 Controller、Matrix 房间或真实 Manager/Worker 推理协作记录。本地控制面证据见 `coordination.json`；评委反馈闭环与剩余门槛见 [`docs/semifinal-reviewer-response.md`](docs/semifinal-reviewer-response.md)。

## 官方云 Skill

仓库实现了官方 `alibabacloud-sls-query` 的最小权限适配器：

- 固定上游来源与 commit；
- 仅规划 `GetIndex` 与 `GetLogsV2`；
- 查询窗口不超过 24 小时；
- 凭据只从已有 Aliyun CLI Profile 获取，不进入 Agent 上下文或证据文件；
- 当前证据 [`evidence/cloud-skill-sls-dry-run.json`](evidence/cloud-skill-sls-dry-run.json) 为 dry-run。

因为尚未提供真实 SLS Project、Logstore 和只读 RAM Profile，目前没有声称完成云端查询。

## GitHub Issue / PR 的边界

本地流水线根据实际 `scenario_path`、`selected_patch.changes`、`rollback_changes`、执行检查和 RiskGate 结果生成：

- `github-issue.md/json`；
- `github-pr.md/json`；
- `github-pr-diff.patch`；
- `github-pr-checks.json`；
- `github-review-audit.jsonl`。

这些文件是可复现的 **local-draft**，不会自动调用 GitHub API。公开 [Issue #1](https://github.com/ASOUL-Official/asoulai-chronosfix/issues/1) 与 [PR #2](https://github.com/ASOUL-Official/asoulai-chronosfix/pull/2) 是 documentation-only 迁移证据，只证明仓库协作路径和证据护照表达，不证明自动代码修复、真实 CI Check Run 或生产发布。

## 评审建议路径

1. 查看本 README 的“当前证据等级”。
2. 运行测试、主 Demo、12 例评测和未审批分支。
3. 检查 `evidence/run-manifest.json`、`trace.jsonl`、`proof-bundle.json`、`github-pr-checks.json`。
4. 查看 AgentTeams v1beta1 清单与离线校验证据。
5. 查看官方 SLS Skill dry-run 与权限边界。
6. 打开 Repair Cockpit 和 `submission/ChronosFix_复赛方案.pdf` 辅助观看。

## 商业价值：当前是待验证假设

A-CFX 面向中大型研发组织、云厂商/DevOps 平台和高审计行业，候选形态包括团队版 SaaS、私有化部署、云市场插件和审计模块。当前仓库只证明工程闭环，不声称已经实现客户节省、MTTR 降幅、付费转化或生产 ROI。

商业验证将采用“人工 baseline vs A-CFX”的同题对照，测量 MTTA、生成可审查 PR 材料的时间、误归因率、审计材料完整度和回滚验证覆盖率。详见 [`docs/business-value.md`](docs/business-value.md) 与 [`docs/measurement-plan.md`](docs/measurement-plan.md)。

## 主要目录

- `src/chronosfix/`：确定性编排、RiskGate、Trace、完整性和评测实现。
- `scenarios/`：9 个 pipeline Golden 和 3 个 evaluation-only 夹具。
- `schemas/`：机器可读 JSON Schema。
- `agentteams/`：本地兼容入口、Worker Skill、v1beta1 正式资源和离线校验工具。
- `evidence/`：主场景证据、AgentTeams 清单校验和官方 SLS Skill dry-run。
- `scripts/run_semifinal_acceptance.py`：一键复赛验收器；隔离执行测试、Schema、AgentTeams、通过/阻断分支和 12 场景评测。
- `repair-cockpit/`：静态可视化 Demo。
- `docs/`：架构、接口、安全、评测、部署、商业与合规说明。
- `submission/`：复赛 PPT/PDF、500 字简介、提交清单，以及带 SHA-256 清单的完整提交压缩包。

项目采用 Apache-2.0 许可证；当前场景均为合成数据，不含真实企业日志、用户数据或密钥。
