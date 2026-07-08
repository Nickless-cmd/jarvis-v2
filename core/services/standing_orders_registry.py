"""Standing-orders registry — INDEPENDENT grounding for the reasoning-interceptor's standing-orders
detector. A small owner-managed store of persistent rules Jarvis must keep. Separate from
db_decisions (per-run conflicts). Self-safe: every read returns [] on failure."""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Any

from core.runtime.db_core import connect


def _ensure(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS standing_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            match_key TEXT NOT NULL DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )"""
    )


def add_standing_order(*, text: str, match_key: str = "") -> int:
    with connect() as conn:
        _ensure(conn)
        cur = conn.execute(
            "INSERT INTO standing_orders (text, match_key, active, created_at) VALUES (?, ?, 1, ?)",
            (str(text)[:400], str(match_key)[:64], datetime.now(UTC).isoformat()),
        )
        conn.commit()
        return int(cur.lastrowid or 0)


def set_standing_order_active(order_id: int, *, active: bool) -> None:
    try:
        with connect() as conn:
            _ensure(conn)
            conn.execute("UPDATE standing_orders SET active = ? WHERE id = ?",
                         (1 if active else 0, int(order_id)))
            conn.commit()
    except Exception:
        pass


def list_active_standing_orders() -> list[dict[str, Any]]:
    try:
        with connect() as conn:
            _ensure(conn)
            rows = conn.execute(
                "SELECT id, text, match_key FROM standing_orders WHERE active = 1 ORDER BY id"
            ).fetchall()
            return [{"id": r["id"], "text": r["text"], "match_key": r["match_key"]} for r in rows]
    except Exception:
        return []
