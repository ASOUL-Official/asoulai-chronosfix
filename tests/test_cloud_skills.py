from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from chronosfix.cloud_skills import AlibabaCloudSlsQueryAdapter, SlsQueryRequest, SlsSkillValidationError


class CloudSkillAdapterTests(unittest.TestCase):
    def test_dry_run_uses_official_skill_identity_and_required_user_agent(self):
        adapter = AlibabaCloudSlsQueryAdapter(session_id="a" * 32)
        plan = adapter.plan(
            SlsQueryRequest(
                project="chronosfix-demo",
                logstore="checkout",
                from_epoch=100,
                to_epoch=200,
                query='status >= 500 and trace_id: "demo"',
            )
        )
        self.assertEqual(plan["skill"]["name"], "alibabacloud-sls-query")
        self.assertEqual(plan["execution_mode"], "dry-run")
        for command in plan["commands"]:
            self.assertIn("--user-agent", command)
            self.assertIn(adapter.user_agent, command)
            self.assertNotIn("AccessKey", " ".join(command))

    def test_query_window_is_bounded(self):
        adapter = AlibabaCloudSlsQueryAdapter(session_id="b" * 32)
        with self.assertRaises(SlsSkillValidationError):
            adapter.plan(
                SlsQueryRequest(
                    project="chronosfix-demo",
                    logstore="checkout",
                    from_epoch=0,
                    to_epoch=172801,
                    query="*",
                )
            )


if __name__ == "__main__":
    unittest.main()
