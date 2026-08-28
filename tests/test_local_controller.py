from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from chronosfix.runtime.controller import LocalController, StaleApprovalError


class LocalControllerTests(unittest.TestCase):
    def make_controller(self, temp_dir: str) -> LocalController:
        root = Path(temp_dir)
        return LocalController(
            root / "matrix.sqlite3",
            root / "runs",
            python_executable=sys.executable,
        )

    def test_badcase_abstains_without_patch_gate_or_pr_tasks(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            controller = self.make_controller(temp_dir)
            snapshot = controller.create_run("conflicting-counterfactuals")

        self.assertEqual(snapshot["run"]["status"], "ABSTAINED")
        self.assertEqual(snapshot["run"]["release_decision"], "blocked-insufficient-evidence")
        task_ids = {item["task_id"] for item in snapshot["tasks"]}
        self.assertEqual(task_ids, {"counterfactual-evaluation"})
        abstention = [item for item in snapshot["events"] if item["event_type"] == "abstention_recorded"]
        self.assertEqual(len(abstention), 1)
        self.assertFalse(abstention[0]["payload"]["patch_task_registered"])

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
        dynamic_tasks = [item for item in first["tasks"] if item["task_id"].startswith("dynamic-evidence-audit-")]
        self.assertEqual(len(dynamic_tasks), 1)
        self.assertEqual(dynamic_tasks[0]["status"], "COMPLETED")
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
