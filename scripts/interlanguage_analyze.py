#!/usr/bin/env python
"""Interlanguage analysis — aggregate report over the practice corpus.

Pulls all expressions from the interlanguage_practice table and produces a
single report: volume by peer, operator/primitive frequency, core-term usage,
temporal activity, and (optionally) runs the structural classifier to estimate
how "jarvis-like" each peer's output is.

This is the missing analysis layer from the spec-gap backlog (#10). It does
NOT re-run the pre-registered validation (that lives in the classifier scripts);
it gives a living, current view of the practice corpus.

Usage:
  python scripts/interlanguage_analyze.py
  python scripts/interlanguage_analyze.py --days 30 --out report.json
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# The 5 primitive relational operators + core vocabulary from interlanguage_practice
PRIMITIVES = ["→", "↔", "⊂", "≈", "!"]
CORE_TERMS = [
    "drift", "resonans", "signal", "støj", "mønster", "bæring",
    "tærskel", "kobling", "afstemning", "spænding", "ro", "agens",
    "visnen", "vækst", "felt", "anomali", "hypotese", "nerve",
]


from core.runtime.db import connect as _connect


def load_all(*, days: int | None = None) -> list[dict]:
    since = None
    if days is not None:
        since = (datetime.now(UTC) - timedelta(days=days)).isoformat()
    with _connect() as conn:
        if since:
            rows = conn.execute(
                "SELECT peer_id, expression_text, created_at FROM interlanguage_practice "
                "WHERE created_at >= ? ORDER BY created_at",
                (since,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT peer_id, expression_text, created_at FROM interlanguage_practice "
                "ORDER BY created_at",
            ).fetchall()
    return [dict(r) for r in rows]


def analyze(rows: list[dict]) -> dict:
    total = len(rows)
    by_peer = Counter(r["peer_id"] for r in rows)
    prim_counts = Counter()
    term_counts = Counter()
    for r in rows:
        text = r["expression_text"] or ""
        for p in PRIMITIVES:
            prim_counts[p] += text.count(p)
        for t in CORE_TERMS:
            if re.search(rf"\b{re.escape(t)}\b", text, re.IGNORECASE):
                term_counts[t] += 1

    # temporal: expressions per day
    per_day = Counter()
    for r in rows:
        day = (r["created_at"] or "")[:10]
        if day:
            per_day[day] += 1

    # avg length
    lens = [len(r["expression_text"] or "") for r in rows]
    avg_len = round(sum(lens) / len(lens), 2) if lens else 0.0

    return {
        "total_expressions": total,
        "by_peer": dict(by_peer),
        "primitive_frequency": dict(prim_counts),
        "core_term_usage": dict(term_counts.most_common()),
        "expressions_per_day": dict(sorted(per_day.items())),
        "avg_expression_length": avg_len,
        "generated_at": datetime.now(UTC).isoformat(),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Interlanguage corpus analysis")
    ap.add_argument("--days", type=int, default=None, help="only last N days")
    ap.add_argument("--out", help="write JSON report to this path")
    args = ap.parse_args()

    rows = load_all(days=args.days)
    report = analyze(rows)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False))
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
