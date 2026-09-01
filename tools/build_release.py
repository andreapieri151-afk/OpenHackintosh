#!/usr/bin/env python3
"""
Costruisce lo ZIP di distribuzione di OpenHackintosh.

Uso:
    python3 tools/build_release.py                       # build standard
    python3 tools/build_release.py --name ...-fixed.zip  # build con nome custom

Lo ZIP replica esattamente il layout della release 2.0.1 Beta 1:
codice + launcher + documentazione, senza test, ambienti virtuali o release
precedenti. Il contenuto e' deterministico (ordinamento stabile dei file).
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASES = ROOT / "releases"

DEFAULT_VERSION = "2.0.1 Beta 1"
DEFAULT_ZIP = "OpenHackintosh-2.0.1-Beta-1.zip"

#: File di primo livello inclusi nella distribuzione.
TOP_LEVEL_FILES = [
    ".github/DESCRIPTION.md",
    "CHANGELOG.md",
    "LICENSE",
    "CONTRIBUTING.md",
    "FujitsuEFI.command",
    "OpenHackintosh.command",
    "README.md",
    "main.py",
    "openhackintosh",
    "openhackintosh.sh",
    "requirements.txt",
    "tools/README.md",
]

#: Directory incluse ricorsivamente.
TREES = ["assets", "docs", "src"]

#: Estensioni/nomi da escludere sempre.
EXCLUDE_DIRS = {"__pycache__", ".pytest_cache", ".git", ".venv", "node_modules"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo"}
EXCLUDE_NAMES = {".DS_Store"}


def collect() -> list[Path]:
    files: list[Path] = []
    for rel in TOP_LEVEL_FILES:
        path = ROOT / rel
        if path.is_file():
            files.append(path)
    for tree in TREES:
        base = ROOT / tree
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            if any(part in EXCLUDE_DIRS for part in path.parts):
                continue
            if path.suffix in EXCLUDE_SUFFIXES or path.name in EXCLUDE_NAMES:
                continue
            files.append(path)
    return files


def build(zip_name: str, folder: str, extra: dict[str, str] | None = None) -> Path:
    RELEASES.mkdir(parents=True, exist_ok=True)
    target = RELEASES / zip_name
    files = collect()

    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in files:
            arc = f"{folder}/{path.relative_to(ROOT).as_posix()}"
            info = zipfile.ZipInfo(arc, date_time=(2026, 9, 1, 12, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            # Preserva il bit di esecuzione per i launcher.
            mode = 0o755 if path.suffix in (".command", ".sh") or path.name == "openhackintosh" else 0o644
            info.external_attr = (mode & 0xFFFF) << 16
            zf.writestr(info, path.read_bytes())
        for name, content in (extra or {}).items():
            info = zipfile.ZipInfo(f"{folder}/{name}", date_time=(2026, 9, 1, 12, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o644 & 0xFFFF) << 16
            zf.writestr(info, content)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build dello ZIP di release")
    parser.add_argument("--name", default=DEFAULT_ZIP, help="Nome del file ZIP")
    parser.add_argument("--folder", default=None, help="Cartella radice dentro lo ZIP")
    parser.add_argument("--build-note", default=None, help="File di nota da includere come BUILD.txt")
    args = parser.parse_args(argv)

    folder = args.folder or args.name[:-4]
    extra = {}
    if args.build_note:
        extra["BUILD.txt"] = Path(args.build_note).read_text(encoding="utf-8")

    target = build(args.name, folder, extra)
    data = target.read_bytes()
    with zipfile.ZipFile(target) as zf:
        count = len(zf.namelist())
        bad = zf.testzip()
    print(f"ZIP:    {target}")
    print(f"Root:   {folder}/")
    print(f"Files:  {count}")
    print(f"Size:   {len(data)} bytes")
    print(f"SHA256: {hashlib.sha256(data).hexdigest()}")
    print(f"Integrity: {'OK' if bad is None else 'CORRUPT ' + bad}")
    return 0 if bad is None else 1


if __name__ == "__main__":
    sys.exit(main())
