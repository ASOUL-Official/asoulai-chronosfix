from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    import jsonschema
except ImportError as exc:  # pragma: no cover - optional validation environment
    raise SystemExit('jsonschema is required; install with: pip install -e ".[validation]"') from exc


ROOT = Path(__file__).resolve().parents[1]


def validate_repository(root: Path = ROOT) -> dict[str, Any]:
    schema_path = root / "schemas" / "scenario.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema)

    scenarios = sorted((root / "scenarios").rglob("scenario.json"))
    errors: list[dict[str, Any]] = []
    for scenario_path in scenarios:
        payload = json.loads(scenario_path.read_text(encoding="utf-8"))
        for issue in sorted(validator.iter_errors(payload), key=lambda item: list(item.absolute_path)):
            errors.append(
                {
                    "scenario": scenario_path.relative_to(root).as_posix(),
                    "path": "$" + "".join(f"[{item}]" for item in issue.absolute_path),
                    "message": issue.message,
                }
            )

    return {
        "schema": "chronosfix.public-scenario-schema-validation/v1",
        "schema_path": schema_path.relative_to(root).as_posix(),
        "draft": "2020-12",
        "scenario_count": len(scenarios),
        "valid": not errors,
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate every ChronosFix scenario against the public JSON Schema.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    report = validate_repository(args.root.resolve())
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
