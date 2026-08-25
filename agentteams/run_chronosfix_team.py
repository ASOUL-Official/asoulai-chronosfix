from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from chronosfix.orchestrator import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_chronosfix_team",
        description="Run the local deterministic ChronosFix engine and emit an AgentTeams-compatible transcript.",
    )
    parser.add_argument(
        "--scenario",
        type=Path,
        default=ROOT / "scenarios" / "checkout-timeout" / "scenario.json",
        help="Incident scenario JSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "output" / "agentteams-latest",
        help="Directory for AgentTeams transcript and evidence artifacts.",
    )
    parser.add_argument(
        "--approve",
        action="store_true",
        help="Record a human approval in the Release Auditor gate.",
    )
    parser.add_argument("--approver", help="Named human approver; required with --approve.")
    parser.add_argument("--approval-reason", help="Reason stored in the approval audit record.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.approve and not args.approver:
        raise SystemExit("--approve requires --approver")
    result = run_pipeline(
        args.scenario,
        args.output,
        approved=args.approve,
        approver=args.approver,
        approval_reason=args.approval_reason,
    )
    state = result["state"]
    summary = {
        "team": "chronosfix-incident-response",
        "execution_mode": "local-deterministic-engine",
        "agentteams_runtime_executed": False,
        "agentteams_spec": str(ROOT / "agentteams" / "chronosfix-team.yaml"),
        "incident_id": state.incident_id,
        "run_id": result["run_id"],
        "trace_id": result["trace_id"],
        "manager": "chronosfix-manager",
        "workers": [
            "incident-commander",
            "timeline-analyst",
            "hypothesis-scientist",
            "universe-builder",
            "patch-engineer",
            "adversarial-verifier",
            "release-auditor",
            "skill-curator",
        ],
        "selected_patch": state.selected_patch.candidate_id if state.selected_patch else None,
        "quality_gate": state.quality_gate,
        "release_decision": state.approval,
        "artifacts": {
            "agentteams_run": str(args.output / "agentteams-run.json"),
            "trace": str(args.output / "trace.jsonl"),
            "metrics": str(args.output / "engineering-metrics.json"),
            "evaluation": str(args.output / "evaluation-report.md"),
            "run_manifest": str(args.output / "run-manifest.json"),
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if state.approval == "approved" else 2


if __name__ == "__main__":
    raise SystemExit(main())
