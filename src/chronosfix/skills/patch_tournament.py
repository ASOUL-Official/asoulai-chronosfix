from __future__ import annotations

from statistics import mean

from ..models import PatchCandidate, PatchScore, ServiceState
from ..simulator import simulate_checkout


def score_patch(
    baseline: ServiceState,
    candidate: PatchCandidate,
    mutations: list[dict],
) -> PatchScore:
    results = []
    for mutation in mutations:
        state = baseline.evolve(mutation["changes"]).evolve(candidate.changes)
        result = simulate_checkout(state)
        results.append(
            {
                "name": mutation["name"],
                "failure_rate": result.failure_rate,
                "p99_ms": result.p99_ms,
                "healthy": result.healthy,
                "effective_pool_size": result.effective_pool_size,
            }
        )
    mean_failure = mean(item["failure_rate"] for item in results)
    worst_failure = max(item["failure_rate"] for item in results)
    success_score = max(0.0, 1.0 - mean_failure)
    total = 0.70 * success_score + 0.20 * (1.0 - candidate.risk) + 0.10 * (1.0 - candidate.cost)
    return PatchScore(
        candidate_id=candidate.id,
        title=candidate.title,
        mean_failure_rate=round(mean_failure, 4),
        worst_failure_rate=round(worst_failure, 4),
        success_score=round(success_score, 4),
        total_score=round(total, 4),
        risk=candidate.risk,
        cost=candidate.cost,
        rollback=candidate.rollback,
        results=results,
    )


def run_tournament(
    baseline: ServiceState,
    candidates: list[PatchCandidate],
    mutations: list[dict],
) -> list[PatchScore]:
    return sorted(
        [score_patch(baseline, candidate, mutations) for candidate in candidates],
        key=lambda item: (-item.total_score, item.candidate_id),
    )
