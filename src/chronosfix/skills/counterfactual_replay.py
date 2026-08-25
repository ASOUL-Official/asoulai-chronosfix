from __future__ import annotations

from dataclasses import replace
import json

from ..models import ExperimentResult, Hypothesis, ServiceState
from ..simulator import simulate_checkout


def replay_hypothesis(baseline: ServiceState, hypothesis: Hypothesis) -> ExperimentResult:
    baseline_result = simulate_checkout(baseline)
    counterfactual = simulate_checkout(baseline.evolve(hypothesis.intervention))
    effect = max(0.0, baseline_result.failure_rate - counterfactual.failure_rate)
    effect_score = effect / baseline_result.failure_rate if baseline_result.failure_rate else 0.0
    if effect_score >= 0.65:
        classification = "primary-cause"
    elif effect_score >= 0.10:
        classification = "amplifier"
    else:
        classification = "not-causal"
    return ExperimentResult(
        hypothesis_id=hypothesis.id,
        title=hypothesis.title,
        baseline_failure_rate=baseline_result.failure_rate,
        counterfactual_failure_rate=counterfactual.failure_rate,
        absolute_effect=round(effect, 4),
        intervention_effect_score=round(effect_score, 4),
        classification=classification,
        classification_reason=(
            "intervention_effect_ratio>=0.65"
            if classification == "primary-cause"
            else "0.10<=intervention_effect_ratio<0.65"
            if classification == "amplifier"
            else "intervention_effect_ratio<0.10"
        ),
    )


def resolve_indistinguishable_interventions(
    hypotheses: list[Hypothesis], experiments: list[ExperimentResult]
) -> list[ExperimentResult]:
    """Fail closed when multiple primary hypotheses use the same intervention.

    A counterfactual can establish that changing a variable repairs the symptom,
    but two provenance hypotheses that make the exact same change cannot be
    distinguished by that replay alone.  Those claims are therefore downgraded
    to ``indeterminate`` until source-level evidence is supplied.
    """

    intervention_by_id = {
        item.id: json.dumps(item.intervention, ensure_ascii=False, sort_keys=True)
        for item in hypotheses
    }
    primary_groups: dict[str, list[str]] = {}
    for item in experiments:
        if item.classification != "primary-cause":
            continue
        fingerprint = intervention_by_id.get(item.hypothesis_id)
        if fingerprint is not None:
            primary_groups.setdefault(fingerprint, []).append(item.hypothesis_id)

    ambiguous_ids = {
        hypothesis_id
        for group in primary_groups.values()
        if len(group) > 1
        for hypothesis_id in group
    }
    if not ambiguous_ids:
        return experiments

    reason = (
        "indistinguishable-intervention: multiple provenance hypotheses map "
        "to the same counterfactual change; source-level evidence required"
    )
    return [
        replace(item, classification="indeterminate", classification_reason=reason)
        if item.hypothesis_id in ambiguous_ids
        else item
        for item in experiments
    ]
