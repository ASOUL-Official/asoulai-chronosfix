from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from chronosfix.github_adapter import (  # noqa: E402
    GitHubWriteError,
    GitHubWriter,
    build_write_plan,
    write_external_evidence_draft,
)


def _fixture(root: Path, *, ready: bool = True) -> None:
    for name in (
        "github-pr.md",
        "github-pr-diff.patch",
        "github-pr-checks.json",
        "github-review-audit.jsonl",
    ):
        (root / name).write_text("evidence\n", encoding="utf-8")
    (root / "github-pr.json").write_text(
        json.dumps({"title": "fix: test", "head": "chronosfix/test", "readiness": {"status": "ready" if ready else "pending"}}),
        encoding="utf-8",
    )
    (root / "github-pr-checks.json").write_text(json.dumps({"status": "completed" if ready else "pending"}), encoding="utf-8")
    (root / "run-manifest.json").write_text(json.dumps({"run_id": "run-test-123", "environment": {"git_commit": "base-source"}}), encoding="utf-8")


class _Response:
    def __init__(self, payload: object, request_id: str):
        self._payload = json.dumps(payload).encode("utf-8")
        self.headers = {"X-GitHub-Request-Id": request_id}

    def read(self) -> bytes:
        return self._payload


class GitHubAdapterTests(unittest.TestCase):
    def test_plan_is_network_free_and_requires_ready_checks(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _fixture(root, ready=False)
            with self.assertRaisesRegex(GitHubWriteError, "not ready"):
                build_write_plan(root)

    def test_plan_rejects_non_main_base_and_protected_head(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _fixture(root)
            with self.assertRaisesRegex(GitHubWriteError, "protected main"):
                build_write_plan(root, base_branch="develop")
            payload = json.loads((root / "github-pr.json").read_text(encoding="utf-8"))
            payload["head"] = "main"
            (root / "github-pr.json").write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(GitHubWriteError, "protected branch"):
                build_write_plan(root)

    def test_missing_token_does_not_invoke_transport(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _fixture(root)
            called = False

            def opener(*_args, **_kwargs):
                nonlocal called
                called = True
                raise AssertionError("transport must not run without a token")

            with self.assertRaisesRegex(GitHubWriteError, "is not set"):
                write_external_evidence_draft(root, token_env="CHRONOSFIX_TEST_TOKEN", opener=opener)
            self.assertFalse(called)

    def test_writer_creates_evidence_only_draft_and_records_request_ids(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _fixture(root)
            calls: list[tuple[str, str, dict | None]] = []
            responses = iter(
                [
                    [],
                    {"object": {"sha": "base-sha"}},
                    {"tree": {"sha": "base-tree"}},
                    *([{ "sha": f"blob-{i}" } for i in range(6)]),
                    {"sha": "new-tree"},
                    {"sha": "new-commit"},
                    {},
                    {"number": 99, "html_url": "https://github.com/example/pr/99", "state": "open", "draft": True},
                ]
            )

            def opener(request, **_kwargs):
                body = json.loads(request.data.decode("utf-8")) if request.data else None
                calls.append((request.method, request.full_url, body))
                return _Response(next(responses), f"req-{len(calls)}")

            plan = build_write_plan(root)
            result = GitHubWriter("ghs_test_token", opener=opener).write_evidence_draft(root, plan)
            self.assertEqual(result["mode"], "external-evidence-draft")
            self.assertTrue(result["draft"])
            self.assertTrue(result["merge_policy"]["no_merge"])
            self.assertEqual(result["published_commit_sha"], "new-commit")
            self.assertEqual(len(result["request_ids"]), len(calls))
            self.assertTrue(any(item[0] == "POST" and "/pulls" in item[1] for item in calls))
            ref_body = next(body for method, url, body in calls if method == "POST" and "/git/refs" in url)
            self.assertTrue(str(ref_body["ref"]).startswith("refs/heads/chronosfix/test-external-"))
            pr_body = next(body for method, url, body in calls if method == "POST" and "/pulls" in url)
            self.assertTrue(pr_body["draft"])
            self.assertNotIn("ghs_test_token", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
