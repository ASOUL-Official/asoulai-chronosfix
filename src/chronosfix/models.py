from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class ChangeEvent:
    timestamp: str
    kind: str
    source: str
    summary: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ServiceState:
    traffic_rps: float
    pool_size: int
    dependency_latency_factor: float
    code_version: str
    adaptive_min_pool: bool = False

    def evolve(self, changes: dict[str, Any]) -> "ServiceState":
        data = asdict(self)
        data.update(changes)
        return ServiceState(**data)


@dataclass(frozen=True)
class SimulationResult:
    effective_pool_size: int
    capacity_rps: float
    failure_rate: float
    p99_ms: float
    healthy: bool


@dataclass(frozen=True)
class Hypothesis:
    id: str
    title: str
    owner: str
    intervention: dict[str, Any]
    rationale: str


@dataclass(frozen=True)
class ExperimentResult:
    hypothesis_id: str
    title: str
    baseline_failure_rate: float
    counterfactual_failure_rate: float
    absolute_effect: float
    causal_confidence: float
    classification: str


@dataclass(frozen=True)
class PatchCandidate:
    id: str
    title: str
    changes: dict[str, Any]
    risk: float
    cost: float
    rollback: str


@dataclass(frozen=True)
class PatchScore:
    candidate_id: str
    title: str
    mean_failure_rate: float
    worst_failure_rate: float
    success_score: float
    total_score: float
    risk: float
    cost: float
    rollback: str
    results: list[dict[str, Any]]


@dataclass(frozen=True)
class FaultVariant:
    name: str
    lineage: str
    trigger: str
    changes: dict[str, Any]
    expected_risk: str


@dataclass(frozen=True)
class EvidencePassport:
    patch_id: str
    requirement_claims: list[str]
    causal_claims: list[str]
    verification_claims: list[str]
    risk_claims: list[str]
    rollback_claims: list[str]
    missing_claims: list[str]


@dataclass(frozen=True)
class SkillCandidate:
    name: str
    source_incident: str
    trigger_pattern: str
    input_schema: dict[str, str]
    output_schema: dict[str, str]
    evaluation_cases: list[str]
    safety_boundary: str
    reuse_targets: list[str]
    version: str = "0.1.0"


@dataclass
class IncidentState:
    incident_id: str
    title: str
    baseline: ServiceState
    events: list[ChangeEvent] = field(default_factory=list)
    hypotheses: list[Hypothesis] = field(default_factory=list)
    experiments: list[ExperimentResult] = field(default_factory=list)
    patch_scores: list[PatchScore] = field(default_factory=list)
    fault_variants: list[FaultVariant] = field(default_factory=list)
    evidence_passport: EvidencePassport | None = None
    skill_candidates: list[SkillCandidate] = field(default_factory=list)
    selected_patch: PatchScore | None = None
    approval: str = "not-requested"
    evidence_index: list[str] = field(default_factory=list)
