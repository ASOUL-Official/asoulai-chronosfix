from pathlib import Path
import json
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from chronosfix.orchestrator import run_pipeline
from chronosfix.simulator import simulate_checkout
from chronosfix.models import PatchCandidate, ServiceState
from chronosfix.skills.patch_tournament import run_tournament


class SimulatorTests(unittest.TestCase):
    def test_pool_restoration_removes_nominal_failures(self):
        broken = ServiceState(120.0, 8, 1.3, "a91c7e")
        fixed = broken.evolve({"pool_size": 24})
        self.assertGreater(simulate_checkout(broken).failure_rate, 0.40)
        self.assertEqual(simulate_checkout(fixed).failure_rate, 0.0)

    def test_mandatory_safe_patch_outranks_higher_scalar_unsafe_patch(self):
        baseline = ServiceState(100.0, 10, 1.0, "v1")
        mutations = [{"name": "traffic-spike", "changes": {"traffic_rps": 150.0}}]
        candidates = [
            PatchCandidate(
                id="P-UNSAFE",
                title="低成本但容量不足",
                changes={},
                risk=0.0,
                cost=0.0,
                rollback="restore baseline",
                rollback_changes={},
            ),
            PatchCandidate(
                id="P-SAFE",
                title="高成本但通过必选验证",
                changes={"pool_size": 20},
                risk=1.0,
                cost=1.0,
                rollback="restore pool size",
                rollback_changes={"pool_size": 10},
            ),
        ]
        ranking = run_tournament(baseline, candidates, mutations)
        self.assertGreater(ranking[0].total_score, 0)
        self.assertEqual(ranking[0].candidate_id, "P-SAFE")


class PipelineTests(unittest.TestCase):
    def test_pipeline_proves_cause_and_selects_patch(self):
        scenario = ROOT / "scenarios" / "checkout-timeout" / "scenario.json"
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_pipeline(
                scenario,
                Path(temp_dir),
                approved=True,
                approver="test-release-owner",
                approval_reason="unit-test approval",
            )
            state = result["state"]
            primary = [item for item in state.experiments if item.classification == "primary-cause"]
            self.assertEqual([item.hypothesis_id for item in primary], ["H-POOL"])
            self.assertEqual(state.selected_patch.candidate_id, "P-RESTORE-POOL")
            self.assertEqual(state.quality_gate, "passed")
            self.assertEqual(state.approval, "approved")
            self.assertGreaterEqual(len(state.fault_variants), 8)
            self.assertIsNotNone(state.evidence_passport)
            self.assertEqual(state.evidence_passport.missing_claims, [])
            self.assertGreaterEqual(len(state.skill_candidates), 3)
            self.assertTrue((Path(temp_dir) / "trace.jsonl").exists())
            proof_bundle = Path(temp_dir) / "proof-bundle.json"
            self.assertTrue(proof_bundle.exists())
            payload = json.loads(proof_bundle.read_text(encoding="utf-8"))
            self.assertIn("fault_variants", payload)
            self.assertIn("evidence_passport", payload)
            self.assertIn("skill_candidates", payload)
            pr_payload = json.loads((Path(temp_dir) / "github-pr.json").read_text(encoding="utf-8"))
            self.assertEqual(pr_payload["selected_patch"]["candidate_id"], "P-RESTORE-POOL")
            self.assertEqual(pr_payload["riskgate"], "approved")
            self.assertTrue((Path(temp_dir) / "github-issue.md").exists())
            self.assertTrue((Path(temp_dir) / "github-pr-diff.patch").exists())
            self.assertTrue((Path(temp_dir) / "github-pr-checks.json").exists())
            transcript = json.loads(
                (Path(temp_dir) / "agentteams-run.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                transcript["framework_mapping"]["manager"], "chronosfix-manager"
            )
            self.assertEqual(len(transcript["framework_mapping"]["workers"]), 8)
            self.assertIn(
                "incident-commander", transcript["framework_mapping"]["workers"]
            )

    def test_medium_risk_patch_requires_human(self):
        scenario = ROOT / "scenarios" / "checkout-timeout" / "scenario.json"
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_pipeline(scenario, Path(temp_dir), approved=False)
            self.assertEqual(result["state"].approval, "blocked-awaiting-human")

    def test_indistinguishable_primary_claims_fail_closed_before_release(self):
        source = ROOT / "scenarios" / "checkout-timeout" / "scenario.json"
        payload = json.loads(source.read_text(encoding="utf-8"))
        pool_intervention = next(
            item["intervention"] for item in payload["hypotheses"] if item["id"] == "H-POOL"
        )
        next(item for item in payload["hypotheses"] if item["id"] == "H-CODE")[
            "intervention"
        ] = pool_intervention
        with tempfile.TemporaryDirectory() as temp_dir:
            scenario = Path(temp_dir) / "scenario.json"
            scenario.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            result = run_pipeline(
                scenario,
                Path(temp_dir) / "output",
                approved=True,
                approver="test-release-owner",
                approval_reason="conflict test",
            )
            state = result["state"]
            self.assertEqual(state.quality_gate, "failed")
            self.assertEqual(state.approval, "blocked-quality-gate")
            self.assertTrue(state.gate_result["conditions"]["critical_missing_claims"])
            self.assertTrue(state.evidence_passport.missing_claims)

    def test_all_scenario_corpus_runs_end_to_end(self):
        scenarios = sorted((ROOT / "scenarios").glob("*/scenario.json"))
        self.assertGreaterEqual(len(scenarios), 7)
        for scenario in scenarios:
            with self.subTest(scenario=scenario.parent.name):
                with tempfile.TemporaryDirectory() as temp_dir:
                    result = run_pipeline(
                        scenario,
                        Path(temp_dir),
                        approved=True,
                        approver="test-release-owner",
                        approval_reason="corpus verification",
                    )
                    state = result["state"]
                    primary = [item for item in state.experiments if item.classification == "primary-cause"]
                    self.assertGreaterEqual(len(primary), 1)
                    all_mandatory_healthy = all(
                        item.get("healthy") is True for item in state.selected_patch.results
                    )
                    if all_mandatory_healthy:
                        self.assertEqual(state.quality_gate, "passed")
                        self.assertEqual(state.approval, "approved")
                    else:
                        self.assertEqual(state.quality_gate, "failed")
                        self.assertEqual(state.approval, "blocked-quality-gate")
                    self.assertIsNotNone(state.evidence_passport)
                    self.assertGreaterEqual(result["metrics"]["trace_spans"], 16)
                    self.assertTrue((Path(temp_dir) / "proof-bundle.json").exists())
                    self.assertTrue((Path(temp_dir) / "proof-report.md").exists())
                    self.assertTrue((Path(temp_dir) / "github-issue.md").exists())
                    self.assertTrue((Path(temp_dir) / "github-pr.md").exists())
                    self.assertTrue((Path(temp_dir) / "github-pr-checks.json").exists())


if __name__ == "__main__":
    unittest.main()
