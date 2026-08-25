from __future__ import annotations

import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from chronosfix.evaluation import (
    discover_scenarios,
    evaluate_corpus,
    write_evaluation_reports,
)


SCENARIOS = ROOT / "scenarios"


class ScenarioContractTests(unittest.TestCase):
    def test_every_pipeline_scenario_has_ground_truth_and_exact_rollback_values(self):
        pipeline_scenarios = sorted(SCENARIOS.glob("*/scenario.json"))
        self.assertEqual(len(pipeline_scenarios), 9)

        for path in pipeline_scenarios:
            with self.subTest(scenario=path.parent.name):
                raw = json.loads(path.read_text(encoding="utf-8"))
                ground_truth = raw["ground_truth"]
                self.assertEqual(ground_truth["case_type"], "golden")
                self.assertEqual(ground_truth["fixture_scope"], "pipeline-and-evaluation")
                self.assertGreaterEqual(len(ground_truth["expected_primary_causes"]), 1)

                baseline = raw["baseline"]
                self.assertGreaterEqual(len(raw["patch_candidates"]), 1)
                for candidate in raw["patch_candidates"]:
                    rollback_changes = candidate.get("rollback_changes")
                    self.assertTrue(rollback_changes, candidate["id"])
                    self.assertEqual(set(candidate["changes"]), set(rollback_changes))
                    for field_name, rollback_value in rollback_changes.items():
                        self.assertEqual(
                            rollback_value,
                            baseline[field_name],
                            f"{candidate['id']} must roll {field_name} back to baseline",
                        )

    def test_corpus_contains_explicit_evaluation_only_badcases(self):
        scenario_paths = discover_scenarios(SCENARIOS)
        self.assertEqual(len(scenario_paths), 12)

        fixtures = []
        for path in scenario_paths:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if raw["ground_truth"]["fixture_scope"] == "evaluation-only-counterfactual":
                fixtures.append(raw["ground_truth"])

        self.assertEqual(len(fixtures), 3)
        self.assertEqual(
            sorted(item["case_type"] for item in fixtures),
            ["badcase", "badcase", "insufficient-evidence"],
        )
        self.assertTrue(all(item["boundary_note"] for item in fixtures))


class EvaluationReportTests(unittest.TestCase):
    def test_report_separates_supported_accuracy_from_known_failures(self):
        report = evaluate_corpus(SCENARIOS)
        summary = report["summary"]

        self.assertEqual(summary["total_cases"], 12)
        self.assertEqual(summary["golden_cases"], 9)
        self.assertEqual(summary["golden_expectation_met"], 9)
        self.assertEqual(summary["supported_diagnosis_cases"], 9)
        self.assertEqual(summary["supported_diagnosis_correct"], 9)
        self.assertEqual(summary["supported_diagnosis_accuracy"], 1.0)
        self.assertEqual(summary["evaluation_only_cases"], 3)
        self.assertEqual(summary["unsupported_cases"], 2)
        self.assertEqual(summary["unsupported_expectation_failures"], 2)
        self.assertEqual(summary["expected_abstention_cases"], 1)
        self.assertEqual(summary["correct_abstentions"], 1)
        self.assertEqual(summary["abstention_success_rate"], 1.0)
        self.assertEqual(summary["expectation_met_cases"], 10)
        self.assertEqual(summary["unexpected_assertion_cases"], 0)
        self.assertEqual(
            summary["status_counts"],
            {"correct": 9, "incorrect": 0, "abstain": 3},
        )

        cases = {item["scenario_id"]: item for item in report["cases"]}
        self.assertFalse(cases["code-regression-unmodeled"]["expectation_met"])
        self.assertEqual(cases["code-regression-unmodeled"]["status"], "abstain")
        self.assertFalse(cases["queue-backlog-unmodeled"]["expectation_met"])
        self.assertFalse(cases["conflicting-counterfactuals"]["unexpected_assertion"])
        self.assertTrue(cases["conflicting-counterfactuals"]["expectation_met"])
        self.assertEqual(cases["conflicting-counterfactuals"]["status"], "abstain")

    def test_generator_writes_consistent_json_csv_and_markdown(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "evaluation"
            report = write_evaluation_reports(SCENARIOS, output_dir)

            json_path = output_dir / "evaluation-summary.json"
            csv_path = output_dir / "evaluation-cases.csv"
            markdown_path = output_dir / "evaluation-report.md"
            self.assertTrue(json_path.exists())
            self.assertTrue(csv_path.exists())
            self.assertTrue(markdown_path.exists())

            json_report = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(json_report, report)

            with csv_path.open(encoding="utf-8-sig", newline="") as handle:
                csv_rows = list(csv.DictReader(handle))
            self.assertEqual(len(csv_rows), report["summary"]["total_cases"])
            self.assertEqual(
                {row["scenario_id"] for row in csv_rows},
                {item["scenario_id"] for item in report["cases"]},
            )

            markdown = markdown_path.read_text(encoding="utf-8")
            self.assertIn("Golden 9", markdown)
            self.assertIn("Badcase 2", markdown)
            self.assertIn("Insufficient Evidence 1", markdown)
            self.assertIn("不计入成功数", markdown)
            self.assertIn("code-regression-unmodeled", markdown)


if __name__ == "__main__":
    unittest.main()
