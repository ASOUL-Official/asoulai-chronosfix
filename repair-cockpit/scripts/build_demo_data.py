from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any


DEMO_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = DEMO_ROOT.parent
SRC_ROOT = PROJECT_ROOT / "src"
SCENARIOS_ROOT = PROJECT_ROOT / "scenarios"

sys.path.insert(0, str(SRC_ROOT))

from chronosfix.evaluation import evaluate_corpus  # noqa: E402
from chronosfix.orchestrator import run_pipeline  # noqa: E402


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _git_head() -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    value = completed.stdout.strip()
    return value or None


def _run_fixture(scenario_path: Path, approved: bool) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="chronosfix-demo-") as temp_dir:
        output_dir = Path(temp_dir)
        run_pipeline(
            scenario_path,
            output_dir,
            approved,
            approver="AsoulAI Demo Reviewer" if approved else None,
            approval_reason="Offline semifinal demo fixture" if approved else None,
        )
        bundle = _read_json(output_dir / "proof-bundle.json")
        metrics = _read_json(output_dir / "engineering-metrics.json")
        checks = _read_json(output_dir / "github-pr-checks.json")
        coordination = _read_json(output_dir / "coordination.json")
    return {
        "run_id": bundle["run_id"],
        "trace_id": metrics["trace_id"],
        "human_approval": bundle["gate_result"]["human_approval"],
        "quality_gate": bundle["quality_gate"],
        "release_decision": bundle["release_decision"],
        "release_ready": bundle["gate_result"]["release_ready"],
        "risk_level": bundle["gate_result"]["risk_level"],
        "blockers": bundle["gate_result"].get("blockers", []),
        "quality_blockers": bundle["gate_result"].get("quality_blockers", []),
        "approval_blockers": bundle["gate_result"].get("approval_blockers", []),
        "approval_record": bundle.get("approval_record", {}),
        "checks": checks["checks"],
        "metrics": {
            "elapsed_ms": metrics["elapsed_ms"],
            "elapsed_ms_kind": metrics["elapsed_ms_kind"],
            "evidence_coverage": metrics["evidence_coverage"],
            "evidence_coverage_kind": metrics["evidence_coverage_kind"],
            "trace_spans": metrics["trace_spans"],
            "rollback_verified": metrics["rollback_verified"],
        },
        "coordination": coordination,
    }


def _build_golden_case(
    scenario_path: Path,
    evaluation_case: dict[str, Any],
) -> dict[str, Any]:
    approved = _run_fixture(scenario_path, approved=True)
    blocked = _run_fixture(scenario_path, approved=False)

    # One additional approved run supplies the shared proof material. The two
    # decision fixtures above remain separate, real RiskGate executions.
    with tempfile.TemporaryDirectory(prefix="chronosfix-demo-proof-") as temp_dir:
        output_dir = Path(temp_dir)
        run_pipeline(
            scenario_path,
            output_dir,
            True,
            approver="AsoulAI Demo Reviewer",
            approval_reason="Offline semifinal demo fixture",
        )
        bundle = _read_json(output_dir / "proof-bundle.json")

    return {
        "id": scenario_path.parent.name,
        "title": bundle["title"],
        "incident_id": bundle["incident_id"],
        "kind": "golden",
        "runtime_scope": "pipeline-and-evaluation",
        "evaluation": evaluation_case,
        "baseline": bundle["baseline"],
        "baseline_metrics": {
            "failure_rate": bundle["metrics"]["baseline_failure_rate"],
            "p99_ms": bundle["metrics"]["baseline_p99_ms"],
        },
        "timeline": bundle["timeline"],
        "experiments": bundle["experiments"],
        "fault_variants": bundle["fault_variants"],
        "patches": bundle["patch_tournament"],
        "selected_patch": bundle["selected_patch"],
        "passport": bundle["evidence_passport"],
        "skills": bundle["skill_candidates"],
        "coordination": approved["coordination"],
        "modes": {
            "approved": approved,
            "blocked": blocked,
        },
    }


