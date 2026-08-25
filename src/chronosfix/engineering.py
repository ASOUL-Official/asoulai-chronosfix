from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from .models import IncidentState


def _json_dump(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _jsonl_dump(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in records),
        encoding="utf-8",
    )


def build_agentteams_transcript(
    state: IncidentState, metrics: dict[str, Any], trace_records: list[dict[str, Any]]
) -> dict[str, Any]:
    """Create an AgentTeams-style execution transcript for semifinal review.

    The local demo does not require a running AgentTeams cluster, but this
    artifact maps the deterministic engine onto the same Manager/Worker,
    shared-state, evidence-room and human-approval concepts. It is intentionally
    machine-readable so it can become a real AgentTeams controller payload with
    only protocol adaptation.
    """

    context_keys = [
        "incident_id",
        "timeline",
        "hypotheses",
        "counterfactual_experiments",
        "fault_variants",
        "patch_tournament",
        "risk_gate",
        "evidence_passport",
        "skill_candidates",
    ]
    return {
        "team": "chronosfix-incident-response",
        "framework_mapping": {
            "human": "release-owner",
            "manager": "incident-commander",
            "workers": [
                "timeline-analyst",
                "hypothesis-scientist",
                "universe-builder",
                "patch-engineer",
                "adversarial-verifier",
                "release-auditor",
                "skill-curator",
            ],
            "matrix_room_equivalent": "repair-cockpit transparent evidence room",
            "shared_state": context_keys,
        },
        "task_decomposition": [
            {"owner": "incident-commander", "task": "accept incident and build evidence index"},
            {"owner": "timeline-analyst", "task": "order Git/config/dependency/traffic/alert events"},
            {"owner": "hypothesis-scientist", "task": "produce falsifiable root-cause contracts"},
            {"owner": "universe-builder", "task": "run counterfactual replay and evolve fault genome"},
            {"owner": "adversarial-verifier", "task": "score repair candidates on mutated scenarios"},
            {"owner": "release-auditor", "task": "enforce RiskGate and create evidence passport"},
            {"owner": "skill-curator", "task": "distill reusable Skill candidates"},
        ],
        "context_passing": [
            {
                "from": item["agent"],
                "skill": item["skill"],
                "span_id": item["span_id"],
                "status": item["status"],
                "writes": _infer_written_state(item["skill"]),
            }
            for item in trace_records
        ],
        "state_tracking": {
            "trace_id": trace_records[0]["trace_id"] if trace_records else None,
            "span_count": len(trace_records),
            "approval": state.approval,
            "selected_patch": state.selected_patch.candidate_id if state.selected_patch else None,
            "selected_patch_score": metrics.get("selected_patch_score"),
            "artifacts": [
                "trace.jsonl",
                "run-log.jsonl",
                "proof-bundle.json",
                "proof-report.md",
                "engineering-metrics.json",
                "agentteams-run.json",
                "evaluation-report.md",
            ],
        },
        "human_gate": {
            "condition": "medium/high risk patch",
            "decision": state.approval,
            "rollback_contract": state.selected_patch.rollback if state.selected_patch else None,
        },
    }


def _infer_written_state(skill: str) -> list[str]:
    mapping = {
        "EvidenceFusion": ["incident_id", "evidence_index"],
        "ChangeTimeline": ["timeline"],
        "BaselineReplay": ["baseline_metrics"],
        "HypothesisContract": ["hypotheses"],
        "CounterfactualReplay": ["counterfactual_experiments"],
        "FaultGenome": ["fault_variants"],
        "PatchTournament": ["patch_tournament", "selected_patch"],
        "RiskGate": ["approval", "risk_decision"],
        "EvidencePassport": ["evidence_passport"],
        "SkillForge": ["skill_candidates"],
        "ProofReport": ["proof_report", "proof_bundle", "engineering_metrics"],
    }
    return mapping.get(skill, ["shared_state"])


