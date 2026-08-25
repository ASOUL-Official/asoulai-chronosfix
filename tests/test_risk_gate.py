from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from chronosfix.models import PatchScore
from chronosfix.skills.risk_gate import evaluate_gate


def patch_score(
    *,
    risk: float = 0.30,
    rollback: str = "restore config snapshot",
    results: list[dict] | None = None,
) -> PatchScore:
    return PatchScore(
        candidate_id="P-1",
        title="restore capacity",
        mean_failure_rate=0.01,
        worst_failure_rate=0.02,
        success_score=0.99,
        total_score=0.91,
        risk=risk,
        cost=0.10,
        rollback=rollback,
        results=results
        if results is not None
        else [
            {"name": "nominal", "mandatory": True, "healthy": True},
            {"name": "combined-stress", "mandatory": True, "healthy": True},
        ],
    )


def real_checks() -> list[dict]:
    return [
        {
            "name": "unit-tests",
            "required": True,
            "executed": True,
            "command": "python -m unittest discover -s tests",
            "exit_code": 0,
            "conclusion": "success",
        },
        {
            "name": "fault-family",
            "required": True,
            "executed": True,
            "run_id": "run-42",
            "conclusion": "success",
        },
    ]


def complete_evidence(**overrides) -> dict:
    evidence = {
        "primary_cause_proven": True,
        "missing_claims": [],
        "rollback_verified": True,
        "checks": real_checks(),
        "approval": {"status": "approved", "approver": "release-owner", "is_human": True},
    }
    evidence.update(overrides)
    return evidence


class RiskGateTests(unittest.TestCase):
    def test_approves_only_complete_quality_evidence_and_named_approval(self):
        gate = evaluate_gate(patch_score(), **complete_evidence())

        self.assertEqual(gate["decision"], "approved")
        self.assertEqual(gate["quality_gate"], "passed")
        self.assertEqual(gate["human_approval"], "approved")
        self.assertTrue(gate["release_ready"])
        self.assertEqual(gate["blockers"], [])

    def test_unhealthy_mandatory_variant_cannot_be_approved_by_a_human(self):
        selected = patch_score(
            results=[
                {"name": "nominal", "mandatory": True, "healthy": True},
                {"name": "combined-stress", "mandatory": True, "healthy": False},
            ]
        )
        gate = evaluate_gate(selected, **complete_evidence())

        self.assertEqual(gate["decision"], "blocked-quality-gate")
        self.assertEqual(gate["failed_mandatory_variants"], ["combined-stress"])
        self.assertIn("mandatory-variants-unhealthy", {item["code"] for item in gate["blockers"]})

    def test_unhealthy_optional_variant_does_not_block_release(self):
        selected = patch_score(
            results=[
                {"name": "nominal", "mandatory": True, "healthy": True},
                {"name": "exploratory", "mandatory": False, "healthy": False},
            ]
        )

        self.assertEqual(evaluate_gate(selected, **complete_evidence())["decision"], "approved")

    def test_missing_primary_cause_is_blocking(self):
        gate = evaluate_gate(patch_score(), **complete_evidence(primary_cause_proven=False))

        self.assertIn("primary-cause-not-proven", {item["code"] for item in gate["blockers"]})

    def test_every_missing_claim_is_blocking_even_if_labelled_low_severity(self):
        critical = evaluate_gate(
            patch_score(),
            **complete_evidence(missing_claims=["rollback owner is unknown"]),
        )
        low = evaluate_gate(
            patch_score(),
            **complete_evidence(
                missing_claims=[{"claim": "add another chart", "severity": "low"}]
            ),
        )

        self.assertEqual(critical["decision"], "blocked-quality-gate")
        self.assertEqual(low["decision"], "blocked-quality-gate")
        self.assertIn("critical-claims-missing", {item["code"] for item in low["blockers"]})

    def test_rollback_requires_contract_and_verification(self):
        no_contract = evaluate_gate(patch_score(rollback=""), **complete_evidence())
        not_verified = evaluate_gate(
            patch_score(),
            **complete_evidence(rollback_verified=False),
        )

        self.assertIn("rollback-contract-missing", {item["code"] for item in no_contract["blockers"]})
        self.assertIn("rollback-not-verified", {item["code"] for item in not_verified["blockers"]})

    def test_check_status_without_execution_evidence_is_not_a_real_check(self):
        gate = evaluate_gate(
            patch_score(),
            **complete_evidence(checks={"unit-tests": "success"}),
        )

        self.assertEqual(gate["decision"], "blocked-quality-gate")
        self.assertEqual(gate["failed_checks"][0]["reason"], "missing execution evidence")

    def test_executed_flag_and_command_alone_are_not_outcome_evidence(self):
        gate = evaluate_gate(
            patch_score(),
            **complete_evidence(
                checks=[
                    {
                        "name": "unit-tests",
                        "required": True,
                        "executed": True,
                        "command": "python -m unittest discover -s tests",
                        "conclusion": "success",
                    }
                ]
            ),
        )

        self.assertEqual(gate["decision"], "blocked-quality-gate")
        self.assertEqual(gate["failed_checks"][0]["reason"], "missing execution evidence")

    def test_medium_risk_requires_named_human_not_legacy_boolean(self):
        evidence = complete_evidence()
        evidence.pop("approval")
        gate = evaluate_gate(patch_score(), approved=True, **evidence)

        self.assertEqual(gate["decision"], "blocked-awaiting-human")
        self.assertEqual(gate["human_approval"], "missing-or-invalid")
        self.assertFalse(gate["release_ready"])
        self.assertEqual(gate["quality_blockers"], [])
        self.assertEqual(
            [item["code"] for item in gate["approval_blockers"]],
            ["human-approval-identity-invalid"],
        )

    def test_low_risk_does_not_require_human_approval(self):
        evidence = complete_evidence()
        evidence.pop("approval")
        gate = evaluate_gate(patch_score(risk=0.10), **evidence)

        self.assertEqual(gate["decision"], "approved")
        self.assertEqual(gate["human_approval"], "not-required")

    def test_legacy_call_remains_valid_but_fails_closed(self):
        gate = evaluate_gate(patch_score(), approved=True)

        self.assertEqual(gate["decision"], "blocked-quality-gate")
        codes = {item["code"] for item in gate["blockers"]}
        self.assertIn("primary-cause-not-proven", codes)
        self.assertIn("missing-claims-not-evaluated", codes)
        self.assertIn("rollback-not-verified", codes)
        self.assertIn("required-checks-missing", codes)


if __name__ == "__main__":
    unittest.main()
