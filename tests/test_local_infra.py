from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("run_local_infra_evidence", ROOT / "scripts" / "run_local_infra_evidence.py")
assert SPEC is not None and SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class LocalInfraTests(unittest.TestCase):
    def test_durable_providers_execute_and_keep_official_boundaries_false(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report = module.build(Path(temp_dir))
        self.assertTrue(report["passed"])
        self.assertTrue(report["boundaries"]["local_durable_event_bus_executed"])
        self.assertFalse(report["boundaries"]["rocketmq_broker_executed"])
        self.assertEqual(report["event_bus"]["dlq"]["status"], "DLQ")
        self.assertTrue(report["unified_model"]["stale_revision_blocked"])
        self.assertEqual(report["tool_gateway"]["denied"]["status"], 403)
        self.assertEqual(report["otlp"]["span_count"], 18)


if __name__ == "__main__":
    unittest.main()
