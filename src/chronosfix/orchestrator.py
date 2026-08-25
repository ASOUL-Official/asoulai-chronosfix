from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, TypeVar

from .engineering import write_engineering_artifacts
from .github_flow import build_github_flow_summary
from .integrity import (
    POLICY_VERSION,
    build_approval_input_digest,
    git_commit,
    sha256_file,
    sha256_json,
    write_run_manifest,
)
from .models import PatchCandidate, ServiceState
from .observability import TraceRecorder
from .simulator import simulate_checkout
from .skills.change_timeline import build_timeline
from .skills.counterfactual_replay import (
    replay_hypothesis,
    resolve_indistinguishable_interventions,
)
from .skills.evidence_fusion import load_incident
from .skills.evidence_passport import (
    build_evidence_passport,
    collect_pre_gate_missing_claims,
)
from .skills.fault_genome import evolve_fault_family
from .skills.patch_tournament import run_tournament
from .skills.proof_report import write_reports
from .skills.risk_gate import evaluate_gate
from .skills.skill_forge import distill_skill_candidates


AGENTS = {
    "incident-commander": "任务拆解、状态路由、冲突裁决与人工升级",
    "timeline-analyst": "融合多源证据并重建故障时间线",
    "hypothesis-scientist": "登记并验证可证伪的根因假设契约",
    "universe-builder": "构建反事实版本并重放故障",
    "patch-engineer": "读取候选修复、生成场景一致的变更草案与回滚契约",
    "adversarial-verifier": "以变异场景对补丁进行对抗验证",
    "release-auditor": "质量门禁、人工审批、审计与证据归档",
    "skill-curator": "将已验证事故模式沉淀为可复用 Skill 候选",
}

T = TypeVar("T")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _run_traced(
    trace: TraceRecorder,
    *,
    agent: str,
    skill: str,
    action: Callable[[], T],
    payload: Callable[[T], Any] | None = None,
    parent_span_id: str | None = None,
) -> tuple[T, str]:
    started_at = _utc_now()
    started = perf_counter()
    try:
        result = action()
    except Exception as exc:
        trace.emit(
            agent,
            skill,
            "error",
            {"error_type": type(exc).__name__, "message": str(exc)},
            parent_span_id=parent_span_id,
            started_at=started_at,
            duration_ms=(perf_counter() - started) * 1000,
        )
        raise
    span_id = trace.emit(
        agent,
        skill,
        "ok",
        payload(result) if payload else result,
        parent_span_id=parent_span_id,
        started_at=started_at,
        duration_ms=(perf_counter() - started) * 1000,
    )
    return result, span_id


def _verify_rollback(baseline: ServiceState, selected: Any) -> bool:
    if not selected.rollback or not selected.rollback_changes:
        return False
    patched = baseline.evolve(selected.changes)
    return patched.evolve(selected.rollback_changes) == baseline


def _build_execution_checks(state: Any, rollback_verified: bool, run_id: str) -> list[dict[str, Any]]:
    primary = [item for item in state.experiments if item.classification == "primary-cause"]
    mandatory_results = [
        item for item in state.selected_patch.results if item.get("mandatory", True)
    ]
    all_mandatory_variants_healthy = bool(mandatory_results) and all(
        item.get("healthy") is True for item in mandatory_results
    )
    return [
        {
            "name": "counterfactual-replay",
            "required": True,
            "executed": True,
            "conclusion": "success" if primary else "failure",
            "exit_code": 0 if primary else 1,
            "run_id": run_id,
            "evidence": "experiment results persisted in proof-bundle.json",
            "summary": f"{len(primary)} primary cause(s) reached the intervention threshold.",
        },
        {
            "name": "fault-gene-suite",
            "required": True,
            "executed": True,
            "conclusion": "success" if all_mandatory_variants_healthy else "failure",
            "exit_code": 0 if all_mandatory_variants_healthy else 1,
            "run_id": run_id,
            "evidence": "selected_patch.results in proof-bundle.json",
            "summary": (
                f"{len(mandatory_results)} mandatory variants evaluated; "
                f"worst failure rate {state.selected_patch.worst_failure_rate:.1%}."
            ),
        },
        {
            "name": "rollback-contract",
            "required": True,
            "executed": True,
            "conclusion": "success" if rollback_verified else "failure",
            "exit_code": 0 if rollback_verified else 1,
            "run_id": run_id,
            "evidence": "patch changes followed by rollback_changes compared with baseline",
            "summary": "Rollback restores the complete baseline state."
            if rollback_verified
            else "Rollback is missing or does not restore the complete baseline state.",
        },
    ]


