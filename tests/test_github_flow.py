from pathlib import Path
import json
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from chronosfix.github_flow import (  # noqa: E402
    build_github_flow_summary,
    write_github_flow_artifacts,
)
from chronosfix.models import (  # noqa: E402
    ChangeEvent,
    EvidencePassport,
    IncidentState,
    PatchScore,
    ServiceState,
)


def _ready_state() -> IncidentState:
    state = IncidentState(
        incident_id="INC-DOWNSTREAM-007",
        title="优惠券依赖抖动放大请求延迟",
        baseline=ServiceState(100.0, 9, 1.6, "e41b99"),
        events=[
            ChangeEvent(
                timestamp="2026-08-24T10:00:00+08:00",
                kind="incident",
                source="alert:coupon-latency",
                summary="依赖长尾延迟触发告警",
                details={"route": "/api/coupon/apply", "severity": "SEV-1"},
            )
        ],
    )
    state.scenario_path = "scenarios/downstream-jitter/scenario.json"
    state.run_id = "run-downstream-007"
    state.selected_patch = PatchScore(
        candidate_id="P-PIN-DEPENDENCY",
        title="将优惠券客户端回退至 1.8",
        mean_failure_rate=0.01,
        worst_failure_rate=0.02,
        success_score=0.98,
        total_score=0.90,
        risk=0.30,
        cost=0.35,
        rollback="恢复 coupon-client 1.9 锁文件",
        results=[{"name": "nominal", "healthy": True}],
        changes={"dependency_latency_factor": 1.0},
        rollback_changes={"dependency_latency_factor": 1.6},
    )
    state.quality_gate = "passed"
    state.approval = "approved"
    state.gate_result = {
        "requires_human": True,
        "decision": "approved",
        "quality_gate": "passed",
        "release_ready": True,
        "blockers": [],
    }
    state.approval_record = {
        "status": "approved",
        "approver": "release-owner@example.test",
        "is_human": True,
        "timestamp": "2026-08-24T11:00:00+08:00",
        "reason": "已复核回滚与验证证据",
        "policy_version": "chronosfix-riskgate/v1",
        "input_digest": "sha256:test-approval-input",
    }
    state.evidence_passport = EvidencePassport(
        patch_id="P-PIN-DEPENDENCY",
        requirement_claims=["依赖延迟恢复到健康阈值。"],
        causal_claims=["反事实回放支持依赖抖动为主因。"],
        verification_claims=["必选变体全部通过。"],
        risk_claims=["风险分 0.30，需要人工审批。"],
        rollback_claims=["rollback_changes 恢复依赖延迟因子 1.6。"],
        missing_claims=[],
    )
    return state


def _metrics(conclusion: str = "success", exit_code: int = 0) -> dict:
    return {
        "run_id": "run-downstream-007",
        "trace_id": "trace-downstream-007",
        "baseline_failure_rate": 0.31,
        "baseline_p99_ms": 420.0,
        "fault_variants": 4,
        "patches_compared": 4,
        "selected_patch_worst_failure_rate": 0.02,
        "trace_spans": 16,
        "git_commit": "base-commit-sha",
        "validation_checks": [
            {
                "name": "counterfactual-replay",
                "required": True,
                "executed": True,
                "conclusion": conclusion,
                "exit_code": exit_code,
                "run_id": "run-downstream-007",
                "evidence": "proof-bundle.json#counterfactual_experiments",
                "summary": "Recorded result from the deterministic replay.",
            }
        ],
    }


