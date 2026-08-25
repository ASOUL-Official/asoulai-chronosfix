from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

try:
    import yaml
except ImportError as exc:  # pragma: no cover - environment-specific helper
    raise SystemExit("PyYAML is required for AgentTeams manifest validation") from exc


ALLOWED_KINDS = {"Manager", "Worker", "Team", "Human"}
API_VERSION = "agentteams.io/v1beta1"


def validate(path: Path) -> dict:
    documents = [item for item in yaml.safe_load_all(path.read_text(encoding="utf-8")) if item]
    errors: list[str] = []
    names_by_kind: dict[str, set[str]] = {kind: set() for kind in ALLOWED_KINDS}

    for index, item in enumerate(documents, start=1):
        label = f"document[{index}]"
        api_version = item.get("apiVersion")
        kind = item.get("kind")
        name = item.get("metadata", {}).get("name")
        spec = item.get("spec", {})
        if api_version != API_VERSION:
            errors.append(f"{label}: apiVersion must be {API_VERSION}")
        if kind not in ALLOWED_KINDS:
            errors.append(f"{label}: unsupported kind {kind!r}")
            continue
        if not name:
            errors.append(f"{label}: metadata.name is required")
            continue
        if name in names_by_kind[kind]:
            errors.append(f"{label}: duplicate {kind} name {name}")
        names_by_kind[kind].add(name)
        if kind in {"Manager", "Worker"} and not spec.get("model"):
            errors.append(f"{kind}/{name}: spec.model is required")

    workers = names_by_kind["Worker"]
    teams = names_by_kind["Team"]
    for item in documents:
        kind = item.get("kind")
        name = item.get("metadata", {}).get("name")
        spec = item.get("spec", {})
        if kind == "Team":
            members = spec.get("workerMembers") or []
            leaders = [member for member in members if member.get("role") == "team_leader"]
            if len(leaders) != 1:
                errors.append(f"Team/{name}: workerMembers must contain exactly one team_leader")
            referenced = {member.get("name") for member in members}
            missing = sorted(value for value in referenced - workers if value)
            if missing:
                errors.append(f"Team/{name}: missing Worker resources: {', '.join(missing)}")
        elif kind == "Human":
            if not spec.get("displayName"):
                errors.append(f"Human/{name}: spec.displayName is required")
            if spec.get("permissionLevel") not in {1, 2, 3}:
                errors.append(f"Human/{name}: permissionLevel must be 1, 2 or 3")
            missing = sorted(set(spec.get("accessibleTeams") or []) - teams)
            if missing:
                errors.append(f"Human/{name}: missing Team resources: {', '.join(missing)}")

    summary = {
        "schema": "chronosfix.agentteams-manifest-validation/v1",
        "manifest": path.as_posix(),
        "valid": not errors,
        "document_count": len(documents),
        "counts": {kind: len(names_by_kind[kind]) for kind in sorted(ALLOWED_KINDS)},
        "team_leaders": [
            member["name"]
            for item in documents
            if item.get("kind") == "Team"
            for member in item.get("spec", {}).get("workerMembers", [])
            if member.get("role") == "team_leader"
        ],
        "errors": errors,
    }
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate ChronosFix AgentTeams v1beta1 resources.")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = validate(args.manifest)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
