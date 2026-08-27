"""Deterministic event-driven coordination kernel.

The production target is AgentTeams Matrix.  This module keeps the same
contracts locally so the semifinal package can demonstrate dynamic task
routing without pretending that a Controller is running.  It deliberately
has no network or background threads: every dispatch, retry and state change
is persisted as an event and can be replayed in tests.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Callable


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _canonical(value: Any) -> str:
    return json.dumps(_jsonable(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class WorkerSpec:
    name: str
    capabilities: tuple[str, ...]
    priority: int = 100


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    skill: str
    capability: str
    depends_on: tuple[str, ...] = ()
    priority: int = 100
    max_attempts: int = 2
    timeout_ms: int = 5000


@dataclass
class TaskAttempt:
    task_id: str
    attempt: int
    worker: str
    status: str
    idempotency_key: str
    started_at: str
    ended_at: str | None = None
    duration_ms: float | None = None
    error: str | None = None
    reassigned_from: str | None = None


@dataclass
class OrchestrationEvent:
    sequence: int
    event_id: str
    event_type: str
    timestamp: str
    revision: int
    task_id: str | None = None
    worker: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    deduplicated: bool = False


@dataclass
class SharedIncidentState:
    incident_id: str
    revision: int = 0
    status: str = "RUNNING"
    checkpoint_revision: int | None = None
    values: dict[str, Any] = field(default_factory=dict)


class DynamicScheduler:
    """A small task scheduler with leases, retries, failover and checkpoints."""

    def __init__(
        self,
        incident_id: str,
        *,
        workers: list[WorkerSpec] | None = None,
        failure_plan: dict[str, int] | None = None,
        on_event: Callable[[OrchestrationEvent], None] | None = None,
    ) -> None:
        self.shared = SharedIncidentState(incident_id)
        self.workers = sorted(
            workers
            or [
                WorkerSpec("timeline-analyst-01", ("timeline",)),
                WorkerSpec("timeline-analyst-02", ("timeline",), priority=110),
                WorkerSpec("hypothesis-scientist-01", ("hypothesis",)),
                WorkerSpec("universe-builder-01", ("replay", "fault-genome")),
                WorkerSpec("patch-engineer-01", ("patch-contract",)),
                WorkerSpec("patch-engineer-02", ("patch-contract",), priority=110),
                WorkerSpec("adversarial-verifier-01", ("patch-tournament",)),
                WorkerSpec("release-auditor-01", ("risk-gate", "evidence")),
                WorkerSpec("skill-curator-01", ("skill",)),
            ],
            key=lambda item: (item.priority, item.name),
        )
        self.failure_plan = dict(failure_plan or {})
        self.on_event = on_event
        self.tasks: dict[str, TaskSpec] = {}
        self.handlers: dict[str, Callable[[], Any]] = {}
        self.task_status: dict[str, str] = {}
        self.attempts: list[TaskAttempt] = []
        self.events: list[OrchestrationEvent] = []
        self.results: dict[str, Any] = {}
        self._seen_event_ids: set[str] = set()
        self._seen_idempotency: dict[str, Any] = {}
        self._last_idempotency: dict[str, str] = {}
        self._replay_tasks: set[str] = set()
        self._sequence = 0

    def _emit(
        self,
        event_type: str,
        *,
        task_id: str | None = None,
        worker: str | None = None,
        payload: dict[str, Any] | None = None,
        event_id: str | None = None,
        deduplicated: bool = False,
        advance_revision: bool = True,
    ) -> OrchestrationEvent:
        if advance_revision and not deduplicated:
            self.shared.revision += 1
        self._sequence += 1
        event = OrchestrationEvent(
            sequence=self._sequence,
            event_id=event_id or f"evt-{self._sequence:04d}",
            event_type=event_type,
            timestamp=_now(),
            revision=self.shared.revision,
            task_id=task_id,
            worker=worker,
            payload=payload or {},
            deduplicated=deduplicated,
        )
        self.events.append(event)
        if self.on_event:
            self.on_event(event)
        return event

    def register(self, spec: TaskSpec, handler: Callable[[], Any]) -> None:
        if spec.task_id in self.tasks:
            raise ValueError(f"task already registered: {spec.task_id}")
        self.tasks[spec.task_id] = spec
        self.handlers[spec.task_id] = handler
        self.task_status[spec.task_id] = "PENDING"
        self._emit(
            "task_registered",
            task_id=spec.task_id,
            payload={
                "skill": spec.skill,
                "capability": spec.capability,
                "depends_on": list(spec.depends_on),
                "priority": spec.priority,
                "max_attempts": spec.max_attempts,
            },
        )

    def cancel(self, task_id: str, reason: str) -> None:
        if task_id not in self.tasks or self.task_status.get(task_id) in {"COMPLETED", "CANCELLED"}:
            return
        self.task_status[task_id] = "CANCELLED"
        self._emit("task_cancelled", task_id=task_id, payload={"reason": reason})

    def update_state(self, key: str, value: Any, *, source: str = "scheduler") -> None:
        self.shared.values[key] = value
        self._emit("state_updated", payload={"key": key, "value": value, "source": source})

    def ingest_evidence(self, event_id: str, payload: dict[str, Any]) -> bool:
        if event_id in self._seen_event_ids:
            self._emit(
                "evidence_deduplicated",
                payload={"source_event_id": event_id},
                event_id=f"dedup-{event_id}",
                deduplicated=True,
                advance_revision=False,
            )
            return False
        self._seen_event_ids.add(event_id)
        self._emit("evidence_observed", payload={"source_event_id": event_id, **payload}, event_id=event_id)
        return True

    def pause(self, reason: str) -> int:
        self.shared.status = "PAUSED_AWAITING_HUMAN"
        self.shared.checkpoint_revision = self.shared.revision
        self._emit(
            "human_pause",
            payload={"reason": reason, "checkpoint_revision": self.shared.checkpoint_revision},
        )
        return self.shared.checkpoint_revision

    def resume(self, approval_revision: int | None, *, actor: str = "human") -> bool:
        expected = self.shared.checkpoint_revision
        if self.shared.status != "PAUSED_AWAITING_HUMAN":
            return self.shared.status == "RUNNING"
        if approval_revision != self.shared.revision:
            self._emit(
                "approval_invalidated",
                payload={
                    "actor": actor,
                    "approved_revision": approval_revision,
                    "current_revision": self.shared.revision,
                    "checkpoint_revision": expected,
                },
            )
            return False
        self.shared.status = "RUNNING"
        self._emit("human_resume", payload={"actor": actor, "resumed_revision": self.shared.revision})
        return True

    def _ready(self) -> list[TaskSpec]:
        ready: list[TaskSpec] = []
        for task_id, spec in self.tasks.items():
            if self.task_status.get(task_id) != "PENDING":
                continue
            dependencies = [self.task_status.get(item) for item in spec.depends_on]
            if any(status == "FAILED" for status in dependencies):
                self.cancel(task_id, "dependency-failed")
                continue
            if all(status == "COMPLETED" for status in dependencies):
                ready.append(spec)
        return sorted(ready, key=lambda item: (item.priority, item.task_id))

    def _worker_for(self, spec: TaskSpec, attempt: int) -> WorkerSpec | None:
        candidates = [item for item in self.workers if spec.capability in item.capabilities]
        if not candidates:
            return None
        return candidates[min(attempt - 1, len(candidates) - 1)]

    def _run_task(self, spec: TaskSpec) -> None:
        self.task_status[spec.task_id] = "RUNNING"
        for attempt_no in range(1, spec.max_attempts + 1):
            worker = self._worker_for(spec, attempt_no)
            if worker is None:
                self.task_status[spec.task_id] = "FAILED"
                self._emit("task_escalated", task_id=spec.task_id, payload={"reason": "no-capable-worker"})
                return
            input_revision = self.shared.revision
            idempotency_key = self._last_idempotency.get(spec.task_id)
            if spec.task_id not in self._replay_tasks or idempotency_key is None:
                idempotency_key = _digest(
                    {
                        "incident_id": self.shared.incident_id,
                        "task_type": spec.skill,
                        "task_id": spec.task_id,
                        "input_revision": input_revision,
                    }
                )
            self._replay_tasks.discard(spec.task_id)
            if idempotency_key in self._seen_idempotency:
                self.results[spec.task_id] = self._seen_idempotency[idempotency_key]
                self.task_status[spec.task_id] = "COMPLETED"
                self._emit(
                    "task_deduplicated",
                    task_id=spec.task_id,
                    worker=worker.name,
                    payload={
                        "idempotency_key": idempotency_key,
                        "input_revision": input_revision,
                        "result_digest": _digest(self.results[spec.task_id]),
                    },
                    deduplicated=True,
                    advance_revision=False,
                )
                return

            previous_worker = self.attempts[-1].worker if self.attempts else None
            started = _now()
            attempt = TaskAttempt(
                task_id=spec.task_id,
                attempt=attempt_no,
                worker=worker.name,
                status="RUNNING",
                idempotency_key=idempotency_key,
                started_at=started,
                reassigned_from=previous_worker if attempt_no > 1 else None,
            )
            self.attempts.append(attempt)
            self._emit(
                "task_dispatched",
                task_id=spec.task_id,
                worker=worker.name,
                payload={
                    "attempt": attempt_no,
                    "lease_ms": spec.timeout_ms,
                    "idempotency_key": idempotency_key,
                    "reassigned_from": attempt.reassigned_from,
                },
            )
            inject_failure = self.failure_plan.get(spec.task_id, 0) >= attempt_no
            try:
                if inject_failure:
                    raise TimeoutError(f"injected worker timeout for {spec.task_id}")
                result = self.handlers[spec.task_id]()
            except Exception as exc:  # fail closed, then retry on the next worker
                attempt.status = "FAILED"
                attempt.ended_at = _now()
                attempt.error = f"{type(exc).__name__}: {exc}"
                self._emit(
                    "task_failed",
                    task_id=spec.task_id,
                    worker=worker.name,
                    payload={"attempt": attempt_no, "error": attempt.error},
                )
                if attempt_no < spec.max_attempts:
                    self._emit(
                        "task_reassigned",
                        task_id=spec.task_id,
                        worker=self._worker_for(spec, attempt_no + 1).name
                        if self._worker_for(spec, attempt_no + 1)
                        else None,
                        payload={"failed_worker": worker.name, "next_attempt": attempt_no + 1},
                    )
                    continue
                self.task_status[spec.task_id] = "FAILED"
                self._emit(
                    "task_escalated",
                    task_id=spec.task_id,
                    worker=worker.name,
                    payload={"attempts": attempt_no, "reason": "retry-exhausted"},
                )
                return
            attempt.status = "COMPLETED"
            attempt.ended_at = _now()
            self.results[spec.task_id] = result
            self._seen_idempotency[idempotency_key] = result
            self._last_idempotency[spec.task_id] = idempotency_key
            self.task_status[spec.task_id] = "COMPLETED"
            result_digest = _digest(result)
            self.update_state(
                spec.task_id,
                {
                    "status": "COMPLETED",
                    "worker": worker.name,
                    "attempt": attempt_no,
                    "result_digest": result_digest,
                },
                source=worker.name,
            )
            self._emit(
                "task_completed",
                task_id=spec.task_id,
                worker=worker.name,
                payload={
                    "attempt": attempt_no,
                    "idempotency_key": idempotency_key,
                    "result_digest": result_digest,
                },
            )
            return

    def run(self) -> None:
        while self.shared.status == "RUNNING":
            ready = self._ready()
            if not ready:
                pending = [key for key, status in self.task_status.items() if status == "PENDING"]
                if pending:
                    self.shared.status = "BLOCKED"
                    self._emit("scheduler_blocked", payload={"pending_tasks": pending})
                else:
                    self.shared.status = "COMPLETED"
                    self._emit("scheduler_completed", payload={"completed_tasks": len(self.results)})
                return
            for spec in ready:
                if self.shared.status != "RUNNING":
                    return
                self._run_task(spec)

    def replay(self, task_id: str) -> None:
        """Replay a task with the same state revision to prove idempotency.

        Matrix redeliveries can happen after a worker acknowledgement is lost.
        Replaying at the same revision must return the durable result without
        invoking the handler or creating an external side effect.
        """
        if task_id not in self.tasks:
            raise KeyError(task_id)
        self.task_status[task_id] = "PENDING"
        self._replay_tasks.add(task_id)
        self._run_task(self.tasks[task_id])

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "chronosfix.dynamic-coordination/v1",
            "incident_id": self.shared.incident_id,
            "status": self.shared.status,
            "revision": self.shared.revision,
            "checkpoint_revision": self.shared.checkpoint_revision,
            "shared_state": self.shared.values,
            "tasks": [
                {
                    **asdict(spec),
                    "depends_on": list(spec.depends_on),
                    "status": self.task_status.get(spec.task_id),
                }
                for spec in self.tasks.values()
            ],
            "attempts": [asdict(item) for item in self.attempts],
            "events": [asdict(item) for item in self.events],
            "idempotency_records": len(self._seen_idempotency),
        }
