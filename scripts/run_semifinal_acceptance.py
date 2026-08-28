from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def node_executable() -> str:
    discovered = shutil.which("node")
    if discovered:
        return discovered
    bundled = (
        Path.home()
        / ".cache"
        / "codex-runtimes"
        / "codex-primary-runtime"
        / "dependencies"
        / "node"
        / "bin"
        / "node.exe"
    )
    return str(bundled) if bundled.is_file() else "node"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return read_json(path)
    except (OSError, json.JSONDecodeError):
        return {}


def nested(data: dict[str, Any], *keys: str) -> Any:
    value: Any = data
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def git_head() -> str | None:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return completed.stdout.strip() or None if completed.returncode == 0 else None


def run_check(
    name: str,
    command: list[str],
    *,
    expected_exit_codes: tuple[int, ...] = (0,),
) -> dict[str, Any]:
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    duration_ms = round((time.perf_counter() - started) * 1000, 3)
    return {
        "name": name,
        "command": command,
        "expected_exit_codes": list(expected_exit_codes),
        "exit_code": completed.returncode,
        "passed": completed.returncode in expected_exit_codes,
        "duration_ms": duration_ms,
        "stdout_excerpt": completed.stdout[-2000:],
        "stderr_excerpt": completed.stderr[-2000:],
    }


def assertion(name: str, actual: Any, expected: Any) -> dict[str, Any]:
    return {"name": name, "actual": actual, "expected": expected, "passed": actual == expected}


