from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import time
from typing import Any
import uuid


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def encode(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def decode(value: str | None) -> Any:
    return None if value is None else json.loads(value)


class RevisionConflict(RuntimeError):
    pass


class UnifiedModelStore:
    """Executable local fallback for PolarDB/UnifiedModel/RocketMQ/Nacos contracts."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def connection(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self.connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    revision INTEGER NOT NULL,
                    state_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS evidence_items (
                    incident_id TEXT NOT NULL,
                    evidence_id TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    digest TEXT NOT NULL,
                    PRIMARY KEY (incident_id, evidence_id)
                );
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL,
                    max_attempts INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS policies (
                    name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    active INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (name, version)
                );
                CREATE TABLE IF NOT EXISTS trace_exports (
                    trace_id TEXT PRIMARY KEY,
                    otlp_json TEXT NOT NULL,
                    span_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    def create_incident(self, incident_id: str, state: dict[str, Any]) -> dict[str, Any]:
        with self.connection() as connection:
            connection.execute(
                "INSERT INTO incidents VALUES (?, 0, ?, ?)",
                (incident_id, encode(state), utc_now()),
            )
        return self.get_incident(incident_id)

    def get_incident(self, incident_id: str) -> dict[str, Any]:
        with self.connection() as connection:
            row = connection.execute("SELECT * FROM incidents WHERE incident_id = ?", (incident_id,)).fetchone()
        if row is None:
            raise KeyError(incident_id)
        return {"incident_id": row["incident_id"], "revision": row["revision"], "state": decode(row["state_json"])}

    def compare_and_swap(self, incident_id: str, expected_revision: int, state: dict[str, Any]) -> dict[str, Any]:
        with self.connection() as connection:
            cursor = connection.execute(
                """UPDATE incidents SET revision = revision + 1, state_json = ?, updated_at = ?
                WHERE incident_id = ? AND revision = ?""",
                (encode(state), utc_now(), incident_id, expected_revision),
            )
            if cursor.rowcount != 1:
                actual = connection.execute(
                    "SELECT revision FROM incidents WHERE incident_id = ?", (incident_id,)
                ).fetchone()
                raise RevisionConflict(
                    f"expected revision {expected_revision}; actual {None if actual is None else actual['revision']}"
                )
        return self.get_incident(incident_id)

    def add_evidence(self, incident_id: str, evidence_id: str, revision: int, payload: dict[str, Any]) -> bool:
        value = encode(payload)
        try:
            with self.connection() as connection:
                connection.execute(
                    "INSERT INTO evidence_items VALUES (?, ?, ?, ?, ?)",
                    (incident_id, evidence_id, revision, value, hashlib.sha256(value.encode()).hexdigest()),
                )
            return True
        except sqlite3.IntegrityError:
            return False

    def publish(self, topic: str, idempotency_key: str, payload: dict[str, Any], *, max_attempts: int = 3) -> dict[str, Any]:
        now = utc_now()
        message_id = f"msg-{uuid.uuid4().hex[:16]}"
        try:
            with self.connection() as connection:
                connection.execute(
                    "INSERT INTO messages VALUES (?, ?, ?, ?, 'READY', 0, ?, ?, ?)",
                    (message_id, topic, idempotency_key, encode(payload), max_attempts, now, now),
                )
        except sqlite3.IntegrityError:
            with self.connection() as connection:
                row = connection.execute(
                    "SELECT * FROM messages WHERE idempotency_key = ?", (idempotency_key,)
                ).fetchone()
            return {**dict(row), "payload": decode(row["payload_json"]), "deduplicated": True}
        # Keep the runtime compatible with the bundled Python 3.8 as well as
        # newer interpreters; dict union (``|``) only arrived in Python 3.9.
        return {**self.message(message_id), "deduplicated": False}

    def message(self, message_id: str) -> dict[str, Any]:
        with self.connection() as connection:
            row = connection.execute("SELECT * FROM messages WHERE message_id = ?", (message_id,)).fetchone()
        if row is None:
            raise KeyError(message_id)
        result = dict(row)
        result["payload"] = decode(result.pop("payload_json"))
        return result

    def consume(self, topic: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT message_id FROM messages WHERE topic = ? AND status = 'READY' ORDER BY created_at LIMIT 1",
                (topic,),
            ).fetchone()
            if row is None:
                return None
            connection.execute(
                "UPDATE messages SET status = 'INFLIGHT', updated_at = ? WHERE message_id = ?",
                (utc_now(), row["message_id"]),
            )
        return self.message(row["message_id"])

    def ack(self, message_id: str) -> dict[str, Any]:
        with self.connection() as connection:
            connection.execute(
                "UPDATE messages SET status = 'ACKED', updated_at = ? WHERE message_id = ?",
                (utc_now(), message_id),
            )
        return self.message(message_id)

    def fail(self, message_id: str) -> dict[str, Any]:
        message = self.message(message_id)
        attempts = int(message["attempts"]) + 1
        status = "DLQ" if attempts >= int(message["max_attempts"]) else "READY"
        with self.connection() as connection:
            connection.execute(
                "UPDATE messages SET attempts = ?, status = ?, updated_at = ? WHERE message_id = ?",
                (attempts, status, utc_now(), message_id),
            )
        return self.message(message_id)

    def publish_policy(self, name: str, version: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self.connection() as connection:
            connection.execute("UPDATE policies SET active = 0 WHERE name = ?", (name,))
            connection.execute(
                "INSERT INTO policies VALUES (?, ?, ?, 1, ?)",
                (name, version, encode(payload), utc_now()),
            )
        return self.active_policy(name)

    def active_policy(self, name: str) -> dict[str, Any]:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT * FROM policies WHERE name = ? AND active = 1", (name,)
            ).fetchone()
        if row is None:
            raise KeyError(name)
        return {"name": row["name"], "version": row["version"], "payload": decode(row["payload_json"])}

    def rollback_policy(self, name: str, version: str) -> dict[str, Any]:
        with self.connection() as connection:
            target = connection.execute(
                "SELECT 1 FROM policies WHERE name = ? AND version = ?", (name, version)
            ).fetchone()
            if target is None:
                raise KeyError((name, version))
            connection.execute("UPDATE policies SET active = 0 WHERE name = ?", (name,))
            connection.execute(
                "UPDATE policies SET active = 1 WHERE name = ? AND version = ?", (name, version)
            )
        return self.active_policy(name)

    def save_otlp(self, trace_id: str, payload: dict[str, Any], span_count: int) -> None:
        with self.connection() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO trace_exports VALUES (?, ?, ?, ?)",
                (trace_id, encode(payload), span_count, utc_now()),
            )


class LocalToolGateway:
    def __init__(self, token: str = "chronosfix-readonly-demo", limit: int = 3) -> None:
        self.token = token
        self.limit = limit
        self.calls: dict[str, int] = {}

    def invoke(self, operation: str, *, token: str, trace_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        if token != self.token:
            return {"status": 401, "decision": "unauthorized", "trace_id": trace_id}
        if operation not in {"GetIndex", "GetLogsV2"}:
            return {"status": 403, "decision": "operation-denied", "trace_id": trace_id}
        count = self.calls.get(trace_id, 0) + 1
        self.calls[trace_id] = count
        if count > self.limit:
            return {"status": 429, "decision": "rate-limited", "trace_id": trace_id}
        return {
            "status": 200,
            "decision": "routed",
            "route": "local-sls-readonly-adapter",
            "trace_id": trace_id,
            "request_digest": hashlib.sha256(encode(payload).encode()).hexdigest(),
        }


def to_otlp_json(records: list[dict[str, Any]]) -> dict[str, Any]:
    spans = []
    for item in records:
        trace_id = str(item["trace_id"]).replace("-", "")[:32].ljust(32, "0")
        span_id = str(item["span_id"]).replace("-", "")[:16].ljust(16, "0")
        parent = str(item.get("parent_span_id") or "").replace("-", "")[:16]
        spans.append(
            {
                "traceId": trace_id,
                "spanId": span_id,
                "parentSpanId": parent,
                "name": f"{item.get('agent')}.{item.get('skill')}",
                "kind": 1,
                "startTimeUnixNano": "0",
                "endTimeUnixNano": str(max(1, int(float(item.get("duration_ms", 0)) * 1_000_000))),
                "attributes": [
                    {"key": "chronosfix.run_id", "value": {"stringValue": str(item.get("run_id"))}},
                    {"key": "chronosfix.status", "value": {"stringValue": str(item.get("status"))}},
                ],
            }
        )
    return {
        "resourceSpans": [
            {
                "resource": {"attributes": [{"key": "service.name", "value": {"stringValue": "chronosfix"}}]},
                "scopeSpans": [{"scope": {"name": "chronosfix.otlp-exporter"}, "spans": spans}],
            }
        ]
    }


def infra_boundaries() -> dict[str, Any]:
    return {
        "local_sqlite_unified_model_executed": True,
        "local_durable_event_bus_executed": True,
        "local_version_registry_executed": True,
        "local_tool_gateway_executed": True,
        "local_otlp_export_executed": True,
        "rocketmq_broker_executed": False,
        "polardb_endpoint_executed": False,
        "nacos_server_executed": False,
        "higress_gateway_executed": False,
        "agentloop_or_agentscope_studio_imported": False,
    }
