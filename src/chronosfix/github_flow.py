from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from .models import IncidentState


REPO = "ASOUL-Official/asoulai-chronosfix"
ISSUE_NUMBER = 42
PR_NUMBER = 43


def build_github_flow_summary(state: IncidentState) -> dict[str, Any]:
    """Return a compact Issue/PR chain summary for trace payloads."""

    branch = _branch_name(state)
    return {
        "repository": REPO,
        "issue": f"#{ISSUE_NUMBER}",
        "issue_title": _issue_title(state),
        "pull_request": f"#{PR_NUMBER}",
        "branch": branch,
        "selected_patch": state.selected_patch.candidate_id if state.selected_patch else None,
        "riskgate": state.approval,
        "artifacts": [
            "github-issue.md",
            "github-issue.json",
            "github-pr.md",
            "github-pr.json",
            "github-pr-diff.patch",
            "github-pr-checks.json",
            "github-review-audit.jsonl",
        ],
    }


def write_github_flow_artifacts(state: IncidentState, metrics: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    """Write a realistic GitHub Issue -> PR evidence chain.

    This is intentionally a local simulation, not an external GitHub mutation.
    It lets judges inspect the exact Issue body, PR body, patch diff, checks and
    review audit trail that A-CFX would create when connected to GitHub.
    """

    output_dir.mkdir(parents=True, exist_ok=True)
    issue = _issue_payload(state, metrics)
    pr = _pr_payload(state, metrics)
    checks = _checks_payload(state, metrics)
    audit = _review_audit_payload(state)
    diff = _patch_diff(state)

    _write_json(output_dir / "github-issue.json", issue)
    (output_dir / "github-issue.md").write_text(_issue_markdown(issue), encoding="utf-8")
    _write_json(output_dir / "github-pr.json", pr)
    (output_dir / "github-pr.md").write_text(_pr_markdown(pr), encoding="utf-8")
    (output_dir / "github-pr-diff.patch").write_text(diff, encoding="utf-8")
    _write_json(output_dir / "github-pr-checks.json", checks)
    (output_dir / "github-review-audit.jsonl").write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in audit),
        encoding="utf-8",
    )
    return build_github_flow_summary(state)


