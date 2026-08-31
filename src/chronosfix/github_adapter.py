from __future__ import annotations

"""Guarded GitHub writer for an evidence-only Draft PR.

The normal ChronosFix pipeline is offline. This module is deliberately
opt-in and only publishes generated evidence artifacts to a new branch. It
never writes ``main``, merges a PR, or reports a Check Run that it did not
observe from GitHub.
"""

import argparse
import base64
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .github_flow import REPO
from .integrity import sha256_file


class GitHubWriteError(RuntimeError):
    """Raised when the guarded external write cannot be completed."""


@dataclass(frozen=True)
class GitHubWritePolicy:
    repository: str = REPO
    base_branch: str = "main"
    token_env: str = "GITHUB_TOKEN"
    timeout_seconds: int = 20

    def validate(self) -> None:
        if not re.fullmatch(r"[^/\s]+/[^/\s]+", self.repository):
            raise GitHubWriteError("repository must use OWNER/REPOSITORY form")
        if self.base_branch != "main":
            raise GitHubWriteError("external writer is locked to the protected main base branch")
        if self.timeout_seconds <= 0:
            raise GitHubWriteError("timeout_seconds must be positive")


_EVIDENCE_FILES = (
    "github-pr.md",
    "github-pr.json",
    "github-pr-diff.patch",
    "github-pr-checks.json",
    "github-review-audit.jsonl",
    "run-manifest.json",
)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GitHubWriteError(f"cannot read {path.name}: {exc}") from exc
    if not isinstance(payload, dict):
        raise GitHubWriteError(f"{path.name} must contain a JSON object")
    return payload


def _safe_run_id(value: Any) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value or "run")).strip("-")
    return (text or "run")[:32]


def _branch_for(pr: Mapping[str, Any], run_id: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9._/-]+", "-", str(pr.get("head") or "chronosfix/evidence"))
    stem = stem.strip("/") or "chronosfix/evidence"
    protected = {"main", "master", "production", "release"}
    if stem in protected or stem.startswith(tuple(f"{item}/" for item in protected)):
        raise GitHubWriteError("refusing to use a protected branch name")
    return f"{stem}-external-{_safe_run_id(run_id)}"


def build_write_plan(
    output_dir: Path,
    *,
    repository: str = REPO,
    base_branch: str = "main",
    token_env: str = "GITHUB_TOKEN",
) -> dict[str, Any]:
    """Validate local evidence and return a write plan without network access."""

    policy = GitHubWritePolicy(repository, base_branch, token_env)
    policy.validate()
    output_dir = Path(output_dir)
    missing = [name for name in _EVIDENCE_FILES if not (output_dir / name).is_file()]
    if missing:
        raise GitHubWriteError(f"missing evidence artifacts: {', '.join(missing)}")
    pr = _read_json(output_dir / "github-pr.json")
    checks = _read_json(output_dir / "github-pr-checks.json")
    readiness = pr.get("readiness")
    if not isinstance(readiness, Mapping) or readiness.get("status") != "ready":
        raise GitHubWriteError("RiskGate/readiness is not ready; external write remains blocked")
    if checks.get("status") != "completed":
        raise GitHubWriteError("required local checks are not completed; external write remains blocked")
    run_manifest = _read_json(output_dir / "run-manifest.json")
    environment = run_manifest.get("environment")
    if not isinstance(environment, Mapping):
        environment = {}
    run_id = str(run_manifest.get("run_id") or pr.get("run_id") or "run")
    branch = _branch_for(pr, run_id)
    return {
        "schema_version": "chronosfix.github-write-plan/v1",
        "mode": "external-evidence-draft",
        "repository": repository,
        "base": base_branch,
        "branch": branch,
        "run_id": run_id,
        "source_commit_sha": environment.get("git_commit"),
        "files": list(_EVIDENCE_FILES),
        "pull_request_title": str(pr.get("title") or "ChronosFix evidence Draft PR"),
        "merge_policy": {"draft_only": True, "no_merge": True, "no_main_write": True},
        "token_env": token_env,
    }


