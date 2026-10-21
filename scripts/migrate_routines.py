#!/usr/bin/env python3
"""Dry-run or apply the fail-closed legacy Routine migration."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from core.runtime.db_core import connect
from core.services.routine_migration import (
    apply_report,
    classify_legacy_sources,
    reconcile_system_definitions,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply-report", metavar="REPORT_ID")
    mode.add_argument("--reconcile-system-definitions", action="store_true")
    parser.add_argument("--json-summary", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        with connect() as conn:
            report = classify_legacy_sources(conn)
        reasons: dict[str, int] = {}
        for item in report.quarantine:
            reasons[item.reason_code] = reasons.get(item.reason_code, 0) + 1
        summary = {
            "report_id": report.report_id,
            "assigned_count": report.assigned_count,
            "quarantine_count": report.quarantine_count,
            "quarantine_reasons": reasons,
            "database_rows_changed": 0,
        }
    elif args.apply_report:
        result = apply_report(args.apply_report)
        summary = {
            "created_routines": result.created_routines,
            "created_quarantine": result.created_quarantine,
            "already_applied": result.already_applied,
        }
    else:
        result = reconcile_system_definitions(apply=True)
        summary = {
            "discovered": list(result.discovered),
            "created": list(result.created),
            "existing": list(result.existing),
        }
    print(json.dumps(summary, sort_keys=True) if args.json_summary else summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
