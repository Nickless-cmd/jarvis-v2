from __future__ import annotations

import sqlite3
from contextlib import contextmanager

import pytest

from core.runtime import db_inbox


@pytest.fixture
def importance_db(monkeypatch, tmp_path):
    path = tmp_path / "importance.db"

    @contextmanager
    def connect():
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    monkeypatch.setattr(db_inbox, "connect", connect)
    monkeypatch.setattr(db_inbox, "_skema_klar", False)
    return path


def _create(*, item_id: str, importance: str, session: str = "s1"):
    return db_inbox.opret_eller_hent(
        bruger_id="owner",
        kildetype="background_attention",
        kilde_id=item_id,
        beskrivelse=f"finding {item_id}",
        importance=importance,
        session_id=session,
    )["post"]


def test_every_durable_item_has_importance_and_can_only_escalate(importance_db):
    assert _create(item_id="a", importance="unknown")["importance"] == "normal"
    assert _create(item_id="b", importance="high")["importance"] == "high"
    assert _create(item_id="b", importance="low")["importance"] == "high"
    assert _create(item_id="b", importance="critical")["importance"] == "critical"


def test_high_and_critical_are_claimed_once_between_rounds(importance_db):
    _create(item_id="low", importance="low")
    _create(item_id="normal", importance="normal")
    _create(item_id="high", importance="high")
    _create(item_id="critical", importance="critical")

    claimed = db_inbox.claim_high_for_run(
        bruger_id="owner", session_id="s1", run_id="run-1",
    )
    assert [p["id"] for p in claimed] == ["critical", "high"]
    assert all(p["vist_at"] and p["leveret_til_run_id"] == "run-1" for p in claimed)
    assert db_inbox.claim_high_for_run(
        bruger_id="owner", session_id="s1", run_id="run-1",
    ) == []
    assert db_inbox.hent(bruger_id="owner", kilde_id="normal")["vist_at"] == ""


def test_claim_is_session_and_owner_scoped(importance_db):
    _create(item_id="other-session", importance="critical", session="s2")
    assert db_inbox.claim_high_for_run(
        bruger_id="owner", session_id="s1", run_id="run-1",
    ) == []
    assert db_inbox.claim_high_for_run(
        bruger_id="another", session_id="s2", run_id="run-2",
    ) == []


def test_prompt_order_prevents_seen_rows_from_starving_unseen_rows():
    from core.services.inbox_importance import prompt_order

    rows = [
        {"id": "seen-critical", "importance": "critical", "vist_at": "yesterday"},
        {"id": "unseen-low", "importance": "low", "vist_at": ""},
        {"id": "unseen-high", "importance": "high", "vist_at": ""},
    ]
    assert [r["id"] for r in sorted(rows, key=prompt_order)] == [
        "unseen-high", "unseen-low", "seen-critical",
    ]


def test_round_guard_appends_claimed_rows_as_runtime_data(monkeypatch):
    from core.services import agent_result_inbox

    monkeypatch.setattr(agent_result_inbox, "claim_for_model_step", lambda **_: "")
    monkeypatch.setattr(
        "core.runtime.db_inbox.claim_high_for_run",
        lambda **_: [{
            "kilde_id": "critical-1", "kildetype": "background_attention",
            "importance": "critical", "beskrivelse": "database finding",
        }],
    )
    monkeypatch.setattr("core.services.run_autonomy_context.current_run_id", lambda: "run-1")

    class Tail:
        def __init__(self):
            self.messages = []

        def tilfoej_vedvarende(self, text):
            self.messages.append(text)

    tail = Tail()
    assert agent_result_inbox.add_to_turn_tail(
        tail, owner_user_id="owner", session_id="s1",
    ) is True
    assert "[CRITICAL]" in tail.messages[0]
    assert "ikke brugerinput" in tail.messages[0]

