"""Tests for identity-guard kerne: audit, session-lock, lockdown, owner-exempt."""
from __future__ import annotations

from types import SimpleNamespace

from core.runtime.db import connect
from core.services import security_guard as sg


def _mk_session(sid: str) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO chat_sessions (session_id, title, created_at, updated_at)"
            " VALUES (?,?,?,?)", (sid, "t", sg._iso(), sg._iso()))


def test_is_owner(monkeypatch):
    import core.identity.users as users
    monkeypatch.setattr(users, "get_owner",
                        lambda: SimpleNamespace(discord_id="OWNER1", name="Bjørn", role="owner"))
    assert sg.is_owner("OWNER1") is True
    assert sg.is_owner("someone-else") is False
    assert sg.is_owner("") is False


def test_session_lock_roundtrip(isolated_runtime):
    _mk_session("chat-lock1")
    assert sg.is_session_locked("chat-lock1") is False
    sg.lock_session("chat-lock1", "test-reason", user_id="u1")
    assert sg.is_session_locked("chat-lock1") is True
    sg.unlock_session("chat-lock1", user_id="u1")
    assert sg.is_session_locked("chat-lock1") is False


def test_audit_and_abuse_persist(isolated_runtime):
    sg.record_audit("u9", "override_activated", session_id="s9", details={"k": "v"})
    sg.record_abuse("u9", "s9", "identity_spoof", "high", details={"claimed": "Bjørn"})
    with connect() as conn:
        a = conn.execute("SELECT action FROM audit_log WHERE user_id='u9'").fetchall()
        b = conn.execute("SELECT event_type FROM abuse_events WHERE user_id='u9'").fetchone()
    actions = {r[0] for r in a}
    assert "override_activated" in actions and "abuse_detected" in actions
    assert b[0] == "identity_spoof"


def test_escalate_locks_session(isolated_runtime, monkeypatch):
    import core.identity.users as users
    monkeypatch.setattr(users, "get_owner", lambda: SimpleNamespace(discord_id="OWNER1", name="B"))
    _mk_session("chat-esc1")
    res = sg.escalate_session_lock("member-x", "chat-esc1", "spoof x3")
    assert res in ("session_lock", "account_lockdown")
    assert sg.is_session_locked("chat-esc1") is True


def test_owner_exempt_from_account_lockdown(isolated_runtime, monkeypatch):
    import core.identity.users as users
    monkeypatch.setattr(users, "get_owner", lambda: SimpleNamespace(discord_id="OWNER1", name="B"))
    # Owner: selv ved mange locks må escalate ALDRIG returnere account_lockdown.
    _mk_session("chat-owner1")
    for _ in range(5):
        sg.lock_session("chat-owner1", "x", user_id="OWNER1")
    res = sg.escalate_session_lock("OWNER1", "chat-owner1", "x")
    assert res == "session_lock"
    assert sg.is_account_locked("OWNER1") is False


def test_fail_open_when_session_absent(isolated_runtime):
    # Ukendt session → ikke låst (fail-open), kaster ikke.
    assert sg.is_session_locked("does-not-exist") is False