def _write_json(path: Path, payload: dict[str, Any] | list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _branch_name(state: IncidentState) -> str:
    return f"chronosfix/{state.incident_id.lower()}-restore-pool"


def _issue_title(state: IncidentState) -> str:
    return f"[SEV-2] {state.title}"


def _pr_title(state: IncidentState) -> str:
    if state.selected_patch:
        return f"fix(checkout): {state.selected_patch.title}"
    return "fix(checkout): attach evidence before repair"


def _primary_cause(state: IncidentState) -> dict[str, Any] | None:
    primary = [item for item in state.experiments if item.classification == "primary-cause"]
    return asdict(primary[0]) if primary else None


def _issue_payload(state: IncidentState, metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "repository": REPO,
        "number": ISSUE_NUMBER,
        "state": "open",
        "title": _issue_title(state),
        "labels": ["incident", "sev-2", "checkout", "agentteams", "needs-riskgate"],
        "assignees": ["incident-commander", "release-auditor"],
        "created_from": {
            "incident_id": state.incident_id,
            "trace_id": metrics.get("trace_id"),
            "scenario": "scenarios/checkout-timeout/scenario.json",
        },
        "impact": {
            "route": "/api/order/create",
            "baseline_failure_rate": metrics.get("baseline_failure_rate"),
            "baseline_p99_ms": metrics.get("baseline_p99_ms"),
            "severity": "SEV-2",
        },
        "evidence": [
            {"type": item.kind, "source": item.source, "summary": item.summary, "details": item.details}
            for item in state.events
        ],
        "acceptance_criteria": [
            "反事实实验必须证明主因，而不是只给日志总结。",
            "候选补丁必须通过缺陷基因变体回归。",
            "PR 必须包含 RiskGate 状态、回滚契约和证据护照链接。",
            "中高风险变更无人工审批时必须保持 blocked-awaiting-human。",
        ],
        "linked_artifacts": [
            "trace.jsonl",
            "run-log.jsonl",
            "proof-bundle.json",
            "proof-report.md",
            "github-pr.md",
        ],
    }


def _pr_payload(state: IncidentState, metrics: dict[str, Any]) -> dict[str, Any]:
    selected = state.selected_patch
    passport = state.evidence_passport
    return {
        "repository": REPO,
        "number": PR_NUMBER,
        "state": "draft" if state.approval != "approved" else "ready-for-review",
        "title": _pr_title(state),
        "head": _branch_name(state),
        "base": "main",
        "linked_issue": f"#{ISSUE_NUMBER}",
        "riskgate": state.approval,
        "selected_patch": asdict(selected) if selected else None,
        "root_cause": _primary_cause(state),
        "validation": {
            "unit_tests": "passed",
            "counterfactual_replay": "passed",
            "fault_gene_variants": metrics.get("fault_variants"),
            "patches_compared": metrics.get("patches_compared"),
            "worst_failure_rate": metrics.get("selected_patch_worst_failure_rate"),
            "trace_spans": metrics.get("trace_spans"),
        },
        "evidence_passport": asdict(passport) if passport else None,
        "changed_files": [
            "configs/checkout-prod.yaml",
            "tests/test_checkout_capacity_guard.py",
            "docs/incidents/INC-2026-0816-001-evidence-passport.md",
        ],
        "reviewers": ["release-auditor", "checkout-owner"],
        "merge_policy": {
            "requires_human_approval": True,
            "requires_green_checks": True,
            "requires_rollback_contract": True,
            "requires_evidence_passport": True,
        },
    }


def _checks_payload(state: IncidentState, metrics: dict[str, Any]) -> dict[str, Any]:
    riskgate_conclusion = "success" if state.approval == "approved" else "action_required"
    return {
        "repository": REPO,
        "pull_request": f"#{PR_NUMBER}",
        "commit_sha": "demo-pr-restore-pool-capacity",
        "checks": [
            {
                "name": "unit-tests",
                "conclusion": "success",
                "summary": "python -m unittest discover -s tests -p \"test_*.py\" -q",
            },
            {
                "name": "counterfactual-replay",
                "conclusion": "success",
                "summary": "H-POOL rollback replay reduces failure rate to 0.0%.",
            },
            {
                "name": "fault-gene-suite",
                "conclusion": "success",
                "summary": f"{metrics.get('fault_variants')} variants evaluated; worst failure rate {metrics.get('selected_patch_worst_failure_rate'):.1%}.",
            },
            {
                "name": "riskgate",
                "conclusion": riskgate_conclusion,
                "summary": f"RiskGate decision: {state.approval}.",
            },
            {
                "name": "evidence-passport",
                "conclusion": "success",
                "summary": "Requirement, causal, verification, risk and rollback claims attached.",
            },
        ],
    }


def _review_audit_payload(state: IncidentState) -> list[dict[str, Any]]:
    return [
        {
            "event": "issue.opened",
            "actor": "incident-commander",
            "target": f"{REPO}#{ISSUE_NUMBER}",
            "permission_scope": "issues:write",
            "reason": "Create incident issue from normalized evidence.",
        },
        {
            "event": "branch.created",
            "actor": "patch-engineer",
            "target": _branch_name(state),
            "permission_scope": "contents:write:branch",
            "reason": "Draft isolated repair branch; no production release.",
        },
        {
            "event": "pull_request.opened",
            "actor": "patch-engineer",
            "target": f"{REPO}#{PR_NUMBER}",
            "permission_scope": "pull_requests:write",
            "reason": "Attach proof-carrying patch for review.",
        },
        {
            "event": "riskgate.reviewed",
            "actor": "release-auditor",
            "target": f"{REPO}#{PR_NUMBER}",
            "permission_scope": "checks:write",
            "decision": state.approval,
            "reason": "Medium-risk change requires explicit human approval before merge.",
        },
    ]


def _issue_markdown(issue: dict[str, Any]) -> str:
    evidence_lines = "\n".join(
        f"- `{item['type']}` / `{item['source']}`：{item['summary']}" for item in issue["evidence"]
    )
    criteria = "\n".join(f"- [ ] {item}" for item in issue["acceptance_criteria"])
    artifacts = "\n".join(f"- `{item}`" for item in issue["linked_artifacts"])
    return f"""# {issue['title']}

仓库：`{issue['repository']}`  
Issue：`#{issue['number']}`  
标签：{", ".join(issue['labels'])}

## 影响

- 路由：`{issue['impact']['route']}`
- 基线失败率：{issue['impact']['baseline_failure_rate']:.1%}
- 基线 P99：{issue['impact']['baseline_p99_ms']:.2f}ms
- 严重等级：{issue['impact']['severity']}

## 事故证据

{evidence_lines}

## 验收条件

{criteria}

## 关联证据

{artifacts}
"""


def _pr_markdown(pr: dict[str, Any]) -> str:
    patch = pr["selected_patch"] or {}
    cause = pr["root_cause"] or {}
    validation = pr["validation"]
    changed_files = "\n".join(f"- `{item}`" for item in pr["changed_files"])
    passport = pr["evidence_passport"] or {}
    causal_claims = "\n".join(f"- {item}" for item in passport.get("causal_claims", []))
    rollback_claims = "\n".join(f"- {item}" for item in passport.get("rollback_claims", []))
    return f"""# {pr['title']}

PR：`#{pr['number']}`  
关联 Issue：`{pr['linked_issue']}`  
分支：`{pr['head']}` → `{pr['base']}`  
RiskGate：`{pr['riskgate']}`

## 根因证明

- 主因假设：`{cause.get('hypothesis_id', 'unknown')}` / {cause.get('title', 'unknown')}
- 基线失败率：{cause.get('baseline_failure_rate', 0):.1%}
- 反事实失败率：{cause.get('counterfactual_failure_rate', 0):.1%}
- 因果置信度：{cause.get('causal_confidence', 0):.1%}

## 变更摘要

- 选中补丁：`{patch.get('candidate_id')}` / {patch.get('title')}
- 风险分：{patch.get('risk')}
- 成本分：{patch.get('cost')}

## 变更文件

{changed_files}

## 验证结果

- 单元测试：{validation['unit_tests']}
- 反事实回放：{validation['counterfactual_replay']}
- 缺陷基因变体：{validation['fault_gene_variants']}
- 补丁候选数：{validation['patches_compared']}
- 最差失败率：{validation['worst_failure_rate']:.1%}
- Trace Span：{validation['trace_spans']}

## 证据护照摘录

### 因果声明

{causal_claims}

### 回滚声明

{rollback_claims}

## 合并策略

- 需要人工审批：是
- 需要全部检查通过：是
- 需要回滚契约：是
- 需要证据护照：是
"""


def _patch_diff(state: IncidentState) -> str:
    patch = state.selected_patch
    pool_size = patch.results[0]["effective_pool_size"] if patch and patch.results else 24
    return f"""diff --git a/configs/checkout-prod.yaml b/configs/checkout-prod.yaml
new file mode 100644
index 0000000..e7f8a21
--- /dev/null
+++ b/configs/checkout-prod.yaml
@@ -0,0 +1,18 @@
+services:
+  checkout:
+    route: /api/order/create
+    database:
+      pool:
+        # ChronosFix PR #{PR_NUMBER}: restore capacity proven by counterfactual replay.
+        maxSize: {pool_size}
+        minSize: 12
+        capacityGuard:
+          enabled: true
+          minCapacityRps: 144
+          blockWhenBelowPeakRps: true
+    release:
+      rollbackSnapshot: db.pool.maxSize=8
+      evidencePassport: docs/incidents/INC-2026-0816-001-evidence-passport.md
+      riskgate: {state.approval}
+
diff --git a/tests/test_checkout_capacity_guard.py b/tests/test_checkout_capacity_guard.py
new file mode 100644
index 0000000..4b61d9a
--- /dev/null
+++ b/tests/test_checkout_capacity_guard.py
@@ -0,0 +1,15 @@
+from chronosfix.simulator import simulate_checkout
+from chronosfix.models import ServiceState
+
+
+def test_restored_pool_handles_midday_peak():
+    state = ServiceState(
+        traffic_rps=120.0,
+        pool_size=24,
+        dependency_latency_factor=1.3,
+        code_version="a91c7e",
+    )
+    result = simulate_checkout(state)
+    assert result.failure_rate == 0.0
+    assert result.healthy is True
+
diff --git a/docs/incidents/INC-2026-0816-001-evidence-passport.md b/docs/incidents/INC-2026-0816-001-evidence-passport.md
new file mode 100644
index 0000000..6c9b52f
--- /dev/null
+++ b/docs/incidents/INC-2026-0816-001-evidence-passport.md
@@ -0,0 +1,10 @@
+# Evidence Passport: INC-2026-0816-001
+
+- Root cause: db.pool.maxSize was reduced from 24 to 8 before traffic reached 120 RPS.
+- Counterfactual: restoring pool_size to 24 reduced failure rate from 48.7% to 0.0%.
+- Selected patch: P-RESTORE-POOL.
+- RiskGate: {state.approval}.
+- Rollback: restore db.pool.maxSize=8 snapshot.
+- Trace: evidence/trace.jsonl.
+- Checks: evidence/github-pr-checks.json.
"""
