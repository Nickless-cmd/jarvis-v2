"""Tests for session summary generation and retrieval."""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest


def _memory_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# session_summaries table
# ---------------------------------------------------------------------------


class TestSessionSummariesTable:
    def test_ensure_creates_table(self) -> None:
        from core.runtime.db import _ensure_session_summaries_table

        conn = _memory_conn()
        _ensure_session_summaries_table(conn)
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='session_summaries'").fetchall()
        assert len(rows) == 1

    def test_ensure_idempotent(self) -> None:
        from core.runtime.db import _ensure_session_summaries_table

        conn = _memory_conn()
        _ensure_session_summaries_table(conn)
        _ensure_session_summaries_table(conn)


# ---------------------------------------------------------------------------
# session_summary_insert
# ---------------------------------------------------------------------------


class TestSessionSummaryInsert:
    def test_inserts_summary(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from core.runtime import db as db_mod

        conn = _memory_conn()

        from contextlib import contextmanager

        @contextmanager
        def fake_connect():
            yield conn

        monkeypatch.setattr(db_mod, "connect", fake_connect)

        db_mod.session_summary_insert(
            session_id="chat-abc123",
            run_id="visible-xyz",
            summary="Emne: Test | Resultat: Alt fungerer",
            key_topics="testing",
            decisions_made="none",
        )

        rows = conn.execute("SELECT * FROM session_summaries").fetchall()
        assert len(rows) == 1
        assert rows[0]["session_id"] == "chat-abc123"
        assert rows[0]["summary"] == "Emne: Test | Resultat: Alt fungerer"
        assert rows[0]["key_topics"] == "testing"

    def test_truncates_long_summary(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from core.runtime import db as db_mod

        conn = _memory_conn()

        from contextlib import contextmanager

        @contextmanager
        def fake_connect():
            yield conn

        monkeypatch.setattr(db_mod, "connect", fake_connect)

        db_mod.session_summary_insert(
            session_id="chat-abc",
            summary="x" * 5000,
        )

        rows = conn.execute("SELECT * FROM session_summaries").fetchall()
        assert len(rows[0]["summary"]) == 2000


# ---------------------------------------------------------------------------
# session_summary_recent
# ---------------------------------------------------------------------------


class TestSessionSummaryRecent:
    def test_returns_recent_entries(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from core.runtime import db as db_mod

        conn = _memory_conn()

        from contextlib import contextmanager

        @contextmanager
        def fake_connect():
            yield conn

        monkeypatch.setattr(db_mod, "connect", fake_connect)

        for i in range(5):
            db_mod.session_summary_insert(
                session_id=f"chat-{i}",
                summary=f"Summary {i}",
            )

        results = db_mod.session_summary_recent(limit=3)
        assert len(results) == 3
        assert "summary" in results[0]
        assert "session_id" in results[0]

    def test_empty_when_no_summaries(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from core.runtime import db as db_mod

        conn = _memory_conn()

        from contextlib import contextmanager

        @contextmanager
        def fake_connect():
            yield conn

        monkeypatch.setattr(db_mod, "connect", fake_connect)

        results = db_mod.session_summary_recent(limit=3)
        assert results == []


# ---------------------------------------------------------------------------
# session_summary_for_session
# ---------------------------------------------------------------------------


class TestSessionSummaryForSession:
    def test_returns_latest_for_session(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from core.runtime import db as db_mod

        conn = _memory_conn()

        from contextlib import contextmanager

        @contextmanager
        def fake_connect():
            yield conn

        monkeypatch.setattr(db_mod, "connect", fake_connect)

        db_mod.session_summary_insert(session_id="chat-1", summary="First")
        db_mod.session_summary_insert(session_id="chat-1", summary="Second")

        result = db_mod.session_summary_for_session("chat-1")
        assert result is not None
        assert result["summary"] == "Second"

    def test_returns_none_for_missing_session(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from core.runtime import db as db_mod

        conn = _memory_conn()

        from contextlib import contextmanager

        @contextmanager
        def fake_connect():
            yield conn

        monkeypatch.setattr(db_mod, "connect", fake_connect)

        result = db_mod.session_summary_for_session("nonexistent")
        assert result is None


# ---------------------------------------------------------------------------
# session_summary_cleanup
# ---------------------------------------------------------------------------


class TestSessionSummaryCleanup:
    def test_removes_old_summaries(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from core.runtime import db as db_mod

        conn = _memory_conn()
        db_mod._ensure_session_summaries_table(conn)

        old_time = (datetime.now(UTC) - timedelta(days=120)).isoformat()
        recent_time = (datetime.now(UTC) - timedelta(days=10)).isoformat()
        conn.execute(
            "INSERT INTO session_summaries (session_id, summary, created_at) VALUES (?, ?, ?)",
            ("old", "Old summary", old_time),
        )
        conn.execute(
            "INSERT INTO session_summaries (session_id, summary, created_at) VALUES (?, ?, ?)",
            ("recent", "Recent summary", recent_time),
        )
        conn.commit()

        from contextlib import contextmanager

        @contextmanager
        def fake_connect():
            yield conn

        monkeypatch.setattr(db_mod, "connect", fake_connect)

        deleted = db_mod.session_summary_cleanup(max_age_days=90)
        assert deleted == 1

        remaining = conn.execute("SELECT * FROM session_summaries").fetchall()
        assert len(remaining) == 1
        assert remaining[0]["session_id"] == "recent"


# ---------------------------------------------------------------------------
# generate_session_summary
# ---------------------------------------------------------------------------


class TestGenerateSessionSummary:
    def test_generates_from_messages(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from apps.api.jarvis_api.services import session_distillation as sd

        monkeypatch.setattr(
            "apps.api.jarvis_api.services.daemon_llm.daemon_llm_call",
            lambda prompt, **kw: "Emne: Test samtale | Resultat: Alt fungerede",
        )

        stored: list[dict] = []

        def fake_insert(**kwargs: object) -> None:
            stored.append(dict(kwargs))

        monkeypatch.setattr(
            "core.runtime.db.session_summary_insert",
            fake_insert,
        )

        result = sd.generate_session_summary(
            session_id="chat-test",
            run_id="run-1",
            user_message="Hvad er status?",
            assistant_response="Alt er godt.",
        )

        assert "Test samtale" in result
        assert len(stored) == 1
        assert stored[0]["session_id"] == "chat-test"

    def test_returns_empty_on_no_context(self) -> None:
        from apps.api.jarvis_api.services.session_distillation import (
            generate_session_summary,
        )

        result = generate_session_summary(
            session_id="chat-empty",
            user_message="",
            assistant_response="",
        )
        assert result == ""

    def test_handles_llm_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "apps.api.jarvis_api.services.daemon_llm.daemon_llm_call",
            lambda prompt, **kw: "",
        )

        from apps.api.jarvis_api.services.session_distillation import (
            generate_session_summary,
        )

        result = generate_session_summary(
            session_id="chat-fail",
            user_message="Test",
            assistant_response="Response",
        )
        assert result == ""


# ---------------------------------------------------------------------------
# build_previous_session_summaries
# ---------------------------------------------------------------------------


class TestBuildPreviousSessionSummaries:
    def test_builds_text_block(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "core.runtime.db.session_summary_recent",
            lambda limit=3: [
                {"summary": "Emne: A | Resultat: B", "created_at": "2026-04-13T10:00:00"},
                {"summary": "Emne: C | Resultat: D", "created_at": "2026-04-13T09:00:00"},
            ],
        )

        from apps.api.jarvis_api.services.session_distillation import (
            build_previous_session_summaries,
        )

        result = build_previous_session_summaries(limit=3)
        assert result is not None
        assert "Tidligere samtaler" in result
        assert "Emne: A" in result
        assert "Emne: C" in result

    def test_returns_none_when_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            "core.runtime.db.session_summary_recent",
            lambda limit=3: [],
        )

        from apps.api.jarvis_api.services.session_distillation import (
            build_previous_session_summaries,
        )

        result = build_previous_session_summaries(limit=3)
        assert result is None
