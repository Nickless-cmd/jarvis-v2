"""Tests for ownership of the one-shot bash tool's default session."""
from __future__ import annotations

from core.tools import bash_session
from core.tools import default_bash_session as default_session


def test_default_session_reuses_the_live_work_session(monkeypatch):
    monkeypatch.setattr(default_session, "_DEFAULT_BASH_SESSION_ID", None)
    opened: list[bool] = []

    monkeypatch.setattr(
        bash_session,
        "_exec_bash_session_list",
        lambda _args: {
            "status": "ok",
            "sessions": [{"session_id": "bsh-work", "alive": True}],
        },
    )

    def _open() -> dict[str, str]:
        opened.append(True)
        return {"status": "ok", "session_id": "bsh-work"}

    monkeypatch.setattr(bash_session, "_open_arbejdssession", _open)

    assert default_session._get_or_open_default_bash_session() == "bsh-work"
    assert default_session._get_or_open_default_bash_session() == "bsh-work"
    assert len(opened) == 1
