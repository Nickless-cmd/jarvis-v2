"""Tests for recent_chat_session_messages_by_user_turns.

Background (2026-06-09): den gamle row-baserede limit gjorde at i tool-tunge
agentic sessions endte ~90% af slots med at være tool-rows, så kun få ægte
user/assistant turns nåede ud i prompt'en. Den nye user-turn-anchored
variant garanterer N reelle samtale-runder.
"""
from __future__ import annotations

import pytest


@pytest.fixture()
def _populated_session(isolated_runtime):
    """Seed en session med kontrolleret blanding af roles."""
    from core.services.chat_sessions import append_chat_message, create_chat_session

    sess = create_chat_session(title="paired-test")
    sid = str(sess.get("session_id") or sess.get("id"))

    # 5 user-turns, hver med 1 assistant + 8 tool messages (typisk agentic)
    for turn in range(5):
        append_chat_message(session_id=sid, role="user", content=f"u{turn}")
        append_chat_message(session_id=sid, role="assistant", content=f"a{turn}")
        for t in range(8):
            append_chat_message(
                session_id=sid, role="tool", content=f"[bash]: t{turn}.{t}"
            )
    return sid


def test_paired_returns_only_requested_turns(_populated_session) -> None:
    """user_turns=2 → kun de 2 sidste user-turns og deres followups."""
    from core.services.chat_sessions import (
        recent_chat_session_messages_by_user_turns,
    )

    msgs = recent_chat_session_messages_by_user_turns(
        _populated_session, user_turns=2
    )
    user_contents = [m["content"] for m in msgs if m["role"] == "user"]
    assert user_contents == ["u3", "u4"]
    # Hver user-turn har 1 assistant + 8 tool messages = 9 followups
    # Plus 2 user messages selv = 20 total
    assert len(msgs) == 20


def test_paired_more_turns_than_available(_populated_session) -> None:
    """Anmodes om flere user-turns end der findes → returnér alt."""
    from core.services.chat_sessions import (
        recent_chat_session_messages_by_user_turns,
    )

    msgs = recent_chat_session_messages_by_user_turns(
        _populated_session, user_turns=999
    )
    user_contents = [m["content"] for m in msgs if m["role"] == "user"]
    assert user_contents == ["u0", "u1", "u2", "u3", "u4"]


def test_paired_excludes_compact_markers(_populated_session) -> None:
    """compact_marker rows skal ikke med selv inden for anchor-vinduet."""
    from core.services.chat_sessions import (
        append_chat_message,
        recent_chat_session_messages_by_user_turns,
    )

    append_chat_message(
        session_id=_populated_session,
        role="compact_marker",
        content="[compacted summary]",
    )
    append_chat_message(session_id=_populated_session, role="user", content="u5")
    append_chat_message(session_id=_populated_session, role="assistant", content="a5")

    msgs = recent_chat_session_messages_by_user_turns(
        _populated_session, user_turns=2
    )
    roles = [m["role"] for m in msgs]
    assert "compact_marker" not in roles


def test_paired_returns_chronological_order(_populated_session) -> None:
    """Resultat skal være ældste-først (chronological)."""
    from core.services.chat_sessions import (
        recent_chat_session_messages_by_user_turns,
    )

    msgs = recent_chat_session_messages_by_user_turns(
        _populated_session, user_turns=3
    )
    user_contents = [m["content"] for m in msgs if m["role"] == "user"]
    assert user_contents == sorted(user_contents)  # u2, u3, u4


def test_paired_empty_session(isolated_runtime) -> None:
    """Ingen beskeder → tom liste."""
    from core.services.chat_sessions import (
        recent_chat_session_messages_by_user_turns,
    )

    assert recent_chat_session_messages_by_user_turns("nonexistent", user_turns=10) == []


def test_since_last_compact_returns_all_when_no_marker(isolated_runtime) -> None:
    """Uden compact_marker → hele session (op til safety cap)."""
    from core.services.chat_sessions import (
        append_chat_message,
        chat_session_messages_since_last_compact,
        create_chat_session,
    )
    sess = create_chat_session(title="grow-test")
    sid = str(sess.get("session_id") or sess.get("id"))
    for i in range(5):
        append_chat_message(session_id=sid, role="user", content=f"u{i}")
        append_chat_message(session_id=sid, role="assistant", content=f"a{i}")
    msgs = chat_session_messages_since_last_compact(sid)
    contents = [m["content"] for m in msgs]
    assert contents == ["u0", "a0", "u1", "a1", "u2", "a2", "u3", "a3", "u4", "a4"]


def test_since_last_compact_returns_only_after_marker(isolated_runtime) -> None:
    """Med compact_marker → kun beskeder efter marker."""
    from core.services.chat_sessions import (
        append_chat_message,
        chat_session_messages_since_last_compact,
        create_chat_session,
    )
    sess = create_chat_session(title="grow-test")
    sid = str(sess.get("session_id") or sess.get("id"))
    for i in range(3):
        append_chat_message(session_id=sid, role="user", content=f"old-u{i}")
        append_chat_message(session_id=sid, role="assistant", content=f"old-a{i}")
    append_chat_message(session_id=sid, role="compact_marker", content="[compact]")
    for i in range(3):
        append_chat_message(session_id=sid, role="user", content=f"new-u{i}")
        append_chat_message(session_id=sid, role="assistant", content=f"new-a{i}")

    msgs = chat_session_messages_since_last_compact(sid)
    contents = [m["content"] for m in msgs]
    assert all("old-" not in c for c in contents)
    assert "[compact]" not in contents
    assert contents == ["new-u0", "new-a0", "new-u1", "new-a1", "new-u2", "new-a2"]


def test_since_last_compact_empty_session(isolated_runtime) -> None:
    """Ingen beskeder → tom liste."""
    from core.services.chat_sessions import chat_session_messages_since_last_compact
    assert chat_session_messages_since_last_compact("nonexistent") == []


def test_paired_demonstrates_old_bug_avoided(isolated_runtime) -> None:
    """Den oprindelige bug: row-limit=60 i en session med 10 tool/svar
    gav kun ~6 user-turns. Den nye paired-variant garanterer 30 user-turns
    selv hvis det betyder mange rows.
    """
    from core.services.chat_sessions import (
        append_chat_message,
        create_chat_session,
        recent_chat_session_messages,
        recent_chat_session_messages_by_user_turns,
    )

    sess = create_chat_session(title="bug-demo")
    sid = str(sess.get("session_id") or sess.get("id"))
    for turn in range(30):
        append_chat_message(session_id=sid, role="user", content=f"u{turn}")
        append_chat_message(session_id=sid, role="assistant", content=f"a{turn}")
        for t in range(8):
            append_chat_message(
                session_id=sid, role="tool", content=f"[bash]: t{turn}.{t}"
            )

    # Gammel adfærd: 60 rows → få user-turns
    old = recent_chat_session_messages(sid, limit=60)
    old_user_count = sum(1 for m in old if m["role"] == "user")
    assert old_user_count <= 6, f"baseline check: gammel adfærd burde give ≤6 (fik {old_user_count})"

    # Ny adfærd: 30 user-turns garanteret
    new = recent_chat_session_messages_by_user_turns(sid, user_turns=30)
    new_user_count = sum(1 for m in new if m["role"] == "user")
    assert new_user_count == 30
