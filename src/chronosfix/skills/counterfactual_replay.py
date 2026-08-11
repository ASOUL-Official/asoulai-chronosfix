from __future__ import annotations

from ..models import ExperimentResult, Hypothesis, ServiceState
from ..simulator import simulate_checkout


def replay_hypothesis(baseline: ServiceState, hypothesis: Hypothesis) -> ExperimentResult:
    baseline_result = simulate_checkout(baseline)
    counterfactual = simulate_checkout(baseline.evolve(hypothesis.intervention))
    effect = max(0.0, baseline_result.failure_rate - counterfactual.failure_rate)
    confidence = effect / baseline_result.failure_rate if baseline_result.failure_rate else 0.0
    if confidence >= 0.65:
        classification = "primary-cause"
    elif confidence >= 0.10:
        classification = "amplifier"
    else:
        classification = "not-causal"
    return ExperimentResult(
        hypothesis_id=hypothesis.id,
        title=hypothesis.title,
        baseline_failure_rate=baseline_result.failure_rate,
        counterfactual_failure_rate=counterfactual.failure_rate,
        absolute_effect=round(effect, 4),
        causal_confidence=round(confidence, 4),
        classification=classification,
    )

