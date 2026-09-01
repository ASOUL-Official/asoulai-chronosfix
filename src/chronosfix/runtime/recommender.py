"""Evidence-driven Agent composition for the local Controller demo.

The planner is deterministic on purpose: its recommendation can be replayed,
audited and compared with the resulting task graph. It is an AgentTeams-style
Manager contract, not a claim that an official AgentTeams runtime executed.
"""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any, Iterable


AGENT_PROFILES: dict[str, dict[str, Any]] = {
    "incident-commander": {
        "role": "事故指挥",
        "capability": "incident-control",
        "skill": "EvidenceFusion",
        "worker": "chronosfix-incident-commander#01",
    },
    "timeline-analyst": {
        "role": "证据时间线",
        "capability": "evidence",
        "skill": "ChangeTimeline",
        "worker": "chronosfix-timeline-analyst#01",
    },
    "hypothesis-scientist": {
        "role": "假设科学家",
        "capability": "hypothesis",
        "skill": "CounterfactualReplay",
        "worker": "chronosfix-hypothesis-scientist#01",
    },
    "universe-builder": {
        "role": "反事实实验",
        "capability": "replay",
        "skill": "FaultGenome",
        "worker": "chronosfix-universe-builder#01",
    },
    "patch-engineer": {
        "role": "补丁工程",
        "capability": "patch-contract",
        "skill": "PatchTournament",
        "worker": "chronosfix-patch-engineer#01",
    },
    "adversarial-verifier": {
        "role": "对抗验证",
        "capability": "patch-tournament",
        "skill": "FaultGenome",
        "worker": "chronosfix-adversarial-verifier#01",
    },
    "release-auditor": {
        "role": "发布审计",
        "capability": "risk-gate",
        "skill": "RiskGate",
        "worker": "chronosfix-release-auditor#01",
    },
    "skill-curator": {
        "role": "Skill 沉淀",
        "capability": "skill",
        "skill": "SkillForge",
        "worker": "chronosfix-skill-curator#01",
    },
}


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _decision_id(value: Any) -> str:
    return sha256(_canonical(value).encode("utf-8")).hexdigest()[:16]


def _signals(scenario: dict[str, Any], evidence: Iterable[dict[str, Any]]) -> list[str]:
    signals = [str(item.get("kind")) for item in scenario.get("events", []) if item.get("kind")]
    for item in evidence:
        if item.get("kind"):
            signals.append(str(item["kind"]))
        if item.get("signal"):
            signals.append(str(item["signal"]))
    return list(dict.fromkeys(signals))


def _has_evidence_conflict(
    scenario: dict[str, Any], evidence: Iterable[dict[str, Any]]
) -> bool:
    """Detect an explicit conflict from observable incident evidence only."""

    for item in [*scenario.get("events", []), *evidence]:
        payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
        details = item.get("details") if isinstance(item.get("details"), dict) else {}
        if item.get("evidence_conflict") or details.get("evidence_conflict") or payload.get("evidence_conflict"):
            return True
    return False


def _item(agent: str, order: int, reason: str, depends_on: list[str]) -> dict[str, Any]:
    profile = AGENT_PROFILES[agent]
    return {
        "order": order,
        "agent": agent,
        "worker": profile["worker"],
        "role": profile["role"],
        "skill": profile["skill"],
        "capability": profile["capability"],
        "reason": reason,
        "depends_on": depends_on,
    }


