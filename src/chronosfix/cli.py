from __future__ import annotations

import argparse
import json
from pathlib import Path

from .orchestrator import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chronosfix",
        description="Run the ChronosFix counterfactual incident demo.",
    )
    parser.add_argument(
        "--scenario",
        type=Path,
        default=Path("scenarios/checkout-timeout/scenario.json"),
        help="Scenario JSON file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/latest"),
        help="Directory for trace and proof bundle.",
    )
    parser.add_argument(
        "--approve",
        action="store_true",
        help="Record the human approval needed for the medium-risk winning patch.",
    )
    parser.add_argument(
        "--approver",
        help="Named human approver. Required together with --approve for medium/high risk patches.",
    )
    parser.add_argument(
        "--approval-reason",
        help="Human-readable reason recorded in the approval audit trail.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.approve and not args.approver:
        raise SystemExit("--approve requires --approver; a boolean alone is not an auditable approval")
    result = run_pipeline(
        args.scenario,
        args.output,
        args.approve,
        approver=args.approver,
        approval_reason=args.approval_reason,
    )
    state = result["state"]
    primary = next((item for item in state.experiments if item.classification == "primary-cause"), None)
    summary = {
        "incident_id": state.incident_id,
        "run_id": result["run_id"],
        "trace_id": result["trace_id"],
        "primary_cause": primary.title if primary else None,
        "intervention_effect_score": primary.intervention_effect_score if primary else None,
        "selected_patch": state.selected_patch.title,
        "quality_gate": state.quality_gate,
        "release_decision": state.approval,
        "proof_report": str(args.output / "proof-report.md"),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if state.approval == "approved" else 2
