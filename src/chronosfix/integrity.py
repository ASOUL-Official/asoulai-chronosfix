from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any, Iterable


POLICY_VERSION = "chronosfix-riskgate/v1"


def canonical_json(payload: Any) -> str:
    if is_dataclass(payload):
        payload = asdict(payload)
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def git_commit(repo_root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = result.stdout.strip()
    return value or None


def build_approval_input_digest(
    *,
    incident_id: str,
    scenario_hash: str,
    patch_id: str | None,
    patch_hash: str | None,
    gate_policy: str = POLICY_VERSION,
) -> str:
    return sha256_json(
        {
            "incident_id": incident_id,
            "scenario_sha256": scenario_hash,
            "patch_id": patch_id,
            "patch_sha256": patch_hash,
            "gate_policy": gate_policy,
        }
    )


def write_run_manifest(
    output_dir: Path,
    *,
    repo_root: Path,
    scenario_path: Path,
    state: Any,
    metrics: dict[str, Any],
    trace_records: list[dict[str, Any]],
    artifact_names: Iterable[str],
) -> dict[str, Any]:
    artifacts: dict[str, dict[str, Any]] = {}
    for name in artifact_names:
        path = output_dir / name
        if path.is_file():
            artifacts[name] = {
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }

    manifest = {
        "schema_version": "chronosfix.run-manifest/v1",
        "generated_at": utc_now(),
        "run_id": getattr(state, "run_id", ""),
        "trace_id": metrics.get("trace_id"),
        "incident_id": state.incident_id,
        "scenario": {
            "path": str(scenario_path.as_posix()),
            "sha256": sha256_file(scenario_path),
        },
        "selected_patch": {
            "id": state.selected_patch.candidate_id if state.selected_patch else None,
            "changes_sha256": sha256_json(state.selected_patch.changes)
            if state.selected_patch
            else None,
            "rollback_changes_sha256": sha256_json(state.selected_patch.rollback_changes)
            if state.selected_patch
            else None,
        },
        "decision": {
            "quality_gate": getattr(state, "quality_gate", "not-evaluated"),
            "release_decision": state.approval,
            "gate_result": getattr(state, "gate_result", {}),
            "approval_record": getattr(state, "approval_record", {}),
        },
        "measurements": {
            "elapsed_ms": metrics.get("elapsed_ms"),
            "elapsed_ms_kind": "measured",
            "evidence_coverage": metrics.get("evidence_coverage"),
            "evidence_coverage_kind": "derived",
            "pipeline_step_completion_rate": metrics.get("pipeline_step_completion_rate"),
            "pipeline_step_completion_rate_kind": "derived",
        },
        "trace": {
            "span_count": len(trace_records),
            "schema": "chronosfix.trace/v1",
        },
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "git_commit": git_commit(repo_root),
        },
        "artifacts": artifacts,
    }
    path = output_dir / "run-manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest
