from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_public_incident", ROOT / "scripts" / "validate_public_incident.py"
)
assert SPEC is not None and SPEC.loader is not None
validation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validation)


class PublicIncidentTests(unittest.TestCase):
    def test_first_party_facts_are_separated_from_project_inferences(self):
        path = ROOT / "public-incidents" / "cloudflare-2019-waf-regex" / "incident.json"
        report = validation.validate(path)
        data = json.loads(path.read_text(encoding="utf-8"))

        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["official_fact_count"], 7)
        self.assertEqual(data["source"]["publisher"], "Cloudflare")
        self.assertTrue(all(item["classification"] == "project-inference-not-source-claim" for item in data["chronosfix_inferences"]))
        self.assertFalse(data["synthetic_reconstruction"]["enabled"])


if __name__ == "__main__":
    unittest.main()
