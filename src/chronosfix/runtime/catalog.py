from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkerInstance:
    logical_worker: str
    instance_id: str
    capabilities: tuple[str, ...]
    priority: int = 100


WORKER_INSTANCES = (
    WorkerInstance("chronosfix-incident-commander", "chronosfix-incident-commander#01", ("incident-control",)),
    WorkerInstance("chronosfix-timeline-analyst", "chronosfix-timeline-analyst#01", ("timeline", "evidence")),
    WorkerInstance("chronosfix-timeline-analyst", "chronosfix-timeline-analyst#02", ("timeline", "evidence"), 110),
    WorkerInstance("chronosfix-hypothesis-scientist", "chronosfix-hypothesis-scientist#01", ("hypothesis",)),
    WorkerInstance("chronosfix-hypothesis-scientist", "chronosfix-hypothesis-scientist#02", ("hypothesis",), 110),
    WorkerInstance("chronosfix-universe-builder", "chronosfix-universe-builder#01", ("replay", "fault-genome")),
    WorkerInstance("chronosfix-patch-engineer", "chronosfix-patch-engineer#01", ("patch-contract",)),
    WorkerInstance("chronosfix-adversarial-verifier", "chronosfix-adversarial-verifier#01", ("patch-tournament",)),
    WorkerInstance("chronosfix-adversarial-verifier", "chronosfix-adversarial-verifier#02", ("patch-tournament",), 110),
    WorkerInstance("chronosfix-release-auditor", "chronosfix-release-auditor#01", ("risk-gate", "attestation")),
    WorkerInstance("chronosfix-skill-curator", "chronosfix-skill-curator#01", ("skill",)),
)

LOGICAL_WORKERS = tuple(dict.fromkeys(item.logical_worker for item in WORKER_INSTANCES))


def capable_instances(capability: str) -> list[WorkerInstance]:
    return sorted(
        (item for item in WORKER_INSTANCES if capability in item.capabilities),
        key=lambda item: (item.priority, item.instance_id),
    )
