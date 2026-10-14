from __future__ import annotations

import threading


def test_experiential_candidates_are_user_scoped(isolated_runtime):
    from core.identity.workspace_context import reset_context, set_context
    from core.runtime.db import (
        get_experiential_memory_candidates,
        insert_cognitive_experiential_memory,
    )

    first = set_context(workspace_name="one", user_id="u1")
    try:
        insert_cognitive_experiential_memory(memory_id="m1", narrative="one")
    finally:
        reset_context(first)
    second = set_context(workspace_name="two", user_id="u2")
    try:
        insert_cognitive_experiential_memory(memory_id="m2", narrative="two")
        assert [row["memory_id"] for row in get_experiential_memory_candidates()] == ["m2"]
    finally:
        reset_context(second)


def test_async_capture_keeps_explicit_member_identity(monkeypatch):
    from core.services import experiential_memory as memory

    done = threading.Event()
    seen = {}
    monkeypatch.setattr(memory, "require_private_scope", lambda: "member-1")
    monkeypatch.setattr(
        memory,
        "create_experiential_memory_from_run",
        lambda **kwargs: (seen.update(kwargs), done.set()),
    )
    memory.create_experiential_memory_async(
        run_id="r", session_id="s", user_message="en relevant besked",
        assistant_response="svar", outcome_status="failed",
    )
    assert done.wait(1)
    assert seen["user_id"] == "member-1"
