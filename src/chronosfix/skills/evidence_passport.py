from __future__ import annotations

from typing import Any

from ..models import EvidencePassport, IncidentState


def collect_pre_gate_missing_claims(state: IncidentState) -> list[str]:
    """Derive release-blocking evidence gaps before RiskGate runs.

    This deliberately excludes human approval because approval is an
    independent gate dimension. Optional fault variants are also excluded:
    they remain visible as limitations but are not mandatory release evidence.
    """

    selected = state.selected_patch
    if selected is None:
        return ["尚未选择补丁，无法构建发布证据。"]

    missing: list[str] = []
    primary = next(
        (item for item in state.experiments if item.classification == "primary-cause"),
        None,
    )
    if primary is None:
        missing.append("未找到可辨识的主因，系统必须保持证据不足状态。")

    mandatory_failed = [
        str(item.get("name") or "unnamed-variant")
        for item in selected.results
        if item.get("mandatory", True) and item.get("healthy") is not True
    ]
    if mandatory_failed:
        missing.append(f"必选验证场景未通过: {', '.join(mandatory_failed)}")
    if not selected.rollback or not selected.rollback_changes:
        missing.append("缺少机器可验证的回滚契约。")
    return missing


def build_evidence_passport(
    state: IncidentState,
    *,
    integrity: dict[str, Any] | None = None,
) -> EvidencePassport:
    """Build a proof-carrying passport for the selected patch.

    A patch is not considered "ready" merely because it passes one happy-path
    test. It must carry explicit claims about requirement fit, causal validity,
    adversarial verification, release risk, and rollback.
    """

    selected = state.selected_patch
    if selected is None:
        raise ValueError("Evidence passport requires a selected patch.")

    primary = next((item for item in state.experiments if item.classification == "primary-cause"), None)
    amplifier = next((item for item in state.experiments if item.classification == "amplifier"), None)
    healthy_cases = [item["name"] for item in selected.results if item["healthy"]]
    optional_failed_cases = [
        item["name"]
        for item in selected.results
        if not item["healthy"] and not item.get("mandatory", True)
    ]

    causal_claims = []
    if primary:
        causal_claims.append(
            f"{primary.title}: 反事实撤销后失败率 {primary.baseline_failure_rate:.1%} -> "
            f"{primary.counterfactual_failure_rate:.1%}，干预效果分 {primary.intervention_effect_score:.1%}"
        )
    if amplifier:
        causal_claims.append(
            f"{amplifier.title}: 单独撤销后失败率 {amplifier.counterfactual_failure_rate:.1%}，判定为放大因素"
        )

    missing = collect_pre_gate_missing_claims(state)
    for blocker in state.gate_result.get("blockers", []):
        message = blocker.get("message", str(blocker)) if isinstance(blocker, dict) else str(blocker)
        if message not in missing:
            missing.append(message)
    if state.approval not in {"approved", "release-ready"}:
        missing.append("发布审批尚未完成，补丁不得进入自动发布。")

    return EvidencePassport(
        patch_id=selected.candidate_id,
        requirement_claims=[
            f"事故 {state.incident_id} 要求降低订单创建失败率与 P99 延迟。",
            "修复不得绕过审批，不得丢失回滚点，不得只修单一样例。",
            "修复必须覆盖由同一根因繁殖出的故障基因变体。",
        ],
        causal_claims=causal_claims,
        verification_claims=[
            f"补丁竞赛总分 {selected.total_score:.3f}。",
            f"平均失败率 {selected.mean_failure_rate:.1%}，最差失败率 {selected.worst_failure_rate:.1%}。",
            f"已覆盖健康变体 {len(healthy_cases)}/{len(selected.results)}: {', '.join(healthy_cases)}。",
        ],
        risk_claims=[
            f"风险分 {selected.risk:.2f}，成本分 {selected.cost:.2f}。",
            f"质量门禁 {state.quality_gate}，发布决策 {state.approval}。",
            "RiskGate 会阻断中高风险补丁的无人值守发布。",
            (
                f"非必选变体失败，仅作为已知限制保留: {', '.join(optional_failed_cases)}。"
                if optional_failed_cases
                else "当前没有失败的非必选变体。"
            ),
        ],
        rollback_claims=[
            selected.rollback,
            f"机器可验证回滚字段: {selected.rollback_changes or '缺失'}。",
        ],
        missing_claims=missing,
        integrity=integrity or {},
    )
