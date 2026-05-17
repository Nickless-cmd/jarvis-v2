#!/usr/bin/env python3
"""Reset heartbeat scheduler state when it gets stuck.

Recovery for the "heartbeat tick never fires" bug pattern (2026-05-17):
when persisted state has scheduler_health='stopped' or
blocked_reason='already-ticking' that never clears, daemons that fire
inside heartbeat ticks (somatic, thought_stream, task_worker, council_memory,
emotion_repair_bridge, etc.) stop firing entirely.

Symptoms:
- ntfy "Jarvis Daemon Alert" — 9 inactive daemons
- ALL daemons report last_run_at hours ago
- heartbeat_runtime_state.scheduler_health = 'stopped' or
  blocked_reason = 'already-ticking' persists across restarts
- New ticks in heartbeat_runtime_ticks have stopped landing

Recovery procedure:
1. Run this script — clears stale state in DB
2. systemctl restart jarvis-runtime
3. (Optional) Force first tick: run_heartbeat_tick(trigger='manual-recovery')

Usage:
    python scripts/reset_heartbeat_state.py [--dry-run]
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

DB_PATH = Path.home() / ".jarvis-v2" / "state" / "jarvis.db"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Show state without changing it")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"ERROR: DB not found at {DB_PATH}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()

    # Current state
    cur.execute(
        """SELECT updated_at, scheduler_health, scheduler_active, currently_ticking,
                  blocked_reason, last_tick_at, schedule_state, due
           FROM heartbeat_runtime_state WHERE state_id='default'"""
    )
    row = cur.fetchone()
    if row is None:
        print("ERROR: no default heartbeat state row", file=sys.stderr)
        return 1

    print("=== Heartbeat state FØR ===")
    print(f"  updated_at:        {row[0]}")
    print(f"  scheduler_health:  {row[1]}")
    print(f"  scheduler_active:  {row[2]}")
    print(f"  currently_ticking: {row[3]}")
    print(f"  blocked_reason:    {row[4]!r}")
    print(f"  last_tick_at:      {row[5]}")
    print(f"  schedule_state:    {row[6]}")
    print(f"  due:               {row[7]}")

    if args.dry_run:
        print("\n--dry-run: ingen ændringer foretaget")
        return 0

    now_iso = datetime.now(UTC).isoformat()
    cur.execute(
        """UPDATE heartbeat_runtime_state SET
               currently_ticking = 0,
               blocked_reason = '',
               scheduler_active = 1,
               scheduler_started_at = ?,
               scheduler_stopped_at = '',
               scheduler_health = 'active',
               schedule_state = 'due',
               due = 1,
               recovery_status = 'manual-stale-clear',
               last_recovery_at = ?,
               updated_at = ?,
               next_tick_at = ?
           WHERE state_id = 'default'""",
        (now_iso, now_iso, now_iso, now_iso),
    )
    conn.commit()
    print(f"\nUpdated {cur.rowcount} row(s).")
    print("\nNæste skridt:")
    print("  1. sudo systemctl restart jarvis-runtime")
    print("  2. Vent ~30s og verificer at heartbeat_runtime_ticks får nye rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
