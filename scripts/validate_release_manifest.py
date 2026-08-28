from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
HEX40 = re.compile(r"^[0-9a-f]{40}$")
SOURCE_INPUTS = [
    "src",
    "agentteams",
    "scripts",
    "repair-cockpit/app.js",
    "repair-cockpit/index.html",
    "repair-cockpit/styles.css",
    "repair-cockpit/scripts/build_demo_data.py",
    "pyproject.toml",
    "ci_sandbox",
    "public-incidents",
    "baseline",
    "deploy",
]


def canonical_file_bytes(path: Path) -> bytes:
    """Normalize UTF-8 text line endings for cross-platform identity."""

    raw = path.read_bytes()
    if b"\0" in raw:
        return raw
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def sha256(path: Path) -> str:
    return hashlib.sha256(canonical_file_bytes(path)).hexdigest()


def source_fingerprint() -> str:
    digest = hashlib.sha256()
    paths: list[Path] = []
    for relative in SOURCE_INPUTS:
        candidate = ROOT / relative
        if candidate.is_dir():
            paths.extend(
                path
                for path in candidate.rglob("*")
                if path.is_file()
                and "__pycache__" not in path.parts
                and not any(part.endswith(".egg-info") for part in path.parts)
                and path.suffix.lower() != ".pyc"
            )
        elif candidate.is_file():
            paths.append(candidate)
    for item in sorted(paths, key=lambda path: path.relative_to(ROOT).as_posix()):
        digest.update(item.relative_to(ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(canonical_file_bytes(item))
        digest.update(b"\0")
    return digest.hexdigest()


def nested(data: dict, *keys: str):
    value = data
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def validate(path: Path) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    source_commit = manifest.get("source_commit")
    if not isinstance(source_commit, str) or not HEX40.fullmatch(source_commit):
        errors.append("source_commit must be a 40-character git commit")
    if manifest.get("source_fingerprint") != source_fingerprint():
        errors.append("source_fingerprint differs from current source inputs")

    for relative, expected in (manifest.get("artifacts") or {}).items():
        target = ROOT / relative
        if not target.is_file():
            errors.append(f"missing artifact: {relative}")
            continue
        actual = sha256(target)
        if actual != expected.get("sha256"):
            errors.append(f"sha256 mismatch: {relative}")
        if len(canonical_file_bytes(target)) != expected.get("bytes"):
            errors.append(f"byte-size mismatch: {relative}")

    demo = json.loads((ROOT / "repair-cockpit/data/demo-data.json").read_text(encoding="utf-8"))
    if nested(demo, "revision", "base_commit") != source_commit:
        errors.append("demo-data revision.base_commit differs from source_commit")

    run_manifest = json.loads((ROOT / "evidence/run-manifest.json").read_text(encoding="utf-8"))
    if nested(run_manifest, "environment", "git_commit") != source_commit:
        errors.append("run-manifest environment.git_commit differs from source_commit")

    metrics = json.loads((ROOT / "evidence/engineering-metrics.json").read_text(encoding="utf-8"))
    if metrics.get("git_commit") != source_commit:
        errors.append("engineering-metrics git_commit differs from source_commit")

    summary = nested(demo, "evaluation", "summary") or {}
    expected_counts = manifest.get("counts") or {}
    if summary.get("total_cases") != expected_counts.get("evaluation_cases"):
        errors.append("evaluation case count differs from manifest")
    if summary.get("supported_diagnosis_correct") != expected_counts.get("supported_golden_cases"):
        errors.append("supported Golden count differs from manifest")
    if nested(metrics, "evidence_passport_claims") != expected_counts.get("evidence_passport_claims"):
        errors.append("evidence passport claim count differs from manifest")

    return {
        "schema": "chronosfix.release-manifest-validation/v1",
        "manifest": str(path),
        "source_commit": source_commit,
        "checked_artifacts": len(manifest.get("artifacts") or {}),
        "valid": not errors,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate ChronosFix release manifest and cross-artifact revisions.")
    parser.add_argument("path", nargs="?", type=Path, default=ROOT / "evidence/release-manifest.json")
    args = parser.parse_args()
    report = validate(args.path.resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