def write_markdown(report: dict[str, Any], path: Path) -> None:
    status = "PASS" if report["passed"] else "FAIL"
    lines = [
        "# ChronosFix 复赛一键验收报告",
        "",
        f"- 结果：**{status}**",
        f"- 生成时间：`{report['generated_at']}`",
        f"- Git commit：`{report['git_commit'] or 'unavailable'}`",
        f"- 总耗时：`{report['duration_ms']:.3f} ms`",
        "",
        "## 自动检查",
        "",
        "| 检查 | 结果 | 退出码 | 耗时 ms |",
        "|---|---:|---:|---:|",
    ]
    for item in report["checks"]:
        lines.append(
            f"| {item['name']} | {'PASS' if item['passed'] else 'FAIL'} | {item['exit_code']} | {item['duration_ms']:.3f} |"
        )

    lines.extend(
        [
            "",
            "## 关键断言",
            "",
            "| 断言 | 结果 | 实际值 | 期望值 |",
            "|---|---:|---|---|",
        ]
    )
    for item in report["assertions"]:
        actual = json.dumps(item["actual"], ensure_ascii=False)
        expected = json.dumps(item["expected"], ensure_ascii=False)
        lines.append(f"| {item['name']} | {'PASS' if item['passed'] else 'FAIL'} | `{actual}` | `{expected}` |")

    lines.extend(
        [
            "",
            "## 证据边界",
            "",
            "- 本报告证明本地/CI 环境中的确定性工程闭环可复现。",
            "- 本地 Controller、独立 Worker 子进程和 SQLite Matrix 事件房间已经真实执行；不冒充官方 AgentTeams Controller / Matrix。",
            "- 真实代码补丁在临时 Git checkout 中完成补丁前失败、补丁后通过和回滚恢复；本地未宣称 OS 级网络命名空间。",
            "- Proof-Carrying Change 使用 DSSE + Ed25519 验签；签名身份是本地临时密钥，不冒充 Sigstore keyless 身份。",
            "- 公开事故只使用首方公开复盘，并把官方事实与项目推断分开。",
            "- 云 Skill 保持 dry-run；评测数据为合成数据，不外推生产准确率或商业 ROI。",
            "- 通过分支和无人审批阻断分支均由同一验收器实际执行。",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def run(output_dir: Path) -> dict[str, Any]:
    started = time.perf_counter()
    output_dir.mkdir(parents=True, exist_ok=True)
    python = sys.executable

    with tempfile.TemporaryDirectory(prefix="chronosfix-acceptance-") as temporary:
        work = Path(temporary)
        approved_dir = work / "approved"
        blocked_dir = work / "blocked"
        evaluation_dir = work / "evaluation"
        agentteams_report = work / "agentteams-validation.json"
        local_controller_dir = work / "local-controller"
        patch_sandbox_dir = work / "patch-sandbox"
        attestation_dir = work / "attestation"
        public_incident_report = work / "public-incident-validation.json"
        local_infra_dir = work / "local-infra"
        scenario_report = work / "scenario-schema-validation.json"

        checks = [
            run_check(
                "unit-and-contract-tests",
                [python, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-q"],
            ),
            run_check("strict-json-jsonl-validation", [python, "scripts/validate_json_artifacts.py", "."]),
            run_check(
                "public-draft-2020-12-scenario-schema",
                [python, "scripts/validate_scenario_schema.py", "--output", str(scenario_report)],
            ),
            run_check(
                "agentteams-v1beta1-resource-validation",
                [
                    python,
                    "agentteams/runtime/validate_resources.py",
                    "agentteams/runtime/chronosfix-resources.yaml",
                    "--output",
                    str(agentteams_report),
                ],
            ),
            run_check(
                "executable-local-controller-worker-matrix",
                [
                    python,
                    "scripts/run_local_controller_evidence.py",
                    "--output",
                    str(local_controller_dir),
                ],
            ),
            run_check(
                "real-code-patch-isolated-ci-sandbox",
                [python, "scripts/run_patch_sandbox.py", "--output", str(patch_sandbox_dir)],
            ),
            run_check(
                "proof-carrying-change-dsse-attestation",
                [
                    python,
                    "scripts/build_change_attestation.py",
                    "--output",
                    str(attestation_dir),
                    "--subject",
                    str(patch_sandbox_dir / "patch-sandbox-run.json"),
                    "--subject",
                    str(local_controller_dir / "local-controller-evidence.json"),
                ],
            ),
            run_check(
                "first-party-public-incident-provenance",
                [
                    python,
                    "scripts/validate_public_incident.py",
                    "--output",
                    str(public_incident_report),
                ],
            ),
            run_check(
                "durable-local-production-infra-contracts",
                [python, "scripts/run_local_infra_evidence.py", "--output", str(local_infra_dir)],
            ),
            run_check(
                "approved-proof-carrying-change-chain",
                [
                    python,
                    "demo.py",
                    "--approve",
                    "--approver",
                    "AsoulAI Acceptance Reviewer",
                    "--approval-reason",
                    "Automated semifinal acceptance",
                    "--output",
                    str(approved_dir),
                ],
            ),
            run_check(
                "missing-human-approval-fail-closed",
                [python, "demo.py", "--output", str(blocked_dir)],
                expected_exit_codes=(2,),
            ),
            run_check(
                "twelve-scenario-golden-badcase-evaluation",
                [python, "evaluate.py", "--output", str(evaluation_dir)],
            ),
            run_check(
                "repair-cockpit-javascript-syntax",
                [node_executable(), "--check", "repair-cockpit/app.js"],
            ),
            run_check(
                "release-manifest-cross-artifact-consistency",
                [python, "scripts/validate_release_manifest.py"],
            ),
        ]

        approved = read_json_if_exists(approved_dir / "proof-bundle.json")
        blocked = read_json_if_exists(blocked_dir / "proof-bundle.json")
        evaluation = read_json_if_exists(evaluation_dir / "evaluation-summary.json")
        agentteams = read_json_if_exists(agentteams_report)
        local_controller = read_json_if_exists(local_controller_dir / "local-controller-evidence.json")
        patch_sandbox = read_json_if_exists(patch_sandbox_dir / "patch-sandbox-run.json")
        attestation = read_json_if_exists(attestation_dir / "change-attestation-verification.json")
        public_incident = read_json_if_exists(public_incident_report)
        local_infra = read_json_if_exists(local_infra_dir / "local-infra-evidence.json")
        scenarios = read_json_if_exists(scenario_report)
        summary = nested(evaluation, "summary") or {}

        assertions = [
            assertion("approved.quality_gate", nested(approved, "quality_gate"), "passed"),
            assertion("approved.release_decision", nested(approved, "release_decision"), "approved"),
            assertion("approved.release_ready", nested(approved, "gate_result", "release_ready"), True),
            assertion("approved.coordination.status", nested(approved, "coordination", "status"), "COMPLETED"),
            assertion("approved.coordination.revision", nested(approved, "coordination", "revision"), 36),
            assertion("blocked.quality_gate", nested(blocked, "quality_gate"), "passed"),
            assertion("blocked.human_approval", nested(blocked, "gate_result", "human_approval"), "missing-or-invalid"),
            assertion("blocked.release_decision", nested(blocked, "release_decision"), "blocked-awaiting-human"),
            assertion(
                "blocked.coordination.status",
                nested(blocked, "coordination", "status"),
                "PAUSED_AWAITING_HUMAN",
            ),
            assertion("evaluation.total_cases", nested(summary, "total_cases"), 12),
            assertion("evaluation.supported_diagnosis", nested(summary, "supported_diagnosis_correct"), 9),
            assertion("evaluation.expectation_met", nested(summary, "expectation_met_cases"), 10),
            assertion("evaluation.correct_abstentions", nested(summary, "correct_abstentions"), 1),
            assertion("evaluation.unexpected_assertions", nested(summary, "unexpected_assertion_cases"), 0),
            assertion("agentteams.valid", nested(agentteams, "valid"), True),
            assertion("agentteams.workers", nested(agentteams, "counts", "Worker"), 8),
            assertion("local_controller.passed", nested(local_controller, "passed"), True),
            assertion(
                "local_controller.executed",
                nested(local_controller, "boundaries", "local_controller_executed"),
                True,
            ),
            assertion(
                "local_controller.official_boundary",
                nested(local_controller, "boundaries", "agentteams_official_controller_executed"),
                False,
            ),
            assertion(
                "local_controller.failover_pid",
                nested(local_controller, "worker_failover", "different_pid"),
                True,
            ),
            assertion(
                "local_controller.badcase",
                nested(local_controller, "badcase_refusal", "status"),
                "ABSTAINED",
            ),
            assertion("patch_sandbox.passed", nested(patch_sandbox, "passed"), True),
            assertion(
                "patch_sandbox.before_fails",
                nested(patch_sandbox, "before_tests", "exit_code"),
                1,
            ),
            assertion(
                "patch_sandbox.after_passes",
                nested(patch_sandbox, "after_tests", "exit_code"),
                0,
            ),
            assertion(
                "patch_sandbox.rollback_clean",
                nested(patch_sandbox, "rollback_clean"),
                True,
            ),
            assertion("attestation.passed", nested(attestation, "passed"), True),
            assertion(
                "attestation.signature_valid",
                nested(attestation, "verification", "valid"),
                True,
            ),
            assertion(
                "attestation.tamper_rejected",
                nested(attestation, "tamper_test", "verification_valid"),
                False,
            ),
            assertion("public_incident.valid", nested(public_incident, "valid"), True),
            assertion("public_incident.fact_count", nested(public_incident, "official_fact_count"), 7),
            assertion("local_infra.passed", nested(local_infra, "passed"), True),
            assertion(
                "local_infra.event_bus",
                nested(local_infra, "boundaries", "local_durable_event_bus_executed"),
                True,
            ),
            assertion(
                "local_infra.rocketmq_boundary",
                nested(local_infra, "boundaries", "rocketmq_broker_executed"),
                False,
            ),
            assertion("scenario_schema.valid", nested(scenarios, "valid"), True),
            assertion("scenario_schema.scenario_count", nested(scenarios, "scenario_count"), 12),
        ]

    report = {
        "schema": "chronosfix.semifinal-acceptance/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_head(),
        "duration_ms": round((time.perf_counter() - started) * 1000, 3),
        "passed": all(item["passed"] for item in checks) and all(item["passed"] for item in assertions),
        "checks": checks,
        "assertions": assertions,
        "boundaries": {
            "local_controller_executed": True,
            "local_worker_processes_executed": True,
            "agentteams_runtime_executed": False,
            "cloud_skill_execution": "dry-run",
            "evaluation_data": "deterministic-synthetic",
            "production_accuracy_claimed": False,
        },
    }
    (output_dir / "semifinal-acceptance.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_markdown(report, output_dir / "semifinal-acceptance.md")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the complete ChronosFix semifinal acceptance chain.")
    parser.add_argument("--output", type=Path, default=ROOT / "output" / "semifinal-acceptance")
    args = parser.parse_args(argv)
    report = run(args.output.resolve())
    failed_checks = [item["name"] for item in report["checks"] if not item["passed"]]
    failed_assertions = [item["name"] for item in report["assertions"] if not item["passed"]]
    print(
        json.dumps(
            {
                "passed": report["passed"],
                "output": str(args.output.resolve()),
                "failed_checks": failed_checks,
                "failed_assertions": failed_assertions,
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
