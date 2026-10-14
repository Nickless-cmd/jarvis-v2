#!/usr/bin/env python3
"""Dry-run, apply or roll back a signed recall ownership migration."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.runtime.db_core import connect
from core.services.recall_ownership_migration import (
    apply_report,
    classify_recall_ownership,
    rollback_report,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--apply-report", default="")
    modes.add_argument("--rollback-report", default="")
    parser.add_argument("--json-summary", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.dry_run:
        with connect() as conn:
            report = classify_recall_ownership(conn)
        summary = {
            "assigned_by_authoritative_link": report.authoritative_count,
            "assigned_by_owner_fallback": report.owner_fallback_count,
            "quarantined_conflicts": report.conflict_count,
            "database_rows_changed": 0,
            "report_id": report.report_id,
        }
    elif args.apply_report:
        result = apply_report(args.apply_report)
        summary = {
            "database_rows_changed": result.updated,
            "quarantined_conflicts": result.quarantined,
            "already_applied": result.already_applied,
            "report_id": args.apply_report,
        }
    else:
        result = rollback_report(args.rollback_report)
        summary = {
            "database_rows_restored": result.restored,
            "quarantined_drift": result.quarantined_drift,
            "already_rolled_back": result.already_rolled_back,
            "report_id": args.rollback_report,
        }
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