def recommend_agent_composition(
    scenario: dict[str, Any],
    *,
    evidence: Iterable[dict[str, Any]] = (),
    objective: str = "prove-and-repair",
) -> dict[str, Any]:
    """Return a replayable, evidence-driven Agent/Skill composition."""

    signals = _signals(scenario, evidence)
    hypotheses = scenario.get("hypotheses") or []
    patches = scenario.get("patch_candidates") or []
    evidence_conflict = _has_evidence_conflict(scenario, evidence)
    abstain = evidence_conflict

    selected: list[dict[str, Any]] = []

    def add(agent: str, reason: str, depends_on: list[str]) -> None:
        selected.append(_item(agent, len(selected) + 1, reason, depends_on))

    add("incident-commander", "先建立共享事故上下文，再决定后续是否需要更多角色。", [])
    if signals or hypotheses:
        add("timeline-analyst", "读取当前时间线与新增证据，补齐可验证的输入边界。", ["incident-commander"])
    if hypotheses:
        add(
            "hypothesis-scientist",
            "当前存在可检验假设，先用反事实结果判断是否可唯一归因。",
            ["timeline-analyst"] if len(selected) > 1 else ["incident-commander"],
        )

    if abstain:
        strategy = "证据不足时缩短队列并拒答"
        confidence = 0.62 if evidence_conflict else 0.78
        stop_before = "PatchTournament / RiskGate"
        rationale = (
            "Agent 判断当前证据无法安全支持唯一根因，因此只组合上下文、证据和假设验证角色；"
            "不生成补丁，不进入 RiskGate。"
        )
    else:
        add(
            "universe-builder",
            "已满足可诊断范围，构造反事实与故障族验证空间。",
            [selected[-1]["agent"]],
        )
        if patches:
            add("patch-engineer", "已有候选变更，比较修复收益、风险和回滚契约。", ["universe-builder"])
            add("adversarial-verifier", "对候选补丁执行同源故障族和回滚验证，避免只在单一样例上通过。", ["patch-engineer"])
            add("release-auditor", "只有质量门禁通过且审批绑定最新 revision 才允许发布决策。", ["adversarial-verifier"])
        strategy = "按证据动态拼接完整修复链"
        confidence = 0.93 if hypotheses and patches else 0.72
        stop_before = "无"
        rationale = "Agent 根据已观测信号和可用候选补丁选择最小充分队列；每个角色的输入来自上游结果。"

    evidence_kinds = set(signals)
    unknown_evidence = evidence_kinds - {"commit", "dependency", "configuration", "traffic", "incident", "policy"}
    if unknown_evidence and not abstain:
        add("skill-curator", "出现未被当前 Skill 映射覆盖的新证据类型，先沉淀可复用 Skill 候选。", [selected[-1]["agent"]])

    composition = [
        {**item, "order": index}
        for index, item in enumerate(selected, start=1)
    ]
    decision_input = {
        "scenario_id": scenario.get("incident_id") or scenario.get("title"),
        "objective": objective,
        "signals": signals,
        "evidence_conflict": evidence_conflict,
        "has_hypotheses": bool(hypotheses),
        "has_patch_candidates": bool(patches),
        "composition": composition,
    }
    return {
        "schema": "chronosfix.agent-recommendation/v1",
        "decision_id": _decision_id(decision_input),
        "planner": "chronosfix-manager",
        "planner_mode": "evidence-driven-deterministic",
        "official_agentteams_executed": False,
        "objective": objective,
        "strategy": strategy,
        "confidence": confidence,
        "observed_signals": signals,
        "rationale": rationale,
        "stop_before": stop_before,
        "free_combination": True,
        "composition": composition,
        "boundary_note": "本地 Manager 依据证据生成可回放组合；不冒充官方 AgentTeams Controller 推理轨迹。",
    }


def compile_agent_dag(recommendation: dict[str, Any]) -> dict[str, Any]:
    """Compile a Manager recommendation into an executable, topologically sorted DAG.

    The graph keeps the human-readable Agent dependency names out of the
    runtime boundary: workers receive concrete task IDs, skills and capability
    requirements. This makes the recommendation directly auditable against the
    task/attempt records held by ``RuntimeStore``.
    """

    composition = list(recommendation.get("composition") or [])
    by_agent: dict[str, dict[str, Any]] = {}
    for item in composition:
        agent = str(item["agent"])
        if agent in by_agent:
            raise ValueError(f"duplicate agent in recommendation: {agent}")
        by_agent[agent] = item

    tasks: list[dict[str, Any]] = []
    task_id_by_agent: dict[str, str] = {}
    for item in composition:
        agent = str(item["agent"])
        order = int(item["order"])
        task_id = f"agent-{order:02d}-{agent}"
        dependency_agents = [str(value) for value in item.get("depends_on") or []]
        missing = [name for name in dependency_agents if name not in task_id_by_agent]
        if missing:
            raise ValueError(f"agent {agent} depends on unresolved upstream role(s): {missing}")
        task_id_by_agent[agent] = task_id
        tasks.append(
            {
                "task_id": task_id,
                "order": order,
                "agent": agent,
                "worker": item["worker"],
                "role": item["role"],
                "skill": item["skill"],
                "capability": item["capability"],
                "depends_on": [task_id_by_agent[name] for name in dependency_agents],
            }
        )

    return {
        "schema": "chronosfix.agent-dag/v1",
        "decision_id": recommendation["decision_id"],
        "planner": recommendation["planner"],
        "tasks": tasks,
    }
