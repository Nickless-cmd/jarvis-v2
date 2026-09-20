"""Tests for session_topic_tracker — topic accumulation + DB persist fix.

2026-06-14 (Jarvis): tests for the int() coercion + exception safety
added to session_topic_accumulate after "int too large to convert to
SQLITE INTEGER" crash in production logs.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime


class TestAccumulateHappyPath:
    """Normal topic accumulation works."""

    def test_accumulate_new_topic(self, isolated_runtime):
        from core.runtime.db import session_topic_accumulate, session_topics_for_session

        session_topic_accumulate("session-1", "cache", 1, "", datetime.now(UTC).isoformat())
        topics = session_topics_for_session("session-1")
        assert len(topics) == 1
        assert topics[0]["topic_label"] == "cache"
        assert topics[0]["mention_count"] == 1

    def test_accumulate_existing_topic_increments(self, isolated_runtime):
        from core.runtime.db import session_topic_accumulate, session_topics_for_session

        session_topic_accumulate("session-2", "memory", 1, "", datetime.now(UTC).isoformat())
        session_topic_accumulate("session-2", "memory", 2, "", datetime.now(UTC).isoformat())
        topics = session_topics_for_session("session-2")
        assert len(topics) == 1
        assert topics[0]["mention_count"] == 3

    def test_accumulate_multiple_topics(self, isolated_runtime):
        from core.runtime.db import session_topic_accumulate, session_topics_for_session

        now = datetime.now(UTC).isoformat()
        session_topic_accumulate("session-3", "cache", 1, "", now)
        session_topic_accumulate("session-3", "memory", 2, "", now)
        session_topic_accumulate("session-3", "tools", 3, "", now)
        topics = session_topics_for_session("session-3")
        assert len(topics) == 3
        # Sorted by mention_count DESC
        assert topics[0]["topic_label"] == "tools"


class TestNullMentionCount:
    """2026-06-14 fix: NULL mention_count should not crash."""

    def test_null_mention_count_coerces_to_zero(self, isolated_runtime):
        """Simulate a row where mention_count is NULL (migration edge-case)."""
        from core.runtime.db import session_topic_accumulate, session_topics_for_session, connect

        # Simulate a LEGACY row with NULL mention_count. The current schema enforces
        # NOT NULL, so we recreate the pre-migration table shape (no NOT NULL) to plant
        # the edge-case row — exactly the state Jarvis' int(x or 0) coercion defends.
        now = datetime.now(UTC).isoformat()
        with connect() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS session_topics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    topic_label TEXT NOT NULL,
                    mention_count INTEGER,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    UNIQUE(session_id, topic_label)
                )"""
            )
            conn.execute(
                "INSERT INTO session_topics (session_id, topic_label, mention_count, first_seen, last_seen) "
                "VALUES (?, ?, ?, ?, ?)",
                ("session-null", "broken-topic", None, now, now),
            )
            conn.commit()

        # Now accumulate should NOT crash — int(None or 0) = 0
        session_topic_accumulate("session-null", "broken-topic", 1, "", now)
        topics = session_topics_for_session("session-null")
        assert len(topics) == 1
        # mention_count should now be 0 + 1 = 1
        assert topics[0]["mention_count"] == 1


class TestExceptionSafety:
    """2026-06-14 fix: wrapped in try/except, never crashes caller."""

    def test_accumulate_does_not_crash_on_db_error(self):
        """Calling with invalid session_id type should be caught by try/except."""
        from core.runtime.db import session_topic_accumulate

        # This should not raise — the try/except should swallow the DB error
        session_topic_accumulate(None, "test", 1)  # type: ignore

    def test_accumulate_with_empty_topic_label(self, isolated_runtime):
        """Empty topic labels should not crash — they just get inserted."""
        from core.runtime.db import session_topic_accumulate, session_topics_for_session

        now = datetime.now(UTC).isoformat()
        session_topic_accumulate("session-empty", "", 1, "", now)
        topics = session_topics_for_session("session-empty")
        assert len(topics) >= 1


class TestCleanup:
    """session_topic_cleanup edge cases."""

    def test_cleanup_removes_old_topics(self, isolated_runtime):
        from core.runtime.db import (
            session_topic_accumulate,
            session_topics_for_session,
            session_topic_cleanup,
        )

        now = datetime.now(UTC).isoformat()
        session_topic_accumulate("session-old", "cache", 1, "", now)
        # Cleanup with 0-day max_age should delete everything
        deleted = session_topic_cleanup(max_age_days=0)
        topics = session_topics_for_session("session-old")
        assert len(topics) == 0


class TestPersistRace:
    """Målt 20/9-2026 ved genstart: «session_topics: DB persist failed:
    dictionary changed size during iteration» (WARNING — topics tabt).

    Kaldestederne er flertrådede: `visible_runs` starter daemon-tråde til
    post-process, og `procedure_bank_pipeline` kalder `load_session_topics`,
    som *skriver* til samme store som et samtidigt run persisterer fra.
    Modul-staten havde ingen lås. `_persist_session_topics` tager nu et
    snapshot under `_STATE_LOCK`, så en samtidig skrivning ikke kan sprænge
    iterationen.
    """

    def _reset(self):
        from core.services import session_topic_tracker as stt

        stt._session_topics.clear()
        stt._session_turn_counts.clear()
        stt._TOPICS_DB_PERSISTED.clear()

    def test_samtidig_mutation_spraenger_ikke_persist(self, monkeypatch, caplog):
        """Den anden tråd skriver nye topics midt i iterationen — før kastede
        det RuntimeError, som `except Exception` slugte til en WARNING."""
        from core.services import session_topic_tracker as stt
        import core.runtime.db as db

        self._reset()
        stt._accumulate_topics("race-1", ["Alpha", "Beta"])

        calls: list[dict] = []

        def _mutating_accumulate(**kw):
            calls.append(kw)
            # Efterligner den samtidige skrivning: et nyt topic lander i
            # store mens persist-løkken kører.
            stt._session_topics["race-1"][f"ny-{len(calls)}"] = {
                "label": "Ny",
                "count": 1,
                "first_seen": "",
                "last_seen": "",
            }

        monkeypatch.setattr(db, "session_topic_accumulate", _mutating_accumulate)

        with caplog.at_level("WARNING"):
            stt._persist_session_topics("race-1")  # må ikke kaste

        # Snapshot: de to poster der fandtes da vi tog det — ikke de nye.
        assert len(calls) == 2
        assert not any(
            "DB persist failed" in r.getMessage() for r in caplog.records
        ), [r.getMessage() for r in caplog.records]

    def test_laasen_er_reentrant(self):
        """`clear_session_topics` kalder `_persist_session_topics` under låsen.
        En almindelig Lock ville dørlåse; RLock gør det lovligt."""
        from core.services import session_topic_tracker as stt

        with stt._STATE_LOCK:
            with stt._STATE_LOCK:
                pass

    def test_clear_doer_ikke_doerlaase(self):
        from core.services import session_topic_tracker as stt

        self._reset()
        stt._accumulate_topics("race-2", ["Gamma"])
        stt.clear_session_topics("race-2")  # må ikke hænge
        assert "race-2" not in stt._session_topics
