from pathlib import Path
import hashlib
import json
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from chronosfix.orchestrator import run_pipeline


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class IntegrityAndTraceTests(unittest.TestCase):
    def test_each_run_has_unique_trace_and_measured_spans(self):
        scenario = ROOT / "scenarios" / "checkout-timeout" / "scenario.json"
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            first = run_pipeline(
                scenario,
                Path(first_dir),
                approved=True,
                approver="test-release-owner",
                approval_reason="trace uniqueness test",
            )
            second = run_pipeline(
                scenario,
                Path(second_dir),
                approved=True,
                approver="test-release-owner",
                approval_reason="trace uniqueness test",
            )
            self.assertNotEqual(first["run_id"], second["run_id"])
            self.assertNotEqual(first["trace_id"], second["trace_id"])

            records = [
                json.loads(line)
                for line in (Path(first_dir) / "trace.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(len(records), 18)
            self.assertTrue(all(item["run_id"] == first["run_id"] for item in records))
            self.assertTrue(all(item["timestamp"] != item["incident_timestamp"] for item in records))
            self.assertTrue(all(item["duration_ms"] >= 0 for item in records))
            self.assertTrue(any(item["duration_kind"] == "measured" for item in records))
            self.assertTrue(any(item["parent_span_id"] for item in records[1:]))

    def test_run_manifest_binds_scenario_patch_approval_and_artifacts(self):
        scenario = ROOT / "scenarios" / "checkout-timeout" / "scenario.json"
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir)
            result = run_pipeline(
                scenario,
                output,
                approved=True,
                approver="test-release-owner",
                approval_reason="manifest integrity test",
            )
            manifest = json.loads((output / "run-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["run_id"], result["run_id"])
            self.assertEqual(manifest["scenario"]["sha256"], _sha256(scenario))
            self.assertEqual(manifest["decision"]["quality_gate"], "passed")
            self.assertEqual(manifest["decision"]["release_decision"], "approved")
            self.assertEqual(
                manifest["decision"]["approval_record"]["approver"],
                "test-release-owner",
            )
            for name, metadata in manifest["artifacts"].items():
                self.assertEqual(metadata["sha256"], _sha256(output / name), name)

            passport = result["state"].evidence_passport
            self.assertFalse(passport.missing_claims)
            self.assertEqual(passport.integrity["run_id"], result["run_id"])


if __name__ == "__main__":
    unittest.main()
