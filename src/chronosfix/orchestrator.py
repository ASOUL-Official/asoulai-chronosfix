from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from time import perf_counter

from .models import PatchCandidate
from .observability import TraceRecorder
from .simulator import simulate_checkout
from .skills.change_timeline import build_timeline
from .skills.counterfactual_replay import replay_hypothesis
from .skills.evidence_fusion import load_incident
from .skills.evidence_passport import build_evidence_passport
from .skills.fault_genome import evolve_fault_family
from .skills.patch_tournament import run_tournament
from .skills.proof_report import write_reports
from .skills.risk_gate import evaluate_gate
from .skills.skill_forge import distill_skill_candidates


AGENTS = {
    "commander": "任务拆解、状态路由、冲突裁决与人工升级",
    "timeline-analyst": "融合多源证据并重建故障时间线",
    "hypothesis-scientist": "生成可证伪的根因假设",
    "universe-builder": "构建反事实平行版本并重放故障",
    "patch-engineer": "生成候选修复并声明回滚路径",
    "adversarial-verifier": "以变异场景对补丁进行对抗验证",
    "release-auditor": "风险分级、人工审批、审计与证据归档",
}


def run_pipeline(scenario_path: Path, output_dir: Path, approved: bool) -> dict:
    started = perf_counter()
    state, raw = load_incident(scenario_path)
    trace = TraceRecorder(state.incident_id)
    trace.emit("commander", "EvidenceFusion", "ok", {"sources": state.evidence_index})

    state.events = build_timeline(state.events)
    trace.emit(
        "timeline-analyst",
        "ChangeTimeline",
        "ok",
        {"event_count": len(state.events), "events": [asdict(item) for item in state.events]},
    )

    baseline_result = simulate_checkout(state.baseline)
    trace.emit("commander", "BaselineReplay", "ok", baseline_result)

    state.experiments = []
    for hypothesis in state.hypotheses:
        trace.emit("hypothesis-scientist", "HypothesisContract", "ok", hypothesis)
        result = replay_hypothesis(state.baseline, hypothesis)
        state.experiments.append(result)
        trace.emit("universe-builder", "CounterfactualReplay", "ok", result)

    state.fault_variants = evolve_fault_family(state.baseline, state.experiments, raw["mutations"])
    trace.emit(
        "universe-builder",
        "FaultGenome",
        "ok",
        {"variants": [asdict(item) for item in state.fault_variants]},
    )

    candidates = [PatchCandidate(**item) for item in raw["patch_candidates"]]
    mutation_suite = [{"name": item.name, "changes": item.changes} for item in state.fault_variants]
    state.patch_scores = run_tournament(state.baseline, candidates, mutation_suite)
    state.selected_patch = state.patch_scores[0]
    trace.emit(
        "adversarial-verifier",
        "PatchTournament",
        "ok",
        {"ranking": [asdict(item) for item in state.patch_scores]},
    )

    gate = evaluate_gate(state.selected_patch, approved)
    state.approval = gate["decision"]
    trace.emit("release-auditor", "RiskGate", gate["decision"], gate)

    state.evidence_passport = build_evidence_passport(state)
    trace.emit(
        "release-auditor",
        "EvidencePassport",
        "ok",
        asdict(state.evidence_passport),
    )

    state.skill_candidates = distill_skill_candidates(state)
    trace.emit(
        "commander",
        "SkillForge",
        "ok",
        {"skills": [asdict(item) for item in state.skill_candidates]},
    )

    metrics = {
        "baseline_failure_rate": baseline_result.failure_rate,
        "baseline_p99_ms": baseline_result.p99_ms,
        "hypotheses_tested": len(state.experiments),
        "parallel_universes": len(state.experiments),
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
        "selected_patch_score": state.selected_patch.total_score,
        "selected_patch_worst_failure_rate": state.selected_patch.worst_failure_rate,
        "trace_spans": len(trace.records) + 1,
        "elapsed_ms": round((perf_counter() - started) * 1000, 2),
        "evidence_coverage": 1.0,
    }
    trace.emit("commander", "ProofReport", "ok", metrics)
    trace.write_jsonl(output_dir / "trace.jsonl")
    write_reports(state, metrics, output_dir)
    return {"state": state, "metrics": metrics, "trace_id": trace.trace_id}
