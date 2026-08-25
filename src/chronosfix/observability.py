from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from uuid import uuid4


class TraceRecorder:
    def __init__(
        self,
        incident_id: str,
        timestamp: str | None = None,
        *,
        run_id: str | None = None,
    ) -> None:
        self.incident_id = incident_id
        # Every execution receives a fresh identity.  The incident timestamp is
        # evidence about the incident, not the timestamp of this program run.
        self.run_id = run_id or f"run-{uuid4().hex}"
        self.trace_id = uuid4().hex
        self.incident_timestamp = timestamp
        self._counter = 0
        self.records: list[dict[str, Any]] = []

    def emit(
        self,
        agent: str,
        skill: str,
        status: str,
        payload: Any,
        *,
        parent_span_id: str | None = None,
        started_at: str | None = None,
        duration_ms: float | None = None,
    ) -> str:
        self._counter += 1
        span_id = f"{self._counter:016x}"
        if is_dataclass(payload):
            payload = asdict(payload)
        ended_at = datetime.now(timezone.utc).isoformat()
        started = started_at or ended_at
        record = {
            "timestamp": ended_at,
            "started_at": started,
            "ended_at": ended_at,
            "duration_ms": round(duration_ms, 3) if duration_ms is not None else 0.0,
            "duration_kind": "measured" if duration_ms is not None else "instant-event",
            "run_id": self.run_id,
            "trace_id": self.trace_id,
            "span_id": span_id,
            "parent_span_id": parent_span_id,
            "incident_id": self.incident_id,
            "incident_timestamp": self.incident_timestamp,
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
