"""Tests for inner LLM enrichment service."""

import sqlite3

from core.runtime import db as jarvis_db


def _get_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cursor.fetchall()]


def test_private_inner_notes_has_enriched_column() -> None:
    jarvis_db.init_db()
    conn = jarvis_db.connect()
    cols = _get_columns(conn, "private_inner_notes")
    conn.close()
    assert "enriched" in cols


def test_private_growth_notes_has_enriched_column() -> None:
    jarvis_db.init_db()
    conn = jarvis_db.connect()
    cols = _get_columns(conn, "private_growth_notes")
    conn.close()
    assert "enriched" in cols


def test_protected_inner_voices_has_enriched_column() -> None:
    jarvis_db.init_db()
    conn = jarvis_db.connect()
    cols = _get_columns(conn, "protected_inner_voices")
    conn.close()
    assert "enriched" in cols
