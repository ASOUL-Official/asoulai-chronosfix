from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SUBMISSION = ROOT / "submission"
ARCHIVE = SUBMISSION / "AsoulAI_ChronosFix_复赛提交包.zip"
MANIFEST = SUBMISSION / "AsoulAI_ChronosFix_复赛提交包.manifest.json"
PACKAGE_ROOT = "AsoulAI_ChronosFix"

EXCLUDED_DIRS = {".git", "tmp", "output", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
EXCLUDED_SUFFIXES = {".pyc", ".zip"}
EXCLUDED_NAMES = {
    "ChronosFix_初赛方案.pptx",
    "ChronosFix_复赛方案.pptx.inspect.ndjson",
    MANIFEST.name,
}


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def source_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_DIRS for part in relative.parts):
            continue
        if path.is_symlink():
            raise RuntimeError(f"Refusing to package symlink: {relative.as_posix()}")
        if not path.is_file():
            continue
        if path.name in EXCLUDED_NAMES or path.suffix.lower() in EXCLUDED_SUFFIXES:
            continue
        files.append(path)
    return sorted(files, key=lambda item: item.relative_to(ROOT).as_posix())


def build() -> dict:
    SUBMISSION.mkdir(parents=True, exist_ok=True)
    files = source_files()
    entries = []
    for path in files:
        payload = path.read_bytes()
        entries.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "size": len(payload),
                "sha256": sha256_bytes(payload),
            }
        )

    package_manifest = {
        "schema": "chronosfix.submission-package/v1",
        "team": "AsoulAI",
        "work": "ChronosFix",
        "direction": "新智基座方向三：软件研发全流程协同",
        "file_count": len(entries),
        "files": entries,
    }
    manifest_payload = (json.dumps(package_manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    with zipfile.ZipFile(ARCHIVE, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            relative = path.relative_to(ROOT).as_posix()
            info = zipfile.ZipInfo(f"{PACKAGE_ROOT}/{relative}", date_time=(2026, 8, 25, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

        info = zipfile.ZipInfo(
            f"{PACKAGE_ROOT}/submission-package-manifest.json",
            date_time=(2026, 8, 25, 0, 0, 0),
        )
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        archive.writestr(info, manifest_payload, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

    external_manifest = {
        **package_manifest,
        "archive": ARCHIVE.name,
        "archive_size": ARCHIVE.stat().st_size,
        "archive_sha256": sha256_bytes(ARCHIVE.read_bytes()),
    }
    MANIFEST.write_text(json.dumps(external_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return external_manifest


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
