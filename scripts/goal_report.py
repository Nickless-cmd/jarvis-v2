#!/usr/bin/env python3
"""Kør goal-reporteren: skriv tick-kvalitet, heed-rate og adherence til målet.

Brug:
    python scripts/goal_report.py              # mål og skriv
    python scripts/goal_report.py --dry-run    # se tallene uden at skrive
    python scripts/goal_report.py --days 30    # andet vindue
"""
from __future__ import annotations

import json
import sys

from core.services.goal_reporter import report_goal_metrics


def main(argv: list[str]) -> int:
    dry = "--dry-run" in argv
    days = 7
    if "--days" in argv:
        try:
            days = int(argv[argv.index("--days") + 1])
        except (IndexError, ValueError):
            print("--days kræver et heltal", file=sys.stderr)
            return 2

    res = report_goal_metrics(days=days, dry_run=dry)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if res.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
