# 接口 Schema、数据流与等价 MCP 契约

ChronosFix 将 Skill 作为能力层，将本地函数、MCP、HTTP 或官方云 Skill 作为可替换的工具层。机器可读 JSON Schema 位于 `schemas/`；本文件解释主要字段、权限和迁移边界。

## 1. 数据流

```text
ScenarioInput
  -> EvidenceFusion / ChangeTimeline
  -> CounterfactualReplay
  -> Identifiability Arbitration
  -> FaultGenome / PatchTournament
  -> RiskGate
  -> EvidencePassport
  -> GitHub local draft
  -> SkillForge / ProofReport
  -> run-manifest + Trace + Metrics
```

## 2. 反事实实验结果

```json
{
  "hypothesis_id": "H-POOL",
  "classification": "primary-cause",
  "baseline_failure_rate": 0.4872,
  "counterfactual_failure_rate": 0.0,
  "intervention_effect_score": 1.0
}
```

`intervention_effect_score` 是确定性回放中“干预后失败率相对下降比例”，不是统计置信度、概率或模型校准分。相同干预对应多个来源假设时，结果会降级为 `indeterminate`；在缺少来源级证据时不得选择补丁。

旧字段 `causal_confidence` 已移除，公开材料不再把模拟效果称为“因果置信度”。

## 3. Trace Span

```json
{
  "timestamp": "2026-08-25T07:11:45.052828+00:00",
  "started_at": "2026-08-25T07:11:45.052777+00:00",
  "ended_at": "2026-08-25T07:11:45.052828+00:00",
  "duration_ms": 0.051,
  "duration_kind": "measured",
  "run_id": "run-...",
  "trace_id": "5b653e47e7e34e00be3f34308ba40c71",
  "span_id": "000000000000000d",
  "parent_span_id": "000000000000000c",
  "incident_id": "INC-2026-0816-001",
  "agent": "release-auditor",
  "skill": "RiskGate",
  "status": "ok",
  "payload": {
    "quality_gate": "passed",
    "human_approval": "approved",
    "release_ready": true
  }
}
```

主场景当前有 18 个 Span。duration 来自本地实测；instant event 明确标记 `duration_kind=instant-event`。

OpenTelemetry 迁移映射：

| A-CFX 字段 | OTel 语义 |
|---|---|
| `trace_id` / `span_id` / `parent_span_id` | Trace/Span 关系 |
| `agent` | `gen_ai.agent.name` |
| `skill` | `gen_ai.operation.name` |
| `status` | `otel.status_code` |
| `duration_ms` | Span duration |
| `payload` | attributes / events |

## 4. RiskGate

输入：

```json
{
  "selected_patch": {
    "changes": {"pool_size": 24},
    "rollback_changes": {"pool_size": 8},
    "results": [{"name": "nominal", "mandatory": true, "healthy": true}]
  },
  "primary_cause_proven": true,
  "missing_claims": [],
  "rollback_verified": true,
  "checks": [{
    "name": "fault-gene-suite",
    "required": true,
    "executed": true,
    "exit_code": 0,
    "conclusion": "success",
    "run_id": "run-..."
  }],
  "approval": {
    "status": "approved",
    "approver": "AsoulAI Release Owner",
    "reason": "Semifinal evidence review",
    "is_human": true
  }
}
```

输出分离：

- `quality_gate=passed|failed`；
- `human_approval=approved|not-required|missing-or-invalid`；
- `decision=approved|blocked-quality-gate|blocked-awaiting-human`；
- `release_ready=true|false`；
- `quality_blockers` 与 `approval_blockers`。

布尔 `approved=true` 不能代替具名审批；人工不能覆盖 `quality_gate=failed`。

## 5. Tool Adapter 通用契约

| 字段 | 说明 |
|---|---|
| `tool_name` | 稳定工具名，如 `git.diff.read`、`ci.test.trigger` |
| `protocol` | local、MCP、HTTP、CLI、CloudSkill |
| `input_schema` / `output_schema` | JSON Schema 与版本 |
| `permission_scope` | read-only、test-trigger、draft-write、approval-required |
| `idempotency_key` | incident + tool + normalized input hash |
| `retry_policy` | timeout、max retries、backoff |
| `audit` | run/trace、caller、目标、脱敏和外部链接 |
| `evidence_level` | measured、derived、simulated、dry-run、external |
| `failure_handling` | retry、degrade、evidence gap、fail-closed |

## 6. 官方 SLS Skill 契约

当前适配器绑定官方 `alibabacloud-sls-query`，只规划：

- SLS `GetIndex`；
- SLS `GetLogsV2`；
- 最长 24 小时查询窗口；
- RAM `log:GetIndex` 与 `log:GetLogStoreLogs`；
- Aliyun CLI Profile 凭据隔离；
- 专用 User-Agent。

`evidence/cloud-skill-sls-dry-run.json` 为 dry-run，不是云查询响应。真实执行必须显式 `--execute` 且由已有只读 Profile 提供凭据。

## 7. GitHub local-draft 契约

本地输出与 GitHub API 的映射：

| 本地产物 | 候选 GitHub API | 当前状态 |
|---|---|---|
| `github-issue.json` | Issues API | local-draft |
| `github-pr.json` | Pulls API | local-draft |
| `github-pr-diff.patch` | Git Data/Contents | local-draft |
| `github-pr-checks.json` | Checks API | 本地检查汇总，不是真实 Check Run |
| `github-review-audit.jsonl` | Audit/SIEM | 本地审计事件 |

草案必须从实际 scenario、selected patch、changes、rollback changes、执行检查和审批记录派生。输入不足时 PR 保持 draft/pending，不能伪造 commit SHA 或成功检查。

公开 Issue #1 / PR #2 为 documentation-only，不是上述 Adapter 的在线执行结果。

## 8. Evidence Passport 与完整性

Evidence Passport 包含 requirement、causal、verification、risk、rollback、missing claims 和 integrity 摘要。`run-manifest.json` 进一步绑定：

- scenario SHA-256；
- patch changes SHA-256；
- rollback changes SHA-256；
- approval input digest；
- 主要产物 SHA-256；
- run/trace、生成时间、Python/平台和 Git commit。

SHA-256 用于检测本地证据漂移，不等同于数字签名或远程可信时间戳。

## 9. 失败处理

| 失败 | 行为 |
|---|---|
| 工具超时/权限不足 | 记录 evidence gap，不输出强结论 |
| 同一干预无法区分来源 | 标记 indeterminate 并拒答 |
| 强制变体失败 | `blocked-quality-gate` |
| required check 无执行结果 | `blocked-quality-gate` |
| 回滚缺失或未验证 | `blocked-quality-gate` |
| 中高风险缺少具名审批 | `blocked-awaiting-human` |
| GitHub 输入不足 | 仅生成 pending draft，不声称外部写入 |
