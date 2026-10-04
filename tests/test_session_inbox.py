"""Tests for session_inbox.py (daemon-interruption gate).

Verifies queueing during active sessions, flush behavior, urgent bypass,
and fallback timeout. Cross-process polling-listener behavior is tested
via direct flush_session calls; the actual thread loop is too slow for
unit tests.
"""
import json
import sqlite3
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest


@pytest.fixture
def tmp_db(monkeypatch):
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    path = Path(tmp.name)
    import core.services.session_inbox as mod
    monkeypatch.setattr(mod, "DB_PATH", path)
    # Seed events table since is_session_active queries it
    with sqlite3.connect(str(path)) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        conn.commit()
    yield path
    path.unlink(missing_ok=True)


def _seed_active_event(db_path, session_id, secs_ago=10):
    when = (datetime.now(UTC) - timedelta(seconds=secs_ago)).isoformat()
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            "INSERT INTO events (kind, payload_json, created_at) VALUES (?, ?, ?)",
            (
                "channel.chat_message_appended",
                json.dumps({"session_id": session_id, "message": {"role": "user"}}),
                when,
            ),
        )
        conn.commit()


# ── is_session_active ────────────────────────────────────────────────────


def test_active_when_recent_event(tmp_db):
    from core.services.session_inbox import is_session_active
    _seed_active_event(tmp_db, "chat-abc", secs_ago=60)
    assert is_session_active("chat-abc") is True


def test_inactive_when_no_events(tmp_db):
    from core.services.session_inbox import is_session_active
    assert is_session_active("chat-nobody") is False


def test_inactive_when_event_too_old(tmp_db):
    from core.services.session_inbox import is_session_active
    _seed_active_event(tmp_db, "chat-old", secs_ago=900)  # 15 min ago
    assert is_session_active("chat-old", window_seconds=300) is False


# ── enqueue + pending_for_session ───────────────────────────────────────


def test_enqueue_and_pending(tmp_db):
    from core.services.session_inbox import enqueue, pending_for_session
    enqueue(session_id="s1", content="hello from daemon", source="test-d")
    pending = pending_for_session("s1")
    assert len(pending) == 1
    assert pending[0]["content"] == "hello from daemon"
    assert pending[0]["source"] == "test-d"


def test_enqueue_rejects_empty(tmp_db):
    from core.services.session_inbox import enqueue
    out = enqueue(session_id="s1", content="", source="x")
    assert out["status"] == "error"


def test_pending_isolated_per_session(tmp_db):
    from core.services.session_inbox import enqueue, pending_for_session
    enqueue(session_id="s1", content="a", source="d")
    enqueue(session_id="s2", content="b", source="d")
    assert len(pending_for_session("s1")) == 1
    assert len(pending_for_session("s2")) == 1


def test_pending_count(tmp_db):
    from core.services.session_inbox import enqueue, pending_count
    enqueue(session_id="s1", content="a", source="d")
    enqueue(session_id="s1", content="b", source="d")
    enqueue(session_id="s2", content="c", source="d")
    assert pending_count("s1") == 2
    assert pending_count() == 3


# ── flush_session ────────────────────────────────────────────────────────


def test_flush_session_marks_delivered(tmp_db, monkeypatch):
    from core.services.session_inbox import enqueue, flush_session, pending_for_session

    enqueue(session_id="s1", content="msg1", source="d")
    enqueue(session_id="s1", content="msg2", source="d")

    # Stub chat_sessions + eventbus so flush succeeds without full stack
    class _StubMsg(dict):
        pass

    def _stub_append(session_id, role, content):
        return _StubMsg(id="m-x", session_id=session_id, role=role, content=content)

    def _stub_get(_sid):
        return {"id": _sid}

    class _StubBus:
        def publish(self, *args, **kwargs):
            pass

    import core.services.chat_sessions as cs
    monkeypatch.setattr(cs, "append_chat_message", _stub_append)
    monkeypatch.setattr(cs, "get_chat_session", _stub_get)
    import core.eventbus.bus as bus_mod
    monkeypatch.setattr(bus_mod, "event_bus", _StubBus())

    out = flush_session("s1")
    assert out["status"] == "ok"
    assert out["delivered"] == 2
    # No more pending for s1
    assert pending_for_session("s1") == []


def test_flush_session_no_items_is_noop(tmp_db):
    from core.services.session_inbox import flush_session
    out = flush_session("s-empty")
    assert out["status"] == "ok"
    assert out["delivered"] == 0


def test_flush_session_handles_deleted_session(tmp_db, monkeypatch):
    """If the chat-session has been deleted, mark items as dropped."""
    from core.services.session_inbox import enqueue, flush_session, pending_for_session

    enqueue(session_id="s-gone", content="orphan", source="d")

    import core.services.chat_sessions as cs
    monkeypatch.setattr(cs, "get_chat_session", lambda _sid: None)

    out = flush_session("s-gone")
    assert out["status"] == "ok"
    assert "note" in out
    # Pending list empty since items moved to 'dropped'
    assert pending_for_session("s-gone") == []


# ── Opgave 6, første halvdel: kilde-mærkningen ──────────────────────────────

