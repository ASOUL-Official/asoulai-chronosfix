"""Strictly parse repository JSON and JSONL artifacts without third-party packages."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Iterable


DEFAULT_EXCLUDED_DIRECTORIES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "output",
    "tmp",
}


class StrictJsonError(ValueError):
    """Raised when JSON uses duplicate keys or non-standard numeric constants."""


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise StrictJsonError(f"duplicate object key {key!r}")
        value[key] = item
    return value


def _reject_nonstandard_constant(value: str) -> None:
    raise StrictJsonError(f"non-standard numeric constant {value!r}")


def parse_strict_json(text: str) -> object:
    return json.loads(
        text,
        object_pairs_hook=_reject_duplicate_keys,
        parse_constant=_reject_nonstandard_constant,
    )


def discover_artifacts(root: Path, excluded: set[str] | None = None) -> list[Path]:
    excluded_names = DEFAULT_EXCLUDED_DIRECTORIES if excluded is None else excluded
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in {".json", ".jsonl"}
        and not any(part in excluded_names for part in path.relative_to(root).parts[:-1])
    )


def validate_artifact(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        return [f"{path}: cannot read UTF-8 text: {exc}"]

    if path.suffix.lower() == ".json":
        try:
            parse_strict_json(text)
        except (json.JSONDecodeError, StrictJsonError) as exc:
            errors.append(f"{path}: invalid JSON: {exc}")
        return errors

    nonempty_lines = 0
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        nonempty_lines += 1
        try:
            parse_strict_json(line)
        except (json.JSONDecodeError, StrictJsonError) as exc:
            errors.append(f"{path}:{line_number}: invalid JSONL record: {exc}")
    if nonempty_lines == 0:
        errors.append(f"{path}: JSONL file contains no records")
    return errors


def validate_repository(root: Path) -> tuple[list[Path], list[str]]:
    artifacts = discover_artifacts(root)
    errors = [error for path in artifacts for error in validate_artifact(path)]
    return artifacts, errors


def _write_errors(errors: Iterable[str]) -> None:
    for error in errors:
        print(error, file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Strictly validate repository .json and .jsonl artifacts."
    )
    parser.add_argument("root", nargs="?", type=Path, default=Path("."))
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if not root.is_dir():
        parser.error(f"root is not a directory: {root}")

    artifacts, errors = validate_repository(root)
    if not artifacts:
        print(f"No JSON or JSONL artifacts found below {root}", file=sys.stderr)
        return 1
    if errors:
        _write_errors(errors)
        print(
            f"Validation failed: {len(errors)} error(s) across {len(artifacts)} artifact(s).",
            file=sys.stderr,
        )
        return 1
    print(f"Validated {len(artifacts)} JSON/JSONL artifacts below {root}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
