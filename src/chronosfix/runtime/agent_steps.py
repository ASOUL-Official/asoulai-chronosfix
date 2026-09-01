"""Executable Worker steps for a Manager-compiled Agent DAG.

Each invocation is intentionally small and process-safe.  The Controller
decides the graph and dependencies; this module performs the named Skill using
the scenario evidence, then returns a compact result for the Matrix event log.
"""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from ..models import ChangeEvent, Hypothesis, IncidentState, PatchCandidate, ServiceState
from ..skills.change_timeline import build_timeline
from ..skills.counterfactual_replay import replay_hypothesis, resolve_indistinguishable_interventions
from ..skills.fault_genome import evolve_fault_family
from ..skills.patch_tournament import run_tournament
from ..skills.risk_gate import evaluate_gate
from ..skills.skill_forge import distill_skill_candidates


def _load(path: Path) -> tuple[IncidentState, dict[str, Any]]:
    """Load the observable fields needed by an individual Worker step.

    Evaluation fixtures intentionally omit patch inputs.  They still need to
    run the context/timeline/hypothesis portion of the DAG before the Controller
    records an abstention, so this parser does not require the full pipeline
    schema.
    """

    raw = json.loads(path.read_text(encoding="utf-8"))
    state = IncidentState(
        incident_id=str(raw["incident_id"]),
        title=str(raw["title"]),
        baseline=ServiceState(**raw["baseline"]),
        events=[ChangeEvent(**item) for item in raw.get("events", [])],
        hypotheses=[Hypothesis(**item) for item in raw.get("hypotheses", [])],
    )
    state.evidence_index = [item.source for item in state.events]
    return state, raw


def _experiments(state: IncidentState) -> list[Any]:
    replayed = [replay_hypothesis(state.baseline, item) for item in state.hypotheses]
    return resolve_indistinguishable_interventions(state.hypotheses, replayed)


def _variants(state: IncidentState, raw: dict[str, Any], experiments: list[Any]) -> list[Any]:
    return evolve_fault_family(state.baseline, experiments, list(raw.get("mutations") or []))


def _ranking(state: IncidentState, raw: dict[str, Any], variants: list[Any]) -> list[Any]:
    candidates = [PatchCandidate(**item) for item in raw.get("patch_candidates") or []]
    mutation_suite = [
        {"name": item.name, "changes": item.changes, "mandatory": item.mandatory}
        for item in variants
    ]
    return run_tournament(state.baseline, candidates, mutation_suite) if candidates else []


def _rollback_verified(state: IncidentState, selected: Any) -> bool:
    return bool(
        selected.rollback
        and selected.rollback_changes
        and state.baseline.evolve(selected.changes).evolve(selected.rollback_changes) == state.baseline
    )


def _checks(experiments: list[Any], selected: Any, rollback_verified: bool, run_id: str) -> list[dict[str, Any]]:
    primary = [item for item in experiments if item.classification == "primary-cause"]
    mandatory = [item for item in selected.results if item.get("mandatory", True)]
    variants_healthy = bool(mandatory) and all(item.get("healthy") is True for item in mandatory)
    return [
        {
            "name": "counterfactual-replay",
            "required": True,
            "executed": True,
            "conclusion": "success" if primary else "failure",
            "exit_code": 0 if primary else 1,
            "run_id": run_id,
            "evidence": "agent-step counterfactual results",
        },
        {
            "name": "fault-genome-suite",
            "required": True,
            "executed": True,
            "conclusion": "success" if variants_healthy else "failure",
            "exit_code": 0 if variants_healthy else 1,
            "run_id": run_id,
            "evidence": "agent-step PatchTournament result",
        },
        {
            "name": "rollback-contract",
            "required": True,
            "executed": True,
            "conclusion": "success" if rollback_verified else "failure",
            "exit_code": 0 if rollback_verified else 1,
            "run_id": run_id,
            "evidence": "agent-step baseline rollback comparison",
        },
    ]


def run_agent_step(
    scenario_path: Path,
    *,
    agent: str,
    skill: str,
    run_id: str,
    approved: bool,
    approver: str | None,
    upstream_result_digests: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Execute the Skill assigned to one compiled DAG node."""

    state, raw = _load(scenario_path)
    result: dict[str, Any]

    if agent == "incident-commander":
        result = {
            "incident_id": state.incident_id,
            "evidence_sources": state.evidence_index,
            "event_count": len(state.events),
            "hypothesis_count": len(state.hypotheses),
        }
    elif agent == "timeline-analyst":
        timeline = build_timeline(state.events)
        result = {
            "event_count": len(timeline),
            "timeline": [asdict(item) for item in timeline],
        }
    elif agent == "hypothesis-scientist":
        experiments = _experiments(state)
        result = {
            "experiments": [asdict(item) for item in experiments],
            "primary_cause_count": sum(item.classification == "primary-cause" for item in experiments),
            "indeterminate_count": sum(item.classification == "indeterminate" for item in experiments),
        }
    elif agent == "universe-builder":
        experiments = _experiments(state)
        variants = _variants(state, raw, experiments)
        result = {
            "primary_cause_count": sum(item.classification == "primary-cause" for item in experiments),
            "fault_variants": [asdict(item) for item in variants],
        }
    elif agent == "patch-engineer":
        experiments = _experiments(state)
        variants = _variants(state, raw, experiments)
        ranking = _ranking(state, raw, variants)
        selected = ranking[0] if ranking else None
        result = {
            "candidate_count": len(ranking),
            "selected_patch": asdict(selected) if selected else None,
            "ranking": [asdict(item) for item in ranking],
        }
    elif agent == "adversarial-verifier":
        experiments = _experiments(state)
        variants = _variants(state, raw, experiments)
        ranking = _ranking(state, raw, variants)
        selected = ranking[0] if ranking else None
        result = {
            "fault_variant_count": len(variants),
            "selected_patch": selected.candidate_id if selected else None,
            "mandatory_variants_healthy": bool(selected) and all(
                item.get("healthy") is True for item in selected.results if item.get("mandatory", True)
            ),
        }
    elif agent == "release-auditor":
        experiments = _experiments(state)
        variants = _variants(state, raw, experiments)
        ranking = _ranking(state, raw, variants)
        if not ranking:
            raise ValueError("RiskGate requires at least one patch candidate")
        selected = ranking[0]
        rollback_verified = _rollback_verified(state, selected)
        gate = evaluate_gate(
            selected,
            approved=approved,
            primary_cause_proven=any(item.classification == "primary-cause" for item in experiments),
            missing_claims=[],
            rollback_verified=rollback_verified,
            checks=_checks(experiments, selected, rollback_verified, run_id),
            approval={
                "status": "approved" if approved else "not-approved",
                "approver": approver if approved else None,
                "is_human": approved,
            },
            mandatory_variant_names=[item.name for item in variants if item.mandatory],
        )
        result = {"selected_patch": selected.candidate_id, "gate": gate}
    elif agent == "skill-curator":
        experiments = _experiments(state)
        variants = _variants(state, raw, experiments)
        ranking = _ranking(state, raw, variants)
        state.experiments = experiments
        state.fault_variants = variants
        state.selected_patch = ranking[0] if ranking else None
        skills = distill_skill_candidates(state)
        result = {"skill_candidates": [asdict(item) for item in skills]}
    else:
        raise ValueError(f"unsupported DAG agent: {agent}")

    return {
        "schema": "chronosfix.agent-step-result/v1",
        "agent": agent,
        "skill": skill,
        "incident_id": state.incident_id,
        "upstream_result_digests": upstream_result_digests or {},
        "result": result,
    }