class GitHubWriter:
    """Minimal Git Data + Pulls API client with injectable transport for tests."""

    def __init__(
        self,
        token: str,
        *,
        policy: GitHubWritePolicy | None = None,
        api_root: str = "https://api.github.com",
        opener: Callable[..., Any] = urlopen,
    ) -> None:
        if not token or token.strip() != token:
            raise GitHubWriteError("GitHub token is missing or contains surrounding whitespace")
        self.token = token
        self.policy = policy or GitHubWritePolicy()
        self.policy.validate()
        self.api_root = api_root.rstrip("/")
        self.opener = opener
        self.request_ids: list[str] = []

    def _request(self, method: str, path: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any] | list[Any]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
        request = Request(
            f"{self.api_root}{path}",
            data=body,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
                "User-Agent": "ChronosFix/0.1 guarded-evidence-writer",
            },
        )
        try:
            response = self.opener(request, timeout=self.policy.timeout_seconds)
            raw = response.read()
            request_id = getattr(response, "headers", {}).get("X-GitHub-Request-Id")
            if request_id:
                self.request_ids.append(str(request_id))
            payload_out = json.loads(raw.decode("utf-8")) if raw else {}
            if isinstance(payload_out, (dict, list)):
                return payload_out
            raise GitHubWriteError(f"GitHub returned a non-object response for {method} {path}")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            request_id = exc.headers.get("X-GitHub-Request-Id") if exc.headers else None
            if request_id:
                self.request_ids.append(str(request_id))
            raise GitHubWriteError(f"GitHub API {exc.code} for {method} {path}: {detail}") from exc
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise GitHubWriteError(f"GitHub API request failed for {method} {path}: {exc}") from exc

    @staticmethod
    def _owner(repository: str) -> str:
        return repository.split("/", 1)[0]

    def write_evidence_draft(self, output_dir: Path, plan: Mapping[str, Any]) -> dict[str, Any]:
        repository = str(plan["repository"])
        base = str(plan["base"])
        branch = str(plan["branch"])
        encoded_repo = quote(repository, safe="/")
        existing = self._request(
            "GET",
            f"/repos/{encoded_repo}/pulls?state=open&head={quote(self._owner(repository) + ':' + branch)}&base={quote(base)}",
        )
        if isinstance(existing, list) and existing:
            return self._result(plan, existing[0], commit_sha=None, reused=True)

        ref = self._request("GET", f"/repos/{encoded_repo}/git/ref/heads/{quote(base, safe='')}")
        try:
            base_sha = str(ref["object"]["sha"])
        except (KeyError, TypeError) as exc:
            raise GitHubWriteError("GitHub base ref response did not include a commit SHA") from exc
        commit = self._request("GET", f"/repos/{encoded_repo}/git/commits/{quote(base_sha, safe='')}")
        try:
            base_tree = str(commit["tree"]["sha"])
        except (KeyError, TypeError) as exc:
            raise GitHubWriteError("GitHub base commit response did not include a tree SHA") from exc

        output_dir = Path(output_dir)
        blobs: list[dict[str, Any]] = []
        for name in plan["files"]:
            blob = self._request(
                "POST",
                f"/repos/{encoded_repo}/git/blobs",
                {"content": base64.b64encode((output_dir / str(name)).read_bytes()).decode("ascii"), "encoding": "base64"},
            )
            if not isinstance(blob, Mapping) or not blob.get("sha"):
                raise GitHubWriteError(f"GitHub did not return a blob SHA for {name}")
            blobs.append({"path": f".chronosfix/runs/{plan['run_id']}/{name}", "mode": "100644", "type": "blob", "sha": blob["sha"]})

        tree = self._request("POST", f"/repos/{encoded_repo}/git/trees", {"base_tree": base_tree, "tree": blobs})
        tree_sha = str(tree.get("sha")) if isinstance(tree, Mapping) else ""
        if not tree_sha:
            raise GitHubWriteError("GitHub did not return a tree SHA")
        commit_payload = self._request(
            "POST",
            f"/repos/{encoded_repo}/git/commits",
            {"message": f"docs: publish ChronosFix evidence for {plan['run_id']}", "tree": tree_sha, "parents": [base_sha]},
        )
        commit_sha = str(commit_payload.get("sha")) if isinstance(commit_payload, Mapping) else ""
        if not commit_sha:
            raise GitHubWriteError("GitHub did not return a commit SHA")
        self._request("POST", f"/repos/{encoded_repo}/git/refs", {"ref": f"refs/heads/{branch}", "sha": commit_sha})

        pr_payload = _read_json(output_dir / "github-pr.json")
        body = (output_dir / "github-pr.md").read_text(encoding="utf-8")
        body += f"\n\n---\nExternal evidence branch: `{branch}`\nCommit: `{commit_sha}`\n"
        online_pr = self._request(
            "POST",
            f"/repos/{encoded_repo}/pulls",
            {"title": str(pr_payload.get("title") or plan["pull_request_title"]), "head": branch, "base": base, "body": body, "draft": True},
        )
        if not isinstance(online_pr, Mapping):
            raise GitHubWriteError("GitHub did not return a pull request object")
        return self._result(plan, online_pr, commit_sha=commit_sha, reused=False)

    def _result(self, plan: Mapping[str, Any], online_pr: Mapping[str, Any], *, commit_sha: str | None, reused: bool) -> dict[str, Any]:
        return {
            "schema_version": "chronosfix.github-write/v1",
            "mode": "external-evidence-draft",
            "repository": plan["repository"],
            "base": plan["base"],
            "branch": plan["branch"],
            "run_id": plan["run_id"],
            "source_commit_sha": plan.get("source_commit_sha"),
            "published_commit_sha": commit_sha,
            "pull_request_number": online_pr.get("number"),
            "pull_request_url": online_pr.get("html_url"),
            "pull_request_state": online_pr.get("state"),
            "draft": online_pr.get("draft") is True,
            "reused_existing_pr": reused,
            "request_ids": list(self.request_ids),
            "files": list(plan["files"]),
            "merge_policy": dict(plan["merge_policy"]),
            "auth": {"token_env": plan["token_env"], "secret_recorded": False},
        }


