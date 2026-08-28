from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "ci_sandbox" / "fixture"
PATCH = ROOT / "ci_sandbox" / "checkout_pool_fix.patch"
PATCH_PATH_RE = re.compile(r"^(?:---|\+\+\+) [ab]/(.+)$", re.MULTILINE)
BANNED_PATCH_TOKENS = (
    "subprocess",
    "os.system",
    "socket",
    "urllib",
    "requests",
    "ctypes",
    "eval(",
    "exec(",
)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def run(command: list[str], cwd: Path, *, expected: tuple[int, ...], timeout: int = 20) -> dict[str, Any]:
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
        "WINDIR": os.environ.get("WINDIR", ""),
        "PYTHONIOENCODING": "utf-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "NO_PROXY": "*",
        "HTTP_PROXY": "http://127.0.0.1:9",
        "HTTPS_PROXY": "http://127.0.0.1:9",
    }
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    return {
        "command": command,
        "exit_code": completed.returncode,
        "expected_exit_codes": list(expected),
        "passed": completed.returncode in expected,
        "duration_ms": round((time.perf_counter() - started) * 1000, 3),
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
    }


def validate_patch(patch_bytes: bytes) -> dict[str, Any]:
    if len(patch_bytes) > 32 * 1024:
        raise ValueError("patch exceeds 32 KiB sandbox limit")
    text = patch_bytes.decode("utf-8")
    paths = sorted(set(PATCH_PATH_RE.findall(text)))
    if not paths:
        raise ValueError("patch has no file paths")
    for relative in paths:
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"unsafe patch path: {relative}")
        if path.as_posix() not in {"checkout_service.py"}:
            raise ValueError(f"path is outside the patch allowlist: {relative}")
    lowered = text.lower()
    found = [token for token in BANNED_PATCH_TOKENS if token.lower() in lowered]
    if found:
        raise ValueError(f"patch contains denied capabilities: {found}")
    return {"paths": paths, "bytes": len(patch_bytes), "sha256": sha256_bytes(patch_bytes)}


def build(output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    patch_bytes = PATCH.read_bytes()
    patch_policy = validate_patch(patch_bytes)
    traversal_blocked = False
    try:
        validate_patch(b"--- a/../escape.py\n+++ b/../escape.py\n@@ -0,0 +1 @@\n+owned=True\n")
    except ValueError:
        traversal_blocked = True

    with tempfile.TemporaryDirectory(prefix="chronosfix-patch-sandbox-") as temp_dir:
        checkout = Path(temp_dir) / "checkout"
        shutil.copytree(FIXTURE, checkout)
        for source in checkout.glob("*.py"):
            source.write_bytes(source.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n"))
        checks = [
            run(["git", "init", "-q"], checkout, expected=(0,)),
            run(["git", "config", "core.autocrlf", "false"], checkout, expected=(0,)),
            run(["git", "config", "user.email", "sandbox@chronosfix.local"], checkout, expected=(0,)),
            run(["git", "config", "user.name", "ChronosFix Sandbox"], checkout, expected=(0,)),
            run(["git", "add", "."], checkout, expected=(0,)),
            run(["git", "commit", "-qm", "sandbox base"], checkout, expected=(0,)),
        ]
        base_commit_check = run(["git", "rev-parse", "HEAD"], checkout, expected=(0,))
        checks.append(base_commit_check)
        base_commit = base_commit_check["stdout"].strip()
        before = run(
            [sys.executable, "-I", "-B", "-m", "unittest", "discover", "-s", ".", "-p", "test_*.py", "-v"],
            checkout,
            expected=(1,),
        )
        checks.append(before)
        patch_copy = checkout / "candidate.patch"
        patch_copy.write_bytes(patch_bytes)
        checks.append(run(["git", "apply", "--check", "candidate.patch"], checkout, expected=(0,)))
        checks.append(run(["git", "apply", "candidate.patch"], checkout, expected=(0,)))
        diff = run(["git", "diff", "--", "checkout_service.py"], checkout, expected=(0,))
        checks.append(diff)
        after = run(
            [sys.executable, "-I", "-B", "-m", "unittest", "discover", "-s", ".", "-p", "test_*.py", "-v"],
            checkout,
            expected=(0,),
        )
        checks.append(after)
        checks.append(run(["git", "apply", "-R", "candidate.patch"], checkout, expected=(0,)))
        patch_copy.unlink()
        rollback = run(["git", "status", "--porcelain"], checkout, expected=(0,))
        checks.append(rollback)

    report = {
        "schema": "chronosfix.patch-sandbox/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "passed": all(item["passed"] for item in checks) and not rollback["stdout"].strip() and traversal_blocked,
        "base_commit": base_commit,
        "patch": patch_policy,
        "isolation_policy": {
            "temporary_git_checkout": True,
            "shell_interpolation": False,
            "python_isolated_mode": True,
            "credentials_forwarded": False,
            "proxy_fail_closed": True,
            "process_timeout_seconds": 20,
            "path_allowlist": ["checkout_service.py"],
            "os_network_namespace_enforced": False,
            "boundary_note": "Process/filesystem isolation is executed locally; CI may add a container network namespace.",
        },
        "security_negative_test": {"path_traversal_patch_blocked": traversal_blocked},
        "before_tests": before,
        "after_tests": after,
        "applied_diff_sha256": sha256_bytes(diff["stdout"].encode("utf-8")),
        "rollback_clean": not rollback["stdout"].strip(),
        "checks": checks,
    }
    (output / "patch-sandbox-run.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply a real code patch inside the ChronosFix CI sandbox")
    parser.add_argument("--output", type=Path, default=ROOT / "output" / "patch-sandbox")
    args = parser.parse_args(argv)
    report = build(args.output.resolve())
    print(json.dumps({"passed": report["passed"], "output": str(args.output.resolve())}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
