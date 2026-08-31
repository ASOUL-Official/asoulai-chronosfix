# 复赛 Demo 视频脚本（建议 4–5 分钟）

原则：画面同时展示“能力”和“证据等级”。Repair Cockpit 用于讲解交互，最终数字以命令生成的 evidence 为准；不要把 local-draft、offline-validated 或 dry-run 说成真实外部执行。

## 0. 开场（15 秒）

画面：在线 Repair Cockpit 首页。

讲法：

> 我们是 AsoulAI，作品是 ChronosFix。它不是让 AI 直接修 Bug，而是让每次事故到 PR 的变更先携带可回放证据：反事实证明根因、故障族验证补丁、质量门禁、具名审批、PR 草案和证据护照。

## 1. 输入与本地执行（30 秒）

画面：主场景 JSON、命令行、证据目录。

```powershell
python demo.py --approve --approver "AsoulAI Release Owner" --approval-reason "Semifinal evidence review" --output evidence
```

讲法：

> 输入是合成的订单接口事故，包含 Issue、Git、依赖、配置、流量和告警。核心流水线使用 Python 标准库离线运行，不需要模型 API 或云账号。

补充画面（可选 15 秒）：运行 `python scripts/run_semifinal_acceptance.py --output output/semifinal-acceptance`，展示验收器同时运行通过分支和无人审批阻断分支。它会在隔离目录生成 JSON/Markdown 报告，不覆盖 `evidence/` 主证据。

## 2. 反事实与可辨识性（45 秒）

画面：展示 H-CODE、H-DEPENDENCY、H-POOL 与评测报告。

讲法：

> 每个假设都绑定一个干预。系统报告的是 intervention effect score，也就是确定性回放中失败率相对下降比例，不是统计置信度。主场景撤销代码没有改善，依赖回退只部分改善，恢复连接池让故障消失。若两个来源假设映射到相同干预，系统会降级为 indeterminate 并拒答，而不会伪造唯一根因。

## 3. 故障族与质量门禁（45 秒）

画面：8 个强制变体、PatchTournament、RiskGate。

讲法：

> 选中补丁必须通过所有强制故障变体。RiskGate 将质量和审批分开：失败变体、缺失声明、未执行检查或回滚失败都会 blocked-quality-gate；人类只能批准风险，不能覆盖质量失败。中高风险还必须记录具名审批人、理由、时间、策略版本和输入摘要。

## 4. Trace、真实耗时与完整性（40 秒）

画面：`trace.jsonl`、`engineering-metrics.json`、`run-manifest.json`。

讲法：

> 主场景当前有 18 个 Span，包含 run ID、trace ID、父子关系和实测 duration。端到端 elapsed 是本地 wall-clock 实测；步骤完成率和证据覆盖率明确标记为派生指标。run manifest 用 SHA-256 绑定场景、补丁、回滚、审批和输出文件。

## 5. 12 例评测（40 秒）

画面：运行 `python evaluate.py --output output/evaluation`，展示 Markdown/CSV。

讲法：

> 评测集有 9 个 Golden、2 个 Badcase 和 1 个证据不足样例。受支持诊断 9/9 正确，整体 10/12 达成预期，冲突场景正确拒答 1/1；两个未建模 Badcase 仍是已知漏诊。全部是合成回放，不代表生产准确率。

## 6. GitHub 协作边界（45 秒）

画面：本地 `github-pr.json`、diff/checks，以及公开 Issue #1/PR #2；最后打开真实 Draft PR #3 的 Checks 页面。

讲法：

> 核心流水线根据本次 scenario、selected changes、rollback 和本地执行检查生成 PR local-draft，默认不会联网。仓库另有显式开启的受控适配器，可把证据文件发布为 external-evidence-draft；公开 Issue #1 和 PR #2 仍是 documentation-only，不证明自动代码修复或真实 GitHub Check Run。

> 另外，我们创建了真实的工程验收 PR #3：它触发 Python 3.10、3.11、3.12 三个 GitHub Actions 作业，并上传一键验收 JSON/Markdown Artifact。PR #3 证明的是工程验证链路，不冒充 AgentTeams Runtime 或云端执行。

## 7. AgentTeams 与官方云 Skill（45 秒）

画面：v1beta1 YAML、manifest validation、runtime-status、SLS dry-run。

讲法：

> AgentTeams 正式资源采用 agentteams.io/v1beta1，包含 1 Manager、8 Worker、1 Team 和 1 Human，已经离线校验。当前 Controller/Matrix 未安装，所以本地 transcript 明确标记 runtime 未执行。官方 alibabacloud-sls-query 已完成只读契约测试和 dry-run，但尚未配置真实 SLS 账号，因此没有声称云查询成功。

## 8. 商业价值与收尾（20 秒）

画面：商业验证计划。

讲法：

> 我们要验证的商业假设是：研发组织愿意为“从事故到可审查 PR 证据”付费。当前没有虚构 MTTR 或 ROI；下一步会用人工 baseline 对照测量定位时间、误归因、PR 材料耗时、审计完整度和回滚覆盖率。

结尾：

> ChronosFix 让人类审查的不只是 AI 的答案，而是一条不能被审批绕过的证据链。

## 9. 现场备用路径（不剪辑时使用）

如果现场网络不可用，直接使用仓库本地的 `repair-cockpit/` 静态页面和 `evidence/` 文件；如果需要证明工程验收，展示已保存的 `output/semifinal-acceptance/semifinal-acceptance.md` 或重新运行一键验收器。演示时明确说“离线确定性验证”，不要把本地文件说成在线服务返回值。