def _evidence_coverage(state: Any, checks: list[dict[str, Any]]) -> float:
    mandatory_results = [
        item
        for item in (state.selected_patch.results if state.selected_patch else [])
        if item.get("mandatory", True)
    ]
    conditions = [
        any(item.classification == "primary-cause" for item in state.experiments),
        bool(mandatory_results and all(item.get("healthy") for item in mandatory_results)),
        bool(state.selected_patch and state.selected_patch.rollback_changes),
        bool(checks and all(item.get("conclusion") == "success" for item in checks)),
        bool(state.approval_record.get("approver"))
        if state.selected_patch and state.selected_patch.risk >= 0.25
        else True,
        bool(state.evidence_passport and not state.evidence_passport.missing_claims),
    ]
    return round(sum(conditions) / len(conditions), 4)


def run_pipeline(
    scenario_path: Path,
    output_dir: Path,
    approved: bool,
    *,
    approver: str | None = None,
    approval_reason: str | None = None,
) -> dict[str, Any]:
    pipeline_started = perf_counter()
    load_started = perf_counter()
    state, raw = load_incident(scenario_path)
    load_duration_ms = (perf_counter() - load_started) * 1000
    incident_event = next((item for item in raw["events"] if item["kind"] == "incident"), raw["events"][-1])
    trace = TraceRecorder(state.incident_id, timestamp=incident_event["timestamp"])
    state.run_id = trace.run_id
    state.scenario_path = scenario_path.as_posix()

    parent_span_id = trace.emit(
        "incident-commander",
        "EvidenceFusion",
        "ok",
        {"sources": state.evidence_index, "scenario": state.scenario_path},
        started_at=_utc_now(),
        duration_ms=load_duration_ms,
    )

    state.events, parent_span_id = _run_traced(
        trace,
        agent="timeline-analyst",
        skill="ChangeTimeline",
        action=lambda: build_timeline(state.events),
        payload=lambda events: {"event_count": len(events), "events": [asdict(item) for item in events]},
        parent_span_id=parent_span_id,
    )
    baseline_result, parent_span_id = _run_traced(
        trace,
        agent="incident-commander",
        skill="BaselineReplay",
        action=lambda: simulate_checkout(state.baseline),
        parent_span_id=parent_span_id,
    )

    state.experiments = []
    for hypothesis in state.hypotheses:
        hypothesis_span = trace.emit(
            "hypothesis-scientist",
            "HypothesisContract",
            "ok",
            hypothesis,
            parent_span_id=parent_span_id,
        )
        result, parent_span_id = _run_traced(
            trace,
            agent="universe-builder",
            skill="CounterfactualReplay",
            action=lambda hypothesis=hypothesis: replay_hypothesis(state.baseline, hypothesis),
            parent_span_id=hypothesis_span,
        )
        state.experiments.append(result)

    state.experiments, parent_span_id = _run_traced(
        trace,
        agent="hypothesis-scientist",
        skill="CausalIdentifiabilityArbitration",
        action=lambda: resolve_indistinguishable_interventions(
            state.hypotheses, state.experiments
        ),
        payload=lambda experiments: {
            "experiments": [asdict(item) for item in experiments],
            "indeterminate": [
                item.hypothesis_id
                for item in experiments
                if item.classification == "indeterminate"
            ],
        },
        parent_span_id=parent_span_id,
    )

    state.fault_variants, parent_span_id = _run_traced(
        trace,
        agent="universe-builder",
        skill="FaultGenome",
        action=lambda: evolve_fault_family(state.baseline, state.experiments, raw["mutations"]),
        payload=lambda variants: {"variants": [asdict(item) for item in variants]},
        parent_span_id=parent_span_id,
    )

    candidates = [PatchCandidate(**item) for item in raw["patch_candidates"]]
    candidate_span = trace.emit(
        "patch-engineer",
        "PatchCandidateContract",
        "ok",
        {"candidates": [asdict(item) for item in candidates]},
        parent_span_id=parent_span_id,
    )
    mutation_suite = [
        {"name": item.name, "changes": item.changes, "mandatory": item.mandatory}
        for item in state.fault_variants
    ]
    state.patch_scores, parent_span_id = _run_traced(
        trace,
        agent="adversarial-verifier",
        skill="PatchTournament",
        action=lambda: run_tournament(state.baseline, candidates, mutation_suite),
        payload=lambda ranking: {"ranking": [asdict(item) for item in ranking]},
        parent_span_id=candidate_span,
    )
    state.selected_patch = state.patch_scores[0]

    rollback_verified = _verify_rollback(state.baseline, state.selected_patch)
    checks = _build_execution_checks(state, rollback_verified, trace.run_id)
    pre_gate_missing_claims = collect_pre_gate_missing_claims(state)
    scenario_hash = sha256_file(scenario_path)
    patch_hash = sha256_json(state.selected_patch.changes)
    approval_record = {
        "status": "approved" if approved else "not-approved",
        "approver": approver,
        "reason": approval_reason,
        "timestamp": _utc_now() if approved else None,
        "policy_version": POLICY_VERSION,
        "is_human": bool(approver),
        "input_digest": build_approval_input_digest(
            incident_id=state.incident_id,
            scenario_hash=scenario_hash,
            patch_id=state.selected_patch.candidate_id,
            patch_hash=patch_hash,
        ),
    }
    state.approval_record = approval_record

    gate, parent_span_id = _run_traced(
        trace,
        agent="release-auditor",
        skill="RiskGate",
        action=lambda: evaluate_gate(
            state.selected_patch,
            approved,
            primary_cause_proven=any(item.classification == "primary-cause" for item in state.experiments),
            missing_claims=pre_gate_missing_claims,
            rollback_verified=rollback_verified,
            checks=checks,
            approval=approval_record,
            mandatory_variant_names=[item.name for item in state.fault_variants],
        ),
        parent_span_id=parent_span_id,
    )
    state.gate_result = gate
    state.quality_gate = gate["quality_gate"]
    state.approval = gate["decision"]

    integrity = {
        "schema_version": "chronosfix.evidence-integrity/v1",
        "run_id": trace.run_id,
        "trace_id": trace.trace_id,
        "scenario_sha256": scenario_hash,
        "patch_changes_sha256": patch_hash,
        "rollback_changes_sha256": sha256_json(state.selected_patch.rollback_changes),
        "approval_input_digest": approval_record["input_digest"],
        "policy_version": POLICY_VERSION,
    }
    state.evidence_passport, parent_span_id = _run_traced(
        trace,
        agent="release-auditor",
        skill="EvidencePassport",
        action=lambda: build_evidence_passport(state, integrity=integrity),
        parent_span_id=parent_span_id,
    )
    parent_span_id = trace.emit(
        "patch-engineer",
        "GitHubIssuePrFlow",
        "ok",
        build_github_flow_summary(state),
        parent_span_id=parent_span_id,
    )
    state.skill_candidates, parent_span_id = _run_traced(
        trace,
        agent="skill-curator",
        skill="SkillForge",
        action=lambda: distill_skill_candidates(state),
        payload=lambda skills: {"skills": [asdict(item) for item in skills]},
        parent_span_id=parent_span_id,
    )

    repo_root = Path(__file__).resolve().parents[2]
    metrics = {
        "run_id": trace.run_id,
        "trace_id": trace.trace_id,
        "scenario_path": state.scenario_path,
        "git_commit": git_commit(repo_root),
        "baseline_failure_rate": baseline_result.failure_rate,
        "baseline_p99_ms": baseline_result.p99_ms,
        "hypotheses_tested": len(state.experiments),
        "counterfactual_experiments": len(state.experiments),
        "primary_causes_proven": sum(item.classification == "primary-cause" for item in state.experiments),
        "patches_compared": len(state.patch_scores),
        "mutation_scenarios": len(mutation_suite),
        "fault_variants": len(state.fault_variants),
        "evidence_passport_claims": (
            len(state.evidence_passport.requirement_claims)
            + len(state.evidence_passport.causal_claims)
            + len(state.evidence_passport.verification_claims)
            + len(state.evidence_passport.risk_claims)
            + len(state.evidence_passport.rollback_claims)
        ),
        "skill_candidates": len(state.skill_candidates),
        "github_flow_artifacts": 7,
        "selected_patch_score": state.selected_patch.total_score,
        "selected_patch_worst_failure_rate": state.selected_patch.worst_failure_rate,
        "selected_patch_changes": state.selected_patch.changes,
        "selected_patch_rollback_changes": state.selected_patch.rollback_changes,
        "rollback_verified": rollback_verified,
        "validation_checks": checks,
        "quality_gate": state.quality_gate,
        "release_decision": state.approval,
        "trace_spans": len(trace.records) + 1,
        "elapsed_ms": round((perf_counter() - pipeline_started) * 1000, 3),
        "elapsed_ms_kind": "measured",
        "pipeline_step_completion_rate": 1.0,
    }
    metrics["evidence_coverage"] = _evidence_coverage(state, checks)
    metrics["evidence_coverage_kind"] = "derived"
    trace.emit(
        "incident-commander",
        "ProofReport",
        "ok",
        metrics,
        parent_span_id=parent_span_id,
        duration_ms=(perf_counter() - pipeline_started) * 1000,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    trace.write_jsonl(output_dir / "trace.jsonl")
    write_reports(state, metrics, output_dir)
    write_engineering_artifacts(state, metrics, trace.records, output_dir)
    write_run_manifest(
        output_dir,
        repo_root=repo_root,
        scenario_path=scenario_path,
        state=state,
        metrics=metrics,
        trace_records=trace.records,
        artifact_names=[
            "trace.jsonl",
            "run-log.jsonl",
            "proof-bundle.json",
            "proof-report.md",
            "engineering-metrics.json",
            "agentteams-run.json",
            "evaluation-report.md",
            "github-issue.json",
            "github-issue.md",
            "github-pr.json",
            "github-pr.md",
            "github-pr-diff.patch",
            "github-pr-checks.json",
            "github-review-audit.jsonl",
        ],
    )
    return {"state": state, "metrics": metrics, "trace_id": trace.trace_id, "run_id": trace.run_id}
