from __future__ import annotations

import sys
import unittest

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from chronosfix.dynamic import DynamicScheduler, TaskSpec, WorkerSpec
from chronosfix.skill_registry import discover_runtime_skills


class DynamicCoordinationTests(unittest.TestCase):
    def test_timeout_reassigns_to_capable_backup_worker(self):
        calls: list[str] = []
        scheduler = DynamicScheduler(
            "INC-DYNAMIC",
            workers=[
                WorkerSpec("worker-a", ("replay",)),
                WorkerSpec("worker-b", ("replay",), priority=110),
            ],
            failure_plan={"replay-task": 1},
        )
        scheduler.register(
            TaskSpec("replay-task", "CounterfactualReplay", "replay", max_attempts=2),
            lambda: calls.append("executed") or {"healthy": True},
        )
        scheduler.run()

        self.assertEqual(scheduler.shared.status, "COMPLETED")
        self.assertEqual(calls, ["executed"])
        self.assertEqual([item.worker for item in scheduler.attempts], ["worker-a", "worker-b"])
        self.assertTrue(any(item.event_type == "task_reassigned" for item in scheduler.events))

    def test_duplicate_event_and_task_replay_are_idempotent(self):
        calls = 0
        scheduler = DynamicScheduler("INC-IDEMPOTENT")

        def handler() -> dict[str, bool]:
            nonlocal calls
            calls += 1
            return {"ok": True}

        scheduler.register(TaskSpec("baseline", "BaselineReplay", "replay"), handler)
        self.assertTrue(scheduler.ingest_evidence("evidence-1", {"kind": "alert"}))
        self.assertFalse(scheduler.ingest_evidence("evidence-1", {"kind": "alert"}))
        scheduler.run()
        scheduler.replay("baseline")

        self.assertEqual(calls, 1)
        self.assertTrue(any(item.event_type == "evidence_deduplicated" for item in scheduler.events))
        self.assertTrue(any(item.event_type == "task_deduplicated" for item in scheduler.events))

    def test_stale_approval_cannot_resume_after_new_evidence(self):
        scheduler = DynamicScheduler("INC-PAUSE")
        checkpoint = scheduler.pause("release owner required")
        self.assertEqual(scheduler.shared.status, "PAUSED_AWAITING_HUMAN")
        scheduler.ingest_evidence("slo-1", {"kind": "slo", "p99_ms": 220})

        self.assertFalse(scheduler.resume(checkpoint, actor="release-owner"))
        self.assertEqual(scheduler.shared.status, "PAUSED_AWAITING_HUMAN")
        self.assertTrue(scheduler.resume(scheduler.shared.revision, actor="release-owner"))
        self.assertEqual(scheduler.shared.status, "RUNNING")
        self.assertTrue(any(item.event_type == "approval_invalidated" for item in scheduler.events))

    def test_runtime_skill_registry_discovers_split_contracts(self):
        skills = discover_runtime_skills(ROOT / "agentteams" / "skills")
        names = {item["name"] for item in skills}
        self.assertTrue({"evidence-fusion", "change-timeline", "risk-gate"}.issubset(names))
        self.assertTrue(all(item["loadable"] for item in skills))


if __name__ == "__main__":
    unittest.main()
