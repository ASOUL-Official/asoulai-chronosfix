from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from chronosfix.runtime.controller import LocalController, StaleApprovalError
from chronosfix.runtime.recommender import AGENT_PROFILES


class LocalControllerTests(unittest.TestCase):
    def make_controller(self, temp_dir: str) -> LocalController:
        root = Path(temp_dir)
        return LocalController(
            root / "matrix.sqlite3",
            root / "runs",
            python_executable=sys.executable,
        )

    def test_badcase_executes_minimal_dag_then_abstains_without_patch_gate_or_pr_tasks(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            controller = self.make_controller(temp_dir)
            snapshot = controller.create_run("conflicting-counterfactuals")

        self.assertEqual(snapshot["run"]["status"], "ABSTAINED")
        self.assertEqual(snapshot["run"]["release_decision"], "blocked-insufficient-evidence")
        task_ids = {item["task_id"] for item in snapshot["tasks"]}
        self.assertEqual(
            task_ids,
            {
                "agent-01-incident-commander",
                "agent-02-timeline-analyst",
                "agent-03-hypothesis-scientist",
                "counterfactual-evaluation",
            },
        )
        tasks = {item["task_id"]: item for item in snapshot["tasks"]}
        self.assertEqual(tasks["agent-02-timeline-analyst"]["depends_on"], ["agent-01-incident-commander"])
        self.assertEqual(tasks["agent-03-hypothesis-scientist"]["depends_on"], ["agent-02-timeline-analyst"])
        self.assertEqual(tasks["counterfactual-evaluation"]["depends_on"], ["agent-03-hypothesis-scientist"])
        abstention = [item for item in snapshot["events"] if item["event_type"] == "abstention_recorded"]
        self.assertEqual(len(abstention), 1)
        self.assertFalse(abstention[0]["payload"]["patch_task_registered"])

    def test_golden_dag_dispatches_named_workers_and_keeps_no_approval_blocked(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            controller = self.make_controller(temp_dir)
            snapshot = controller.create_run("checkout-timeout", auto_approve=False)

        tasks = {item["task_id"]: item for item in snapshot["tasks"]}
        self.assertNotIn("incident-pipeline", tasks)
        self.assertEqual(snapshot["run"]["status"], "PAUSED_AWAITING_HUMAN")
        self.assertEqual(snapshot["run"]["quality_gate"], "passed")
        self.assertEqual(snapshot["run"]["release_decision"], "blocked-awaiting-human")
        self.assertFalse(snapshot["approvals"])
        self.assertEqual(len([key for key in tasks if key.startswith("agent-")]), 7)
        self.assertEqual(tasks["agent-07-release-auditor"]["depends_on"], ["agent-06-adversarial-verifier"])
        for task_id, task in tasks.items():
            if not task_id.startswith("agent-"):
                continue
            self.assertEqual(task["status"], "COMPLETED")
            self.assertEqual(task["result"]["agent"], task_id.split("-", 2)[2])
            self.assertEqual(task["result"]["skill"], task["skill"])
            self.assertEqual(
                set(task["result"]["upstream_result_digests"]),
                set(task["depends_on"]),
            )
            attempts = [item for item in snapshot["attempts"] if item["task_id"] == task_id]
            self.assertEqual(len(attempts), 1)
            self.assertEqual(attempts[0]["instance_id"], AGENT_PROFILES[task["result"]["agent"]]["worker"])

    def test_unknown_evidence_inserts_and_executes_skill_curator_dag_node(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            controller = self.make_controller(temp_dir)
            created = controller.create_run("checkout-timeout", auto_approve=False)
            run_id = created["run"]["run_id"]
            controller.ingest_evidence(
                run_id,
                "live-evidence-new-observation",
                {"kind": "runtime-topology", "summary": "新型连接池拓扑信号已确认"},
            )
            result = controller.recommend(run_id, objective="adapt-to-new-evidence")

        tasks = {item["task_id"]: item for item in result["snapshot"]["tasks"]}
        curator = tasks["agent-08-skill-curator"]
        self.assertEqual(curator["status"], "COMPLETED")
        self.assertEqual(curator["depends_on"], ["agent-07-release-auditor"])
        self.assertEqual(curator["result"]["agent"], "skill-curator")
        self.assertEqual(curator["result"]["skill"], "SkillForge")
        self.assertTrue(any(
            item["event_type"] == "agent_dag_compiled" and item["payload"]["task_count"] == 8
            for item in result["snapshot"]["events"]
        ))
        recompute = [
            item for item in result["snapshot"]["events"]
            if item["event_type"] == "incremental_recompute_started"
        ]
        self.assertEqual(recompute[-1]["payload"]["affected_task_ids"], [])
        self.assertEqual(recompute[-1]["payload"]["new_task_ids"], ["agent-08-skill-curator"])
        self.assertEqual(
            recompute[-1]["payload"]["reused_task_ids"],
            [
                "agent-01-incident-commander",
                "agent-02-timeline-analyst",
                "agent-03-hypothesis-scientist",
                "agent-04-universe-builder",
                "agent-05-patch-engineer",
                "agent-06-adversarial-verifier",
                "agent-07-release-auditor",
            ],
        )

    def test_slo_evidence_incrementally_invalidates_causal_patch_and_gate_nodes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            controller = self.make_controller(temp_dir)
            created = controller.create_run("checkout-timeout", auto_approve=False)
            run_id = created["run"]["run_id"]
            result = controller.ingest_evidence(
                run_id,
                "live-evidence-slo-001",
                {
                    "kind": "slo",
                    "signal": "runtime-topology",
                    "summary": "SLO window changed and a new runtime topology was observed",
                },
            )

        events = result["events"]
        recompute = [item for item in events if item["event_type"] == "incremental_recompute_started"][-1]
        affected = recompute["payload"]["affected_task_ids"]
        self.assertEqual(
            affected,
            [
                "agent-02-timeline-analyst",
                "agent-03-hypothesis-scientist",
                "agent-04-universe-builder",
                "agent-05-patch-engineer",
                "agent-06-adversarial-verifier",
                "agent-07-release-auditor",
            ],
        )
        self.assertEqual(recompute["payload"]["reused_task_ids"], ["agent-01-incident-commander"])
        self.assertEqual(recompute["payload"]["new_task_ids"], ["agent-08-skill-curator"])
        invalidations = [item for item in events if item["event_type"] == "task_invalidated"]
        self.assertEqual({item["task_id"] for item in invalidations}, set(affected))
        self.assertTrue(any(item["event_type"] == "agent_dag_task_reused" and item["task_id"] == "agent-01-incident-commander" for item in events))
        tasks = {item["task_id"]: item for item in result["tasks"]}
        self.assertTrue(all(tasks[item]["status"] == "COMPLETED" for item in affected))
        self.assertEqual(tasks["agent-08-skill-curator"]["status"], "COMPLETED")
        attempts = {
            task_id: [item for item in result["attempts"] if item["task_id"] == task_id]
            for task_id in affected + ["agent-01-incident-commander", "agent-08-skill-curator"]
        }
        self.assertEqual([item["attempt"] for item in attempts["agent-02-timeline-analyst"]], [1, 2])
        self.assertEqual([item["attempt"] for item in attempts["agent-07-release-auditor"]], [1, 2])
        self.assertEqual([item["attempt"] for item in attempts["agent-01-incident-commander"]], [1])
        self.assertEqual([item["attempt"] for item in attempts["agent-08-skill-curator"]], [1])

    def test_timeout_reassignment_uses_different_process_and_instance(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            controller = self.make_controller(temp_dir)
            created = controller.create_run("checkout-timeout")
            run_id = created["run"]["run_id"]
            snapshot = controller.trigger_failover(run_id, "timeout")

        task_id = next(item["task_id"] for item in snapshot["tasks"] if item["task_id"].startswith("live-timeout-"))
        attempts = [item for item in snapshot["attempts"] if item["task_id"] == task_id]
        self.assertEqual([item["status"] for item in attempts], ["FAILED", "COMPLETED"])
        self.assertNotEqual(attempts[0]["pid"], attempts[1]["pid"])
        self.assertNotEqual(attempts[0]["instance_id"], attempts[1]["instance_id"])
        self.assertTrue(all(item["duration_ms"] is not None for item in attempts))

    def test_new_evidence_executes_task_invalidates_approval_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            controller = self.make_controller(temp_dir)
            created = controller.create_run("checkout-timeout")
            run_id = created["run"]["run_id"]
            event_id = "live-evidence-001"
            first = controller.ingest_evidence(
                run_id,
                event_id,
                {"kind": "configuration", "summary": "pool size drift confirmed"},
            )
            revision = first["run"]["revision"]
            second = controller.ingest_evidence(
                run_id,
                event_id,
                {"kind": "configuration", "summary": "duplicate delivery"},
            )

        self.assertEqual(first["run"]["status"], "PAUSED_AWAITING_HUMAN")
        self.assertTrue(any(item["status"] == "STALE" for item in first["approvals"]))
        self.assertFalse(any(item["task_id"].startswith("dynamic-evidence-audit-") for item in first["tasks"]))
        self.assertEqual(len([item for item in first["tasks"] if item["task_id"].startswith("agent-")]), 7)
        self.assertTrue(any(item["event_type"] == "agent_dag_task_reused" for item in first["events"]))
        self.assertEqual(second["run"]["revision"], revision)
        self.assertEqual(len(second["evidence"]), 1)
        self.assertTrue(any(item["event_type"] == "evidence_deduplicated" for item in second["events"]))

    def test_stale_approval_is_rejected_and_state_survives_restart(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            controller = self.make_controller(temp_dir)
            created = controller.create_run("checkout-timeout")
            run_id = created["run"]["run_id"]
            old_revision = created["run"]["revision"]
            controller.ingest_evidence(
                run_id,
                "live-evidence-stale",
                {"kind": "slo", "summary": "P99 watch window changed"},
            )
            with self.assertRaises(StaleApprovalError):
                controller.approve(run_id, "old-review", expected_revision=old_revision)
            restarted = self.make_controller(temp_dir)
            snapshot = restarted.snapshot(run_id)

        self.assertEqual(snapshot["run"]["status"], "PAUSED_AWAITING_HUMAN")
        self.assertTrue(any(item["event_type"] == "approval_rejected_stale" for item in snapshot["events"]))
        self.assertTrue(any(item["status"] == "STALE" for item in snapshot["approvals"]))


if __name__ == "__main__":
    unittest.main()
