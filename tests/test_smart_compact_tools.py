"""Tests for core.tools.smart_compact_tools — session-token estimation.

Regression guard for the N+1 + wrong-key bug: _estimate_session_tokens used
list_chat_sessions() (formats every session) then read sessions[0]["session_id"]
— but _session_summary renames it to "id", so it ALWAYS got None → estimate
was always 0. The fix routes through most_recent_session_id().
"""
from __future__ import annotations

import core.services.chat_sessions as cs
import core.tools.smart_compact_tools as sc


def test_estimate_uses_most_recent_session_and_is_nonzero(monkeypatch):
    """With a real session id + messages, the estimate must be > 0 (the bug
    made it always 0 by reading a renamed key)."""
    monkeypatch.setattr(cs, "most_recent_session_id", lambda: "sess-1", raising=False)
    monkeypatch.setattr(
        cs, "recent_chat_session_messages",
        lambda sid, limit=200: [{"content": "x" * 4000}] if sid == "sess-1" else [],
        raising=False,
    )
    est = sc._estimate_session_tokens()
    assert est > 0, "estimate must be non-zero for a session with messages (was the bug)"


def test_estimate_zero_when_no_session(monkeypatch):
    monkeypatch.setattr(cs, "most_recent_session_id", lambda: "", raising=False)
    assert sc._estimate_session_tokens() == 0


def test_estimate_does_not_call_list_chat_sessions(monkeypatch):
    """The hot-path estimate must NOT format every session (the ~3184-call N+1)."""
    called = {"n": 0}

    def _boom(*a, **k):
        called["n"] += 1
        return []

    monkeypatch.setattr(cs, "list_chat_sessions", _boom, raising=False)
    monkeypatch.setattr(cs, "most_recent_session_id", lambda: "sess-1", raising=False)
    monkeypatch.setattr(cs, "recent_chat_session_messages", lambda sid, limit=200: [], raising=False)
    sc._estimate_session_tokens()
    assert called["n"] == 0, "must not call list_chat_sessions on the hot path"
