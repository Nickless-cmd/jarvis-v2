#!/usr/bin/env python
"""Bulk-rewrite legacy `[MEMORY.md]` / `[USER.md]` prefixes in daily memory.

2026-05-22 (Claude): After 82c96c1d changed the daily-memory writer to
emit `[CANDIDATE→MEMORY.md]` / `[CANDIDATE→USER.md]` (so consolidated
LLM-proposed lines are not mistakenly read as citations), legacy daily
files still contain ~2000 lines with the old prefix. Each of those is
a candidate that was never approved into MEMORY.md, but currently
LOOKS like a citation when search_memory surfaces it.

This script rewrites them retroactively. Idempotent — safe to re-run.

Backup: a tar.gz of memory/daily/ is written to memory/daily/_backups/
before any in-place edits.

Usage:
  /opt/conda/envs/ai/bin/python scripts/rewrite_legacy_memory_provenance.py [--dry-run]
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import tarfile
from datetime import datetime
from pathlib import Path

# Patterns to rewrite. Targets the "carried:" sub-list lines specifically
# (two-space indent + dash + bracketed target). Does NOT touch top-level
# `- [HH:MM] [source] note` lines from append_daily_memory_note, which
# use a different format and a different (timestamp-based) prefix.
_CARRIED_RE = re.compile(r"^(  - )\[(MEMORY\.md|USER\.md)\] (.+)$")


def rewrite_file(path: Path, *, dry_run: bool) -> tuple[int, int]:
    """Return (matched_lines, rewritten_lines)."""
    text = path.read_text(encoding="utf-8", errors="replace")
    out_lines: list[str] = []
    matched = 0
    changed = 0
    for line in text.split("\n"):
        m = _CARRIED_RE.match(line)
        if m:
            matched += 1
            new_line = f"{m.group(1)}[CANDIDATE→{m.group(2)}] {m.group(3)}"
            if new_line != line:
                changed += 1
            out_lines.append(new_line)
        else:
            out_lines.append(line)
    if changed and not dry_run:
        path.write_text("\n".join(out_lines), encoding="utf-8")
    return matched, changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="report only, don't modify")
    parser.add_argument(
        "--daily-dir",
        default=str(Path.home() / ".jarvis-v2" / "workspaces" / "default" / "memory" / "daily"),
    )
    args = parser.parse_args()

    daily_dir = Path(args.daily_dir)
    if not daily_dir.exists():
        print(f"FEJL: {daily_dir} findes ikke")
        return 1

    md_files = sorted(daily_dir.glob("*.md"))
    if not md_files:
        print(f"Ingen .md-filer i {daily_dir}")
        return 0

    # Backup before any modification
    if not args.dry_run:
        backup_dir = daily_dir / "_backups"
        backup_dir.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_tar = backup_dir / f"pre-rewrite-{ts}.tar.gz"
        with tarfile.open(backup_tar, "w:gz") as tar:
            for f in md_files:
                tar.add(f, arcname=f.name)
        print(f"Backup: {backup_tar}")

    print(f"\n{'DRY RUN' if args.dry_run else 'REWRITING'} — {len(md_files)} files")
    print(f"{'File':<24}  {'matched':>8}  {'changed':>8}")
    print(f"{'-' * 24}  {'-' * 8}  {'-' * 8}")
    total_matched = 0
    total_changed = 0
    for f in md_files:
        matched, changed = rewrite_file(f, dry_run=args.dry_run)
        total_matched += matched
        total_changed += changed
        if matched:
            print(f"{f.name:<24}  {matched:>8}  {changed:>8}")
    print(f"{'-' * 24}  {'-' * 8}  {'-' * 8}")
    print(f"{'TOTAL':<24}  {total_matched:>8}  {total_changed:>8}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