def write_external_evidence_draft(
    output_dir: Path,
    *,
    repository: str = REPO,
    base_branch: str = "main",
    token_env: str = "GITHUB_TOKEN",
    api_root: str = "https://api.github.com",
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    """Publish the validated local evidence as a guarded Draft PR."""

    plan = build_write_plan(output_dir, repository=repository, base_branch=base_branch, token_env=token_env)
    token = os.environ.get(token_env)
    if not token:
        raise GitHubWriteError(f"{token_env} is not set; no GitHub write was attempted")
    result = GitHubWriter(token, policy=GitHubWritePolicy(repository, base_branch, token_env), api_root=api_root, opener=opener).write_evidence_draft(output_dir, plan)
    result_path = Path(output_dir) / "github-write-result.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest_path = Path(output_dir) / "run-manifest.json"
    manifest = _read_json(manifest_path)
    manifest["github_external_write"] = result
    artifacts = manifest.setdefault("artifacts", {})
    if isinstance(artifacts, dict):
        artifacts["github-write-result.json"] = {
            "sha256": sha256_file(result_path),
            "bytes": result_path.stat().st_size,
        }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Publish ChronosFix evidence as a guarded GitHub Draft PR")
    parser.add_argument("--output", type=Path, required=True, help="Completed ChronosFix output directory")
    parser.add_argument("--write-github", action="store_true", help="Confirm the external write; omitted means plan-only")
    parser.add_argument("--github-token-env", default="GITHUB_TOKEN")
    parser.add_argument("--github-repo", default=REPO)
    args = parser.parse_args(argv)
    if not args.write_github:
        print(json.dumps(build_write_plan(args.output, repository=args.github_repo, token_env=args.github_token_env), ensure_ascii=False, indent=2))
        return 0
    try:
        print(json.dumps(write_external_evidence_draft(args.output, repository=args.github_repo, token_env=args.github_token_env), ensure_ascii=False, indent=2))
    except GitHubWriteError as exc:
        raise SystemExit(f"GitHub write blocked: {exc}") from exc
    return 0
