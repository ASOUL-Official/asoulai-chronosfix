from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
from statistics import median
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "baseline" / "human-study-protocol.json"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def start(participant_code: str, scenario: Path, output: Path) -> dict[str, Any]:
    if not participant_code or len(participant_code) > 32:
        raise ValueError("participant code must be 1-32 characters")
    scenario_bytes = scenario.read_bytes()
    session = {
        "schema": "chronosfix.human-baseline-observation/v1",
        "session_id": f"human-{secrets.token_hex(6)}",
        "participant_code": participant_code,
        "scenario": str(scenario),
        "scenario_sha256": hashlib.sha256(scenario_bytes).hexdigest(),
        "started_at": now(),
        "completed_at": None,
        "status": "RUNNING",
        "answer_key_exposed": False,
        "response": None
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(session, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return session


def finish(session_path: Path, primary_cause: str, evidence: list[str], rollback: str, decision: str) -> dict[str, Any]:
    session = load(session_path)
    if session.get("status") != "RUNNING":
        raise ValueError("session is not running")
    if decision not in {"diagnose", "abstain"}:
        raise ValueError("decision must be diagnose or abstain")
    started = datetime.fromisoformat(session["started_at"])
    completed = datetime.now(timezone.utc)
    session.update(
        completed_at=completed.isoformat(),
        status="COMPLETED",
        elapsed_seconds=round((completed - started).total_seconds(), 3),
        response={
            "primary_cause": primary_cause,
            "evidence": evidence,
            "rollback": rollback,
            "decision": decision,
        },
    )
    session_path.write_text(json.dumps(session, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return session


def summarize(directory: Path) -> dict[str, Any]:
    observations = [load(path) for path in sorted(directory.glob("*.json"))]
    completed = [item for item in observations if item.get("status") == "COMPLETED"]
    protocol = load(PROTOCOL)
    elapsed = [float(item["elapsed_seconds"]) for item in completed]
    return {
        "schema": "chronosfix.human-baseline-summary/v1",
        "study_id": protocol["study_id"],
        "completed_participants": len(completed),
        "minimum_completed_participants": protocol["minimum_completed_participants"],
        "study_status": (
            "completed-descriptive-only"
            if len(completed) >= protocol["minimum_completed_participants"]
            else "awaiting-human-observations"
        ),
        "median_elapsed_seconds": median(elapsed) if elapsed else None,
        "claim_boundary": protocol["controls"]["small_sample_claim_boundary"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Capture a real pseudonymous human baseline observation")
    sub = parser.add_subparsers(dest="command", required=True)
    start_parser = sub.add_parser("start")
    start_parser.add_argument("--participant-code", required=True)
    start_parser.add_argument("--scenario", type=Path, required=True)
    start_parser.add_argument("--output", type=Path, required=True)
    finish_parser = sub.add_parser("finish")
    finish_parser.add_argument("--session", type=Path, required=True)
    finish_parser.add_argument("--primary-cause", required=True)
    finish_parser.add_argument("--evidence", action="append", default=[])
    finish_parser.add_argument("--rollback", required=True)
    finish_parser.add_argument("--decision", choices=("diagnose", "abstain"), required=True)
    summary_parser = sub.add_parser("summarize")
    summary_parser.add_argument("--observations", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "start":
        result = start(args.participant_code, args.scenario.resolve(), args.output.resolve())
    elif args.command == "finish":
        result = finish(args.session.resolve(), args.primary_cause, args.evidence, args.rollback, args.decision)
    else:
        result = summarize(args.observations.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
