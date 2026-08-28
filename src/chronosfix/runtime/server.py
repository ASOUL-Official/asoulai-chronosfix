from __future__ import annotations

import argparse
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
from typing import Any

from .controller import LocalController, ROOT, StaleApprovalError


RUN_ROUTE = re.compile(r"^/api/runs/([^/]+)(?:/(.*))?$")


class RuntimeHandler(SimpleHTTPRequestHandler):
    controller: LocalController

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(ROOT / "repair-cockpit"), **kwargs)

    def send_json(self, value: Any, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict[str, Any]:
        length = min(int(self.headers.get("Content-Length", "0")), 64 * 1024)
        return json.loads(self.rfile.read(length).decode("utf-8")) if length else {}

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/api/health":
            self.send_json(self.controller.health())
            return
        if self.path == "/api/scenarios":
            self.send_json({"scenarios": self.controller.scenarios()})
            return
        match = RUN_ROUTE.match(self.path)
        if match and not match.group(2):
            try:
                self.send_json(self.controller.snapshot(match.group(1)))
            except KeyError:
                self.send_json({"error": "run not found"}, HTTPStatus.NOT_FOUND)
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        try:
            payload = self.read_json()
            if self.path == "/api/runs":
                self.send_json(
                    self.controller.create_run(
                        str(payload.get("scenario_id", "checkout-timeout")),
                        auto_approve=bool(payload.get("auto_approve", True)),
                    ),
                    HTTPStatus.CREATED,
                )
                return
            match = RUN_ROUTE.match(self.path)
            if not match:
                self.send_json({"error": "route not found"}, HTTPStatus.NOT_FOUND)
                return
            run_id, action = match.groups()
            if action == "evidence":
                event_id = str(payload.get("event_id") or "")
                if not event_id or len(event_id) > 128:
                    raise ValueError("event_id is required and must be <= 128 characters")
                self.send_json(self.controller.ingest_evidence(run_id, event_id, payload.get("evidence") or {}))
            elif action == "actions/worker-timeout":
                self.send_json(self.controller.trigger_failover(run_id, "timeout"))
            elif action == "actions/worker-crash":
                self.send_json(self.controller.trigger_failover(run_id, "crash"))
            elif action == "actions/stale-approval":
                self.send_json(self.controller.stale_approval_demo(run_id))
            elif action == "actions/pause":
                self.send_json(self.controller.pause(run_id))
            elif action == "actions/resume":
                self.send_json(self.controller.resume(run_id, str(payload.get("approver", "AsoulAI Release Owner"))))
            elif action == "actions/tool-denied":
                self.send_json(self.controller.deny_tool(run_id))
            elif action == "actions/retry-exhausted":
                self.send_json(self.controller.retry_exhausted(run_id))
            elif action == "recommendation":
                self.send_json(
                    self.controller.recommend(
                        run_id,
                        objective=str(payload.get("objective", "prove-and-repair")),
                    )
                )
            elif action == "approvals":
                self.send_json(
                    self.controller.approve(
                        run_id,
                        str(payload.get("approver", "AsoulAI Release Owner")),
                        expected_revision=int(payload["expected_revision"]),
                    )
                )
            else:
                self.send_json({"error": "route not found"}, HTTPStatus.NOT_FOUND)
        except StaleApprovalError as error:
            self.send_json({"error": str(error), "code": "stale-approval"}, HTTPStatus.CONFLICT)
        except (KeyError, ValueError) as error:
            self.send_json({"error": str(error)}, HTTPStatus.BAD_REQUEST)
        except Exception as error:
            self.send_json({"error": f"{type(error).__name__}: {error}"}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[chronosfix-controller] {self.address_string()} {format % args}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the executable ChronosFix Repair Cockpit")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--database", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    RuntimeHandler.controller = LocalController(args.database, args.output)
    server = ThreadingHTTPServer((args.host, args.port), RuntimeHandler)
    print(json.dumps({"url": f"http://{args.host}:{args.port}", **RuntimeHandler.controller.health()}, ensure_ascii=False))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
