"""Persistence primitives for the runtime open-loop thread registry.

This module owns registry schema, declaration and lookup. Signal persistence
and lifecycle transitions remain in ``db_runtime_executive_signals`` because
they update both the registry and ``runtime_open_loop_signals`` atomically.
"""
from __future__ import annotations

import sqlite3
from uuid import uuid4

from core.runtime.db_core import connect


THREAD_DECLARERS = ("jarvis", "bjorn")
# Loftet skal fange OPHOBNING, ikke arve den. Målt 15/11-2026: 146 ulukkede
# signaler (112 open + 34 stale), og ingen af dem ældre end 5 dage — så
# forfaldet (5d til stale + 7d til closed) kunne ikke rydde én eneste inden for
# den næste uge. Et loft under den målte population ville derfor afvise AL ny
# autonomi fra dag ét, hvilket er en blokade, ikke et værn. 300 er ~2x den målte
# population: rigeligt til normal vækst over forfaldets 12 dage, men stramt nok
# til at fange en løkke der rejser loops.
MAX_ACTIVE_OPEN_LOOPS = 300


class OpenLoopLimitReached(RuntimeError):
    """Raised before a thread/signal pair would exceed the active ceiling."""

    def __init__(self, *, active_signals: int, open_threads: int) -> None:
        self.limit = MAX_ACTIVE_OPEN_LOOPS
        self.active_signals = active_signals
        self.open_threads = open_threads
        super().__init__(
            f"active open-loop limit {self.limit} reached "
            f"(signals={active_signals}, threads={open_threads})"
        )


def _ensure_runtime_thread_registry_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_thread_registry (
            thread_id TEXT PRIMARY KEY,
            name TEXT NOT NULL COLLATE NOCASE,
            status TEXT NOT NULL DEFAULT 'open',
            declared_by TEXT NOT NULL,
            opened_in_run_id TEXT NOT NULL DEFAULT '',
            opened_at TEXT NOT NULL,
            closed_at TEXT NOT NULL DEFAULT '',
            closed_in_run_id TEXT NOT NULL DEFAULT '',
            closure_evidence TEXT NOT NULL DEFAULT ''
        )
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_runtime_thread_registry_open_name
        ON runtime_thread_registry(name) WHERE status = 'open'
        """
    )


def _thread_from_row(row: sqlite3.Row) -> dict[str, object]:
    return {key: row[key] for key in row.keys()}


def _require_open_thread(
    conn: sqlite3.Connection, thread_id: str
) -> dict[str, object]:
    _ensure_runtime_thread_registry_table(conn)
    row = conn.execute(
        "SELECT * FROM runtime_thread_registry WHERE thread_id = ?", (thread_id,)
    ).fetchone()
    if row is None:
        raise ValueError(f"unknown thread_id {thread_id!r}: declare it first")
    if row["status"] != "open":
        raise ValueError(f"thread {thread_id!r} is {row['status']}, not open")
    return _thread_from_row(row)


def _declare_runtime_thread_in_conn(
    conn: sqlite3.Connection,
    *,
    name: str,
    declared_by: str,
    opened_at: str,
    opened_in_run_id: str = "",
    thread_id: str = "",
) -> dict[str, object]:
    """Declare a thread on the caller's transaction."""
    clean_name = " ".join(str(name or "").split())
    if not clean_name:
        raise ValueError("a thread needs a name set on purpose")
    if declared_by not in THREAD_DECLARERS:
        raise ValueError(f"declared_by must be one of {THREAD_DECLARERS}")
    resolved_id = str(thread_id or "").strip() or f"thread-{uuid4().hex[:12]}"
    _ensure_runtime_thread_registry_table(conn)
    if not conn.in_transaction:
        conn.execute("BEGIN IMMEDIATE")
    signal_table_exists = conn.execute(
        "SELECT 1 FROM sqlite_master "
        "WHERE type = 'table' AND name = 'runtime_open_loop_signals'"
    ).fetchone()
    active_signals = 0
    if signal_table_exists is not None:
        active_signals = int(
            conn.execute(
                "SELECT COUNT(*) FROM runtime_open_loop_signals "
                "WHERE status IN ('open', 'softening', 'stale')"
            ).fetchone()[0]
        )
    open_threads = int(
        conn.execute(
            "SELECT COUNT(*) FROM runtime_thread_registry WHERE status = 'open'"
        ).fetchone()[0]
    )
    if (
        active_signals >= MAX_ACTIVE_OPEN_LOOPS
        or open_threads >= MAX_ACTIVE_OPEN_LOOPS
    ):
        raise OpenLoopLimitReached(
            active_signals=active_signals, open_threads=open_threads
        )
    clash = conn.execute(
        "SELECT thread_id FROM runtime_thread_registry "
        "WHERE name = ? AND status = 'open'",
        (clean_name,),
    ).fetchone()
    if clash is not None:
        raise ValueError(
            f"thread named {clean_name!r} is already open as {clash['thread_id']}"
        )
    conn.execute(
        """
        INSERT INTO runtime_thread_registry
            (thread_id, name, status, declared_by, opened_in_run_id, opened_at)
        VALUES (?, ?, 'open', ?, ?, ?)
        """,
        (resolved_id, clean_name, declared_by, opened_in_run_id, opened_at),
    )
    row = conn.execute(
        "SELECT * FROM runtime_thread_registry WHERE thread_id = ?", (resolved_id,)
    ).fetchone()
    if row is None:
        raise RuntimeError("runtime thread was not persisted")
    return _thread_from_row(row)


def declare_runtime_thread(
    *,
    name: str,
    declared_by: str,
    opened_at: str,
    opened_in_run_id: str = "",
    thread_id: str = "",
) -> dict[str, object]:
    """Declare a named thread by Jarvis or Bjorn."""
    with connect() as conn:
        thread = _declare_runtime_thread_in_conn(
            conn,
            name=name,
            declared_by=declared_by,
            opened_at=opened_at,
            opened_in_run_id=opened_in_run_id,
            thread_id=thread_id,
        )
        conn.commit()
    return thread


def get_runtime_thread(thread_id: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_runtime_thread_registry_table(conn)
        row = conn.execute(
            "SELECT * FROM runtime_thread_registry WHERE thread_id = ?", (thread_id,)
        ).fetchone()
    return _thread_from_row(row) if row is not None else None


def get_open_runtime_thread_by_name(name: str) -> dict[str, object] | None:
    """Look up the exact, case-insensitive assigned name; never fuzzy text."""
    clean_name = " ".join(str(name or "").split())
    with connect() as conn:
        _ensure_runtime_thread_registry_table(conn)
        row = conn.execute(
            "SELECT * FROM runtime_thread_registry WHERE name = ? AND status = 'open'",
            (clean_name,),
        ).fetchone()
    return _thread_from_row(row) if row is not None else None


def list_runtime_threads(
    *, status: str | None = None, limit: int = 50
) -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_runtime_thread_registry_table(conn)
        where, params = ("WHERE status = ?", (status,)) if status else ("", ())
        rows = conn.execute(
            f"SELECT * FROM runtime_thread_registry {where} "
            "ORDER BY opened_at DESC LIMIT ?",
            (*params, max(limit, 1)),
        ).fetchall()
    return [_thread_from_row(row) for row in rows]

