"""Schema for the claude_dispatch_* tables.

Kept in its own module so the claude-code dispatch subsystem can own its
schema without growing core/runtime/db.py. Called once from db.init_db().
"""
from __future__ import annotations

import sqlite3


def ensure_claude_dispatch_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS claude_dispatch_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL UNIQUE,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            spec_json TEXT NOT NULL,
            status TEXT NOT NULL,
            tokens_used INTEGER NOT NULL DEFAULT 0,
            exit_code INTEGER,
            diff_summary TEXT,
            error TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS claude_dispatch_budget (
            hour_bucket TEXT PRIMARY KEY,
            dispatch_count INTEGER NOT NULL DEFAULT 0,
            tokens_used INTEGER NOT NULL DEFAULT 0
        )
        """
    )
