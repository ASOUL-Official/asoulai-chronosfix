from __future__ import annotations

from datetime import datetime, timezone
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def encode(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def decode(value: str | None, default: Any) -> Any:
    return default if value is None else json.loads(value)


class RuntimeStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def connection(self):
        connection = self.connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self.connection() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode = WAL;
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    trace_id TEXT NOT NULL,
                    scenario_id TEXT NOT NULL,
                    scenario_path TEXT NOT NULL,
                    status TEXT NOT NULL,
                    quality_gate TEXT NOT NULL,
                    release_decision TEXT NOT NULL,
                    revision INTEGER NOT NULL DEFAULT 0,
                    output_dir TEXT NOT NULL,
                    boundary_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    run_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    event_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    task_id TEXT,
                    worker TEXT,
                    payload_json TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    PRIMARY KEY (run_id, event_id),
                    UNIQUE (run_id, sequence),
                    FOREIGN KEY (run_id) REFERENCES runs(run_id)
                );
                CREATE TABLE IF NOT EXISTS tasks (
                    run_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    skill TEXT NOT NULL,
                    capability TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result_json TEXT,
                    created_revision INTEGER NOT NULL,
                    PRIMARY KEY (run_id, task_id),
                    FOREIGN KEY (run_id) REFERENCES runs(run_id)
                );
                CREATE TABLE IF NOT EXISTS attempts (
                    run_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    attempt INTEGER NOT NULL,
                    logical_worker TEXT NOT NULL,
                    instance_id TEXT NOT NULL,
                    pid INTEGER,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    duration_ms REAL,
                    exit_code INTEGER,
                    error TEXT,
                    result_digest TEXT,
                    PRIMARY KEY (run_id, task_id, attempt),
                    FOREIGN KEY (run_id, task_id) REFERENCES tasks(run_id, task_id)
                );
                CREATE TABLE IF NOT EXISTS evidence (
                    run_id TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    digest TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (run_id, event_id),
                    FOREIGN KEY (run_id) REFERENCES runs(run_id)
                );
                CREATE TABLE IF NOT EXISTS approvals (
                    run_id TEXT NOT NULL,
                    approval_id TEXT NOT NULL,
                    state_revision INTEGER NOT NULL,
                    input_digest TEXT NOT NULL,
                    policy_version TEXT NOT NULL,
                    approver TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    invalidated_at TEXT,
                    PRIMARY KEY (run_id, approval_id),
                    FOREIGN KEY (run_id) REFERENCES runs(run_id)
                );
                """
            )

    def create_run(self, run: dict[str, Any]) -> None:
        now = utc_now()
        with self.connection() as connection:
            connection.execute(
                """INSERT INTO runs
                (run_id, trace_id, scenario_id, scenario_path, status, quality_gate,
                 release_decision, revision, output_dir, boundary_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)""",
                (
                    run["run_id"], run["trace_id"], run["scenario_id"], run["scenario_path"],
                    run["status"], run["quality_gate"], run["release_decision"],
                    run["output_dir"], encode(run["boundary"]), now, now,
                ),
            )

    def get_run(self, run_id: str) -> dict[str, Any]:
        with self.connection() as connection:
            row = connection.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(run_id)
        result = dict(row)
        result["boundary"] = decode(result.pop("boundary_json"), {})
        return result

    def update_run(self, run_id: str, **fields: Any) -> None:
        allowed = {"status", "quality_gate", "release_decision", "trace_id", "boundary_json"}
        unknown = set(fields) - allowed
        if unknown:
            raise ValueError(f"unsupported run fields: {sorted(unknown)}")
        if "boundary_json" in fields and not isinstance(fields["boundary_json"], str):
            fields["boundary_json"] = encode(fields["boundary_json"])
        fields["updated_at"] = utc_now()
        assignments = ", ".join(f"{key} = ?" for key in fields)
        with self.connection() as connection:
            connection.execute(
                f"UPDATE runs SET {assignments} WHERE run_id = ?",
                (*fields.values(), run_id),
            )

    def append_event(
        self,
        run_id: str,
        event_type: str,
        *,
        event_id: str,
        task_id: str | None = None,
        worker: str | None = None,
        payload: dict[str, Any] | None = None,
        advance_revision: bool = True,
        invalidate_approval: bool = False,
    ) -> tuple[dict[str, Any], int]:
        with self.connection() as connection:
            run = connection.execute("SELECT revision FROM runs WHERE run_id = ?", (run_id,)).fetchone()
            if run is None:
                raise KeyError(run_id)
            revision = int(run["revision"]) + (1 if advance_revision else 0)
            sequence_row = connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) + 1 AS next_sequence FROM events WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            sequence = int(sequence_row["next_sequence"])
            timestamp = utc_now()
            connection.execute(
                "UPDATE runs SET revision = ?, updated_at = ? WHERE run_id = ?",
                (revision, timestamp, run_id),
            )
            stale_count = 0
            if invalidate_approval:
                cursor = connection.execute(
                    """UPDATE approvals SET status = 'STALE', invalidated_at = ?
                    WHERE run_id = ? AND status = 'APPROVED'""",
                    (timestamp, run_id),
                )
                stale_count = cursor.rowcount
            event = {
                "sequence": sequence,
                "event_id": event_id,
                "event_type": event_type,
                "timestamp": timestamp,
                "revision": revision,
                "task_id": task_id,
                "worker": worker,
                "payload": payload or {},
            }
            connection.execute(
                """INSERT INTO events
                (run_id, sequence, event_id, event_type, revision, task_id, worker, payload_json, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (run_id, sequence, event_id, event_type, revision, task_id, worker, encode(payload or {}), timestamp),
            )
        return event, stale_count

    def register_task(self, run_id: str, task_id: str, skill: str, capability: str) -> None:
        revision = self.get_run(run_id)["revision"]
        with self.connection() as connection:
            connection.execute(
                """INSERT INTO tasks (run_id, task_id, skill, capability, status, result_json, created_revision)
                VALUES (?, ?, ?, ?, 'PENDING', NULL, ?)
                ON CONFLICT(run_id, task_id) DO UPDATE SET skill=excluded.skill, capability=excluded.capability""",
                (run_id, task_id, skill, capability, revision),
            )

    def update_task(self, run_id: str, task_id: str, status: str, result: Any = None) -> None:
        with self.connection() as connection:
            connection.execute(
                "UPDATE tasks SET status = ?, result_json = ? WHERE run_id = ? AND task_id = ?",
                (status, None if result is None else encode(result), run_id, task_id),
            )

    def upsert_attempt(self, attempt: dict[str, Any]) -> None:
        columns = (
            "run_id", "task_id", "attempt", "logical_worker", "instance_id", "pid", "status",
            "started_at", "ended_at", "duration_ms", "exit_code", "error", "result_digest",
        )
        values = tuple(attempt.get(key) for key in columns)
        with self.connection() as connection:
            connection.execute(
                f"""INSERT INTO attempts ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})
                ON CONFLICT(run_id, task_id, attempt) DO UPDATE SET
                pid=excluded.pid, status=excluded.status, ended_at=excluded.ended_at,
                duration_ms=excluded.duration_ms, exit_code=excluded.exit_code,
                error=excluded.error, result_digest=excluded.result_digest""",
                values,
            )

    def add_evidence(self, run_id: str, event_id: str, kind: str, payload: dict[str, Any], digest: str) -> bool:
        try:
            with self.connection() as connection:
                connection.execute(
                    "INSERT INTO evidence VALUES (?, ?, ?, ?, ?, ?)",
                    (run_id, event_id, kind, encode(payload), digest, utc_now()),
                )
            return True
        except sqlite3.IntegrityError:
            return False

    def add_approval(self, approval: dict[str, Any]) -> None:
        with self.connection() as connection:
            connection.execute(
                "UPDATE approvals SET status = 'SUPERSEDED' WHERE run_id = ? AND status = 'APPROVED'",
                (approval["run_id"],),
            )
            connection.execute(
                """INSERT INTO approvals
                (run_id, approval_id, state_revision, input_digest, policy_version, approver, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'APPROVED', ?)""",
                (
                    approval["run_id"], approval["approval_id"], approval["state_revision"],
                    approval["input_digest"], approval["policy_version"], approval["approver"], utc_now(),
                ),
            )

    def snapshot(self, run_id: str) -> dict[str, Any]:
        run = self.get_run(run_id)
        with self.connection() as connection:
            events = [dict(row) for row in connection.execute(
                "SELECT * FROM events WHERE run_id = ? ORDER BY sequence", (run_id,)
            )]
            tasks = [dict(row) for row in connection.execute(
                "SELECT * FROM tasks WHERE run_id = ? ORDER BY created_revision, task_id", (run_id,)
            )]
            attempts = [dict(row) for row in connection.execute(
                "SELECT * FROM attempts WHERE run_id = ? ORDER BY task_id, attempt", (run_id,)
            )]
            evidence = [dict(row) for row in connection.execute(
                "SELECT * FROM evidence WHERE run_id = ? ORDER BY created_at", (run_id,)
            )]
            approvals = [dict(row) for row in connection.execute(
                "SELECT * FROM approvals WHERE run_id = ? ORDER BY created_at", (run_id,)
            )]
        for item in events:
            item["payload"] = decode(item.pop("payload_json"), {})
            item.pop("run_id", None)
        for item in tasks:
            item["result"] = decode(item.pop("result_json"), None)
            item.pop("run_id", None)
        for item in evidence:
            item["payload"] = decode(item.pop("payload_json"), {})
            item.pop("run_id", None)
        for collection in (attempts, approvals):
            for item in collection:
                item.pop("run_id", None)
        return {
            "run": run,
            "events": events,
            "tasks": tasks,
            "attempts": attempts,
            "evidence": evidence,
            "approvals": approvals,
        }
