from __future__ import annotations

import json
from pathlib import Path

from ..models import ChangeEvent, Hypothesis, IncidentState, ServiceState


def load_incident(path: Path) -> tuple[IncidentState, dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    state = IncidentState(
        incident_id=raw["incident_id"],
        title=raw["title"],
        baseline=ServiceState(**raw["baseline"]),
        events=[ChangeEvent(**event) for event in raw["events"]],
        hypotheses=[Hypothesis(**item) for item in raw["hypotheses"]],
    )
    state.evidence_index = [event.source for event in state.events]
    return state, raw

