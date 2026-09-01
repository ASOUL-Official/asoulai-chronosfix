# Skill 工程体系

ChronosFix 提供 10 个稳定 Skill 契约：核心流水线包含 9 个业务 Skill，另有 1 个官方 SLS 只读 Skill Adapter；Schema、完整性和评测属于工程支撑模块。

| Skill | 输入 | 输出 | 安全边界 |
|---|---|---|---|
| EvidenceFusion | Issue/事件/Trace/Git/配置摘要 | Incident State、证据索引 | 只读；缺失证据显式记录 |
| ChangeTimeline | ChangeEvent | 排序时间线 | 不执行外部变更 |
| CounterfactualReplay | baseline、hypothesis intervention | failure/P99、`intervention_effect_score`、classification | 隔离回放；effect score 不是统计置信度 |
| FaultGenome | baseline、已证明主因 | mandatory/optional variants | 只生成合成测试状态 |
| PatchTournament | patch candidates、variants | ranking、mean/worst metrics、changes/rollback | 只产出候选 |
| RiskGate | selected patch、checks、rollback、approval | quality/human/decision/blockers | fail-closed；人工不覆盖失败质量 |
| EvidencePassport | state、gate、integrity | requirement/causal/verification/risk/rollback/missing/integrity | 缺关键声明不可 release-ready |
| SkillForge | resolved incident、passport、variants | Skill candidates | 只生成候选，不自动上线 |
| ProofReport | state、metrics、trace | proof bundle/report/manifest | 不写密钥或原始敏感数据 |

## CounterfactualReplay 的可辨识性

`intervention_effect_score` 是确定性干预效果比例。多个来源假设若映射到相同干预，系统无法凭该回放区分来源，将分类降级为 `indeterminate` 并拒答。这个限制进入评测与 Trace，不会被隐藏。

## RiskGate 契约

```json
{
  "quality_gate": "passed|failed",
  "human_approval": "approved|not-required|missing-or-invalid",
  "decision": "approved|blocked-quality-gate|blocked-awaiting-human",
  "release_ready": false,
  "quality_blockers": [],
  "approval_blockers": []
}
```

具名审批至少包含 approver、reason、timestamp、policy version 和 input digest。未执行的 check、缺失 rollback、失败 mandatory variant 或 missing claim 均使质量门禁失败。

## AgentTeams Worker Skill

`agentteams/skills/` 现在包含 9 个独立、运行时可发现的业务 Skill，以及一个用于离线验收的 `chronosfix-local-engine` 聚合入口。`src/chronosfix/skill_registry.py` 在运行时读取每个 `SKILL.md` 的 name、description、version 和权限，发现结果写入 `coordination.json`。AgentTeams Worker 根据自身 capability 只加载所需 Skill；聚合入口仅作为离线兼容 fallback。

Skill 规定：

- 合成数据必须标注；
- 输出 run/trace/quality/release 状态；
- 不把本地 transcript 称为 Controller/Matrix 证据；
- 不绕过 RiskGate；
- 生成 run manifest。

动态任务执行由 `src/chronosfix/runtime/controller.py` 与 `store.py` 记录 task graph、attempt、lease、idempotency key、state revision、重派和人工 checkpoint。新 evidence kind 会先计算受影响节点闭包，记录 `incremental_recompute_started` / `task_invalidated`，只重算相关结论、补丁和审批；当前记录仍是本地兼容证据，真实 Controller/Matrix 加载证据尚待部署。

AgentTeams v1beta1 正式资源已经离线校验，但 Worker 尚未在真实 Controller 中执行。

## 官方云 Skill

当前接入对象是官方 `alibabacloud-sls-query`：

| 项 | 当前实现 |
|---|---|
| 身份 | 固定官方 portal、source、source commit |
| 操作 | SLS GetIndex + GetLogsV2 |
| 权限 | 只读 RAM Actions |
| 凭据 | 仅已有 Aliyun CLI Profile |
| 审计 | 参数、User-Agent、execution mode |
| 失败 | CLI/权限/云失败时不伪造查询结果 |
| 当前证据 | dry-run，不是真实云端查询 |

证据：`evidence/cloud-skill-sls-dry-run.json`。

## 生命周期

- Schema 与 Skill 使用版本号；
- 候选 Skill 经人工评审和 12 例回放后才能注册；
- 失败样例不从分母删除；
- 新版本若导致质量回退则回滚到上一个稳定版本；
- 外部 Skill 的来源版本、权限和执行模式必须进入证据。