def _build_evaluation_case(
    scenario_path: Path,
    evaluation_case: dict[str, Any],
) -> dict[str, Any]:
    raw = _read_json(scenario_path)
    return {
        "id": scenario_path.parent.name,
        "title": raw["title"],
        "incident_id": raw["incident_id"],
        "kind": evaluation_case["case_type"],
        "runtime_scope": evaluation_case["fixture_scope"],
        "evaluation": evaluation_case,
        "baseline": raw["baseline"],
        "timeline": raw.get("events", []),
        "experiments": [],
        "fault_variants": [],
        "patches": [],
        "selected_patch": None,
        "passport": None,
        "skills": [],
        "coordination": None,
        "modes": {},
    }


def build_demo_data() -> dict[str, Any]:
    evaluation = evaluate_corpus(SCENARIOS_ROOT)
    evaluation_by_id = {item["scenario_id"]: item for item in evaluation["cases"]}

    cases: list[dict[str, Any]] = []
    for scenario_path in sorted(SCENARIOS_ROOT.rglob("scenario.json")):
        scenario_id = scenario_path.parent.name
        evaluation_case = evaluation_by_id.get(scenario_id)
        if evaluation_case is None:
            continue
        if evaluation_case["fixture_scope"] == "pipeline-and-evaluation":
            cases.append(_build_golden_case(scenario_path, evaluation_case))
        else:
            cases.append(_build_evaluation_case(scenario_path, evaluation_case))

    head = _git_head()
    return {
        "schema_version": "chronosfix.repair-cockpit/v2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "product": {
            "team": "AsoulAI",
            "name": "ChronosFix",
            "short_name": "A-CFX",
            "title": "AsoulAI ChronosFix（A-CFX）：软件故障时间机器",
            "subtitle": "让每一次软件变更都携带可验证的证据",
        },
        "links": [
            {
                "label": "公开仓库",
                "href": "https://github.com/ASOUL-Official/asoulai-chronosfix",
            },
            {
                "label": "Issue #1 · 协作证据",
                "href": "https://github.com/ASOUL-Official/asoulai-chronosfix/issues/1",
            },
            {
                "label": "PR #2 · 协作证据",
                "href": "https://github.com/ASOUL-Official/asoulai-chronosfix/pull/2",
            },
            {
                "label": "Golden / Badcase 评测",
                "href": "https://github.com/ASOUL-Official/asoulai-chronosfix/blob/main/evidence/evaluation-report.md",
            },
        ],
        "truthful_status": [
            {
                "label": "核心流水线",
                "value": "offline-validated",
                "detail": "确定性合成回放与本地测试已执行",
            },
            {
                "label": "GitHub 变更链",
                "value": "dry-run",
                "detail": "Issue/PR 公开链接是协作证据；补丁 PR 仍为本地草案",
            },
            {
                "label": "AgentTeams / 云调用",
                "value": "pending",
                "detail": "本页不宣称已连接真实 Controller Runtime 或云 API",
            },
        ],
        "revision": {
            "commit": "pending",
            "kind": "local-draft",
            "base_commit": head,
        },
        "evaluation": evaluation,
        "cases": cases,
        "judge_steps": [
            {"id": "incident", "number": "01", "label": "事故事实"},
            {"id": "coordination", "number": "02", "label": "动态协同"},
            {"id": "causal", "number": "03", "label": "因果证明"},
            {"id": "patch", "number": "04", "label": "故障族验证"},
            {"id": "gate", "number": "05", "label": "三态门禁"},
            {"id": "evidence", "number": "06", "label": "证据护照"},
            {"id": "learning", "number": "07", "label": "评测与沉淀"},
        ],
    }


def main() -> int:
    output_path = DEMO_ROOT / "data" / "demo-data.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_demo_data()
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(output_path),
                "golden": payload["evaluation"]["summary"]["golden_cases"],
                "total": payload["evaluation"]["summary"]["total_cases"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
