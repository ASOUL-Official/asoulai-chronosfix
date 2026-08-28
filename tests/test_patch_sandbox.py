from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("run_patch_sandbox", ROOT / "scripts" / "run_patch_sandbox.py")
assert SPEC is not None and SPEC.loader is not None
sandbox = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sandbox)


class PatchSandboxTests(unittest.TestCase):
    def test_real_patch_fails_before_passes_after_and_rolls_back(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report = sandbox.build(Path(temp_dir))
        self.assertTrue(report["passed"])
        self.assertEqual(report["before_tests"]["exit_code"], 1)
        self.assertEqual(report["after_tests"]["exit_code"], 0)
        self.assertTrue(report["rollback_clean"])
        self.assertTrue(report["security_negative_test"]["path_traversal_patch_blocked"])

    def test_patch_policy_rejects_denied_capabilities(self):
        with self.assertRaises(ValueError):
            sandbox.validate_patch(
                b"--- a/checkout_service.py\n+++ b/checkout_service.py\n@@ -1 +1 @@\n-import math\n+import socket\n"
            )


if __name__ == "__main__":
    unittest.main()