def write_engineering_artifacts(
    state: IncidentState,
    metrics: dict[str, Any],
    trace_records: list[dict[str, Any]],
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    ok_spans = sum(item["status"] in {"ok", "approved"} for item in trace_records)
    tool_success_rate = ok_spans / len(trace_records) if trace_records else 0.0
    engineering_metrics = {
        **metrics,
        "tool_success_rate": round(tool_success_rate, 4),
        "approval_gate_present": state.approval in {"approved", "blocked-awaiting-human"},
        "rollback_contract_present": bool(state.selected_patch and state.selected_patch.rollback),
        "trace_schema": {
            "required_fields": [
                "timestamp",
                "trace_id",
                "span_id",
                "incident_id",
                "agent",
                "skill",
                "status",
                "payload",
            ],
            "open_telemetry_mapping": {
                "trace_id": "trace_id",
                "span_id": "span_id",
                "agent": "gen_ai.agent.name",
                "skill": "gen_ai.operation.name",
                "status": "otel.status_code",
            },
        },
    }
    _json_dump(output_dir / "engineering-metrics.json", engineering_metrics)

    logs = [
        {
            "level": "INFO" if item["status"] in {"ok", "approved"} else "WARN",
            "trace_id": item["trace_id"],
            "span_id": item["span_id"],
            "agent": item["agent"],
            "event": item["skill"],
            "message": f"{item['agent']} executed {item['skill']} with status {item['status']}",
            "audit": {
                "permission_scope": _permission_scope(item["skill"]),
                "requires_human": item["skill"] == "RiskGate",
            },
        }
        for item in trace_records
    ]
    _jsonl_dump(output_dir / "run-log.jsonl", logs)

    transcript = build_agentteams_transcript(state, metrics, trace_records)
    _json_dump(output_dir / "agentteams-run.json", transcript)

    lines = [
        "# ChronosFix 复赛评测报告",
        "",
        "## 1. 自动化验证摘要",
        "",
        f"- 事故样例：{state.incident_id} / {state.title}",
        f"- Agent/Skill Trace Span：{len(trace_records)}",
        f"- 工具/Skill 成功率：{tool_success_rate:.1%}",
        f"- 根因假设数：{metrics['hypotheses_tested']}",
        f"- 反事实实验数：{metrics['parallel_universes']}",
        f"- 故障基因变体数：{metrics['fault_variants']}",
        f"- 补丁候选数：{metrics['patches_compared']}",
        f"- 选中补丁最差失败率：{metrics['selected_patch_worst_failure_rate']:.1%}",
        f"- 审批状态：{state.approval}",
        "",
        "## 2. 复赛验收点覆盖",
        "",
        "| 验收点 | 证据 |",
        "|---|---|",
        "| AgentTeams 编排 | `agentteams/chronosfix-team.yaml`、`agentteams-run.json` |",
        "| 样例输入输出 | `scenarios/checkout-timeout/scenario.json`、`proof-bundle.json` |",
        "| 日志与 Trace | `run-log.jsonl`、`trace.jsonl` |",
        "| Metrics | `engineering-metrics.json` |",
        "| 风险审批 | `RiskGate` Span 与 evidence passport 风险声明 |",
        "| 回滚审计 | selected patch rollback contract 与 proof-report |",
        "| Skill 复用 | `SkillForge` 输出 3 个 Skill Candidate |",
        "",
        "## 3. 失败处理分支",
        "",
        "运行 `python demo.py --output output/no-approval` 时不传 `--approve`，RiskGate 会返回 `blocked-awaiting-human`，证明中风险补丁不会无人值守发布。",
        "",
        "## 4. 开放 / 开源复现",
        "",
        "项目使用 Python 标准库实现核心闭环，Apache-2.0 协议开放，评委可用 README 中的一键命令复现实验。",
    ]
    (output_dir / "evaluation-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _permission_scope(skill: str) -> str:
    if skill in {"EvidenceFusion", "ChangeTimeline", "BaselineReplay", "HypothesisContract"}:
        return "read-only"
    if skill in {"CounterfactualReplay", "FaultGenome", "PatchTournament"}:
        return "isolated-simulation"
    if skill == "RiskGate":
        return "human-approval-required"
    if skill in {"EvidencePassport", "SkillForge", "ProofReport"}:
        return "write-evidence-artifacts"
    return "least-privilege"


def state_to_unified_model_entities(state: IncidentState) -> dict[str, Any]:
    return {
        "entities": [
            {"type": "Incident", "id": state.incident_id, "name": state.title},
            *[
                {"type": "ChangeEvent", "id": f"{event.timestamp}:{event.source}", **asdict(event)}
                for event in state.events
            ],
            *[
                {"type": "PatchCandidate", "id": score.candidate_id, "name": score.title}
                for score in state.patch_scores
            ],
            *[
                {"type": "SkillCandidate", "id": skill.name, "name": skill.name, "version": skill.version}
                for skill in state.skill_candidates
            ],
        ],
        "relationships": [
            {"from": state.incident_id, "to": f"{event.timestamp}:{event.source}", "type": "HAS_EVIDENCE"}
            for event in state.events
        ],
    }
