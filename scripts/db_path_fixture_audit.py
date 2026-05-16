"""Audit: find test fixtures that monkeypatch DB_PATH on db but not db_core.

Post-2026-05-15 db.py split: DB_PATH lever i db_core. db re-eksporterer
det som lokal binding. Patch af db.DB_PATH alone ændrer ikke hvad
connect() ser. Output: liste af suspekte filer + linjer.

Usage:
    python scripts/db_path_fixture_audit.py            # report, exit 0
    python scripts/db_path_fixture_audit.py --strict   # exit 1 hvis fund
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

PATTERN_DB = re.compile(r'monkeypatch\.setattr\([^)]*\bdb\b[^)]*DB_PATH')
PATTERN_DB_CORE = re.compile(r'monkeypatch\.setattr\([^)]*\bdb_core\b[^)]*DB_PATH')


def main() -> int:
    repo = Path(__file__).resolve().parent.parent
    suspect: list[tuple[Path, int, str]] = []
    for py in (repo / "tests").rglob("*.py"):
        text = py.read_text()
        if not PATTERN_DB.search(text):
            continue
        if PATTERN_DB_CORE.search(text):
            continue  # Both patched — OK
        for i, line in enumerate(text.splitlines(), start=1):
            if PATTERN_DB.search(line):
                suspect.append((py.relative_to(repo), i, line.strip()))
    if not suspect:
        print("OK: alle DB_PATH-monkeypatches patcher også db_core")
        return 0
    print(f"FOUND {len(suspect)} suspect locations:")
    for path, lineno, line in suspect:
        print(f"  {path}:{lineno}: {line}")
    return 1 if "--strict" in sys.argv else 0


if __name__ == "__main__":
    sys.exit(main())
