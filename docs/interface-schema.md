# 接口 Schema、数据流与等价 MCP 契约

复赛评审不要求所有外部系统都已实现 MCP Server，但要求工具调用链稳定、可迁移、可审计。A-CFX 的接口设计将 Skill 作为能力抽象层，将 MCP/Adapter/云 Skills 作为工具连接层。

## 1. 端到端数据流

```text
IncidentInput
  -> EvidenceFusion
  -> IncidentState
  -> ChangeTimeline
  -> HypothesisContract
  -> CounterfactualReplay
  -> FaultGenome
  -> PatchTournament
  -> RiskGate
  -> EvidencePassport
  -> SkillForge
  -> ProofReport / Metrics / Trace / AgentTeams Transcript
```

## 2. IncidentInput

```json
{
  "incident_id": "INC-2026-0816-001",
  "title": "订单创建接口高失败率",
  "baseline": {
    "traffic_rps": 120.0,
    "pool_size": 8,
    "dependency_latency_factor": 1.3,
    "code_version": "a91c7e"
  },
  "events": [
    {
      "timestamp": "2026-08-06T10:10:00+08:00",
      "kind": "config",
      "source": "db.pool.maxSize",
      "summary": "数据库连接池从 24 调整为 8",
      "details": {}
    }
  ],
  "hypotheses": [],
  "patch_candidates": []
}
```

## 3. Trace Span

```json
{
  "timestamp": "2026-08-06T10:16:00+08:00",
  "trace_id": "5408b7a5223b5c79a16bd69f1b06ea34",
  "span_id": "0000000000000006",
  "incident_id": "INC-2026-0816-001",
  "agent": "universe-builder",
  "skill": "CounterfactualReplay",
  "status": "ok",
  "payload": {
    "hypothesis_id": "H-POOL",
    "counterfactual_failure_rate": 0.0,
    "causal_confidence": 1.0
  }
}
```

OpenTelemetry GenAI 迁移映射：

| A-CFX 字段 | OTel 语义 |
|---|---|
| `trace_id` | Trace ID |
| `span_id` | Span ID |
| `agent` | `gen_ai.agent.name` |
| `skill` | `gen_ai.operation.name` |
| `status` | `otel.status_code` |
| `payload` | Span attributes / event payload |

## 4. Tool Adapter 契约

| 字段 | 说明 |
|---|---|
| `tool_name` | 稳定工具名，如 `git.diff.read`、`ci.test.trigger`、`nacos.config.diff` |
| `protocol` | `MCP`、`HTTP`、`CLI`、`CloudSkill` |
| `auth` | RAM Role、PAT、consumer token、OIDC、read-only token |
| `input_schema` | JSON Schema 或等价字段表 |
| `output_schema` | 返回结构、证据等级和错误结构 |
| `permission_scope` | read-only、test-trigger、approval-required、write-evidence |
| `idempotency_key` | incident_id + tool_name + normalized input hash |
| `retry_policy` | timeout、max_retries、backoff |
| `audit` | trace_id、span_id、caller、external_link、redaction |
| `mcp_migration_cost` | low / medium / high，以及原因 |

## 5. 关键工具契约

### Git Adapter

```json
{
  "tool_name": "git.diff.read",
  "protocol": "MCP/CLI",
  "auth": "read-only repository token",
  "input_schema": {
    "repo": "string",
    "base_ref": "string",
    "head_ref": "string",
    "paths": "array<string>"
  },
  "output_schema": {
    "diffs": "array<object>",
    "commits": "array<object>",
    "evidence_level": "strong|weak|missing"
  },
  "permission_scope": "read-only",
  "failure_handling": "timeout 后记录 evidence gap，不生成强因果结论",
  "audit": "记录 repo、commit range、trace_id、caller"
}
```

### CI Adapter

```json
{
  "tool_name": "ci.test.trigger",
  "protocol": "MCP/HTTP",
  "auth": "CI trigger token scoped to test jobs",
  "input_schema": {
    "branch": "string",
    "test_suite": "string",
    "scenario_id": "string"
  },
  "output_schema": {
    "job_id": "string",
    "status": "passed|failed|timeout",
    "logs_url": "string",
    "coverage": "number"
  },
  "permission_scope": "test-trigger",
  "failure_handling": "失败进入 PatchTournament 低分；超时进入待人工确认",
  "audit": "记录 job_id、branch、scenario_id"
}
```

### Nacos Config Adapter

```json
{
  "tool_name": "nacos.config.diff",
  "protocol": "CloudSkill/MCP/HTTP",
  "auth": "RAM role with read-only config access; rollback requires HITL",
  "input_schema": {
    "namespace": "string",
    "group": "string",
    "data_id": "string",
    "time_window": "string"
  },
  "output_schema": {
    "config_events": "array<object>",
    "rollback_point": "string",
    "risk_level": "low|medium|high"
  },
  "permission_scope": "read-only unless RiskGate approved",
  "failure_handling": "配置读取失败时不允许把配置变更标记为主因",
  "audit": "记录 namespace/group/dataId、审批人、回滚点"
}
```

### Higress Gateway Adapter

```json
{
  "tool_name": "higress.gateway.metrics",
  "protocol": "MCP/HTTP",
  "auth": "gateway consumer token",
  "input_schema": {
    "route": "string",
    "time_window": "string",
    "metrics": "array<string>"
  },
  "output_schema": {
    "status_code_rate": "object",
    "latency": "object",
    "rate_limit_events": "array<object>"
  },
  "permission_scope": "read-only metrics; policy changes require approval",
  "failure_handling": "网关证据缺失时降级为应用侧 Trace + Log 证据",
  "audit": "记录 route、time_window、trace_id"
}
```

## 6. Evidence Passport

```json
{
  "patch_id": "P-RESTORE-POOL",
  "requirement_claims": ["修复必须降低订单创建失败率与 P99 延迟"],
  "causal_claims": ["恢复连接池后失败率 48.7% -> 0.0%"],
  "verification_claims": ["补丁通过 8/8 个故障基因变体"],
  "risk_claims": ["风险分 0.30，审批状态 approved"],
  "rollback_claims": ["恢复 db.pool.maxSize=8 配置快照"],
  "missing_claims": ["复赛需接入真实 CI、日志和历史事故回放集"]
}
```

## 7. 失败处理规范

| 失败类型 | 系统行为 |
|---|---|
| 工具超时 | 重试；仍失败则记录 evidence gap，不输出强证据 |
| 权限不足 | 写入 run-log，等待人工授权，不绕过权限 |
| 证据冲突 | Hypothesis Scientist 保留多假设，交给反事实实验裁决 |
| 评测失败 | PatchTournament 降低分数，不进入 EvidencePassport 可发布状态 |
| 中高风险未审批 | RiskGate 返回 `blocked-awaiting-human` |
| 回滚点缺失 | EvidencePassport 写入 missing claim，禁止标记为可发布 |

