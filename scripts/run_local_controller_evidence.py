from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from chronosfix.runtime.controller import LocalController


def build(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    controller = LocalController(output / "matrix.sqlite3", output / "runs", python_executable=sys.executable)

    golden = controller.create_run("checkout-timeout", auto_approve=True)
    run_id = golden["run"]["run_id"]
    golden_plan = controller.recommend(run_id, objective="judge-and-compose")
    failover = controller.trigger_failover(run_id, "timeout")
    evidence = controller.ingest_evidence(
        run_id,
        "acceptance-live-evidence-001",
        {
            "kind": "slo",
            "signal": "runtime-topology",
            "summary": "new SLO and runtime topology evidence confirmed during acceptance",
        },
    )
    badcase = controller.create_run("conflicting-counterfactuals", auto_approve=False)
    badcase_plan = controller.recommend(badcase["run"]["run_id"], objective="judge-and-compose")

    failover_task = next(item for item in failover["tasks"] if item["task_id"].startswith("live-timeout-"))
    attempts = [item for item in failover["attempts"] if item["task_id"] == failover_task["task_id"]]
    dynamic_task = next(item for item in evidence["tasks"] if item["task_id"] == "agent-08-skill-curator")
    recompute_event = next(
        item for item in reversed(evidence["events"])
        if item["event_type"] == "incremental_recompute_started"
    )
    badcase_task_ids = [item["task_id"] for item in badcase["tasks"]]
    report = {
        "schema": "chronosfix.local-controller-evidence/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "passed": (
            len(attempts) == 2
            and attempts[0]["status"] == "FAILED"
            and attempts[1]["status"] == "COMPLETED"
            and attempts[0]["pid"] != attempts[1]["pid"]
            and attempts[0]["instance_id"] != attempts[1]["instance_id"]
            and dynamic_task["status"] == "COMPLETED"
            and len(recompute_event["payload"]["affected_task_ids"]) == 6
            and recompute_event["payload"]["new_task_ids"] == ["agent-08-skill-curator"]
            and recompute_event["payload"]["reused_task_ids"] == ["agent-01-incident-commander"]
            and any(item["status"] == "STALE" for item in evidence["approvals"])
            and badcase["run"]["status"] == "ABSTAINED"
            and badcase_task_ids == [
                "agent-01-incident-commander",
                "agent-02-timeline-analyst",
                "agent-03-hypothesis-scientist",
                "counterfactual-evaluation",
            ]
            and len(golden_plan["recommendation"]["composition"]) > len(badcase_plan["recommendation"]["composition"])
            and golden_plan["recommendation"]["stop_before"] == "无"
            and badcase_plan["recommendation"]["stop_before"] == "PatchTournament / RiskGate"
        ),
        "boundaries": controller.health()["boundaries"],
        "golden_run": {
            "run_id": run_id,
            "trace_id": golden["run"]["trace_id"],
            "initial_release_decision": golden["run"]["release_decision"],
            "after_evidence_release_decision": evidence["run"]["release_decision"],
            "matrix_database": str(controller.database),
            "agent_recommendation": golden_plan["recommendation"],
        },
        "worker_failover": {
            "task_id": failover_task["task_id"],
            "attempts": attempts,
            "different_pid": attempts[0]["pid"] != attempts[1]["pid"],
            "different_instance": attempts[0]["instance_id"] != attempts[1]["instance_id"],
        },
        "dynamic_evidence": {
            "event_id": "acceptance-live-evidence-001",
            "task": dynamic_task,
            "approval_statuses": [item["status"] for item in evidence["approvals"]],
            "incremental_recompute": recompute_event["payload"],
            "events": [
                item
                for item in evidence["events"]
                if item["event_type"] in {
                    "evidence_observed",
                    "approval_invalidated",
                    "incremental_recompute_started",
                    "task_invalidated",
                    "task_completed",
                }
            ],
        },
        "badcase_refusal": {
            "run_id": badcase["run"]["run_id"],
            "status": badcase["run"]["status"],
            "release_decision": badcase["run"]["release_decision"],
            "registered_tasks": badcase_task_ids,
            "agent_recommendation": badcase_plan["recommendation"],
        },
    }
    (output / "local-controller-evidence.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Execute and record the real local Controller Demo")
    parser.add_argument("--output", type=Path, default=ROOT / "output" / "local-controller-evidence")
    args = parser.parse_args(argv)
    report = build(args.output.resolve())
    print(json.dumps({"passed": report["passed"], "output": str(args.output.resolve())}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
