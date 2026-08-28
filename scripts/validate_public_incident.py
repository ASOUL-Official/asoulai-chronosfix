from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]


def validate(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    source = data.get("source") or {}
    parsed = urlparse(str(source.get("url", "")))
    if parsed.scheme != "https" or not parsed.netloc:
        errors.append("source URL must be HTTPS")
    if source.get("authority") != "first-party-public-postmortem":
        errors.append("source must be a first-party public postmortem")
    facts = data.get("official_facts") or []
    if len(facts) < 5:
        errors.append("at least five official facts are required")
    fact_ids = [item.get("fact_id") for item in facts]
    if None in fact_ids or len(fact_ids) != len(set(fact_ids)):
        errors.append("official fact IDs must be present and unique")
    for item in data.get("chronosfix_inferences") or []:
        if item.get("classification") != "project-inference-not-source-claim":
            errors.append(f"inference {item.get('inference_id')} is not clearly separated")
        unknown = set(item.get("basis") or []) - set(fact_ids)
        if unknown:
            errors.append(f"inference {item.get('inference_id')} references unknown facts: {sorted(unknown)}")
    if data.get("synthetic_reconstruction", {}).get("enabled") is not False:
        errors.append("public incident must not silently enable synthetic reconstruction")
    privacy = data.get("privacy") or {}
    if any(privacy.get(key) is not False for key in ("personal_data_included", "credentials_included", "customer_logs_included")):
        errors.append("privacy boundary is not clean")
    return {
        "schema": "chronosfix.public-incident-validation/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "path": str(path),
        "incident_id": data.get("incident_id"),
        "source_url": source.get("url"),
        "official_fact_count": len(facts),
        "inference_count": len(data.get("chronosfix_inferences") or []),
        "valid": not errors,
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate provenance separation for a public incident")
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=ROOT / "public-incidents" / "cloudflare-2019-waf-regex" / "incident.json",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    report = validate(args.path.resolve())
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
