#!/usr/bin/env python
"""Pre-commit hook: catch kitchen-sink commits.

Built 2026-05-25 after Jarvis committed 9000+ lines of unrelated
composio skill scaffolding (.agents/skills/composio-*/SKILL.md) under
a commit message claiming "architecture revision of associative_recall"
(commit 155eafc6). The actual associative_recall code wasn't even
touched in that commit.

This hook blocks commits that exhibit the "kitchen-sink" anti-pattern:
many files changed AND spanning multiple unrelated top-level domains.

Rule of thumb:
  - ≤ 5 files: always OK (small focused commit)
  - 6-20 files: OK if all under ≤ 2 top-level paths
  - > 20 files: OK if all under 1 top-level path, OR explicit --no-verify
  - Mix of code (core/, apps/, scripts/) + scaffolding (.agents/, .codex/)
    in same commit: always blocked

Override: --no-verify (skips ALL hooks, use sparingly). Or commit in
multiple passes — one domain at a time.
"""
from __future__ import annotations

import subprocess
import sys
from collections import Counter
from pathlib import Path


# Top-level domains we recognize. Files outside these go to "other".
_DOMAINS = {
    "core": "core",
    "apps": "apps",
    "scripts": "scripts",
    "tests": "tests",
    "docs": "docs",
    ".agents": "scaffolding",
    ".codex": "scaffolding",
    ".claude": "scaffolding",
    "workspace": "workspace",
    "state": "state",
}

_CODE_DOMAINS = {"core", "apps", "scripts", "tests"}
_SCAFFOLDING_DOMAINS = {"scaffolding"}

_KITCHEN_SINK_THRESHOLD = 20
_SOFT_THRESHOLD = 6
_MAX_UNRELATED_DOMAINS_AT_SOFT = 2


def _staged_files() -> list[Path]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        return []
    return [Path(line) for line in result.stdout.splitlines() if line.strip()]


def _classify(path: Path) -> str:
    top = path.parts[0] if path.parts else ""
    return _DOMAINS.get(top, "other")


def _merge_in_progress() -> bool:
    """A merge commit combines commits that already passed this gate one by
    one; its staged file count is the union of both sides and says nothing
    about kitchen-sink authoring. (2026-09-04: a 57-file branch merge was
    blocked although every commit on both sides was focused.)"""
    result = subprocess.run(
        ["git", "rev-parse", "-q", "--verify", "MERGE_HEAD"],
        capture_output=True, text=True, check=False,
    )
    return result.returncode == 0 and bool(result.stdout.strip())


def main() -> int:
    files = _staged_files()
    if not files:
        return 0
    if _merge_in_progress():
        print("commit-hygiene: merge commit — size gate skipped (both sides already gated).")
        return 0

    domains = Counter(_classify(f) for f in files)
    distinct = set(domains.keys())
    total = len(files)

    # Always-block: code + scaffolding in same commit
    code_present = bool(distinct & _CODE_DOMAINS)
    scaffolding_present = bool(distinct & _SCAFFOLDING_DOMAINS)
    if code_present and scaffolding_present:
        print(
            "\n❌ COMMIT HYGIENE GATE — commit blocked\n"
            "\nThis commit mixes code files with tool scaffolding "
            "(.agents/.codex/.claude). Make TWO commits: one for the code, "
            "one for the scaffolding (or .gitignore the scaffolding).\n"
            "\nFiles per domain:"
        )
        for d, n in sorted(domains.items(), key=lambda kv: -kv[1]):
            print(f"  {d:15s} {n:4d}")
        print("\nOverride with `git commit --no-verify` if intentional.")
        return 1

    # Kitchen-sink: >20 files spanning multiple unrelated domains
    if total > _KITCHEN_SINK_THRESHOLD and len(distinct - {"other"}) > 1:
        print(
            f"\n❌ COMMIT HYGIENE GATE — commit blocked\n"
            f"\nKitchen-sink pattern detected: {total} files across "
            f"{len(distinct)} domains. Split into focused commits.\n"
            f"\nFiles per domain:"
        )
        for d, n in sorted(domains.items(), key=lambda kv: -kv[1]):
            print(f"  {d:15s} {n:4d}")
        print(
            f"\nThreshold: ≤{_KITCHEN_SINK_THRESHOLD} files for multi-domain "
            f"commits.\nOverride with `git commit --no-verify` if intentional."
        )
        return 1

    # Soft warning: 6-20 files spanning >2 domains
    if total >= _SOFT_THRESHOLD and len(distinct - {"other"}) > _MAX_UNRELATED_DOMAINS_AT_SOFT:
        print(
            f"\n⚠ Commit hygiene WARNING (not blocking)\n"
            f"\n{total} files across {len(distinct)} domains. Consider "
            f"splitting for cleaner history.\n"
            f"\nFiles per domain:"
        )
        for d, n in sorted(domains.items(), key=lambda kv: -kv[1]):
            print(f"  {d:15s} {n:4d}")
        # warning only — exit 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
