from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest
from copy import deepcopy


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from chronosfix.runtime.controller import LocalController
from chronosfix.runtime.recommender import compile_agent_dag, recommend_agent_composition


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

    def test_manager_does_not_read_fixture_labels(self):
        visible = scenario("checkout-timeout")
        relabelled = deepcopy(visible)
        relabelled["ground_truth"] = {
            "expected_outcome": "abstain",
            "fixture_scope": "evaluation-only-counterfactual",
            "model_support": "unsupported",
        }

        expected = recommend_agent_composition(visible)
        actual = recommend_agent_composition(relabelled)

        self.assertEqual(actual["decision_id"], expected["decision_id"])
        self.assertEqual(actual["composition"], expected["composition"])

    def test_recommendation_compiles_to_concrete_topological_tasks(self):
        dag = compile_agent_dag(recommend_agent_composition(scenario("checkout-timeout")))
        tasks = dag["tasks"]

        self.assertEqual(dag["schema"], "chronosfix.agent-dag/v1")
        self.assertEqual(tasks[0]["task_id"], "agent-01-incident-commander")
        self.assertEqual(tasks[0]["depends_on"], [])
        self.assertEqual(tasks[-1]["task_id"], "agent-07-release-auditor")
        self.assertEqual(tasks[-1]["depends_on"], ["agent-06-adversarial-verifier"])

    def test_controller_persists_recommendation_as_matrix_event(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            controller = LocalController(root / "matrix.sqlite3", root / "runs", python_executable=sys.executable)
            created = controller.create_run("checkout-timeout")
            result = controller.recommend(created["run"]["run_id"], objective="judge-and-compose")

        recommendation = result["recommendation"]
        events = [item for item in result["snapshot"]["events"] if item["event_type"] == "agent_plan_recommended"]
        self.assertEqual(len(events), 2)
        self.assertEqual(events[-1]["payload"]["recommendation"]["decision_id"], recommendation["decision_id"])
        self.assertEqual(events[-1]["payload"]["recommendation"]["composition"], recommendation["composition"])
        dag_events = [item for item in result["snapshot"]["events"] if item["event_type"] == "agent_dag_compiled"]
        self.assertEqual(len(dag_events), 2)


if __name__ == "__main__":
    unittest.main()
