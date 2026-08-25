from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from ..models import PatchScore


_SUCCESS_STATES = {"success", "successful", "passed", "pass", "completed"}
_NON_HUMAN_APPROVERS = {"anonymous", "auto", "automation", "bot", "system", "unknown"}


def _blocker(code: str, message: str, **details: Any) -> dict[str, Any]:
    item: dict[str, Any] = {"code": code, "message": message}
    if details:
        item["details"] = details
    return item


def _normalise_checks(
    checks: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Accept either a named check map or a list of check-run records."""

    if checks is None:
        return []

    if isinstance(checks, Mapping):
        if "name" in checks or "status" in checks or "conclusion" in checks:
            return [dict(checks)]

        records: list[dict[str, Any]] = []
        for name, value in checks.items():
            if isinstance(value, Mapping):
                record = dict(value)
                record.setdefault("name", str(name))
            else:
                # A bare string is deliberately not enough to prove that a
                # check actually ran. It is kept as a status for diagnostics.
                record = {"name": str(name), "status": value}
            records.append(record)
        return records

    return [dict(item) for item in checks]


def _check_has_execution_evidence(check: Mapping[str, Any]) -> bool:
    """Require an execution marker plus an outcome that can be audited.

    A command only describes what *could* be run.  It is not evidence that the
    command actually ran, so a check also needs an exit code or a durable
    result reference.
    """

    if check.get("executed") is not True:
        return False
    return any(
        check.get(key) is not None and check.get(key) != ""
        for key in ("evidence", "log_path", "run_id", "run_url")
    ) or "exit_code" in check


def _critical_missing_claims(
    missing_claims: Sequence[str | Mapping[str, Any]] | None,
) -> tuple[bool, list[str]]:
    if missing_claims is None:
        return False, []

    unresolved: list[str] = []
    for claim in missing_claims:
        if isinstance(claim, Mapping):
            text = claim.get("claim") or claim.get("message") or claim.get("name")
            unresolved.append(str(text or "unnamed missing claim"))
        else:
            unresolved.append(str(claim))
    # A release gate cannot waive an unresolved evidence claim merely because
    # the producer labelled it "low".  Severity may guide triage, but every
    # item in ``missing_claims`` remains a gap until it is removed upstream.
    return True, unresolved


def evaluate_gate(
    selected: PatchScore,
    approved: bool = False,
    *,
    primary_cause_proven: bool | None = None,
    missing_claims: Sequence[str | Mapping[str, Any]] | None = None,
    rollback_verified: bool | None = None,
    checks: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
    approval: Mapping[str, Any] | None = None,
    mandatory_variant_names: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Evaluate the release gate using explicit, fail-closed evidence.

    ``approved`` is retained for call compatibility, but a boolean is not a
    named human approval. Medium/high-risk changes must provide ``approval``
    with ``status=approved`` and a human ``approver`` (or ``approved_by``).

    The remaining keyword arguments intentionally default to ``None`` rather
    than optimistic values. A caller that does not supply evidence cannot turn
    an unevaluated patch into a release-ready patch.
    """

    risk_level = "high" if selected.risk >= 0.7 else "medium" if selected.risk >= 0.25 else "low"
    requires_human = risk_level in {"medium", "high"}
    quality_blockers: list[dict[str, Any]] = []

    # 1. Causality: a selected patch is not proof of a primary cause.
    primary_cause_ready = primary_cause_proven is True
    if not primary_cause_ready:
        quality_blockers.append(
            _blocker(
                "primary-cause-not-proven",
                "No proven primary cause was supplied to RiskGate.",
                supplied=primary_cause_proven,
            )
        )

    # 2. Fault-family verification: every mandatory variant must be healthy.
    result_by_name = {str(item.get("name", "")): item for item in selected.results}
    if mandatory_variant_names is None:
        mandatory_results = [item for item in selected.results if item.get("mandatory", True)]
        missing_variants: list[str] = []
    else:
        mandatory_results = [result_by_name[name] for name in mandatory_variant_names if name in result_by_name]
        missing_variants = [name for name in mandatory_variant_names if name not in result_by_name]

    failed_variants = [
        str(item.get("name") or "unnamed-variant")
        for item in mandatory_results
        if item.get("healthy") is not True
    ]
    if not mandatory_results:
        quality_blockers.append(
            _blocker(
                "mandatory-variants-missing",
                "No mandatory fault variant results were supplied.",
            )
        )
    if missing_variants:
        quality_blockers.append(
            _blocker(
                "mandatory-variant-results-missing",
                "One or more mandatory fault variants have no result.",
                variants=missing_variants,
            )
        )
    if failed_variants:
        quality_blockers.append(
            _blocker(
                "mandatory-variants-unhealthy",
                "The selected patch failed mandatory fault variants.",
                variants=failed_variants,
            )
        )

    # 3. Evidence completeness. The caller must explicitly establish that the
    # passport has been built and contains no unresolved gap.
    claims_evaluated, critical_claims = _critical_missing_claims(missing_claims)
    if not claims_evaluated:
        quality_blockers.append(
            _blocker(
                "missing-claims-not-evaluated",
                "Missing evidence claims were not evaluated.",
            )
        )
    elif critical_claims:
        quality_blockers.append(
            _blocker(
                "critical-claims-missing",
                "The evidence passport still contains unresolved missing claims.",
                claims=critical_claims,
            )
        )

    # 4. Rollback: a text contract and a successful verification are separate
    # requirements. Never infer verification merely from a non-empty string.
    rollback_contract_present = bool(selected.rollback and selected.rollback.strip())
    if not rollback_contract_present:
        quality_blockers.append(
            _blocker("rollback-contract-missing", "The selected patch has no rollback contract.")
        )
    if rollback_verified is not True:
        quality_blockers.append(
            _blocker(
                "rollback-not-verified",
                "The rollback contract has not been successfully verified.",
                supplied=rollback_verified,
            )
        )

    # 5. Real checks: success text alone is not execution evidence.
    check_records = _normalise_checks(checks)
    required_checks = [item for item in check_records if item.get("required", True)]
    failed_checks: list[dict[str, str]] = []
    for index, check in enumerate(required_checks, start=1):
        name = str(check.get("name") or f"check-{index}")
        status = str(check.get("conclusion") or check.get("status") or "missing").lower()
        reason = None
        if not _check_has_execution_evidence(check):
            reason = "missing execution evidence"
        elif "exit_code" in check and check.get("exit_code") != 0:
            reason = f"exit code {check.get('exit_code')}"
        elif status not in _SUCCESS_STATES:
            reason = f"status {status}"
        if reason:
            failed_checks.append({"name": name, "reason": reason})

    if not required_checks:
        quality_blockers.append(
            _blocker("required-checks-missing", "No required executed checks were supplied.")
        )
    elif failed_checks:
        quality_blockers.append(
            _blocker(
                "required-checks-failed",
                "One or more required checks failed or lack execution evidence.",
                checks=failed_checks,
            )
        )

    # 6. Human approval is deliberately outside the quality gate. A person
    # cannot approve away failed tests, missing evidence, or an unverified
    # rollback. The legacy boolean is exposed for audit but is not an identity.
    approval_record = dict(approval or {})
    approval_status = str(approval_record.get("status") or ("approved" if approved else "not-approved")).lower()
    approver = str(
        approval_record.get("approver")
        or approval_record.get("approved_by")
        or approval_record.get("actor")
        or ""
    ).strip()
    human_approval_ready = (
        not requires_human
        or (
            approval_status == "approved"
            and bool(approver)
            and approver.lower() not in _NON_HUMAN_APPROVERS
            and approval_record.get("is_human", True) is True
        )
    )

    approval_blockers: list[dict[str, Any]] = []
    if requires_human and not human_approval_ready:
        if approval_status != "approved":
            approval_blockers.append(
                _blocker(
                    "human-approval-required",
                    "A named human approval is required for a medium/high-risk patch.",
                    status=approval_status,
                )
            )
        else:
            approval_blockers.append(
                _blocker(
                    "human-approval-identity-invalid",
                    "The approval is not attributable to a named human approver.",
                    approver=approver or None,
                    is_human=approval_record.get("is_human"),
                )
            )

    quality_gate = "passed" if not quality_blockers else "failed"
    if quality_blockers:
        decision = "blocked-quality-gate"
    elif approval_blockers:
        decision = "blocked-awaiting-human"
    else:
        decision = "approved"

    blockers = [*quality_blockers, *approval_blockers]

    return {
        "risk_level": risk_level,
        "requires_human": requires_human,
        "decision": decision,
        "release_ready": decision == "approved",
        "quality_gate": quality_gate,
        "human_approval": (
            "not-required"
            if not requires_human
            else "approved"
            if human_approval_ready
            else "missing-or-invalid"
        ),
        "rollback_ready": rollback_contract_present and rollback_verified is True,
        "failed_mandatory_variants": failed_variants,
        "missing_mandatory_variants": missing_variants,
        "failed_checks": failed_checks,
        "blockers": blockers,
        "quality_blockers": quality_blockers,
        "approval_blockers": approval_blockers,
        "conditions": {
            "primary_cause_proven": primary_cause_ready,
            "mandatory_variants_healthy": bool(mandatory_results)
            and not failed_variants
            and not missing_variants,
            "critical_missing_claims": critical_claims,
            "rollback_contract_present": rollback_contract_present,
            "rollback_verified": rollback_verified is True,
            "required_checks_executed": bool(required_checks) and not failed_checks,
            "approval_status": approval_status,
            "approver": approver or None,
            "legacy_boolean_approval": approved,
        },
    }
