from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
except ImportError as error:  # pragma: no cover - exercised by deployment checks
    raise RuntimeError('cryptography is required; install with: pip install -e ".[validation]"') from error


PAYLOAD_TYPE = "application/vnd.in-toto+json"


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dsse_pae(payload_type: str, payload: bytes) -> bytes:
    type_bytes = payload_type.encode("utf-8")
    return b"DSSEv1 %d " % len(type_bytes) + type_bytes + b" %d " % len(payload) + payload


def public_key_record(public_key: Ed25519PublicKey) -> dict[str, str]:
    raw = public_key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return {
        "keyid": hashlib.sha256(raw).hexdigest(),
        "keyType": "ed25519",
        "publicKeyBase64": base64.b64encode(raw).decode("ascii"),
    }


def build_statement(subjects: list[dict[str, Any]], predicate: dict[str, Any]) -> dict[str, Any]:
    return {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": subjects,
        "predicateType": "https://asoul.ai/chronosfix/ProofCarryingChange/v1",
        "predicate": predicate,
    }


def sign_statement(statement: dict[str, Any], private_key: Ed25519PrivateKey | None = None) -> tuple[dict, dict]:
    key = private_key or Ed25519PrivateKey.generate()
    payload = canonical_json(statement)
    public_record = public_key_record(key.public_key())
    signature = key.sign(dsse_pae(PAYLOAD_TYPE, payload))
    envelope = {
        "payloadType": PAYLOAD_TYPE,
        "payload": base64.b64encode(payload).decode("ascii"),
        "signatures": [
            {
                "keyid": public_record["keyid"],
                "sig": base64.b64encode(signature).decode("ascii"),
            }
        ],
    }
    return envelope, public_record


def verify_envelope(envelope: dict[str, Any], public_record: dict[str, str]) -> dict[str, Any]:
    try:
        raw_key = base64.b64decode(public_record["publicKeyBase64"], validate=True)
        public_key = Ed25519PublicKey.from_public_bytes(raw_key)
        payload = base64.b64decode(envelope["payload"], validate=True)
        signature = base64.b64decode(envelope["signatures"][0]["sig"], validate=True)
        if envelope["signatures"][0]["keyid"] != public_record["keyid"]:
            raise ValueError("keyid mismatch")
        public_key.verify(signature, dsse_pae(envelope["payloadType"], payload))
        statement = json.loads(payload.decode("utf-8"))
        return {"valid": True, "statement": statement, "error": None}
    except Exception as error:  # verification must fail closed
        return {"valid": False, "statement": None, "error": f"{type(error).__name__}: {error}"}


def subject(path: Path, *, name: str | None = None) -> dict[str, Any]:
    return {"name": name or path.name, "digest": {"sha256": sha256_file(path)}, "bytes": path.stat().st_size}
