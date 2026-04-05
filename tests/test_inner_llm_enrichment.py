"""Tests for inner LLM enrichment service."""

import sqlite3
from datetime import datetime, timezone

from core.runtime import db as jarvis_db


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _insert_inner_note(run_id: str = "run-001") -> None:
    jarvis_db.record_private_inner_note(
        note_id=f"private-inner-note:{run_id}",
        source="visible-selected-work-note",
        run_id=run_id,
        work_id="work-001",
        status="completed",
        note_kind="bounded-reflection",
        focus="workspace-search",
        uncertainty="low",
        identity_alignment="aligned",
        work_signal="task-completed",
        private_summary="template summary",
        created_at=_iso_now(),
    )


def _insert_growth_note(run_id: str = "run-001") -> None:
    jarvis_db.record_private_growth_note(
        record_id=f"private-growth-note:{run_id}",
        source="private-inner-note:private-runtime-grounded",
        run_id=run_id,
        work_id="work-001",
        learning_kind="reinforce",
        lesson="template lesson",
        mistake_signal="",
        helpful_signal="template helpful signal",
        identity_signal="steady",
        confidence="medium",
        created_at=_iso_now(),
    )


def _insert_inner_voice(run_id: str = "run-001") -> None:
    jarvis_db.record_protected_inner_voice(
        voice_id=f"protected-inner-voice:{run_id}",
        source="private-state+private-self-model",
        run_id=run_id,
        work_id="work-001",
        mood_tone="steady",
        self_position="observing",
        current_concern="stability:medium",
        current_pull="retain-current-pattern",
        voice_line="steady | position=observing | concern=stability | pull=retain",
        created_at=_iso_now(),
    )


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


def test_update_private_inner_note_enriched() -> None:
    jarvis_db.init_db()
    _insert_inner_note("run-enrich-1")

    jarvis_db.update_private_inner_note_enriched(
        run_id="run-enrich-1",
        enriched_summary="LLM-generated reflective summary",
    )

    conn = jarvis_db.connect()
    row = conn.execute(
        "SELECT private_summary, enriched FROM private_inner_notes WHERE run_id = ?",
        ("run-enrich-1",),
    ).fetchone()
    conn.close()
    assert row[0] == "LLM-generated reflective summary"
    assert row[1] == 1


def test_update_private_growth_note_enriched() -> None:
    jarvis_db.init_db()
    _insert_growth_note("run-enrich-2")

    jarvis_db.update_private_growth_note_enriched(
        run_id="run-enrich-2",
        enriched_lesson="LLM lesson",
        enriched_helpful_signal="LLM helpful signal",
    )

    conn = jarvis_db.connect()
    row = conn.execute(
        "SELECT lesson, helpful_signal, enriched FROM private_growth_notes WHERE run_id = ?",
        ("run-enrich-2",),
    ).fetchone()
    conn.close()
    assert row[0] == "LLM lesson"
    assert row[1] == "LLM helpful signal"
    assert row[2] == 1


def test_update_protected_inner_voice_enriched() -> None:
    jarvis_db.init_db()
    _insert_inner_voice("run-enrich-3")

    jarvis_db.update_protected_inner_voice_enriched(
        run_id="run-enrich-3",
        enriched_voice_line="LLM voice line",
    )

    conn = jarvis_db.connect()
    row = conn.execute(
        "SELECT voice_line, enriched FROM protected_inner_voices WHERE run_id = ?",
        ("run-enrich-3",),
    ).fetchone()
    conn.close()
    assert row[0] == "LLM voice line"
    assert row[1] == 1
