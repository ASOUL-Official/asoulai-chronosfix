from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    message: str


class ScenarioValidationError(ValueError):
    def __init__(self, issues: list[ValidationIssue]) -> None:
        self.issues = issues
        detail = "; ".join(f"{item.path}: {item.message}" for item in issues)
        super().__init__(f"Invalid ChronosFix scenario: {detail}")


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_scenario(payload: Any) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not isinstance(payload, dict):
        return [ValidationIssue("$", "must be a JSON object")]

    for key in ("incident_id", "title", "baseline", "events", "hypotheses", "mutations", "patch_candidates"):
        if key not in payload:
            issues.append(ValidationIssue(f"$.{key}", "required field is missing"))

    if issues:
        return issues

    if not isinstance(payload["incident_id"], str) or not payload["incident_id"].strip():
        issues.append(ValidationIssue("$.incident_id", "must be a non-empty string"))
    if not isinstance(payload["title"], str) or not payload["title"].strip():
        issues.append(ValidationIssue("$.title", "must be a non-empty string"))

    baseline = payload["baseline"]
    if not isinstance(baseline, dict):
        issues.append(ValidationIssue("$.baseline", "must be an object"))
    else:
        required_baseline = ("traffic_rps", "pool_size", "dependency_latency_factor", "code_version")
        for key in required_baseline:
            if key not in baseline:
                issues.append(ValidationIssue(f"$.baseline.{key}", "required field is missing"))
        for key in ("traffic_rps", "pool_size", "dependency_latency_factor", "code_latency_factor"):
            if key in baseline and (not _number(baseline[key]) or baseline[key] <= 0):
                issues.append(ValidationIssue(f"$.baseline.{key}", "must be a positive number"))

    events = payload["events"]
    if not isinstance(events, list) or not events:
        issues.append(ValidationIssue("$.events", "must contain at least one event"))
    elif not any(isinstance(item, dict) and item.get("kind") == "incident" for item in events):
        issues.append(ValidationIssue("$.events", "must contain an incident event"))

    hypotheses = payload["hypotheses"]
    if not isinstance(hypotheses, list) or not hypotheses:
        issues.append(ValidationIssue("$.hypotheses", "must contain at least one hypothesis"))
    else:
        ids = [item.get("id") for item in hypotheses if isinstance(item, dict)]
        if len(ids) != len(hypotheses) or any(not item for item in ids):
            issues.append(ValidationIssue("$.hypotheses[*].id", "every hypothesis needs a non-empty id"))
        elif len(ids) != len(set(ids)):
            issues.append(ValidationIssue("$.hypotheses[*].id", "hypothesis ids must be unique"))

    mutations = payload["mutations"]
    if not isinstance(mutations, list) or not mutations:
        issues.append(ValidationIssue("$.mutations", "must contain at least one validation mutation"))

    candidates = payload["patch_candidates"]
    if not isinstance(candidates, list) or not candidates:
        issues.append(ValidationIssue("$.patch_candidates", "must contain at least one candidate"))
    else:
        for index, candidate in enumerate(candidates):
            path = f"$.patch_candidates[{index}]"
            if not isinstance(candidate, dict):
                issues.append(ValidationIssue(path, "must be an object"))
                continue
            for key in ("id", "title", "changes", "risk", "cost", "rollback", "rollback_changes"):
                if key not in candidate:
                    issues.append(ValidationIssue(f"{path}.{key}", "required field is missing"))
            for key in ("risk", "cost"):
                value = candidate.get(key)
                if not _number(value) or not 0 <= value <= 1:
                    issues.append(ValidationIssue(f"{path}.{key}", "must be a number between 0 and 1"))
            if "changes" in candidate and not isinstance(candidate["changes"], dict):
                issues.append(ValidationIssue(f"{path}.changes", "must be an object"))
            if "rollback_changes" in candidate and not isinstance(candidate["rollback_changes"], dict):
                issues.append(ValidationIssue(f"{path}.rollback_changes", "must be an object"))

    return issues


def require_valid_scenario(payload: Any) -> None:
    issues = validate_scenario(payload)
    if issues:
        raise ScenarioValidationError(issues)
