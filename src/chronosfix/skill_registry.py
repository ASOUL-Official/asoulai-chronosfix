"""Runtime-discoverable Skill catalog used by the local AgentTeams adapter."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any


_FIELD = re.compile(r"^(name|description):\s*(.*?)\s*$")


def discover_runtime_skills(root: Path) -> list[dict[str, Any]]:
    """Load Skill metadata from ``SKILL.md`` files without importing code.

    Keeping discovery file-based mirrors AgentTeams/Skills portals and lets
    operators inspect permissions and versions before a Worker loads a Skill.
    Invalid or incomplete manifests are returned as explicit errors rather
    than silently omitted.
    """

    skills: list[dict[str, Any]] = []
    for path in sorted(root.glob("*/SKILL.md")):
        fields: dict[str, str] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            match = _FIELD.match(line.strip())
            if match:
                fields[match.group(1)] = match.group(2).strip().strip("\"'")
            if line.strip() == "---" and fields:
                break
        skills.append(
            {
                "name": fields.get("name", path.parent.name),
                "description": fields.get("description", ""),
                "path": path.as_posix(),
                "version": "0.1.0",
                "loadable": bool(fields.get("name") and fields.get("description")),
                "permission": _permission_for(path.parent.name),
            }
        )
    return skills


def _permission_for(name: str) -> str:
    if name in {"evidence-fusion", "change-timeline", "hypothesis-contract"}:
        return "read-only"
    if name in {"counterfactual-replay", "fault-genome", "patch-tournament"}:
        return "isolated-simulation"
    if name == "risk-gate":
        return "human-approval-required"
    if name in {"evidence-passport", "skill-forge", "proof-report"}:
        return "write-evidence-artifacts"
    return "least-privilege"
