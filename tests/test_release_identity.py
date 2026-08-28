from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = load_script("build_release_manifest", "scripts/build_release_manifest.py")
validator = load_script("validate_release_manifest", "scripts/validate_release_manifest.py")


class ReleaseIdentityTests(unittest.TestCase):
    def test_utf8_text_identity_is_independent_of_line_endings(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            lf = root / "lf.json"
            crlf = root / "crlf.json"
            lf.write_bytes("{\n  \"结论\": \"通过\"\n}\n".encode("utf-8"))
            crlf.write_bytes("{\r\n  \"结论\": \"通过\"\r\n}\r\n".encode("utf-8"))

            self.assertEqual(builder.canonical_file_bytes(lf), builder.canonical_file_bytes(crlf))
            self.assertEqual(builder.sha256(lf), builder.sha256(crlf))
            self.assertEqual(validator.sha256(lf), validator.sha256(crlf))

    def test_binary_identity_remains_byte_exact(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = root / "first.bin"
            second = root / "second.bin"
            first.write_bytes(b"\x00\r\n")
            second.write_bytes(b"\x00\n")

            self.assertNotEqual(builder.sha256(first), builder.sha256(second))
            self.assertEqual(builder.canonical_file_bytes(first), first.read_bytes())


if __name__ == "__main__":
    unittest.main()
