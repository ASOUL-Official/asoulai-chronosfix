from pathlib import Path
import json
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from chronosfix.orchestrator import run_pipeline
from chronosfix.simulator import simulate_checkout
from chronosfix.models import ServiceState


class SimulatorTests(unittest.TestCase):
    def test_pool_restoration_removes_nominal_failures(self):
        broken = ServiceState(120.0, 8, 1.3, "a91c7e")
        fixed = broken.evolve({"pool_size": 24})
        self.assertGreater(simulate_checkout(broken).failure_rate, 0.40)
        self.assertEqual(simulate_checkout(fixed).failure_rate, 0.0)


class PipelineTests(unittest.TestCase):
    def test_pipeline_proves_cause_and_selects_patch(self):
        scenario = ROOT / "scenarios" / "checkout-timeout" / "scenario.json"
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_pipeline(scenario, Path(temp_dir), approved=True)
            state = result["state"]
            primary = [item for item in state.experiments if item.classification == "primary-cause"]
            self.assertEqual([item.hypothesis_id for item in primary], ["H-POOL"])
            self.assertEqual(state.selected_patch.candidate_id, "P-RESTORE-POOL")
            self.assertEqual(state.approval, "approved")
            self.assertGreaterEqual(len(state.fault_variants), 8)
            self.assertIsNotNone(state.evidence_passport)
            self.assertGreaterEqual(len(state.skill_candidates), 3)
            self.assertTrue((Path(temp_dir) / "trace.jsonl").exists())
            proof_bundle = Path(temp_dir) / "proof-bundle.json"
            self.assertTrue(proof_bundle.exists())
            payload = json.loads(proof_bundle.read_text(encoding="utf-8"))
            self.assertIn("fault_variants", payload)
            self.assertIn("evidence_passport", payload)
            self.assertIn("skill_candidates", payload)

    def test_medium_risk_patch_requires_human(self):
        scenario = ROOT / "scenarios" / "checkout-timeout" / "scenario.json"
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_pipeline(scenario, Path(temp_dir), approved=False)
            self.assertEqual(result["state"].approval, "blocked-awaiting-human")


if __name__ == "__main__":
    unittest.main()
