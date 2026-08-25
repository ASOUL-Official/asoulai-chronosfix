from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import shutil
import subprocess
from time import perf_counter
from typing import Any
from uuid import uuid4


OFFICIAL_SLS_SKILL = {
    "name": "alibabacloud-sls-query",
    "portal": "https://skills.aliyun.com/skills/alibabacloud-sls-query",
    "source": "https://github.com/aliyun/alibabacloud-aiops-skills",
    "source_commit": "4dc1013ec2564f85fd07e5b5945b2d34ceca7eff",
    "source_path": "skills/storage/sls/alibabacloud-sls-query",
    "permission_boundary": "SLS GetIndex + GetLogsV2 read-only",
}


@dataclass(frozen=True)
class SlsQueryRequest:
    project: str
    logstore: str
    from_epoch: int
    to_epoch: int
    query: str
    profile: str | None = None


class SlsSkillValidationError(ValueError):
    pass


def _validate(request: SlsQueryRequest) -> None:
    for field_name in ("project", "logstore", "query"):
        value = getattr(request, field_name)
        if not isinstance(value, str) or not value.strip():
            raise SlsSkillValidationError(f"{field_name} must be a non-empty string")
    if request.from_epoch < 0 or request.to_epoch <= request.from_epoch:
        raise SlsSkillValidationError("to_epoch must be greater than from_epoch")
    if request.to_epoch - request.from_epoch > 24 * 60 * 60:
        raise SlsSkillValidationError("read-only demo queries are limited to a 24-hour window")


class AlibabaCloudSlsQueryAdapter:
    """Least-privilege adapter for the official alibabacloud-sls-query Skill.

    The default mode only builds a replayable command plan.  Cloud execution is
    opt-in and relies on an existing Aliyun CLI credential profile; credentials
    are never accepted as function arguments or written to evidence files.
    """

    def __init__(self, *, session_id: str | None = None, aliyun_binary: str = "aliyun") -> None:
        self.session_id = session_id or uuid4().hex
        if len(self.session_id) != 32 or any(ch not in "0123456789abcdef" for ch in self.session_id):
            raise ValueError("session_id must be 32 lowercase hexadecimal characters")
        self.aliyun_binary = aliyun_binary

    @property
    def user_agent(self) -> str:
        return f"AlibabaCloud-Agent-Skills/alibabacloud-sls-query/{self.session_id}"

    def plan(self, request: SlsQueryRequest) -> dict[str, Any]:
        _validate(request)
        common = [
            "--project",
            request.project,
            "--logstore",
            request.logstore,
            "--user-agent",
            self.user_agent,
        ]
        if request.profile:
            common.extend(["--profile", request.profile])
        commands = [
            [self.aliyun_binary, "sls", "get-index", *common],
            [
                self.aliyun_binary,
                "sls",
                "get-logs-v2",
                *common,
                "--from",
                str(request.from_epoch),
                "--to",
                str(request.to_epoch),
                "--query",
                request.query,
            ],
        ]
        return {
            "skill": OFFICIAL_SLS_SKILL,
            "request": asdict(request),
            "commands": commands,
            "execution_mode": "dry-run",
            "credential_handling": "existing aliyun CLI profile only; secrets never enter the Agent context",
            "required_ram_actions": ["log:GetIndex", "log:GetLogStoreLogs"],
            "fallback": "If SLS or credentials are unavailable, retain local synthetic evidence and label it simulated.",
        }

    def execute(self, request: SlsQueryRequest, *, audit_path: Path | None = None) -> dict[str, Any]:
        plan = self.plan(request)
        binary = shutil.which(self.aliyun_binary)
        if binary is None:
            raise RuntimeError("Aliyun CLI is not installed or is not on PATH")

        results: list[dict[str, Any]] = []
        for command in plan["commands"]:
            started = perf_counter()
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
            )
            results.append(
                {
                    "operation": command[2],
                    "exit_code": completed.returncode,
                    "duration_ms": round((perf_counter() - started) * 1000, 3),
                    "stdout": completed.stdout[-4000:],
                    "stderr": completed.stderr[-2000:],
                }
            )
            if completed.returncode != 0:
                break

        evidence = {
            **plan,
            "execution_mode": "cloud-read-only",
            "executed": True,
            "success": len(results) == len(plan["commands"])
            and all(item["exit_code"] == 0 for item in results),
            "results": results,
        }
        if audit_path is not None:
            audit_path.parent.mkdir(parents=True, exist_ok=True)
            audit_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        return evidence
