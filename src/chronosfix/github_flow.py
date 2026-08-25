from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any

from .models import IncidentState


REPO = "ASOUL-Official/asoulai-chronosfix"
ISSUE_NUMBER = 42
PR_NUMBER = 43

_ARTIFACTS = [
    "github-issue.md",
    "github-issue.json",
    "github-pr.md",
    "github-pr.json",
    "github-pr-diff.patch",
    "github-pr-checks.json",
    "github-review-audit.jsonl",
]
_SUCCESS_STATES = {"success", "successful", "passed", "pass", "completed"}
_FAILURE_STATES = {"failure", "failed", "error", "cancelled", "timed_out"}
_NON_HUMAN_APPROVERS = {"anonymous", "auto", "automation", "bot", "system", "unknown"}


def build_github_flow_summary(state: IncidentState) -> dict[str, Any]:
    """Return the stable, compact Issue/PR summary used in trace payloads.

    The numbers identify local draft artifacts; this module never claims that
    it has mutated GitHub.  Readiness comes only from the recorded RiskGate
    result.  Detailed check readiness is added by ``write_github_flow_artifacts``
    when the measured check records are available.
    """

    gate = _mapping(getattr(state, "gate_result", {}))
    release_ready = gate.get("release_ready") is True
    return {
        "repository": REPO,
        "mode": "local-draft",
        "issue": f"#{ISSUE_NUMBER}",
        "issue_title": _issue_title(state),
        "pull_request": f"#{PR_NUMBER}",
        "pr_state": "ready-for-review" if release_ready else "draft",
        "branch": _branch_name(state),
        "scenario": _scenario_path(state) or None,
        "selected_patch": (
            state.selected_patch.candidate_id if state.selected_patch else None
        ),
        "riskgate": getattr(state, "approval", "not-requested"),
        "quality_gate": gate.get(
            "quality_gate", getattr(state, "quality_gate", "not-evaluated")
        ),
        "release_ready": release_ready,
        "artifacts": list(_ARTIFACTS),
    }


def write_github_flow_artifacts(
    state: IncidentState, metrics: dict[str, Any], output_dir: Path
) -> dict[str, Any]:
    """Write an evidence-backed local GitHub Issue -> PR draft chain.

    No check result, source change, approval identity or commit SHA is invented.
    Missing evidence is represented as ``pending`` and keeps the PR in draft.
    The generated patch is a scenario-specific declarative change contract
    containing the exact selected ``changes`` and ``rollback_changes``.
    """

    output_dir.mkdir(parents=True, exist_ok=True)
    checks = _checks_payload(state, metrics)
    issue = _issue_payload(state, metrics)
    pr = _pr_payload(state, metrics, checks)
    audit = _review_audit_payload(state, metrics, checks, pr)
    diff = _patch_diff(state, metrics, checks)

    _write_json(output_dir / "github-issue.json", issue)
    (output_dir / "github-issue.md").write_text(
        _issue_markdown(issue), encoding="utf-8"
    )
    _write_json(output_dir / "github-pr.json", pr)
    (output_dir / "github-pr.md").write_text(_pr_markdown(pr), encoding="utf-8")
    (output_dir / "github-pr-diff.patch").write_text(diff, encoding="utf-8")
    _write_json(output_dir / "github-pr-checks.json", checks)
    (output_dir / "github-review-audit.jsonl").write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in audit),
        encoding="utf-8",
    )

    summary = build_github_flow_summary(state)
    summary.update(
        {
            "pr_state": pr["state"],
            "release_ready": pr["readiness"]["status"] == "ready",
            "readiness": pr["readiness"],
        }
    )
    return summary


def _mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _slug(value: Any, fallback: str) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or fallback


def _scenario_path(state: IncidentState) -> str:
    return str(getattr(state, "scenario_path", "") or "").replace("\\", "/")


def _scenario_slug(state: IncidentState) -> str:
    raw = _scenario_path(state)
    if not raw:
        return "unscoped"
    path = PurePosixPath(raw)
    candidate = path.parent.name if path.name.lower() == "scenario.json" else path.stem
    return _slug(candidate, "unscoped")


