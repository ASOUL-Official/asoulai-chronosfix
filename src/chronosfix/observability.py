from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5


class TraceRecorder:
    def __init__(self, incident_id: str) -> None:
        self.incident_id = incident_id
        self.trace_id = uuid5(NAMESPACE_URL, f"chronosfix:{incident_id}").hex
        self._counter = 0
        self.records: list[dict[str, Any]] = []

    def emit(self, agent: str, skill: str, status: str, payload: Any) -> str:
        self._counter += 1
        span_id = f"{self._counter:016x}"
        if is_dataclass(payload):
            payload = asdict(payload)
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trace_id": self.trace_id,
            "span_id": span_id,
            "incident_id": self.incident_id,
            "agent": agent,
            "skill": skill,
            "status": status,
            "payload": payload,
        }
        self.records.append(record)
        return span_id

    def write_jsonl(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in self.records),
            encoding="utf-8",
        )

