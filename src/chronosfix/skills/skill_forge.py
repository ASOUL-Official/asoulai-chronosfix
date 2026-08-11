from __future__ import annotations

from ..models import IncidentState, SkillCandidate


def distill_skill_candidates(state: IncidentState) -> list[SkillCandidate]:
    """Turn a resolved incident into reusable Skill candidates."""

    primary = next((item for item in state.experiments if item.classification == "primary-cause"), None)
    incident = state.incident_id
    primary_title = primary.title if primary else "未确认主因"

    return [
        SkillCandidate(
            name="ConnectionPoolCapacityGuard",
            source_incident=incident,
            trigger_pattern="连接池配置变更与流量上涨在同一时间窗出现。",
            input_schema={"traffic_rps": "number", "pool_size": "integer", "latency_factor": "number"},
            output_schema={"capacity_rps": "number", "failure_risk": "number", "recommendation": "string"},
            evaluation_cases=[variant.name for variant in state.fault_variants],
            safety_boundary="只生成容量建议和测试门禁；真实配置变更必须进入 RiskGate。",
            reuse_targets=["电商订单", "支付链路", "网关服务", "数据库连接池治理"],
        ),
        SkillCandidate(
            name="CounterfactualConfigReplay",
            source_incident=incident,
            trigger_pattern=f"需要验证配置变更是否为主因：{primary_title}。",
            input_schema={"baseline_state": "object", "intervention": "object", "success_metric": "string"},
            output_schema={"counterfactual_result": "object", "causal_confidence": "number"},
            evaluation_cases=[item.hypothesis_id for item in state.experiments],
            safety_boundary="只在隔离环境重放，不直接修改生产配置。",
            reuse_targets=["配置中心", "依赖升级", "发布回滚", "性能回退分析"],
        ),
        SkillCandidate(
            name="ProofCarryingPatch",
            source_incident=incident,
            trigger_pattern="补丁需要进入 PR、变更单或发布审批。",
            input_schema={"patch_score": "object", "trace_id": "string", "rollback": "string"},
            output_schema={"evidence_passport": "object", "audit_summary": "string"},
            evaluation_cases=[state.selected_patch.candidate_id if state.selected_patch else "none"],
            safety_boundary="没有因果、验证、风险、回滚证据时，禁止标记为可发布。",
            reuse_targets=["代码修复 PR", "配置变更", "依赖升级", "事故复盘"],
        ),
    ]