def _patch_slug(state: IncidentState) -> str:
    selected = state.selected_patch
    return _slug(selected.candidate_id if selected else None, "pending-patch")


def _branch_name(state: IncidentState) -> str:
    incident = _slug(getattr(state, "incident_id", ""), "pending-incident")
    return f"chronosfix/{incident}-{_scenario_slug(state)}-{_patch_slug(state)}"


def _incident_event(state: IncidentState) -> dict[str, Any]:
    for event in state.events:
        if getattr(event, "kind", "") == "incident":
            return asdict(event) if is_dataclass(event) else _mapping(event)
    return {}


def _incident_context(state: IncidentState) -> dict[str, Any]:
    event = _incident_event(state)
    details = _mapping(event.get("details"))
    severity = str(details.get("severity") or "unclassified")
    return {
        "severity": severity,
        "route": details.get("route"),
        "event_source": event.get("source"),
        "event_timestamp": event.get("timestamp"),
    }


def _issue_title(state: IncidentState) -> str:
    severity = _incident_context(state)["severity"]
    prefix = severity.upper() if severity != "unclassified" else "INCIDENT"
    title = str(getattr(state, "title", "") or "Untitled incident")
    return f"[{prefix}] {title}"


def _pr_title(state: IncidentState) -> str:
    selected = state.selected_patch
    scope = _scenario_slug(state)
    if selected:
        return f"fix({scope}): {selected.title}"
    return f"draft({scope}): evidence required before repair"


def _primary_cause(state: IncidentState) -> dict[str, Any] | None:
    for item in state.experiments:
        if item.classification == "primary-cause":
            return asdict(item) if is_dataclass(item) else _mapping(item)
    return None


def _selected_patch(state: IncidentState) -> dict[str, Any] | None:
    selected = state.selected_patch
    if selected is None:
        return None
    return asdict(selected) if is_dataclass(selected) else _mapping(selected)


