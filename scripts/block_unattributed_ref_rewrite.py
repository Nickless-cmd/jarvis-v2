#!/usr/bin/env python3
"""Block local branch rewrites that can preserve stale actor attribution."""

from __future__ import annotations

import os
import subprocess
import sys


ZERO_OID = "0" * 40


def _is_ancestor(old: str, new: str) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", old, new],
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.returncode == 0


def main(
    argv: list[str] | None = None,
    *,
    input_text: str | None = None,
) -> int:
    args = argv or sys.argv[1:]
    if not args or args[0] != "prepared":
        return 0
    if os.environ.get("JARVIS_ATTRIBUTED_REWRITE") == "1":
        return 0

    updates = input_text if input_text is not None else sys.stdin.read()
    for line in updates.splitlines():
        fields = line.split()
        if len(fields) != 3:
            print(
                f"commit attribution: malformed reference transaction: {line}",
                file=sys.stderr,
            )
            return 1
        old, new, ref = fields
        if not ref.startswith("refs/heads/"):
            continue
        if old == ZERO_OID or new == ZERO_OID:
            continue
        if not _is_ancestor(old, new):
            print(
                "commit attribution: non-fast-forward branch rewrite blocked "
                f"for {ref}; rebase/reset can preserve a stale Actor trailer",
                file=sys.stderr,
            )
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
