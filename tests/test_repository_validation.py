from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_json_artifacts.py"
SPEC = importlib.util.spec_from_file_location("validate_json_artifacts", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
validation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validation)


class RepositoryJsonValidationTests(unittest.TestCase):
    def test_all_submission_json_and_jsonl_are_strictly_valid(self):
        artifacts, errors = validation.validate_repository(ROOT)
        self.assertGreaterEqual(len(artifacts), 20)
        self.assertEqual(errors, [])

    def test_duplicate_keys_and_nonstandard_numbers_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            duplicate = root / "duplicate.json"
            nonstandard = root / "nonstandard.json"
            duplicate.write_text('{"gate":"passed","gate":"failed"}\n', encoding="utf-8")
            nonstandard.write_text('{"score":NaN}\n', encoding="utf-8")

            artifacts, errors = validation.validate_repository(root)

        self.assertEqual(len(artifacts), 2)
        self.assertEqual(len(errors), 2)
        self.assertTrue(any("duplicate object key" in item for item in errors))
        self.assertTrue(any("non-standard numeric constant" in item for item in errors))

    def test_jsonl_error_reports_exact_record_line(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            trace = root / "trace.jsonl"
            trace.write_text('{"ok":true}\n{"broken":}\n', encoding="utf-8")

            errors = validation.validate_artifact(trace)

        self.assertEqual(len(errors), 1)
        self.assertIn("trace.jsonl:2:", errors[0])


if __name__ == "__main__":
    unittest.main()
