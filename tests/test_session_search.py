"""SECURITY: search_sessions must NOT leak one user's sessions/DMs to another.

Regression for the 2026-06-15 privacy break: search_sessions queried chat_messages
with no user_id filter, so the owner (or an autonomous run) could search a member's
private conversation. Northstar: neither owner nor Jarvis can read others' private data.
"""
from __future__ import annotations

from core.services.chat_sessions import create_chat_session, append_chat_message
from core.tools.session_search import _keyword_search


BJORN = "1246415163603816499"
MICHELLE = "1313522677369143429"


def _seed(isolated_runtime):
    sb = str(create_chat_session(title="Bjørn webchat")["id"])
    append_chat_message(session_id=sb, role="user",
                        content="hemmelig pingvin-plan fra bjørn", user_id=BJORN)
    sm = str(create_chat_session(title="Michelle DM")["id"])
    append_chat_message(session_id=sm, role="user",
                        content="hemmelig pingvin-plan fra michelle", user_id=MICHELLE)
    return sb, sm


def test_owner_search_excludes_member_sessions(isolated_runtime) -> None:
    sb, sm = _seed(isolated_runtime)
    rows = _keyword_search("pingvin", channel="all", since=None, until=None, limit=30, user_id=BJORN)
    ids = {r["session_id"] for r in rows}
    assert sb in ids
    assert sm not in ids  # ← Bjørn må IKKE se Michelles DM


def test_member_search_excludes_owner_sessions(isolated_runtime) -> None:
    sb, sm = _seed(isolated_runtime)
    rows = _keyword_search("pingvin", channel="all", since=None, until=None, limit=30, user_id=MICHELLE)
    ids = {r["session_id"] for r in rows}
    assert sm in ids
    assert sb not in ids


def test_empty_uid_sees_no_member_data(isolated_runtime) -> None:
    # Autonom-run / manglende kontekst (uid="") må ALDRIG ramme medlemsdata.
    sb, sm = _seed(isolated_runtime)
    rows = _keyword_search("pingvin", channel="all", since=None, until=None, limit=30, user_id="")
    ids = {r["session_id"] for r in rows}
    assert sm not in ids
    assert sb not in ids  # begge har ikke-tomt user_id → ingen match på ''


def test_exec_uses_current_user_scope(isolated_runtime, monkeypatch) -> None:
    # Verificér at exec_search_sessions trækker current_user_id() og scoper.
    _seed(isolated_runtime)
    import core.identity.workspace_context as wc
    monkeypatch.setattr(wc, "current_user_id", lambda: BJORN)
    from core.tools.session_search import exec_search_sessions
    res = exec_search_sessions({"query": "pingvin", "mode": "keyword"})
    text = res.get("text", "")
    assert "michelle" not in text.lower()
