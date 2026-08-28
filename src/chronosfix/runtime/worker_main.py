from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import time

from chronosfix.evaluation import evaluate_scenario
from chronosfix.orchestrator import run_pipeline


ROOT = Path(__file__).resolve().parents[3]


def emit(value: dict) -> None:
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":")))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ChronosFix isolated local worker process")
    parser.add_argument("--job", choices=("pipeline", "evaluate", "evidence-audit", "probe"), required=True)
    parser.add_argument("--scenario", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--payload-json", default="{}")
    parser.add_argument("--mode", choices=("normal", "timeout", "crash", "denied"), default="normal")
    parser.add_argument("--sleep-ms", type=int, default=0)
    parser.add_argument("--approve", action="store_true")
    parser.add_argument("--approver")
    args = parser.parse_args(argv)

    if args.mode == "denied":
        emit({"error": "tool permission denied by local least-privilege policy"})
        return 77
    if args.mode == "crash":
        emit({"error": "injected worker process crash"})
        return 23
    if args.mode == "timeout" or args.sleep_ms:
        time.sleep(max(args.sleep_ms, 2000 if args.mode == "timeout" else 0) / 1000)

    if args.job == "probe":
        emit({"ok": True, "worker_pid": __import__("os").getpid(), "mode": args.mode})
        return 0

    if args.scenario is None:
        raise SystemExit("--scenario is required")
    scenario = args.scenario.resolve()
    if ROOT not in scenario.parents:
        raise SystemExit("scenario must remain inside the repository")

    if args.job == "evaluate":
        emit({"evaluation": asdict(evaluate_scenario(scenario, ROOT / "scenarios"))})
        return 0

    if args.job == "evidence-audit":
        payload = json.loads(args.payload_json)
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        emit(
            {
                "finding": "new evidence accepted and audited",
                "kind": payload.get("kind", "unknown"),
                "result_digest": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            }
        )
        return 0

    if args.output is None:
        raise SystemExit("--output is required for pipeline")
    result = run_pipeline(
        scenario,
        args.output,
        approved=args.approve,
        approver=args.approver,
        approval_reason="Local Controller executable Demo",
    )
    state = result["state"]
    emit(
        {
            "run_id": result["run_id"],
            "trace_id": result["trace_id"],
            "quality_gate": state.quality_gate,
            "release_decision": state.approval,
            "state_revision": state.state_revision,
            "selected_patch": state.selected_patch.candidate_id if state.selected_patch else None,
            "output": str(args.output),
        }
    )
    return 0 if state.approval == "approved" else 2


if __name__ == "__main__":
    raise SystemExit(main())
