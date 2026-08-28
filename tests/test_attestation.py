from __future__ import annotations

import base64
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from chronosfix.attestation import build_statement, sign_statement, verify_envelope


class AttestationTests(unittest.TestCase):
    def test_dsse_ed25519_signature_verifies_and_tamper_fails(self):
        statement = build_statement(
            [{"name": "patch", "digest": {"sha256": "a" * 64}}],
            {"qualityGate": "passed"},
        )
        envelope, public_key = sign_statement(statement)
        self.assertTrue(verify_envelope(envelope, public_key)["valid"])

        tampered = json.loads(json.dumps(envelope))
        payload = bytearray(base64.b64decode(tampered["payload"]))
        payload[0] ^= 1
        tampered["payload"] = base64.b64encode(payload).decode("ascii")
        self.assertFalse(verify_envelope(tampered, public_key)["valid"])

    def test_wrong_public_key_fails_closed(self):
        statement = build_statement([], {"qualityGate": "blocked"})
        envelope, _public_key = sign_statement(statement)
        _other_envelope, other_public_key = sign_statement(statement)
        self.assertFalse(verify_envelope(envelope, other_public_key)["valid"])


if __name__ == "__main__":
    unittest.main()
