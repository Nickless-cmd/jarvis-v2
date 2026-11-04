"""Tests for ownership of the one-shot bash tool's default session."""
from __future__ import annotations

from core.tools import bash_session
from core.tools import default_bash_session as default_session


def test_default_session_reuses_the_live_work_session(monkeypatch):
    monkeypatch.setattr(default_session, "_DEFAULT_BASH_SESSION_IDS", {})
    opened: list[bool] = []

    monkeypatch.setattr(
        bash_session,
        "_exec_bash_session_list",
        lambda _args: {
            "status": "ok",
            "sessions": [{"session_id": "bsh-work", "alive": True}],
        },
    )

    def _open(_scope: str = "") -> dict[str, str]:
        opened.append(True)
        return {"status": "ok", "session_id": "bsh-work"}

    monkeypatch.setattr(bash_session, "_open_arbejdssession", _open)

    assert default_session._get_or_open_default_bash_session() == "bsh-work"
    assert default_session._get_or_open_default_bash_session() == "bsh-work"
    assert len(opened) == 1


def test_two_chat_sessions_never_share_the_same_shell(monkeypatch):
    monkeypatch.setattr(default_session, "_DEFAULT_BASH_SESSION_IDS", {})
    live: list[dict[str, object]] = []

    monkeypatch.setattr(
        bash_session,
        "_exec_bash_session_list",
        lambda _args: {"status": "ok", "sessions": list(live)},
    )

    def _open(_scope: str = "") -> dict[str, str]:
        sid = f"bsh-{len(live) + 1}"
        live.append({"session_id": sid, "alive": True, "busy": False})
        return {"status": "ok", "session_id": sid}

    monkeypatch.setattr(bash_session, "_open_arbejdssession", _open)

    first_scope = default_session._default_bash_session_scope({
        "_runtime_user_id": "owner",
        "_runtime_session_id": "chat-A",
    })
    second_scope = default_session._default_bash_session_scope({
        "_runtime_user_id": "owner",
        "_runtime_session_id": "chat-B",
    })

    first = default_session._get_or_open_default_bash_session(first_scope)
    second = default_session._get_or_open_default_bash_session(second_scope)

    assert first != second
    assert default_session._get_or_open_default_bash_session(first_scope) == first
    assert default_session._get_or_open_default_bash_session(second_scope) == second


def test_full_pool_falls_back_instead_of_waiting(monkeypatch):
    sessions = {
        "session:u:a": "bsh-a",
        "session:u:b": "bsh-b",
    }
    monkeypatch.setattr(default_session, "_DEFAULT_BASH_SESSION_IDS", sessions)
    monkeypatch.setattr(default_session, "_MAX_DEFAULT_BASH_SESSIONS", 2)
    monkeypatch.setattr(
        bash_session,
        "_exec_bash_session_list",
        lambda _args: {
            "status": "ok",
            "sessions": [
                {"session_id": "bsh-a", "alive": True, "busy": True},
                {"session_id": "bsh-b", "alive": True, "busy": True},
            ],
        },
    )
    monkeypatch.setattr(
        bash_session,
        "_open_arbejdssession",
        lambda _scope="": (_ for _ in ()).throw(
            AssertionError("must not open while pool is busy")
        ),
    )

    assert default_session._get_or_open_default_bash_session("session:u:c") is None


def test_scoped_shell_is_readopted_after_api_restart(monkeypatch):
    monkeypatch.setattr(default_session, "_DEFAULT_BASH_SESSION_IDS", {})
    monkeypatch.setattr(
        bash_session,
        "_exec_bash_session_list",
        lambda _args: {
            "status": "ok",
            "sessions": [{
                "session_id": "bsh-survivor",
                "alive": True,
                "busy": False,
                "arbejde": True,
                "arbejde_scope": "session:owner:chat-A",
            }],
        },
    )
    monkeypatch.setattr(
        bash_session,
        "_open_arbejdssession",
        lambda _scope="": (_ for _ in ()).throw(
            AssertionError("must reuse the daemon's scoped shell")
        ),
    )

    assert (
        default_session._get_or_open_default_bash_session("session:owner:chat-A")
        == "bsh-survivor"
    )


def test_full_legacy_daemon_reclaims_one_idle_unscoped_shell(monkeypatch):
    monkeypatch.setattr(default_session, "_DEFAULT_BASH_SESSION_IDS", {})
    closed: list[str] = []
    attempts: list[str] = []
    monkeypatch.setattr(
        bash_session,
        "_exec_bash_session_list",
        lambda _args: {
            "status": "ok",
            "sessions": [{
                "session_id": "bsh-legacy",
                "alive": True,
                "busy": False,
                "arbejde": True,
                "arbejde_scope": "",
            }],
        },
    )
    monkeypatch.setattr(
        bash_session,
        "_exec_bash_session_close",
        lambda args: closed.append(str(args["session_id"])) or {"status": "ok"},
    )

    def _open(scope: str = "") -> dict[str, str]:
        attempts.append(scope)
        if len(attempts) == 1:
            return {"status": "error", "error": "max 8 concurrent sessions"}
        return {"status": "ok", "session_id": "bsh-scoped"}

    monkeypatch.setattr(bash_session, "_open_arbejdssession", _open)

    assert (
        default_session._get_or_open_default_bash_session("session:owner:chat-A")
        == "bsh-scoped"
    )
    assert closed == ["bsh-legacy"]
    assert attempts == ["session:owner:chat-A", "session:owner:chat-A"]
