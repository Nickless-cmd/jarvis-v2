#!/usr/bin/env python3
"""Cache hit rate monitor.

Bygges 2026-06-09 efter Bjørns ønske om at logge cache rate hver halve
time, så vi kan se trend over dagen/døgnet og verificere DeepSeek's
påståede "hours to days" TTL empirisk.

Læser cost.recorded events fra Jarvis' eventbus, aggregerer cache
hit/miss-tokens i forskellige tidsvinduer (30 min, 6 timer, 24 timer)
og logger til ~/.jarvis-v2/logs/cache_rate.jsonl. Hver linje er en
tidsstempelet snapshot — kan plottes/analyseres senere.

Run:
  /opt/conda/envs/ai/bin/python3 /media/projects/jarvis-v2/scripts/cache_rate_monitor.py

Setup som cron-job hver 30 min (på Jarvis-host):
  */30 * * * * /opt/conda/envs/ai/bin/python3 /media/projects/jarvis-v2/scripts/cache_rate_monitor.py

JSONL output schema per linje:
  {"ts": "2026-06-09T19:30:00Z", "window_30m": {...}, "window_6h": {...},
   "window_24h": {...}, "by_lane": {...}, "n_total_events": N}
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

HOME = Path(os.environ.get("HOME", "/root")) / ".jarvis-v2"
DB_PATH = HOME / "state" / "jarvis.db"
LOG_PATH = HOME / "logs" / "cache_rate.jsonl"


def _aggregate_events(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate hit/miss across a list of cost.recorded payloads."""
    hit = 0
    miss = 0
    in_tokens = 0
    n = 0
    for p in rows:
        try:
            h = int(p.get("cache_hit_tokens") or 0)
            m = int(p.get("cache_miss_tokens") or 0)
            hit += h
            miss += m
            in_tokens += int(p.get("input_tokens") or 0)
            n += 1
        except (ValueError, TypeError):
            continue
    total = hit + miss
    return {
        "n_events": n,
        "input_tokens": in_tokens,
        "cache_hit_tokens": hit,
        "cache_miss_tokens": miss,
        "hit_rate_pct": round(100 * hit / total, 2) if total else 0.0,
    }


def _by_lane(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Same aggregation grouped by lane."""
    by_lane: dict[str, list[dict[str, Any]]] = {}
    for p in rows:
        lane = str(p.get("lane") or "?")
        by_lane.setdefault(lane, []).append(p)
    return {lane: _aggregate_events(items) for lane, items in by_lane.items()}


def _fetch_costs(con: sqlite3.Connection, since_sql: str) -> list[dict[str, Any]]:
    """Fetch cost rows from the costs table as dicts with cache_hit/miss keys."""
    try:
        rows = con.execute(
            f"SELECT lane, input_tokens, cache_hit_tokens, cache_miss_tokens, "
            f"created_at FROM costs "
            f"WHERE created_at > {since_sql}",
        ).fetchall()
    except Exception:
        return []
    out = []
    for r in rows:
        out.append({
            "lane": r["lane"],
            "input_tokens": r["input_tokens"],
            "cache_hit_tokens": r["cache_hit_tokens"],
            "cache_miss_tokens": r["cache_miss_tokens"],
        })
    return out


def collect_snapshot() -> dict[str, Any]:
    """Read costs from DB and produce a rich snapshot — ALL lanes."""
    if not DB_PATH.exists():
        return {"ts": datetime.now(UTC).isoformat(), "error": "no DB"}

    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row

    win_30m = _fetch_costs(con, "datetime('now', '-30 minutes')")
    win_6h = _fetch_costs(con, "datetime('now', '-6 hours')")
    win_24h = _fetch_costs(con, "datetime('now', '-1 day')")

    con.close()

    return {
        "ts": datetime.now(UTC).isoformat(),
        "window_30m": _aggregate_events(win_30m),
        "window_6h": _aggregate_events(win_6h),
        "window_24h": _aggregate_events(win_24h),
        "by_lane_24h": _by_lane(win_24h),
        "n_total_24h": len(win_24h),
    }


def append_log(snapshot: dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(snapshot, ensure_ascii=False) + "\n")


def main() -> int:
    snap = collect_snapshot()
    append_log(snap)
    # Pretty print to stdout for cron logs
    w30 = snap.get("window_30m", {})
    w6 = snap.get("window_6h", {})
    w24 = snap.get("window_24h", {})
    print(
        f"[{snap['ts']}] "
        f"30m: {w30.get('hit_rate_pct', 0):.1f}% (n={w30.get('n_events', 0)}) | "
        f"6h: {w6.get('hit_rate_pct', 0):.1f}% (n={w6.get('n_events', 0)}) | "
        f"24h: {w24.get('hit_rate_pct', 0):.1f}% (n={w24.get('n_events', 0)})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
