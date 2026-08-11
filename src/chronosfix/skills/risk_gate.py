from __future__ import annotations

from ..models import PatchScore


def evaluate_gate(selected: PatchScore, approved: bool) -> dict:
    risk_level = "high" if selected.risk >= 0.7 else "medium" if selected.risk >= 0.25 else "low"
    requires_human = risk_level in {"medium", "high"}
    if requires_human and not approved:
        decision = "blocked-awaiting-human"
    else:
        decision = "approved"
    return {
        "risk_level": risk_level,
        "requires_human": requires_human,
        "decision": decision,
        "rollback_ready": True,
    }