def test_notifikationen_gaar_i_FEEDEN_og_IKKE_i_chatview(tmp_path, monkeypatch):
    """Bjørn 4/10-2026: «de forurenere chatview når vi arbejder.»

    Omlægningens anden halvdel. Første halvdel skrev notifikationen som en
    **assistant-besked** og begrundede det med at «omlægningen til en ren
    henvisning venter på en klient-udrulning». Klienten findes nu, og målt før
    omlægningen stod ni sådanne beskeder i `chat_messages` — «Drømme — hvad
    jeg lavede mens du var væk», «5 skygge-eksperimenter venter på review» —
    alle `role=assistant`, midt i en arbejdssamtale.

    To påstande, og den anden er den vigtigste: feeden får rækken, OG
    chatview får ingenting. En test der kun målte det første ville bestå
    selvom beskeden stadig blev skrevet begge steder.
    """
    from unittest.mock import patch

    from core.services import session_inbox
    from core.services.visible_run_guard_notices import SYSTEM_MAERKE

    feed: list[dict] = []
    chat: list[dict] = []
    monkeypatch.setattr(session_inbox, "pending_for_session", lambda s: [
        {"id": 1, "session_id": s, "content": "Jeg har ryddet op i databasen.",
         "source": "jarvis-notify", "user_id": "u-bjorn"}])
    monkeypatch.setattr(session_inbox, "_connect", _tom_connect)
    with patch("core.services.notifikationer.opret",
               side_effect=lambda **kw: feed.append(kw) or "n1"), \
         patch("core.services.chat_sessions.append_chat_message",
               side_effect=lambda **kw: chat.append(kw) or {"id": "m1"}), \
         patch("core.services.chat_sessions.get_chat_session",
               return_value={"id": "s1"}), \
         patch("core.eventbus.bus.event_bus.publish", return_value=None):
        session_inbox.flush_session("s1")

    assert chat == [], f"notifikationen landede STADIG i chatview: {chat}"
    assert len(feed) == 1, "feeden fik den ikke"
    assert feed[0]["user_id"] == "u-bjorn"
    assert feed[0]["session_id"] == "s1", "raekken mistede sin samtale-reference"


def test_feed_raekken_er_stadig_KILDE_MAERKET(tmp_path, monkeypatch):
    """Mærkningen flytter med. Bjørns stående regel er at alt der ikke er
    skrevet fra hans composer skal kunne skelnes fra ham — og en feed-række
    kan også citeres videre."""
    from unittest.mock import patch

    from core.services import session_inbox
    from core.services.visible_run_guard_notices import SYSTEM_MAERKE

    feed: list[dict] = []
    monkeypatch.setattr(session_inbox, "pending_for_session", lambda s: [
        {"id": 1, "session_id": s, "content": "Jeg har ryddet op i databasen.",
         "source": "jarvis-notify", "user_id": "u-bjorn"}])
    monkeypatch.setattr(session_inbox, "_connect", _tom_connect)
    with patch("core.services.notifikationer.opret",
               side_effect=lambda **kw: feed.append(kw) or "n1"), \
         patch("core.services.chat_sessions.get_chat_session",
               return_value={"id": "s1"}), \
         patch("core.eventbus.bus.event_bus.publish", return_value=None):
        session_inbox.flush_session("s1")

    tekst = str(feed[0]["tekst"])
    assert SYSTEM_MAERKE in tekst, "feed-raekken blev skrevet UMAERKET"
    assert "ryddet op i databasen" in tekst, "indholdet forsvandt"
    assert "samtykke" in tekst, "forbuddet mod at laese den som et ja mangler"
    # Titlen er foerste linje, saa feeden ikke viser samme overskrift paa alt.
    assert feed[0]["titel"] == "Jeg har ryddet op i databasen."


def test_UDEN_modtager_skrives_der_hverken_i_feed_eller_chat(tmp_path, monkeypatch, caplog):
    """Vi falder IKKE tilbage på en ejer: det ville lægge husets besked i én
    bestemt brugers feed. Posten markeres leveret, så køen ikke looper."""
    import logging
    from unittest.mock import patch

    from core.services import session_inbox

    feed: list[dict] = []
    chat: list[dict] = []
    monkeypatch.setattr(session_inbox, "pending_for_session", lambda s: [
        {"id": 1, "session_id": s, "content": "noget", "source": "jarvis-notify"}])
    monkeypatch.setattr(session_inbox, "_connect", _tom_connect)
    with caplog.at_level(logging.WARNING), \
         patch("core.services.notifikationer.opret",
               side_effect=lambda **kw: feed.append(kw) or "n1"), \
         patch("core.services.chat_sessions.append_chat_message",
               side_effect=lambda **kw: chat.append(kw) or {"id": "m1"}), \
         patch("core.services.chat_sessions.get_chat_session",
               return_value={"id": "s1"}), \
         patch("core.eventbus.bus.event_bus.publish", return_value=None):
        session_inbox.flush_session("s1")

    assert feed == [] and chat == []
    assert any("uden user_id" in r.message for r in caplog.records), \
        "posten forsvandt TAVST"


class _tom_connect:
    """En forbindelse der tager imod UPDATE'et uden en rigtig base.

    `flush_session`s eneste skrivning til `session_inbox` er statusskiftet, og
    det er ikke det denne test måler. En rigtig base ville tilføje en
    skema-afhængighed til en test om tekst.
    """

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, *a, **k):
        return self

    def commit(self):
        return None
