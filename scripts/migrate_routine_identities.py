#!/usr/bin/env python3
"""Dry-run/apply the explicit legacy identity bridge required by Routines."""
from __future__ import annotations

import argparse
import json

from core.services.routine_identity_migration import (
    apply_legacy_identity_cutover,
    plan_legacy_identity_cutover,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--expected-watermark", default="")
    args = parser.parse_args()

    report = plan_legacy_identity_cutover()
    if args.dry_run:
        print(json.dumps({
            "watermark": report.watermark,
            "create_count": report.create_count,
            "already_linked_count": report.linked_count,
            "conflict_count": report.conflict_count,
            "conflict_reasons": sorted({
                item.reason_code for item in report.items if item.reason_code
            }),
        }, sort_keys=True))
        return 0
    result = apply_legacy_identity_cutover(
        expected_watermark=args.expected_watermark
    )
    print(json.dumps({
        "created": result.created,
        "already_linked": result.already_linked,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
