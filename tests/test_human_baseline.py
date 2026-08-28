from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("human_baseline", ROOT / "scripts" / "human_baseline.py")
assert SPEC is not None and SPEC.loader is not None
baseline = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(baseline)


class HumanBaselineProtocolTests(unittest.TestCase):
    def test_protocol_is_privacy_preserving_and_does_not_claim_results(self):
        protocol = json.loads((ROOT / "baseline" / "human-study-protocol.json").read_text(encoding="utf-8"))
        self.assertEqual(protocol["study_status"], "awaiting-human-observations")
        self.assertFalse(protocol["privacy"]["collect_name"])
        self.assertTrue(protocol["controls"]["answer_key_hidden_until_submission"])

    def test_capture_and_summary_require_real_completed_observations(self):
        scenario = ROOT / "scenarios" / "checkout-timeout" / "scenario.json"
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            session_path = root / "participant-a.json"
            baseline.start("participant-a", scenario, session_path)
            running = baseline.summarize(root)
            baseline.finish(session_path, "config-pool", ["change-ticket"], "restore pool=20", "diagnose")
            completed = baseline.summarize(root)
        self.assertEqual(running["completed_participants"], 0)
        self.assertEqual(completed["completed_participants"], 1)
        self.assertEqual(completed["study_status"], "awaiting-human-observations")


if __name__ == "__main__":
    unittest.main()