class GitHubFlowTests(unittest.TestCase):
    def test_artifacts_are_derived_from_scenario_patch_checks_and_approval(self):
        state = _ready_state()
        with tempfile.TemporaryDirectory() as temp_dir:
            summary = write_github_flow_artifacts(state, _metrics(), Path(temp_dir))
            output = Path(temp_dir)
            issue = json.loads((output / "github-issue.json").read_text(encoding="utf-8"))
            pr = json.loads((output / "github-pr.json").read_text(encoding="utf-8"))
            checks = json.loads((output / "github-pr-checks.json").read_text(encoding="utf-8"))
            diff = (output / "github-pr-diff.patch").read_text(encoding="utf-8")

            self.assertEqual(
                issue["created_from"]["scenario"],
                "scenarios/downstream-jitter/scenario.json",
            )
            self.assertEqual(issue["impact"]["route"], "/api/coupon/apply")
            self.assertIn("downstream-jitter", pr["head"])
            self.assertEqual(pr["state"], "ready-for-review")
            self.assertEqual(
                pr["change_contract"]["changes"],
                {"dependency_latency_factor": 1.0},
            )
            self.assertEqual(
                pr["change_contract"]["rollback_changes"],
                {"dependency_latency_factor": 1.6},
            )
            self.assertIn('"dependency_latency_factor": 1.0', diff)
            self.assertIn('"dependency_latency_factor": 1.6', diff)
            self.assertNotIn("checkout-prod", diff)
            self.assertNotIn("INC-2026-0816-001", diff)

            by_name = {item["name"]: item for item in checks["checks"]}
            self.assertEqual(
                set(by_name),
                {"counterfactual-replay", "riskgate", "human-approval"},
            )
            self.assertEqual(by_name["counterfactual-replay"]["conclusion"], "success")
            self.assertEqual(by_name["riskgate"]["conclusion"], "success")
            self.assertEqual(by_name["human-approval"]["conclusion"], "success")
            self.assertIsNone(checks["commit_sha"])
            self.assertEqual(checks["base_commit_sha"], "base-commit-sha")
            self.assertTrue(summary["release_ready"])

    def test_command_text_alone_is_not_check_execution_evidence(self):
        state = _ready_state()
        metrics = _metrics()
        metrics["validation_checks"] = [
            {
                "name": "unit-tests",
                "required": True,
                "executed": True,
                "command": "python -m unittest discover -s tests",
                "conclusion": "success",
            }
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            write_github_flow_artifacts(state, metrics, Path(temp_dir))
            checks = json.loads(
                (Path(temp_dir) / "github-pr-checks.json").read_text(encoding="utf-8")
            )
            unit = next(item for item in checks["checks"] if item["name"] == "unit-tests")
            self.assertEqual(unit["conclusion"], "pending")

    def test_missing_inputs_fail_closed_as_pending_draft(self):
        state = IncidentState(
            incident_id="INC-PENDING",
            title="证据尚未齐全",
            baseline=ServiceState(50.0, 8, 1.0, "unknown"),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            write_github_flow_artifacts(state, {}, Path(temp_dir))
            output = Path(temp_dir)
            pr = json.loads((output / "github-pr.json").read_text(encoding="utf-8"))
            checks = json.loads((output / "github-pr-checks.json").read_text(encoding="utf-8"))
            diff = (output / "github-pr-diff.patch").read_text(encoding="utf-8")

            self.assertEqual(pr["state"], "draft")
            self.assertEqual(pr["readiness"]["status"], "pending")
            self.assertIn("scenario_path", pr["readiness"]["missing_evidence"])
            self.assertIn("selected_patch", pr["readiness"]["missing_evidence"])
            self.assertIn("metrics.validation_checks", pr["readiness"]["missing_evidence"])
            self.assertEqual(pr["changed_files"], [])
            self.assertIn("no patch diff generated", diff)
            self.assertTrue(
                all(item["conclusion"] != "success" for item in checks["checks"])
            )
            self.assertEqual(checks["status"], "pending")

    def test_explicit_failed_check_and_gate_keep_pr_blocked(self):
        state = _ready_state()
        state.quality_gate = "failed"
        state.approval = "blocked-quality-gate"
        state.gate_result = {
            "requires_human": True,
            "decision": "blocked-quality-gate",
            "quality_gate": "failed",
            "release_ready": False,
            "blockers": [{"code": "required-checks-failed"}],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            write_github_flow_artifacts(
                state, _metrics(conclusion="failure", exit_code=1), Path(temp_dir)
            )
            output = Path(temp_dir)
            pr = json.loads((output / "github-pr.json").read_text(encoding="utf-8"))
            checks = json.loads((output / "github-pr-checks.json").read_text(encoding="utf-8"))
            by_name = {item["name"]: item for item in checks["checks"]}

            self.assertEqual(pr["state"], "draft")
            self.assertEqual(pr["readiness"]["status"], "blocked")
            self.assertIn("riskgate", pr["readiness"]["failed_evidence"])
            self.assertEqual(by_name["counterfactual-replay"]["conclusion"], "failure")
            self.assertEqual(by_name["riskgate"]["conclusion"], "failure")
            self.assertEqual(checks["status"], "blocked")

    def test_public_summary_interface_remains_available(self):
        summary = build_github_flow_summary(_ready_state())
        self.assertEqual(summary["repository"], "ASOUL-Official/asoulai-chronosfix")
        self.assertEqual(summary["issue"], "#42")
        self.assertEqual(summary["pull_request"], "#43")
        self.assertEqual(summary["selected_patch"], "P-PIN-DEPENDENCY")


if __name__ == "__main__":
    unittest.main()
