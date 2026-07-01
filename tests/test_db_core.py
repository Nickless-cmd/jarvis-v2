"""Tests for core/runtime/db_core.py — DB-forbindelse + concurrency-hærdning."""
from __future__ import annotations

from core.runtime.db import connect


def test_connect_sets_busy_timeout():
    # Rygrads-fix (1. jul): connect() skal sætte busy_timeout, så en låst DB VENTER
    # i stedet for at fejle øjeblikkeligt (OperationalError) — fixede eventbus-writer-fejl.
    with connect() as conn:
        val = conn.execute("PRAGMA busy_timeout").fetchone()[0]
    assert int(val) >= 5000


def test_connect_row_factory():
    with connect() as conn:
        conn.row_factory  # sat til sqlite3.Row
        row = conn.execute("SELECT 1 AS x").fetchone()
    assert row["x"] == 1  # navngivet kolonne-adgang virker
