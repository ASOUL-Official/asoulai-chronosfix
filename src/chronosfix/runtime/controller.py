from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any
import uuid

from .catalog import LOGICAL_WORKERS, WorkerInstance, capable_instances
from .recommender import compile_agent_dag, recommend_agent_composition
from .store import RuntimeStore, utc_now


ROOT = Path(__file__).resolve().parents[3]
POLICY_VERSION = "chronosfix-local-riskgate/v1"


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


class StaleApprovalError(ValueError):
    pass


class LocalController:
    def __init__(
        self,
        database: Path | None = None,
        output_root: Path | None = None,
        *,
        python_executable: str | None = None,
    ) -> None:
        self.database = database or ROOT / "output" / "local-controller" / "matrix.sqlite3"
        self.output_root = output_root or ROOT / "output" / "local-controller" / "runs"
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.store = RuntimeStore(self.database)
        self.python = python_executable or sys.executable

    def _event_id(self, event_type: str) -> str:
        return f"{event_type}-{uuid.uuid4().hex[:16]}"

    def scenarios(self) -> list[dict[str, Any]]:
        result = []
        for path in sorted((ROOT / "scenarios").rglob("scenario.json")):
            raw = json.loads(path.read_text(encoding="utf-8"))
            ground_truth = raw.get("ground_truth") or {}
            if not ground_truth:
                continue
            result.append(
                {
                    "scenario_id": path.parent.name,
                    "title": raw.get("title", path.parent.name),
                    "incident_id": raw.get("incident_id"),
                    "case_type": ground_truth.get("case_type"),
                    "expected_outcome": ground_truth.get("expected_outcome"),
                    "fixture_scope": ground_truth.get("fixture_scope"),
                }
            )
        return result

    def scenario_path(self, scenario_id: str) -> Path:
        matches = [item for item in (ROOT / "scenarios").rglob("scenario.json") if item.parent.name == scenario_id]
        if len(matches) != 1:
            raise ValueError(f"unknown or ambiguous scenario: {scenario_id}")
        return matches[0]

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "runtime": "chronosfix-local-controller/v1",
            "database": str(self.database),
            "logical_workers": list(LOGICAL_WORKERS),
            "boundaries": {
                "local_controller_executed": True,
                "local_worker_processes_executed": True,
                "local_matrix_event_log_executed": True,
                "agentteams_official_controller_executed": False,
                "matrix_protocol_executed": False,
            },
        }

    def create_run(self, scenario_id: str, *, auto_approve: bool = True) -> dict[str, Any]:
        scenario = self.scenario_path(scenario_id)
        raw = json.loads(scenario.read_text(encoding="utf-8"))
        ground_truth = raw.get("ground_truth") or {}
        suffix = uuid.uuid4().hex[:10]
        run_id = f"acfx-local-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-{suffix}"
        trace_id = uuid.uuid4().hex
        output_dir = self.output_root / run_id
        output_dir.mkdir(parents=True, exist_ok=True)
        boundary = self.health()["boundaries"]
        self.store.create_run(
            {
                "run_id": run_id,
                "trace_id": trace_id,
                "scenario_id": scenario_id,
                "scenario_path": scenario.relative_to(ROOT).as_posix(),
                "status": "RUNNING",
                "quality_gate": "pending",
                "release_decision": "pending",
                "output_dir": str(output_dir),
                "boundary": boundary,
            }
        )
        self.store.append_event(
            run_id,
            "controller_run_created",
            event_id=self._event_id("run"),
            payload={"scenario_id": scenario_id, "trace_id": trace_id, "boundary": boundary},
        )

        recommendation, dag = self._plan_agent_dag(run_id, raw)
        results = self._execute_agent_dag(run_id, scenario, dag, approved=False)

        if ground_truth.get("fixture_scope") == "evaluation-only-counterfactual":
            result = self.execute_task(
                run_id,
                task_id="counterfactual-evaluation",
                skill="CounterfactualReplay",
                capability="hypothesis",
                job="evaluate",
                scenario=scenario,
                depends_on=[item["task_id"] for item in dag["tasks"][-1:]],
                timeout_seconds=10,
            )
            status = result["evaluation"]["status"]
            if status == "abstain":
                self.store.append_event(
                    run_id,
                    "abstention_recorded",
                    event_id=self._event_id("abstain"),
                    task_id="counterfactual-evaluation",
                    worker="chronosfix-hypothesis-scientist",
                    payload={
                        "reason": result["evaluation"]["boundary_note"],
                        "patch_task_registered": False,
                        "risk_gate_task_registered": False,
                        "pr_task_registered": False,
                    },
                )
                self.store.update_run(
                    run_id,
                    status="ABSTAINED",
                    quality_gate="not-run",
                    release_decision="blocked-insufficient-evidence",
                )
            return self.snapshot(run_id)

        release_task = next(
            (item["task_id"] for item in dag["tasks"] if item["agent"] == "release-auditor"),
            None,
        )
        gate = ((results.get(release_task) or {}).get("result") or {}).get("gate") if release_task else None
        if not gate:
            self.store.update_run(
                run_id,
                status="BLOCKED_INSUFFICIENT_EVIDENCE",
                quality_gate="not-run",
                release_decision="blocked-insufficient-evidence",
            )
            return self.snapshot(run_id)
        self.store.update_run(
            run_id,
            status="PAUSED_AWAITING_HUMAN",
            quality_gate=gate["quality_gate"],
            release_decision=gate["decision"],
        )
        if auto_approve and gate["quality_gate"] == "passed":
            self.approve(run_id, "AsoulAI Release Owner", expected_revision=self.store.get_run(run_id)["revision"])
        return self.snapshot(run_id)

    def _plan_agent_dag(
        self,
        run_id: str,
        scenario: dict[str, Any],
        *,
        evidence: list[dict[str, Any]] | None = None,
        objective: str = "prove-and-repair",
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        recommendation = recommend_agent_composition(
            scenario,
            evidence=evidence or [],
            objective=objective,
        )
        dag = compile_agent_dag(recommendation)
        self.store.append_event(
            run_id,
            "agent_plan_recommended",
            event_id=self._event_id("agent-plan"),
            task_id="agent-manager",
            worker="chronosfix-manager",
            payload={"recommendation": recommendation},
        )
        self.store.append_event(
            run_id,
            "agent_dag_compiled",
            event_id=self._event_id("agent-dag"),
            task_id="agent-manager",
            worker="chronosfix-manager",
            payload={
                "decision_id": dag["decision_id"],
                "task_count": len(dag["tasks"]),
                "tasks": dag["tasks"],
            },
        )
        return recommendation, dag

    def _execute_agent_dag(
        self,
        run_id: str,
        scenario: Path,
        dag: dict[str, Any],
        *,
        approved: bool,
    ) -> dict[str, dict[str, Any]]:
        """Dispatch compiled DAG nodes only after every declared parent completed."""

        existing = {item["task_id"]: item for item in self.snapshot(run_id)["tasks"]}
        results: dict[str, dict[str, Any]] = {
            task_id: item["result"]
            for task_id, item in existing.items()
            if item["status"] == "COMPLETED" and isinstance(item.get("result"), dict)
        }
        for task in dag["tasks"]:
            task_id = task["task_id"]
            previous = existing.get(task_id)
            if previous and previous["status"] == "COMPLETED":
                self.store.append_event(
                    run_id,
                    "agent_dag_task_reused",
                    event_id=self._event_id("agent-dag-reused"),
                    task_id=task_id,
                    worker=task["worker"],
                    payload={"decision_id": dag["decision_id"], "reason": "completed-node-reused"},
                )
                continue
            unmet = [dependency for dependency in task["depends_on"] if dependency not in results]
            if unmet:
                raise RuntimeError(f"DAG dependency not completed for {task_id}: {unmet}")
            result = self.execute_task(
                run_id,
                task_id=task_id,
                skill=task["skill"],
                capability=task["capability"],
                job="agent-step",
                scenario=scenario,
                payload={
                    "run_id": run_id,
                    "agent": task["agent"],
                    "skill": task["skill"],
                    "depends_on": task["depends_on"],
                    "upstream_result_digests": {
                        dependency: digest(results[dependency])
                        for dependency in task["depends_on"]
                    },
                },
                depends_on=task["depends_on"],
                approved=approved,
                timeout_seconds=15,
            )
            results[task_id] = result
            if task["agent"] == "patch-engineer":
                # Persist the tournament summary as a first-class coordination
                # event.  The task result remains the complete replay payload;
                # this compact event makes candidate competition visible in the
                # Matrix feed without requiring consumers to unpack a Worker
                # result blob.
                ranking = ((result.get("result") or {}).get("ranking") or [])
                self.store.append_event(
                    run_id,
                    "patch_tournament_completed",
                    event_id=self._event_id("patch-tournament"),
                    task_id=task_id,
                    worker=task["worker"],
                    payload={
                        "candidate_count": len(ranking),
                        "selected_patch": ((result.get("result") or {}).get("selected_patch") or {}).get("candidate_id"),
                        "competition": "same-fault-genome-suite",
                        "ranking": [
                            {
                                "candidate_id": item.get("candidate_id"),
                                "title": item.get("title"),
                                "total_score": item.get("total_score"),
                                "mean_failure_rate": item.get("mean_failure_rate"),
                                "worst_failure_rate": item.get("worst_failure_rate"),
                                "release_eligible": any(
                                    result_item.get("mandatory", True)
                                    for result_item in item.get("results", [])
                                )
                                and all(
                                    result_item.get("healthy") is True
                                    for result_item in item.get("results", [])
                                    if result_item.get("mandatory", True)
                                ),
                            }
                            for item in ranking
                        ],
                    },
                )
        return results

    @staticmethod
    def _impact_agents(evidence_kind: str | None) -> set[str]:
        """Return the smallest set of Agent roles whose conclusions depend on a signal.

        The mapping is intentionally explicit: an incremental recompute must be
        explainable in the event log, and should never silently turn into a full
        pipeline replay. Descendants are added by ``_affected_task_ids`` below.
        """

        if evidence_kind in {"commit", "dependency", "configuration", "traffic", "incident", "slo"}:
            return {
                "timeline-analyst",
                "hypothesis-scientist",
                "universe-builder",
                "patch-engineer",
                "adversarial-verifier",
                "release-auditor",
            }
        if evidence_kind == "policy":
            return {"release-auditor"}
        if evidence_kind:
            return {"skill-curator"}
        return set()

    def _incremental_recompute(
        self,
        run_id: str,
        dag: dict[str, Any],
        *,
        evidence_kind: str | None,
    ) -> dict[str, Any]:
        """Invalidate and recompute only the affected DAG closure.

        The Manager recommendation is still regenerated so a newly observed
        capability can be inserted. Existing completed nodes outside the
        affected closure remain reusable and are recorded as such.
        """

        if not evidence_kind:
            return {"affected_task_ids": [], "reused_task_ids": [], "evidence_kind": None}
        snapshot = self.snapshot(run_id)
        tasks = {item["task_id"]: item for item in snapshot["tasks"]}
        dag_tasks = {item["task_id"]: item for item in dag["tasks"]}
        impacted_agents = self._impact_agents(evidence_kind)
        candidate_affected = {
            task["task_id"]
            for task in dag["tasks"]
            if task["agent"] in impacted_agents
        }
        changed = True
        while changed:
            changed = False
            for task in dag["tasks"]:
                if task["task_id"] in candidate_affected:
                    continue
                if any(dependency in candidate_affected for dependency in task["depends_on"]):
                    candidate_affected.add(task["task_id"])
                    changed = True
        affected = {task_id for task_id in candidate_affected if task_id in tasks}
        new_task_ids = sorted(candidate_affected - affected)
        dag_task_ids = {task["task_id"] for task in dag["tasks"]}
        reused = {
            task_id
            for task_id, task in tasks.items()
            if task_id in dag_task_ids and task["status"] == "COMPLETED" and task_id not in affected
        }
        self.store.append_event(
            run_id,
            "incremental_recompute_started",
            event_id=self._event_id("incremental-recompute"),
            task_id="agent-manager",
            worker="chronosfix-manager",
            payload={
                "evidence_kind": evidence_kind,
                "impacted_agents": sorted(impacted_agents),
                "affected_task_ids": sorted(affected),
                "new_task_ids": new_task_ids,
                "reused_task_ids": sorted(reused),
                "mode": "incremental-causal-recompute",
            },
        )
        for task_id in sorted(affected):
            task = tasks.get(task_id)
            if not task or task["status"] != "COMPLETED":
                continue
            self.store.update_task(run_id, task_id, "INVALIDATED")
            self.store.append_event(
                run_id,
                "task_invalidated",
                event_id=self._event_id("task-invalidated"),
                task_id=task_id,
                worker=dag_tasks.get(task_id, {}).get("worker"),
                payload={
                    "reason": "new-evidence-affects-upstream-causal-input",
                    "evidence_kind": evidence_kind,
                    "recompute_scope": "incremental",
                },
            )
        return {
            "affected_task_ids": sorted(affected),
            "new_task_ids": new_task_ids,
            "reused_task_ids": sorted(reused),
            "evidence_kind": evidence_kind,
        }

    def _command(
        self,
        *,
        job: str,
        scenario: Path | None,
        output: Path | None,
        mode: str,
        payload: dict[str, Any] | None,
        approved: bool,
    ) -> list[str]:
        command = [self.python, "-m", "chronosfix.runtime.worker_main", "--job", job, "--mode", mode]
        if scenario is not None:
            command.extend(["--scenario", str(scenario)])
        if output is not None:
            command.extend(["--output", str(output)])
        if payload is not None:
            command.extend(["--payload-json", canonical(payload)])
        if approved:
            command.extend(["--approve", "--approver", "AsoulAI Local Controller"])
        return command

    def execute_task(
        self,
        run_id: str,
        *,
        task_id: str,
        skill: str,
        capability: str,
        job: str,
        scenario: Path | None = None,
        output: Path | None = None,
        payload: dict[str, Any] | None = None,
        first_mode: str = "normal",
        retry_mode: str = "normal",
        timeout_seconds: float = 10,
        approved: bool = False,
        accepted_exit_codes: tuple[int, ...] = (0,),
        depends_on: list[str] | tuple[str, ...] = (),
    ) -> dict[str, Any]:
        instances = capable_instances(capability)
        if not instances:
            raise RuntimeError(f"no local worker instance for capability {capability}")
        self.store.register_task(run_id, task_id, skill, capability, depends_on=depends_on)
        self.store.append_event(
            run_id,
            "task_registered",
            event_id=self._event_id("task-registered"),
            task_id=task_id,
            payload={
                "skill": skill,
                "capability": capability,
                "depends_on": list(depends_on),
                "max_attempts": min(2, len(instances)),
            },
        )
        modes = (first_mode, retry_mode)
        last_error = "unknown worker failure"
        attempt_base = self.store.next_attempt_number(run_id, task_id)
        for attempt_offset, instance in enumerate(instances[:2]):
            attempt_number = attempt_base + attempt_offset
            mode = modes[min(attempt_offset, len(modes) - 1)]
            command = self._command(
                job=job,
                scenario=scenario,
                output=output,
                mode=mode,
                payload=payload,
                approved=approved,
            )
            started_at = utc_now()
            started = time.perf_counter()
            process = subprocess.Popen(
                command,
                cwd=ROOT,
                env={
                    **os.environ,
                    "PYTHONPATH": str(ROOT / "src")
                    + (os.pathsep + os.environ["PYTHONPATH"] if os.environ.get("PYTHONPATH") else ""),
                    "PYTHONIOENCODING": "utf-8",
                },
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            attempt = {
                "run_id": run_id,
                "task_id": task_id,
                "attempt": attempt_number,
                "logical_worker": instance.logical_worker,
                "instance_id": instance.instance_id,
                "pid": process.pid,
                "status": "RUNNING",
                "started_at": started_at,
                "ended_at": None,
                "duration_ms": None,
                "exit_code": None,
                "error": None,
                "result_digest": None,
            }
            self.store.upsert_attempt(attempt)
            self.store.append_event(
                run_id,
                "task_dispatched",
                event_id=self._event_id("dispatch"),
                task_id=task_id,
                worker=instance.instance_id,
                payload={"attempt": attempt_number, "pid": process.pid, "lease_ms": int(timeout_seconds * 1000)},
            )
            try:
                attempt_timeout = timeout_seconds if attempt_number == 1 else max(timeout_seconds, 3)
                stdout, stderr = process.communicate(timeout=attempt_timeout)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    stdout, stderr = process.communicate(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    stdout, stderr = process.communicate()
                last_error = f"lease expired after {timeout_seconds:.3f}s"
                attempt.update(
                    status="FAILED",
                    ended_at=utc_now(),
                    duration_ms=round((time.perf_counter() - started) * 1000, 3),
                    exit_code=process.returncode,
                    error=last_error,
                )
                self.store.upsert_attempt(attempt)
                self.store.append_event(
                    run_id,
                    "lease_expired",
                    event_id=self._event_id("lease"),
                    task_id=task_id,
                    worker=instance.instance_id,
                    payload={"attempt": attempt_number, "pid": process.pid, "error": last_error},
                )
            else:
                if process.returncode in accepted_exit_codes:
                    lines = [line for line in stdout.splitlines() if line.strip()]
                    result = json.loads(lines[-1]) if lines else {}
                    result_digest = digest(result)
                    attempt.update(
                        status="COMPLETED",
                        ended_at=utc_now(),
                        duration_ms=round((time.perf_counter() - started) * 1000, 3),
                        exit_code=process.returncode,
                        result_digest=result_digest,
                    )
                    self.store.upsert_attempt(attempt)
                    self.store.update_task(run_id, task_id, "COMPLETED", result)
                    self.store.append_event(
                        run_id,
                        "task_completed",
                        event_id=self._event_id("task-completed"),
                        task_id=task_id,
                        worker=instance.instance_id,
                        payload={
                            "attempt": attempt_number,
                            "pid": process.pid,
                            "duration_ms": attempt["duration_ms"],
                            "result_digest": result_digest,
                        },
                    )
                    return result
                last_error = (stderr or stdout or f"worker exited {process.returncode}")[-1200:]
                attempt.update(
                    status="FAILED",
                    ended_at=utc_now(),
                    duration_ms=round((time.perf_counter() - started) * 1000, 3),
                    exit_code=process.returncode,
                    error=last_error,
                )
                self.store.upsert_attempt(attempt)
                self.store.append_event(
                    run_id,
                    "worker_exited",
                    event_id=self._event_id("worker-exit"),
                    task_id=task_id,
                    worker=instance.instance_id,
                    payload={"attempt": attempt_number, "pid": process.pid, "exit_code": process.returncode},
                )

            self.store.append_event(
                run_id,
                "task_failed",
                event_id=self._event_id("task-failed"),
                task_id=task_id,
                worker=instance.instance_id,
                payload={"attempt": attempt_number, "error": last_error},
            )
            if attempt_offset + 1 < min(2, len(instances)):
                next_instance = instances[attempt_offset + 1]
                self.store.append_event(
                    run_id,
                    "task_reassigned",
                    event_id=self._event_id("reassign"),
                    task_id=task_id,
                    worker=next_instance.instance_id,
                    payload={"failed_worker": instance.instance_id, "next_attempt": attempt_number + 1},
                )

        self.store.update_task(run_id, task_id, "FAILED")
        self.store.update_run(run_id, status="BLOCKED_RETRY_EXHAUSTED", quality_gate="failed", release_decision="blocked-quality")
        self.store.append_event(
            run_id,
            "retry_exhausted",
            event_id=self._event_id("retry-exhausted"),
            task_id=task_id,
            payload={"error": last_error},
        )
        raise RuntimeError(last_error)

    def trigger_failover(self, run_id: str, failure: str) -> dict[str, Any]:
        if failure not in {"timeout", "crash"}:
            raise ValueError(failure)
        task_id = f"live-{failure}-{uuid.uuid4().hex[:8]}"
        self.execute_task(
            run_id,
            task_id=task_id,
            skill="LiveWorkerFailoverProbe",
            capability="timeline" if failure == "timeout" else "hypothesis",
            job="probe",
            first_mode=failure,
            retry_mode="normal",
            timeout_seconds=0.25 if failure == "timeout" else 5,
        )
        return self.snapshot(run_id)

    def ingest_evidence(self, run_id: str, event_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        evidence_digest = digest(payload)
        if not self.store.add_evidence(run_id, event_id, str(payload.get("kind", "unknown")), payload, evidence_digest):
            self.store.append_event(
                run_id,
                "evidence_deduplicated",
                event_id=self._event_id("evidence-dedup"),
                payload={"source_event_id": event_id, "digest": evidence_digest},
                advance_revision=False,
            )
            return self.snapshot(run_id)
        event, stale_count = self.store.append_event(
            run_id,
            "evidence_observed",
            event_id=event_id,
            payload={**payload, "digest": evidence_digest},
            invalidate_approval=True,
        )
        if stale_count:
            self.store.update_run(run_id, status="PAUSED_AWAITING_HUMAN", release_decision="blocked-awaiting-human")
            self.store.append_event(
                run_id,
                "approval_invalidated",
                event_id=self._event_id("approval-invalidated"),
                task_id="risk-gate",
                worker="chronosfix-release-auditor#01",
                payload={"source_event_id": event_id, "current_revision": event["revision"], "stale_approvals": stale_count},
            )
        # Evidence ingestion is a control-plane boundary: re-plan immediately
        # so any newly required Skill becomes a real Manager-compiled DAG node.
        # Do not append a legacy fixed audit task beside the DAG.
        return self.recommend(
            run_id,
            objective="evidence-triggered-replan",
            changed_evidence_kind=str(payload.get("kind", "unknown")),
        )["snapshot"]

    def approve(self, run_id: str, approver: str, *, expected_revision: int) -> dict[str, Any]:
        current = int(self.store.get_run(run_id)["revision"])
        if expected_revision != current:
            self.store.append_event(
                run_id,
                "approval_rejected_stale",
                event_id=self._event_id("approval-rejected"),
                task_id="risk-gate",
                worker="chronosfix-release-auditor#01",
                payload={"approved_revision": expected_revision, "current_revision": current},
            )
            raise StaleApprovalError(f"approval revision {expected_revision} is stale; current revision is {current}")
        event, _ = self.store.append_event(
            run_id,
            "approval_recorded",
            event_id=self._event_id("approval-recorded"),
            task_id="risk-gate",
            worker="chronosfix-release-auditor#01",
            payload={"approver": approver, "approved_revision": expected_revision},
        )
        approval = {
            "run_id": run_id,
            "approval_id": f"approval-{uuid.uuid4().hex[:12]}",
            "state_revision": event["revision"],
            "input_digest": digest(
                {"run_id": run_id, "state_revision": event["revision"], "policy_version": POLICY_VERSION}
            ),
            "policy_version": POLICY_VERSION,
            "approver": approver,
        }
        self.store.add_approval(approval)
        self.store.update_run(run_id, status="COMPLETED", release_decision="approved")
        return self.snapshot(run_id)

    def pause(self, run_id: str) -> dict[str, Any]:
        self.store.append_event(
            run_id,
            "human_pause",
            event_id=self._event_id("pause"),
            task_id="risk-gate",
            payload={"reason": "manual live-demo checkpoint"},
        )
        self.store.update_run(run_id, status="PAUSED_AWAITING_HUMAN", release_decision="blocked-awaiting-human")
        return self.snapshot(run_id)

    def resume(self, run_id: str, approver: str = "AsoulAI Release Owner") -> dict[str, Any]:
        return self.approve(run_id, approver, expected_revision=int(self.store.get_run(run_id)["revision"]))

    def stale_approval_demo(self, run_id: str) -> dict[str, Any]:
        old_revision = int(self.store.get_run(run_id)["revision"])
        event_id = f"policy-evidence-{uuid.uuid4().hex[:10]}"
        self.ingest_evidence(
            run_id,
            event_id,
            {"kind": "policy", "summary": "RiskGate policy input changed during review"},
        )
        try:
            self.approve(run_id, "Stale Approval Replay", expected_revision=old_revision)
        except StaleApprovalError:
            pass
        return self.snapshot(run_id)

    def deny_tool(self, run_id: str) -> dict[str, Any]:
        self.store.append_event(
            run_id,
            "tool_permission_denied",
            event_id=self._event_id("tool-denied"),
            task_id="dynamic-config-audit",
            worker="chronosfix-timeline-analyst#01",
            payload={"policy": "read-only-minimum", "operation": "write-cloud-resource"},
        )
        self.store.update_run(run_id, status="BLOCKED_PERMISSION_DENIED", quality_gate="failed", release_decision="blocked-quality")
        return self.snapshot(run_id)

    def retry_exhausted(self, run_id: str) -> dict[str, Any]:
        try:
            self.execute_task(
                run_id,
                task_id=f"live-retry-exhausted-{uuid.uuid4().hex[:8]}",
                skill="RiskGateWorkerProbe",
                capability="patch-tournament",
                job="probe",
                first_mode="crash",
                retry_mode="crash",
                timeout_seconds=3,
            )
        except RuntimeError:
            pass
        return self.snapshot(run_id)

    def recommend(
        self,
        run_id: str,
        *,
        objective: str = "prove-and-repair",
        changed_evidence_kind: str | None = None,
    ) -> dict[str, Any]:
        """Recompute the Manager plan and execute any newly compiled DAG nodes."""

        snapshot = self.snapshot(run_id)
        scenario_path = self.scenario_path(snapshot["run"]["scenario_id"])
        scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
        recommendation, dag = self._plan_agent_dag(
            run_id,
            scenario,
            evidence=[item["payload"] for item in snapshot["evidence"]],
            objective=objective,
        )
        recompute = self._incremental_recompute(
            run_id,
            dag,
            evidence_kind=changed_evidence_kind,
        )
        self._execute_agent_dag(run_id, scenario_path, dag, approved=False)
        return {"recommendation": recommendation, "recompute": recompute, "snapshot": self.snapshot(run_id)}

    def snapshot(self, run_id: str) -> dict[str, Any]:
        return self.store.snapshot(run_id)
