from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from chronosfix.infra import LocalToolGateway, RevisionConflict, UnifiedModelStore, infra_boundaries, to_otlp_json


def build(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    store = UnifiedModelStore(output / "unified-model.sqlite3")
    incident = store.create_incident("INC-INFRA-001", {"status": "RUNNING"})
    updated = store.compare_and_swap(incident["incident_id"], 0, {"status": "EVIDENCE_READY"})
    conflict_blocked = False
    try:
        store.compare_and_swap(incident["incident_id"], 0, {"status": "STALE_WRITE"})
    except RevisionConflict:
        conflict_blocked = True

    published = store.publish("experiment.done", "experiment-001", {"healthy": True}, max_attempts=2)
    duplicate = store.publish("experiment.done", "experiment-001", {"healthy": True}, max_attempts=2)
    first_delivery = store.consume("experiment.done")
    retried = store.fail(first_delivery["message_id"])
    second_delivery = store.consume("experiment.done")
    acked = store.ack(second_delivery["message_id"])
    dlq_message = store.publish("riskgate.waiting", "riskgate-001", {"approval": "missing"}, max_attempts=1)
    dlq_delivery = store.consume("riskgate.waiting")
    dlq = store.fail(dlq_delivery["message_id"])

    policy_v1 = store.publish_policy("risk-gate", "1.0.0", {"max_risk": 0.35})
    policy_v2 = store.publish_policy("risk-gate", "1.1.0", {"max_risk": 0.25})
    rolled_back = store.rollback_policy("risk-gate", "1.0.0")

    gateway = LocalToolGateway(limit=2)
    trace_id = "1" * 32
    routed = gateway.invoke("GetLogsV2", token="chronosfix-readonly-demo", trace_id=trace_id, payload={"query": "status>=500"})
    denied = gateway.invoke("DeleteLogstore", token="chronosfix-readonly-demo", trace_id=trace_id, payload={})
    unauthorized = gateway.invoke("GetIndex", token="wrong", trace_id=trace_id, payload={})
    gateway.invoke("GetIndex", token="chronosfix-readonly-demo", trace_id=trace_id, payload={})
    rate_limited = gateway.invoke("GetIndex", token="chronosfix-readonly-demo", trace_id=trace_id, payload={})

    records = [json.loads(line) for line in (ROOT / "evidence" / "trace.jsonl").read_text(encoding="utf-8").splitlines()]
    otlp = to_otlp_json(records)
    span_count = len(otlp["resourceSpans"][0]["scopeSpans"][0]["spans"])
    store.save_otlp(records[0]["trace_id"], otlp, span_count)

    report = {
        "schema": "chronosfix.local-infra-evidence/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "passed": all(
            [
                updated["revision"] == 1,
                conflict_blocked,
                duplicate["deduplicated"],
                retried["status"] == "READY",
                acked["status"] == "ACKED",
                dlq["status"] == "DLQ",
                policy_v2["version"] == "1.1.0",
                rolled_back["version"] == "1.0.0",
                routed["status"] == 200,
                denied["status"] == 403,
                unauthorized["status"] == 401,
                rate_limited["status"] == 429,
                span_count == len(records),
            ]
        ),
        "boundaries": infra_boundaries(),
        "unified_model": {"incident": updated, "stale_revision_blocked": conflict_blocked},
        "event_bus": {
            "published": published,
            "duplicate": duplicate,
            "retry": retried,
            "acked": acked,
            "dlq": dlq,
        },
        "policy_registry": {"v1": policy_v1, "v2": policy_v2, "active_after_rollback": rolled_back},
        "tool_gateway": {"routed": routed, "denied": denied, "unauthorized": unauthorized, "rate_limited": rate_limited},
        "otlp": {"trace_id": records[0]["trace_id"], "span_count": span_count, "payload": otlp},
    }
    (output / "local-infra-evidence.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Execute local production-infra compatible providers")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    report = build(args.output.resolve())
    print(json.dumps({"passed": report["passed"], "output": str(args.output.resolve())}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
