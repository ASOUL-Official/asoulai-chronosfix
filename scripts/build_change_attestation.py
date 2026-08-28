from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from chronosfix.attestation import build_statement, sign_statement, subject, verify_envelope


def git_head() -> str | None:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else None


def build(output: Path, subject_paths: list[Path], predicate_input: dict[str, Any] | None = None) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    resolved = [path.resolve() for path in subject_paths]
    missing = [str(path) for path in resolved if not path.is_file()]
    if missing:
        raise FileNotFoundError(", ".join(missing))
    predicate = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourceCommit": git_head(),
        "changeClass": "causal-software-repair",
        "riskGate": "evidence-and-human-approval-required",
        "verification": predicate_input or {},
        "boundaries": {
            "signatureIdentity": "local-ephemeral-ed25519",
            "trustedTimestamp": False,
            "sigstoreKeyless": False,
            "claim": "DSSE signature and subject integrity are verified; external identity trust is not claimed.",
        },
    }
    statement = build_statement(
        [subject(path, name=path.name) for path in resolved],
        predicate,
    )
    envelope, public_key = sign_statement(statement)
    verification = verify_envelope(envelope, public_key)
    tampered = json.loads(json.dumps(envelope))
    payload = bytearray(base64.b64decode(tampered["payload"]))
    payload[-1] ^= 1
    tampered["payload"] = base64.b64encode(payload).decode("ascii")
    tamper_verification = verify_envelope(tampered, public_key)
    report = {
        "schema": "chronosfix.proof-carrying-change-attestation/v1",
        "passed": verification["valid"] and not tamper_verification["valid"],
        "statement": statement,
        "envelope": envelope,
        "public_key": public_key,
        "verification": verification,
        "tamper_test": {
            "payload_modified": True,
            "verification_valid": tamper_verification["valid"],
            "error": tamper_verification["error"],
        },
    }
    (output / "change-attestation-statement.json").write_text(
        json.dumps(statement, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / "change-attestation.dsse.json").write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / "change-attestation-public-key.json").write_text(
        json.dumps(public_key, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / "change-attestation-verification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a DSSE-wrapped in-toto Proof-Carrying Change attestation")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--subject", type=Path, action="append", required=True)
    args = parser.parse_args(argv)
    report = build(args.output.resolve(), args.subject)
    print(json.dumps({"passed": report["passed"], "output": str(args.output.resolve())}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
