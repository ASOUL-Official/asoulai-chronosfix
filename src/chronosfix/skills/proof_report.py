from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

from ..models import EvidencePassport, IncidentState


def _render_claims(title: str, claims: list[str]) -> list[str]:
    if not claims:
        return [f"### {title}", "", "- 暂无。", ""]
    return [f"### {title}", "", *[f"- {item}" for item in claims], ""]


def _passport_claim_count(passport: EvidencePassport | None) -> int:
    if passport is None:
        return 0
    return (
        len(passport.requirement_claims)
        + len(passport.causal_claims)
        + len(passport.verification_claims)
        + len(passport.risk_claims)
        + len(passport.rollback_claims)
    )


def write_reports(state: IncidentState, metrics: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "incident_id": state.incident_id,
        "title": state.title,
        "baseline": asdict(state.baseline),
        "timeline": [asdict(item) for item in state.events],
        "experiments": [asdict(item) for item in state.experiments],
        "fault_variants": [asdict(item) for item in state.fault_variants],
        "patch_tournament": [asdict(item) for item in state.patch_scores],
        "selected_patch": asdict(state.selected_patch) if state.selected_patch else None,
        "evidence_passport": asdict(state.evidence_passport) if state.evidence_passport else None,
        "skill_candidates": [asdict(item) for item in state.skill_candidates],
        "approval": state.approval,
        "evidence_index": state.evidence_index,
        "metrics": metrics,
    }
    (output_dir / "proof-bundle.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    primary = next((item for item in state.experiments if item.classification == "primary-cause"), None)
    amplifier = next((item for item in state.experiments if item.classification == "amplifier"), None)
    selected = state.selected_patch
    passport = state.evidence_passport

    lines = [
        f"# ChronosFix 证据化修复报告：{state.incident_id}",
        "",
        f"**故障：** {state.title}",
        f"**审批状态：** {state.approval}",
        f"**Trace ID：** {metrics.get('trace_id', '见 trace.jsonl')}",
        "",
        "## 0. 结论摘要",
        "",
        (
            f"系统从 {len(state.events)} 条证据中重建时间线，验证 {len(state.experiments)} 个根因假设，"
            f"生成 {len(state.fault_variants)} 个故障基因变体，对 {len(state.patch_scores)} 个补丁进行对抗竞赛，"
            f"最终选择 **{selected.title if selected else '未选择'}**。"
        ),
        "",
        "这份报告不是普通事故复盘，而是一份“带证据护照的补丁”：每个修复都必须同时回答需求、因果、验证、风险、回滚和可复用 Skill 沉淀六个问题。",
        "",
        "## 1. 因果结论",
        "",
    ]
    if primary:
        lines.append(
            f"- 主因：**{primary.title}**。反事实实验将失败率从 "
            f"{primary.baseline_failure_rate:.1%} 降至 {primary.counterfactual_failure_rate:.1%}，"
            f"因果置信度 {primary.causal_confidence:.1%}。"
        )
    else:
        lines.append("- 尚未找到达到阈值的主因。")
    if amplifier:
        lines.append(
            f"- 放大因子：**{amplifier.title}**。单独撤销后失败率为 "
            f"{amplifier.counterfactual_failure_rate:.1%}，说明它会放大故障但不是唯一主因。"
        )

    lines.extend(["", "## 2. 缺陷基因谱系", ""])
    for variant in state.fault_variants:
        lines.append(
            f"- **{variant.name}**：来源 `{variant.lineage}`，触发条件：{variant.trigger}，"
            f"预期风险：{variant.expected_risk}，变更：`{variant.changes}`。"
        )

    lines.extend(["", "## 3. 补丁竞赛", ""])
    for index, score in enumerate(state.patch_scores, start=1):
        lines.append(
            f"{index}. **{score.title}**：总分 {score.total_score:.3f}，"
            f"平均失败率 {score.mean_failure_rate:.1%}，最差失败率 {score.worst_failure_rate:.1%}，"
            f"风险 {score.risk:.2f}，成本 {score.cost:.2f}，回滚：{score.rollback}。"
        )

    lines.extend(["", "## 4. 证据护照", ""])
    if passport:
        lines.extend(_render_claims("需求声明", passport.requirement_claims))
        lines.extend(_render_claims("因果声明", passport.causal_claims))
        lines.extend(_render_claims("验证声明", passport.verification_claims))
        lines.extend(_render_claims("风险声明", passport.risk_claims))
        lines.extend(_render_claims("回滚声明", passport.rollback_claims))
        lines.extend(_render_claims("缺口声明", passport.missing_claims))
        lines.append(f"证据声明总数：{_passport_claim_count(passport)}。")
    else:
        lines.append("- 未生成证据护照。")

    lines.extend(["", "", "## 5. Skill 自进化候选", ""])
    for skill in state.skill_candidates:
        lines.append(
            f"- **{skill.name} v{skill.version}**：由事故 {skill.source_incident} 沉淀；"
            f"触发模式：{skill.trigger_pattern}；复用目标：{', '.join(skill.reuse_targets)}；"
            f"安全边界：{skill.safety_boundary}。"
        )

    if selected:
        lines.extend(
            [
                "",
                "## 6. 最终选择与审计",
                "",
                f"选择 **{selected.title}**，因为它在正确性、风险和实施成本的综合评分中排名第一。",
                f"发布前必须保留回滚点：{selected.rollback}。",
                "全部 Agent、Skill、实验、审批和报告动作均写入 `trace.jsonl`，可用于复盘和审计。",
            ]
        )

    (output_dir / "proof-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
