from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from chronosfix.cloud_skills import AlibabaCloudSlsQueryAdapter, SlsQueryRequest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build or execute a read-only official SLS Skill request.")
    parser.add_argument("--project", default="chronosfix-demo")
    parser.add_argument("--logstore", default="checkout")
    parser.add_argument("--from-epoch", type=int, default=1787623200)
    parser.add_argument("--to-epoch", type=int, default=1787624100)
    parser.add_argument("--query", default='status >= 500 and route: "/api/order/create"')
    parser.add_argument("--profile")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "output" / "cloud-skill-sls.json")
    args = parser.parse_args(argv)

    adapter = AlibabaCloudSlsQueryAdapter()
    request = SlsQueryRequest(
        project=args.project,
        logstore=args.logstore,
        from_epoch=args.from_epoch,
        to_epoch=args.to_epoch,
        query=args.query,
        profile=args.profile,
    )
    if args.execute:
        result = adapter.execute(request, audit_path=args.output)
    else:
        result = adapter.plan(request)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "execution_mode": result["execution_mode"]}, ensure_ascii=False))
    return 0 if not args.execute or result.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())
