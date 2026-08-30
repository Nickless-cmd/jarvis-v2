#!/usr/bin/env python3
"""Reject rebases because replayed commits retain stale actor trailers."""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    del argv
    print(
        "commit attribution: rebase is blocked because replay preserves a "
        "stale Actor trailer; merge the target branch instead",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
