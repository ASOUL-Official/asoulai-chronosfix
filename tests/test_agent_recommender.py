from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from chronosfix.runtime.controller import LocalController
from chronosfix.runtime.recommender import recommend_agent_composition


def scenario(name: str) -> dict:
    matches = [path for path in (ROOT / "scenarios").rglob("scenario.json") if path.parent.name == name]
    assert len(matches) == 1
    return json.loads(matches[0].read_text(encoding="utf-8"))


class AgentRecommenderTests(unittest.TestCase):
    def test_golden_case_builds_minimum_complete_repair_team(self):
        recommendation = recommend_agent_composition(scenario("checkout-timeout"))
        agents = [item["agent"] for item in recommendation["composition"]]

        self.assertTrue(recommendation["free_combination"])
        self.assertEqual(recommendation["stop_before"], "无")
        self.assertIn("patch-engineer", agents)
        self.assertIn("adversarial-verifier", agents)
        self.assertIn("release-auditor", agents)
        self.assertLess(len(agents), 8)

    def test_conflicting_evidence_stops_before_patch_and_risk_gate(self):
        recommendation = recommend_agent_composition(scenario("conflicting-counterfactuals"))
        agents = [item["agent"] for item in recommendation["composition"]]

        self.assertEqual(recommendation["stop_before"], "PatchTournament / RiskGate")
        self.assertNotIn("patch-engineer", agents)
        self.assertNotIn("release-auditor", agents)
        self.assertEqual(agents[-1], "hypothesis-scientist")

    def test_controller_persists_recommendation_as_matrix_event(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            controller = LocalController(root / "matrix.sqlite3", root / "runs", python_executable=sys.executable)
            created = controller.create_run("checkout-timeout")
            result = controller.recommend(created["run"]["run_id"], objective="judge-and-compose")

        recommendation = result["recommendation"]
        events = [item for item in result["snapshot"]["events"] if item["event_type"] == "agent_plan_recommended"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["payload"]["decision_id"], recommendation["decision_id"])
        self.assertEqual(events[0]["payload"]["composition"], recommendation["composition"])


if __name__ == "__main__":
    unittest.main()
