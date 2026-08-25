from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Iterable

from .models import Hypothesis, ServiceState
from .skills.counterfactual_replay import (
    replay_hypothesis,
    resolve_indistinguishable_interventions,
)


SCHEMA_VERSION = "chronosfix.evaluation/v1"
CASE_TYPES = {"golden", "badcase", "insufficient-evidence"}
MODEL_SUPPORT_VALUES = {"supported", "unsupported"}
EXPECTED_OUTCOMES = {"diagnose", "abstain"}
FIXTURE_SCOPES = {"pipeline-and-evaluation", "evaluation-only-counterfactual"}


@dataclass(frozen=True)
class EvaluationCaseResult:
    scenario_id: str
    scenario_path: str
    incident_id: str
    case_type: str
    model_support: str
    fixture_scope: str
    expected_outcome: str
    known_actual_causes: list[str]
    expected_primary_causes: list[str]
    expected_amplifiers: list[str]
    expected_not_causal: list[str]
    observed_primary_causes: list[str]
    observed_amplifiers: list[str]
    observed_not_causal: list[str]
    status: str
    expectation_met: bool
    classification_match: bool
    unexpected_assertion: bool
    rationale: str
    boundary_note: str


def discover_scenarios(scenarios_root: Path) -> list[Path]:
    """Return only scenario files that opt in to evaluation via ground_truth."""

    discovered: list[Path] = []
    for path in sorted(scenarios_root.rglob("scenario.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        if "ground_truth" in raw:
            discovered.append(path)
    return discovered


def _validated_ground_truth(raw: dict[str, Any], scenario_path: Path) -> dict[str, Any]:
    ground_truth = raw.get("ground_truth")
    if not isinstance(ground_truth, dict):
        raise ValueError(f"{scenario_path}: ground_truth must be an object")

    required = {
        "case_type",
        "model_support",
        "expected_outcome",
        "expected_primary_causes",
        "expected_amplifiers",
        "expected_not_causal",
        "fixture_scope",
        "known_actual_causes",
        "rationale",
        "boundary_note",
    }
    missing = sorted(required - set(ground_truth))
    if missing:
        raise ValueError(f"{scenario_path}: missing ground_truth fields: {', '.join(missing)}")

    if ground_truth["case_type"] not in CASE_TYPES:
        raise ValueError(f"{scenario_path}: unsupported case_type {ground_truth['case_type']!r}")
    if ground_truth["model_support"] not in MODEL_SUPPORT_VALUES:
        raise ValueError(
            f"{scenario_path}: unsupported model_support {ground_truth['model_support']!r}"
        )
    if ground_truth["expected_outcome"] not in EXPECTED_OUTCOMES:
        raise ValueError(
            f"{scenario_path}: unsupported expected_outcome {ground_truth['expected_outcome']!r}"
        )
    if ground_truth["fixture_scope"] not in FIXTURE_SCOPES:
        raise ValueError(
            f"{scenario_path}: unsupported fixture_scope {ground_truth['fixture_scope']!r}"
        )

    classification_fields = (
        "expected_primary_causes",
        "expected_amplifiers",
        "expected_not_causal",
        "known_actual_causes",
    )
    for field_name in classification_fields:
        values = ground_truth[field_name]
        if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
            raise ValueError(f"{scenario_path}: {field_name} must be a string array")
        if len(values) != len(set(values)):
            raise ValueError(f"{scenario_path}: {field_name} cannot contain duplicates")

    expected = ground_truth["expected_primary_causes"]
    if ground_truth["expected_outcome"] == "abstain" and expected:
        raise ValueError(
            f"{scenario_path}: abstain cases cannot declare expected_primary_causes"
        )
    if ground_truth["expected_outcome"] == "diagnose" and not expected:
        raise ValueError(
            f"{scenario_path}: diagnose cases must declare expected_primary_causes"
        )
    if (
        ground_truth["case_type"] == "insufficient-evidence"
        and ground_truth["expected_outcome"] != "abstain"
    ):
        raise ValueError(
            f"{scenario_path}: insufficient-evidence cases must expect abstention"
        )
    if (
        ground_truth["case_type"] == "golden"
        and ground_truth["fixture_scope"] != "pipeline-and-evaluation"
    ):
        raise ValueError(
            f"{scenario_path}: golden cases must be pipeline-and-evaluation fixtures"
        )

    hypothesis_ids = {item["id"] for item in raw.get("hypotheses", [])}
    referenced_ids = set().union(
        *(set(ground_truth[field_name]) for field_name in classification_fields)
    )
    unknown = sorted(referenced_ids - hypothesis_ids)
    if unknown:
        raise ValueError(
            f"{scenario_path}: ground truth references unknown hypotheses: {', '.join(unknown)}"
        )
    expected_classifications = (
        set(ground_truth["expected_primary_causes"]),
        set(ground_truth["expected_amplifiers"]),
        set(ground_truth["expected_not_causal"]),
    )
    if any(
        left & right
        for index, left in enumerate(expected_classifications)
        for right in expected_classifications[index + 1 :]
    ):
        raise ValueError(f"{scenario_path}: expected classification sets must be disjoint")
    for text_field in ("rationale", "boundary_note"):
        if not isinstance(ground_truth[text_field], str) or not ground_truth[text_field].strip():
            raise ValueError(f"{scenario_path}: {text_field} must be a non-empty string")
    return ground_truth


def evaluate_scenario(scenario_path: Path, scenarios_root: Path | None = None) -> EvaluationCaseResult:
    raw = json.loads(scenario_path.read_text(encoding="utf-8"))
    ground_truth = _validated_ground_truth(raw, scenario_path)
    baseline = ServiceState(**raw["baseline"])
    hypotheses = [Hypothesis(**item) for item in raw.get("hypotheses", [])]
    experiments = resolve_indistinguishable_interventions(
        hypotheses,
        [replay_hypothesis(baseline, item) for item in hypotheses],
    )

    observed_primary = sorted(
        item.hypothesis_id for item in experiments if item.classification == "primary-cause"
    )
    observed_amplifiers = sorted(
        item.hypothesis_id for item in experiments if item.classification == "amplifier"
    )
    observed_not_causal = sorted(
        item.hypothesis_id for item in experiments if item.classification == "not-causal"
    )
    expected_primary = sorted(ground_truth["expected_primary_causes"])
    expected_amplifiers = sorted(ground_truth["expected_amplifiers"])
    expected_not_causal = sorted(ground_truth["expected_not_causal"])
    classification_match = (
        observed_primary == expected_primary
        and observed_amplifiers == expected_amplifiers
        and observed_not_causal == expected_not_causal
    )

    if not observed_primary:
        status = "abstain"
    elif (
        ground_truth["expected_outcome"] == "diagnose"
        and classification_match
    ):
        status = "correct"
    else:
        status = "incorrect"

    expectation_met = (
        classification_match and status == "correct"
        if ground_truth["expected_outcome"] == "diagnose"
        else status == "abstain"
    )
    unexpected_assertion = (
        ground_truth["expected_outcome"] == "abstain" and bool(observed_primary)
    )
    relative_path = (
        scenario_path.relative_to(scenarios_root).as_posix()
        if scenarios_root is not None
        else scenario_path.as_posix()
    )
    return EvaluationCaseResult(
        scenario_id=scenario_path.parent.name,
        scenario_path=relative_path,
        incident_id=raw["incident_id"],
        case_type=ground_truth["case_type"],
        model_support=ground_truth["model_support"],
        fixture_scope=ground_truth["fixture_scope"],
        expected_outcome=ground_truth["expected_outcome"],
        known_actual_causes=sorted(ground_truth["known_actual_causes"]),
        expected_primary_causes=expected_primary,
        expected_amplifiers=expected_amplifiers,
        expected_not_causal=expected_not_causal,
        observed_primary_causes=observed_primary,
        observed_amplifiers=observed_amplifiers,
        observed_not_causal=observed_not_causal,
        status=status,
        expectation_met=expectation_met,
        classification_match=classification_match,
        unexpected_assertion=unexpected_assertion,
        rationale=ground_truth["rationale"],
        boundary_note=ground_truth["boundary_note"],
    )


def evaluate_corpus(scenarios_root: Path) -> dict[str, Any]:
    scenario_paths = discover_scenarios(scenarios_root)
    if not scenario_paths:
        raise ValueError(f"No ground-truth scenarios found below {scenarios_root}")

    results = [evaluate_scenario(path, scenarios_root) for path in scenario_paths]
    status_counts = {
        status: sum(item.status == status for item in results)
        for status in ("correct", "incorrect", "abstain")
    }
    supported_diagnosis = [
        item
        for item in results
        if item.model_support == "supported" and item.expected_outcome == "diagnose"
    ]
    supported_correct = sum(item.status == "correct" for item in supported_diagnosis)
    expected_abstentions = [item for item in results if item.expected_outcome == "abstain"]
    correct_abstentions = sum(item.status == "abstain" for item in expected_abstentions)
    unsupported = [item for item in results if item.model_support == "unsupported"]
    unsupported_expectation_failures = sum(not item.expectation_met for item in unsupported)
    unsupported_false_assertions = sum(
        item.unexpected_assertion for item in unsupported
    )
    evaluation_only = [
        item for item in results if item.fixture_scope == "evaluation-only-counterfactual"
    ]
    golden = [item for item in results if item.case_type == "golden"]
    unexpected_assertions = [item for item in results if item.unexpected_assertion]
    expectation_met = sum(item.expectation_met for item in results)

    def ratio(numerator: int, denominator: int) -> float | None:
        return round(numerator / denominator, 4) if denominator else None

    return {
        "schema_version": SCHEMA_VERSION,
        "measurement_scope": {
            "supported_diagnosis_accuracy": (
                "Only cases whose causal variable is represented by the deterministic simulator."
            ),
            "unsupported_cases": (
                "Reported as known limitations and excluded from supported diagnosis accuracy."
            ),
            "evaluation_only_fixtures": (
                "Run only through counterfactual classification, never through patch, gate or PR flow."
            ),
            "synthetic_data": True,
        },
        "summary": {
            "total_cases": len(results),
            "case_type_counts": {
                case_type: sum(item.case_type == case_type for item in results)
                for case_type in sorted(CASE_TYPES)
            },
            "status_counts": status_counts,
            "expectation_met_cases": expectation_met,
            "expectation_met_rate": ratio(expectation_met, len(results)),
            "golden_cases": len(golden),
            "golden_expectation_met": sum(item.expectation_met for item in golden),
            "supported_diagnosis_cases": len(supported_diagnosis),
            "supported_diagnosis_correct": supported_correct,
            "supported_diagnosis_accuracy": ratio(
                supported_correct, len(supported_diagnosis)
            ),
            "expected_abstention_cases": len(expected_abstentions),
            "correct_abstentions": correct_abstentions,
            "abstention_success_rate": ratio(correct_abstentions, len(expected_abstentions)),
            "unsupported_cases": len(unsupported),
            "unsupported_expectation_failures": unsupported_expectation_failures,
            "unsupported_false_assertions": unsupported_false_assertions,
            "evaluation_only_cases": len(evaluation_only),
            "unexpected_assertion_cases": len(unexpected_assertions),
        },
        "known_limitations": [
            {
                "scenario_id": item.scenario_id,
                "model_support": item.model_support,
                "status": item.status,
                "expectation_met": item.expectation_met,
                "boundary_note": item.boundary_note,
            }
            for item in evaluation_only
        ],
        "cases": [asdict(item) for item in results],
    }


def _join(values: Iterable[str]) -> str:
    return ";".join(values) if values else "-"


def _write_csv(path: Path, cases: list[dict[str, Any]]) -> None:
    columns = [
        "scenario_id",
        "scenario_path",
        "incident_id",
        "case_type",
        "model_support",
        "fixture_scope",
        "expected_outcome",
        "known_actual_causes",
        "expected_primary_causes",
        "expected_amplifiers",
        "expected_not_causal",
        "observed_primary_causes",
        "observed_amplifiers",
        "observed_not_causal",
        "status",
        "expectation_met",
        "classification_match",
        "unexpected_assertion",
        "rationale",
        "boundary_note",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for item in cases:
            row = {key: item[key] for key in columns}
            for key in (
                "known_actual_causes",
                "expected_primary_causes",
                "expected_amplifiers",
                "expected_not_causal",
                "observed_primary_causes",
                "observed_amplifiers",
                "observed_not_causal",
            ):
                row[key] = _join(row[key])
            writer.writerow(row)


def _percent(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.1%}"


def _write_markdown(path: Path, report: dict[str, Any]) -> None:
    summary = report["summary"]
    lines = [
        "# ChronosFix Golden / Badcase 评测报告",
        "",
        "> 口径：本报告由 `python -m chronosfix.evaluation` 从场景 Ground Truth 自动生成；",
        "> 数据为确定性合成回放，不代表真实生产环境准确率。",
        "",
        "## 汇总",
        "",
        f"- 总样例：{summary['total_cases']}。",
        (
            f"- 样例构成：Golden {summary['case_type_counts']['golden']}，"
            f"Badcase {summary['case_type_counts']['badcase']}，"
            f"Insufficient Evidence {summary['case_type_counts']['insufficient-evidence']}；"
            f"其中评测专用夹具 {summary['evaluation_only_cases']}。"
        ),
        (
            f"- 当前模拟器可支持的诊断样例：{summary['supported_diagnosis_cases']}，"
            f"正确 {summary['supported_diagnosis_correct']}，限定口径准确率 "
            f"{_percent(summary['supported_diagnosis_accuracy'])}。"
        ),
        (
            f"- 预期拒答样例：{summary['expected_abstention_cases']}，正确拒答 "
            f"{summary['correct_abstentions']}，拒答成功率 "
            f"{_percent(summary['abstention_success_rate'])}。"
        ),
        (
            f"- 当前模型不支持样例：{summary['unsupported_cases']}；"
            f"未达到理想预期 {summary['unsupported_expectation_failures']}，"
            f"错误强行归因 {summary['unsupported_false_assertions']}。"
        ),
        (
            f"- 应拒答却仍给出主因的样例：{summary['unexpected_assertion_cases']}；"
            "这些样例按失败保留，不计入成功数。"
        ),
        (
            "- 状态分布："
            f"correct={summary['status_counts']['correct']}，"
            f"incorrect={summary['status_counts']['incorrect']}，"
            f"abstain={summary['status_counts']['abstain']}。"
        ),
        "",
        "## 逐例结果",
        "",
        "| 场景 | 类型 | 执行范围 | 模型边界 | 期望 | 观测主因 | 状态 | 达成期望 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for item in report["cases"]:
        expected = (
            _join(item["expected_primary_causes"])
            if item["expected_outcome"] == "diagnose"
            else "abstain"
        )
        lines.append(
            f"| `{item['scenario_id']}` | {item['case_type']} | {item['fixture_scope']} | "
            f"{item['model_support']} | "
            f"{expected} | {_join(item['observed_primary_causes'])} | {item['status']} | "
            f"{'yes' if item['expectation_met'] else 'no'} |"
        )

    lines.extend(
        [
            "",
            "## 结果解释",
            "",
            "- `correct`：系统给出的主因集合与 Ground Truth 完全一致。",
            "- `incorrect`：系统给出了主因，但与 Ground Truth 不一致，或在应拒答时强行归因。",
            "- `abstain`：没有可辨识的假设达到主因阈值；相同干预对应多个来源假设时会安全拒答。",
            "- `supported_diagnosis_accuracy` 只覆盖模拟器实际建模的容量与依赖延迟变量。",
            "- `evaluation-only-counterfactual` 夹具只运行反事实分类，不进入补丁、RiskGate 或 PR 流水线。",
            "- `code_version`、队列深度当前不进入容量方程；相关 Badcase 会如实显示为已知漏诊，"
            "并排除在受支持口径准确率之外。",
            "- 证据冲突夹具要求拒答；相同干预无法区分来源时由可辨识性仲裁降级为 `indeterminate`。",
            "",
            "## 已知边界",
            "",
        ]
    )
    for item in report["known_limitations"]:
        lines.append(
            f"- `{item['scenario_id']}`：status={item['status']}，"
            f"expectation_met={'yes' if item['expectation_met'] else 'no'}；"
            f"{item['boundary_note']}"
        )

    lines.extend(
        [
            "",
            "## 机器可读证据",
            "",
            "- `evaluation-summary.json`：完整口径、汇总和逐例结果。",
            "- `evaluation-cases.csv`：可导入表格或评测平台的逐例记录。",
            "- 本文件：由同一次运行生成的可读摘要。",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_evaluation_reports(scenarios_root: Path, output_dir: Path) -> dict[str, Any]:
    report = evaluate_corpus(scenarios_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "evaluation-summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    _write_csv(output_dir / "evaluation-cases.csv", report["cases"])
    _write_markdown(output_dir / "evaluation-report.md", report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chronosfix-evaluate",
        description="Evaluate ground-truthed ChronosFix Golden/Badcase scenarios.",
    )
    parser.add_argument(
        "--scenarios",
        type=Path,
        default=Path("scenarios"),
        help="Root containing scenario.json files with ground_truth.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/evaluation"),
        help="Directory for JSON, CSV and Markdown reports.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = write_evaluation_reports(args.scenarios, args.output)
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