def _normalise_validation_checks(metrics: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw_checks = metrics.get("validation_checks")
    if isinstance(raw_checks, Mapping):
        source: Sequence[Any] = [
            ({"name": name, **dict(value)} if isinstance(value, Mapping) else {"name": name, "status": value})
            for name, value in raw_checks.items()
        ]
    elif isinstance(raw_checks, Sequence) and not isinstance(raw_checks, (str, bytes)):
        source = raw_checks
    else:
        source = []

    records: list[dict[str, Any]] = []
    for index, raw in enumerate(source, start=1):
        item = _mapping(raw)
        name = str(item.get("name") or f"check-{index}")
        executed = item.get("executed") is True
        exit_code_present = "exit_code" in item
        status_text = str(item.get("conclusion") or item.get("status") or "").lower()
        has_execution_reference = any(
            item.get(key) not in (None, "")
            for key in ("evidence", "log_path", "run_id", "run_url")
        ) or exit_code_present

        if not executed or not has_execution_reference:
            conclusion = "pending"
        elif exit_code_present and item.get("exit_code") != 0:
            conclusion = "failure"
        elif status_text in _SUCCESS_STATES:
            conclusion = "success"
        elif status_text in _FAILURE_STATES:
            conclusion = "failure"
        else:
            conclusion = "pending"

        record = dict(item)
        record.update(
            {
                "name": name,
                "required": item.get("required", True) is True,
                "executed": executed,
                "conclusion": conclusion,
                "source": "metrics.validation_checks",
            }
        )
        records.append(record)
    return records


def _requires_human(state: IncidentState) -> bool | None:
    gate = _mapping(getattr(state, "gate_result", {}))
    if isinstance(gate.get("requires_human"), bool):
        return gate["requires_human"]
    selected = state.selected_patch
    if selected is None:
        return None
    return selected.risk >= 0.25


def _human_approval_ready(state: IncidentState) -> bool:
    approval = _mapping(getattr(state, "approval_record", {}))
    status = str(approval.get("status") or "").lower()
    approver = str(
        approval.get("approver")
        or approval.get("approved_by")
        or approval.get("actor")
        or ""
    ).strip()
    return (
        status == "approved"
        and bool(approver)
        and approver.lower() not in _NON_HUMAN_APPROVERS
        and approval.get("is_human", True) is True
    )


def _riskgate_check(state: IncidentState) -> dict[str, Any]:
    gate = _mapping(getattr(state, "gate_result", {}))
    if not gate:
        return {
            "name": "riskgate",
            "required": True,
            "executed": False,
            "conclusion": "pending",
            "summary": "RiskGate has not produced a decision.",
            "source": "state.gate_result",
        }

    quality_gate = str(gate.get("quality_gate") or "not-evaluated")
    decision = str(gate.get("decision") or "not-evaluated")
    if quality_gate == "failed" or decision == "blocked-quality-gate":
        conclusion = "failure"
    elif gate.get("release_ready") is True and decision == "approved":
        conclusion = "success"
    elif decision == "blocked-awaiting-human":
        conclusion = "action_required"
    else:
        conclusion = "pending"
    return {
        "name": "riskgate",
        "required": True,
        "executed": True,
        "conclusion": conclusion,
        "quality_gate": quality_gate,
        "decision": decision,
        "blockers": gate.get("blockers", []),
        "summary": f"RiskGate decision: {decision}; quality gate: {quality_gate}.",
        "source": "state.gate_result",
    }


def _approval_check(state: IncidentState) -> dict[str, Any]:
    required = _requires_human(state)
    approval = _mapping(getattr(state, "approval_record", {}))
    ready = _human_approval_ready(state)
    if required is None:
        conclusion = "pending"
        summary = "Human-approval requirement cannot be evaluated without a selected patch or gate result."
    elif not required:
        conclusion = "neutral"
        summary = "RiskGate does not require human approval for this patch."
    elif ready:
        conclusion = "success"
        summary = f"Named human approval recorded for {approval.get('approver') or approval.get('approved_by') or approval.get('actor')}."
    else:
        conclusion = "action_required"
        summary = "A named human approval is required but has not been recorded."
    return {
        "name": "human-approval",
        "required": required is not False,
        "executed": bool(approval),
        "conclusion": conclusion,
        "approver": approval.get("approver") or approval.get("approved_by") or approval.get("actor"),
        "approved_at": approval.get("timestamp") or approval.get("approved_at"),
        "reason": approval.get("reason"),
        "policy_version": approval.get("policy_version"),
        "input_digest": approval.get("input_digest"),
        "summary": summary,
        "source": "state.approval_record",
    }


def _checks_payload(state: IncidentState, metrics: Mapping[str, Any]) -> dict[str, Any]:
    measured = _normalise_validation_checks(metrics)
    checks = [*measured, _riskgate_check(state), _approval_check(state)]
    required = [item for item in checks if item.get("required", True)]
    if required and all(item.get("conclusion") == "success" for item in required):
        status = "completed"
    elif any(item.get("conclusion") == "failure" for item in required):
        status = "blocked"
    else:
        status = "pending"
    return {
        "repository": REPO,
        "mode": "local-draft",
        "pull_request": f"#{PR_NUMBER}",
        "commit_sha": metrics.get("patch_commit_sha"),
        "base_commit_sha": metrics.get("git_commit"),
        "run_id": metrics.get("run_id") or getattr(state, "run_id", "") or None,
        "status": status,
        "checks": checks,
    }


def _readiness(
    state: IncidentState, metrics: Mapping[str, Any], checks_payload: Mapping[str, Any]
) -> dict[str, Any]:
    missing: list[str] = []
    failed: list[str] = []
    selected = state.selected_patch
    gate = _mapping(getattr(state, "gate_result", {}))

    if not _scenario_path(state):
        missing.append("scenario_path")
    if selected is None:
        missing.append("selected_patch")
    else:
        if not selected.changes:
            missing.append("selected_patch.changes")
        if not selected.rollback_changes:
            missing.append("selected_patch.rollback_changes")

    validation = _normalise_validation_checks(metrics)
    required_validation = [item for item in validation if item.get("required", True)]
    if not required_validation:
        missing.append("metrics.validation_checks")
    else:
        for item in required_validation:
            conclusion = item.get("conclusion")
            if conclusion == "failure":
                failed.append(f"validation:{item['name']}")
            elif conclusion != "success":
                missing.append(f"validation:{item['name']}")

    if not gate:
        missing.append("gate_result")
    elif gate.get("release_ready") is not True:
        if gate.get("quality_gate") == "failed" or gate.get("decision") == "blocked-quality-gate":
            failed.append("riskgate")
        else:
            missing.append("riskgate-release-approval")

    if _requires_human(state) is not False and not _human_approval_ready(state):
        missing.append("named-human-approval")

    passport = getattr(state, "evidence_passport", None)
    if passport is None:
        missing.append("evidence_passport")
    elif getattr(passport, "missing_claims", []):
        failed.append("evidence-passport-missing-claims")

    required_checks = [
        item for item in checks_payload.get("checks", []) if item.get("required", True)
    ]
    if any(item.get("conclusion") == "failure" for item in required_checks):
        if "github-checks" not in failed:
            failed.append("github-checks")
    elif any(item.get("conclusion") not in {"success"} for item in required_checks):
        if "github-checks" not in missing:
            missing.append("github-checks")

    if failed:
        status = "blocked"
    elif missing:
        status = "pending"
    else:
        status = "ready"
    return {
        "status": status,
        "release_ready": status == "ready",
        "missing_evidence": sorted(set(missing)),
        "failed_evidence": sorted(set(failed)),
    }


def _issue_payload(state: IncidentState, metrics: Mapping[str, Any]) -> dict[str, Any]:
    context = _incident_context(state)
    severity = context["severity"]
    labels = ["incident", "agentteams", "needs-riskgate", "local-draft"]
    if severity != "unclassified":
        labels.append(_slug(severity, "severity-unclassified"))
    scenario_slug = _scenario_slug(state)
    if scenario_slug != "unscoped":
        labels.append(scenario_slug)
    return {
        "repository": REPO,
        "mode": "local-draft",
        "number": ISSUE_NUMBER,
        "number_kind": "local-placeholder",
        "state": "open-draft",
        "title": _issue_title(state),
        "labels": labels,
        "assignees": [],
        "created_from": {
            "incident_id": getattr(state, "incident_id", None),
            "run_id": metrics.get("run_id") or getattr(state, "run_id", "") or None,
            "trace_id": metrics.get("trace_id"),
            "scenario": _scenario_path(state) or None,
        },
        "impact": {
            "route": context["route"],
            "baseline_failure_rate": metrics.get("baseline_failure_rate"),
            "baseline_p99_ms": metrics.get("baseline_p99_ms"),
            "severity": severity,
        },
        "evidence": [
            {
                "type": item.kind,
                "source": item.source,
                "summary": item.summary,
                "details": item.details,
            }
            for item in state.events
        ],
        "acceptance_criteria": [
            "反事实实验必须提供可复查的主因证据。",
            "选中变更必须通过全部必选验证检查。",
            "PR 必须绑定场景、精确 changes、rollback_changes 与 RiskGate 决策。",
            "缺少检查、回滚或必要人工审批时，PR 必须保持 draft。",
        ],
        "linked_artifacts": [
            "trace.jsonl",
            "run-log.jsonl",
            "proof-bundle.json",
            "proof-report.md",
            "run-manifest.json",
            "github-pr.md",
        ],
    }


def _contract_path(state: IncidentState) -> str | None:
    selected = state.selected_patch
    if selected is None or not selected.changes:
        return None
    return f"changes/chronosfix/{_scenario_slug(state)}/{_patch_slug(state)}.json"


def _pr_payload(
    state: IncidentState,
    metrics: Mapping[str, Any],
    checks_payload: Mapping[str, Any],
) -> dict[str, Any]:
    selected = _selected_patch(state)
    readiness = _readiness(state, metrics, checks_payload)
    contract_path = _contract_path(state)
    return {
        "repository": REPO,
        "mode": "local-draft",
        "number": PR_NUMBER,
        "number_kind": "local-placeholder",
        "state": "ready-for-review" if readiness["status"] == "ready" else "draft",
        "title": _pr_title(state),
        "head": _branch_name(state),
        "base": "main",
        "linked_issue": f"#{ISSUE_NUMBER}",
        "scenario": _scenario_path(state) or None,
        "riskgate": getattr(state, "approval", "not-requested"),
        "quality_gate": getattr(state, "quality_gate", "not-evaluated"),
        "gate_result": _mapping(getattr(state, "gate_result", {})),
        "approval_record": _mapping(getattr(state, "approval_record", {})),
        "selected_patch": selected,
        "root_cause": _primary_cause(state),
        "validation": {
            "checks": _normalise_validation_checks(metrics),
            "fault_gene_variants": metrics.get("fault_variants"),
            "patches_compared": metrics.get("patches_compared"),
            "worst_failure_rate": metrics.get("selected_patch_worst_failure_rate"),
            "trace_spans": metrics.get("trace_spans"),
        },
        "evidence_passport": (
            asdict(state.evidence_passport)
            if state.evidence_passport and is_dataclass(state.evidence_passport)
            else _mapping(state.evidence_passport)
            if state.evidence_passport
            else None
        ),
        "changed_files": [contract_path] if contract_path else [],
        "change_contract": {
            "changes": selected.get("changes", {}) if selected else {},
            "rollback_changes": selected.get("rollback_changes", {}) if selected else {},
            "rollback": selected.get("rollback") if selected else None,
        },
        "readiness": readiness,
        "reviewers": [],
        "merge_policy": {
            "requires_human_approval": _requires_human(state),
            "requires_green_checks": True,
            "requires_rollback_contract": True,
            "requires_evidence_passport": True,
            "fail_closed": True,
        },
    }


def _change_contract(
    state: IncidentState,
    metrics: Mapping[str, Any],
    checks_payload: Mapping[str, Any],
) -> dict[str, Any] | None:
    selected = state.selected_patch
    if selected is None or not selected.changes:
        return None
    baseline = asdict(state.baseline) if is_dataclass(state.baseline) else _mapping(state.baseline)
    before = {key: baseline.get(key) for key in selected.changes}
    return {
        "schema_version": "chronosfix.change-contract/v1",
        "mode": "local-draft",
        "incident_id": state.incident_id,
        "run_id": metrics.get("run_id") or getattr(state, "run_id", "") or None,
        "scenario_path": _scenario_path(state) or None,
        "patch": {
            "id": selected.candidate_id,
            "title": selected.title,
            "before": before,
            "changes": selected.changes,
            "rollback_changes": selected.rollback_changes,
            "rollback_contract": selected.rollback or None,
            "risk": selected.risk,
            "cost": selected.cost,
        },
        "decision": {
            "quality_gate": getattr(state, "quality_gate", "not-evaluated"),
            "release_decision": getattr(state, "approval", "not-requested"),
            "release_ready": _mapping(getattr(state, "gate_result", {})).get("release_ready") is True,
        },
        "validation_checks": [
            {
                "name": item.get("name"),
                "executed": item.get("executed"),
                "conclusion": item.get("conclusion"),
                "run_id": item.get("run_id"),
                "evidence": item.get("evidence"),
            }
            for item in checks_payload.get("checks", [])
        ],
        "approval": _mapping(getattr(state, "approval_record", {})),
    }


def _patch_diff(
    state: IncidentState,
    metrics: Mapping[str, Any],
    checks_payload: Mapping[str, Any],
) -> str:
    path = _contract_path(state)
    contract = _change_contract(state, metrics, checks_payload)
    if not path or contract is None:
        return (
            "# ChronosFix local draft: no patch diff generated because "
            "selected_patch.changes is missing.\n"
        )
    content = json.dumps(contract, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    lines = content.splitlines()
    added = "\n".join(f"+{line}" for line in lines)
    return (
        f"diff --git a/{path} b/{path}\n"
        "new file mode 100644\n"
        "--- /dev/null\n"
        f"+++ b/{path}\n"
        f"@@ -0,0 +1,{len(lines)} @@\n"
        f"{added}\n"
    )


def _review_audit_payload(
    state: IncidentState,
    metrics: Mapping[str, Any],
    checks_payload: Mapping[str, Any],
    pr: Mapping[str, Any],
) -> list[dict[str, Any]]:
    run_id = metrics.get("run_id") or getattr(state, "run_id", "") or None
    gate = _mapping(getattr(state, "gate_result", {}))
    approval = _mapping(getattr(state, "approval_record", {}))
    records: list[dict[str, Any]] = [
        {
            "event": "issue.draft.generated",
            "actor": "incident-commander",
            "target": f"{REPO}#{ISSUE_NUMBER}",
            "mode": "local-draft",
            "permission_scope": "local-artifact:write",
            "run_id": run_id,
            "scenario": _scenario_path(state) or None,
        }
    ]
    if _contract_path(state):
        records.append(
            {
                "event": "change-contract.generated",
                "actor": "patch-engineer",
                "target": _contract_path(state),
                "mode": "local-draft",
                "permission_scope": "local-artifact:write",
                "run_id": run_id,
                "patch_id": state.selected_patch.candidate_id if state.selected_patch else None,
            }
        )
    records.extend(
        {
            "event": "validation.check.observed",
            "actor": "adversarial-verifier",
            "target": f"{REPO}#{PR_NUMBER}",
            "mode": "local-draft",
            "permission_scope": "local-artifact:write",
            "run_id": run_id,
            "check": item.get("name"),
            "executed": item.get("executed"),
            "conclusion": item.get("conclusion"),
            "source": item.get("source"),
        }
        for item in checks_payload.get("checks", [])
    )
    records.append(
        {
            "event": "riskgate.evaluated" if gate else "riskgate.pending",
            "actor": "release-auditor",
            "target": f"{REPO}#{PR_NUMBER}",
            "mode": "local-draft",
            "permission_scope": "local-artifact:write",
            "run_id": run_id,
            "decision": gate.get("decision"),
            "quality_gate": gate.get("quality_gate"),
            "release_ready": gate.get("release_ready") is True,
            "blockers": gate.get("blockers", []),
        }
    )
    records.append(
        {
            "event": "human-approval.recorded" if _human_approval_ready(state) else "human-approval.pending",
            "actor": approval.get("approver") or approval.get("approved_by") or approval.get("actor"),
            "target": f"{REPO}#{PR_NUMBER}",
            "mode": "local-draft",
            "permission_scope": "local-artifact:write",
            "run_id": run_id,
            "status": approval.get("status"),
            "timestamp": approval.get("timestamp") or approval.get("approved_at"),
            "reason": approval.get("reason"),
            "policy_version": approval.get("policy_version"),
            "input_digest": approval.get("input_digest"),
        }
    )
    records.append(
        {
            "event": "pull-request.draft.generated",
            "actor": "patch-engineer",
            "target": f"{REPO}#{PR_NUMBER}",
            "mode": "local-draft",
            "permission_scope": "local-artifact:write",
            "run_id": run_id,
            "state": pr.get("state"),
            "readiness": pr.get("readiness"),
        }
    )
    return records


def _format_percent(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.1%}"
    return "pending"


def _format_number(value: Any, suffix: str = "") -> str:
    if isinstance(value, (int, float)):
        return f"{value:.2f}{suffix}"
    return "pending"


def _issue_markdown(issue: Mapping[str, Any]) -> str:
    evidence = issue.get("evidence", [])
    evidence_lines = "\n".join(
        f"- `{item.get('type')}` / `{item.get('source')}`：{item.get('summary')}"
        for item in evidence
    ) or "- pending：尚未提供事故证据。"
    criteria = "\n".join(
        f"- [ ] {item}" for item in issue.get("acceptance_criteria", [])
    )
    artifacts = "\n".join(
        f"- `{item}`" for item in issue.get("linked_artifacts", [])
    )
    impact = _mapping(issue.get("impact"))
    source = _mapping(issue.get("created_from"))
    return f"""# {issue.get('title')}

> 本文件是本地可复现的 GitHub Issue 草案，不代表已写入远端仓库。

仓库：`{issue.get('repository')}`
本地草案编号：`#{issue.get('number')}`
场景：`{source.get('scenario') or 'pending'}`
标签：{", ".join(issue.get('labels', []))}

## 影响

- 路由：`{impact.get('route') or 'pending'}`
- 基线失败率：{_format_percent(impact.get('baseline_failure_rate'))}
- 基线 P99：{_format_number(impact.get('baseline_p99_ms'), 'ms')}
- 严重等级：{impact.get('severity') or 'unclassified'}

## 事故证据

{evidence_lines}

## 验收条件

{criteria}

## 关联证据

{artifacts}
"""


def _pr_markdown(pr: Mapping[str, Any]) -> str:
    patch = _mapping(pr.get("selected_patch"))
    cause = _mapping(pr.get("root_cause"))
    validation = _mapping(pr.get("validation"))
    checks = validation.get("checks", [])
    check_lines = "\n".join(
        f"- `{item.get('name')}`：{item.get('conclusion')}（executed={item.get('executed')}）"
        for item in checks
    ) or "- pending：尚无 `metrics.validation_checks`。"
    changed_files = "\n".join(
        f"- `{item}`" for item in pr.get("changed_files", [])
    ) or "- 暂无：缺少可验证的 `selected_patch.changes`。"
    passport = _mapping(pr.get("evidence_passport"))
    causal_claims = "\n".join(
        f"- {item}" for item in passport.get("causal_claims", [])
    ) or "- pending"
    rollback_claims = "\n".join(
        f"- {item}" for item in passport.get("rollback_claims", [])
    ) or "- pending"
    readiness = _mapping(pr.get("readiness"))
    missing = ", ".join(readiness.get("missing_evidence", [])) or "none"
    failed = ", ".join(readiness.get("failed_evidence", [])) or "none"
    return f"""# {pr.get('title')}

> 本文件是本地可复现的 GitHub PR 草案，不代表已创建远端分支或 PR。

本地草案编号：`#{pr.get('number')}`
关联 Issue：`{pr.get('linked_issue')}`
场景：`{pr.get('scenario') or 'pending'}`
分支：`{pr.get('head')}` → `{pr.get('base')}`
状态：`{pr.get('state')}`
RiskGate：`{pr.get('riskgate')}` / quality=`{pr.get('quality_gate')}`

## 准入状态

- 结论：`{readiness.get('status')}`
- 缺失证据：{missing}
- 失败证据：{failed}

## 根因证明

- 主因假设：`{cause.get('hypothesis_id') or 'pending'}` / {cause.get('title') or 'pending'}
- 基线失败率：{_format_percent(cause.get('baseline_failure_rate'))}
- 反事实失败率：{_format_percent(cause.get('counterfactual_failure_rate'))}
- 干预效果分：{_format_percent(cause.get('intervention_effect_score'))}（确定性回放效果比例，不是统计置信度）

## 变更合同

- 选中补丁：`{patch.get('candidate_id') or 'pending'}` / {patch.get('title') or 'pending'}
- changes：`{json.dumps(patch.get('changes', {}), ensure_ascii=False, sort_keys=True)}`
- rollback_changes：`{json.dumps(patch.get('rollback_changes', {}), ensure_ascii=False, sort_keys=True)}`
- 回滚说明：{patch.get('rollback') or 'pending'}

## 变更文件

{changed_files}

## 已记录的验证检查

{check_lines}

## 证据护照摘录

### 因果声明

{causal_claims}

### 回滚声明

{rollback_claims}

## 合并策略

- 缺证据即保持 draft：是
- 需要全部必选检查通过：是
- 需要回滚合同与 rollback_changes：是
- 需要证据护照：是
"""
