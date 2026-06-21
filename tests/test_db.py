"""Smoke-test for db-skema — sikrer at security-guard-tabellerne oprettes (spec 2026-06-21)."""
from __future__ import annotations

from core.runtime.db import connect


def _tables() -> set[str]:
    with connect() as conn:
        return {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}


def _cols(table: str) -> set[str]:
    with connect() as conn:
        return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def test_security_guard_tables_created(isolated_runtime):
    t = _tables()
    assert {"abuse_events", "user_flags", "audit_log"} <= t


def test_chat_sessions_lock_columns(isolated_runtime):
    cols = _cols("chat_sessions")
    assert {"locked", "locked_reason", "locked_at"} <= cols
