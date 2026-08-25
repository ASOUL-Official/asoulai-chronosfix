from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from chronosfix.schema import ScenarioValidationError, require_valid_scenario, validate_scenario


class ScenarioSchemaTests(unittest.TestCase):
    def test_all_repository_scenarios_pass_runtime_contract(self):
        for path in sorted((ROOT / "scenarios").glob("*/scenario.json")):
            with self.subTest(path=path):
                payload = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(validate_scenario(payload), [])

    def test_missing_rollback_changes_is_rejected(self):
        payload = json.loads(
            (ROOT / "scenarios" / "checkout-timeout" / "scenario.json").read_text(encoding="utf-8")
        )
        payload["patch_candidates"][0].pop("rollback_changes", None)
        with self.assertRaises(ScenarioValidationError):
            require_valid_scenario(payload)

    def test_empty_event_stream_is_rejected(self):
        payload = json.loads(
            (ROOT / "scenarios" / "checkout-timeout" / "scenario.json").read_text(encoding="utf-8")
        )
        payload["events"] = []
        issues = validate_scenario(payload)
        self.assertTrue(any(item.path == "$.events" for item in issues))


if __name__ == "__main__":
    unittest.main()
