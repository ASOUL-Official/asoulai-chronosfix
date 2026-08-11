from __future__ import annotations

from ..models import EvidencePassport, IncidentState


def build_evidence_passport(state: IncidentState) -> EvidencePassport:
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
    failed_cases = [item["name"] for item in selected.results if not item["healthy"]]

    causal_claims = []
    if primary:
        causal_claims.append(
            f"{primary.title}: 反事实撤销后失败率 {primary.baseline_failure_rate:.1%} -> "
            f"{primary.counterfactual_failure_rate:.1%}，因果置信度 {primary.causal_confidence:.1%}"
        )
    if amplifier:
        causal_claims.append(
            f"{amplifier.title}: 单独撤销后失败率 {amplifier.counterfactual_failure_rate:.1%}，判定为放大因素"
        )

    missing = []
    if failed_cases:
        missing.append(f"仍需补强场景: {', '.join(failed_cases)}")
    if state.approval != "approved":
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
            f"审批状态 {state.approval}。",
            "RiskGate 会阻断中高风险补丁的无人值守发布。",
        ],
        rollback_claims=[selected.rollback],
        missing_claims=missing,
    )
