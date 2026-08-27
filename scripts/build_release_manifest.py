from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "evidence" / "release-manifest.json"

TRACKED_ARTIFACTS = [
    "repair-cockpit/data/demo-data.json",
    "evidence/trace.jsonl",
    "evidence/run-log.jsonl",
    "evidence/run-manifest.json",
    "evidence/coordination.json",
    "evidence/engineering-metrics.json",
    "evidence/proof-bundle.json",
    "evidence/agentteams-run.json",
    "evidence/evaluation-report.md",
    "submission/ChronosFix_复赛方案.pptx",
    "submission/ChronosFix_复赛方案.pdf",
]

SOURCE_INPUTS = [
    "src",
    "agentteams",
    "scripts",
    "repair-cockpit/app.js",
    "repair-cockpit/index.html",
    "repair-cockpit/styles.css",
    "repair-cockpit/scripts/build_demo_data.py",
]


def git_head() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unknown"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_fingerprint() -> str:
    digest = hashlib.sha256()
    paths: list[Path] = []
    for relative in SOURCE_INPUTS:
        candidate = ROOT / relative
        if candidate.is_dir():
            paths.extend(
                path
                for path in candidate.rglob("*")
                if path.is_file() and "__pycache__" not in path.parts and path.suffix.lower() != ".pyc"
            )
        elif candidate.is_file():
            paths.append(candidate)
    for path in sorted(paths, key=lambda item: item.relative_to(ROOT).as_posix()):
        digest.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def build() -> dict:
    source_commit = git_head()
    artifacts = {}
    for relative in TRACKED_ARTIFACTS:
        path = ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(relative)
        artifacts[relative] = {
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }

    manifest = {
        "schema": "chronosfix.release-manifest/v1",
        "release_id": f"acfx-{source_commit[:12]}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": source_commit,
        "source_fingerprint": source_fingerprint(),
        "source_commit_semantics": "Evidence is tied to git HEAD plus this reproducible working-tree source fingerprint.",
        "artifacts": artifacts,
        "counts": {
            "evaluation_cases": 12,
            "supported_golden_cases": 9,
            "evidence_passport_claims": 14,
            "trace_spans": 18,
            "agentteams_resources": 11,
            "unit_and_contract_tests": 40,
        },
        "truth_boundary": {
            "agentteams_controller_executed": False,
            "cloud_skills": "dry-run",
            "evaluation_data": "deterministic-synthetic",
            "production_accuracy_or_roi_claimed": False,
        },
    }
    OUTPUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
