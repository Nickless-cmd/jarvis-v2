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
    seen_scope = {}
    monkeypatch.setattr(
        memory,
        "require_private_scope",
        lambda session_id="": (seen_scope.update(session_id=session_id) or "member-1"),
    )
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
    assert seen_scope["session_id"] == "s"


def test_async_capture_falls_back_to_persisted_run_owner(monkeypatch):
    """Postprocess has no ContextVars; the run row still carries its owner."""
    from core.services import experiential_memory as memory
    from core.services.scoped_recall_policy import MissingRecallScope

    done = threading.Event()
    seen = {}

    class _Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, _sql, params):
            assert params == ("visible-r1",)
            return self

        def fetchone(self):
            return ("member-from-run",)

    monkeypatch.setattr(
        memory, "require_private_scope",
        lambda _session_id="": (_ for _ in ()).throw(MissingRecallScope()),
    )
    monkeypatch.setattr("core.runtime.db_core.connect", lambda: _Connection())
    monkeypatch.setattr(
        "core.services.routine_migration.resolve_canonical_identity",
        lambda owner: owner,
    )
    monkeypatch.setattr(
        memory,
        "create_experiential_memory_from_run",
        lambda **kwargs: (seen.update(kwargs), done.set()),
    )

    memory.create_experiential_memory_async(
        run_id="visible-r1", user_message="en relevant besked",
        assistant_response="svar", outcome_status="failed",
    )

    assert done.wait(1)
    assert seen["user_id"] == "member-from-run"


def test_run_owner_fallback_persists_a_real_experiential_memory(
    isolated_runtime, monkeypatch,
):
    """Integration: use the production tables, not an invented run payload."""
    from core.runtime.db import connect, list_cognitive_experiential_memories
    from core.services import experiential_memory as memory
    from core.services.scoped_recall_policy import MissingRecallScope

    with connect() as conn:
        conn.execute(
            """INSERT INTO visible_runs
               (run_id, lane, provider, model, status, finished_at, user_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                "visible-real-owner", "visible", "test", "test-model",
                "failed", "2026-11-03T15:00:00+00:00", "member-real",
            ),
        )
    monkeypatch.setattr(
        memory, "require_private_scope",
        lambda _session_id="": (_ for _ in ()).throw(MissingRecallScope()),
    )
    monkeypatch.setattr(
        "core.services.routine_migration.resolve_canonical_identity",
        lambda owner: owner,
    )
    monkeypatch.setattr(memory.event_bus, "publish", lambda *_a, **_k: None)

    created = memory.create_experiential_memory_from_run(
        run_id="visible-real-owner",
        user_message="denne pipeline fejlede igen",
        assistant_response="jeg fandt fejlen",
        outcome_status="failed",
    )

    assert created is not None
    rows = list_cognitive_experiential_memories(user_id="member-real")
    assert len(rows) == 1
    assert rows[0]["key_lesson"] == "Verificér grundigere før næste forsøg"


def test_empty_scoped_surface_is_online(monkeypatch):
    from core.services import experiential_memory as memory

    monkeypatch.setattr(memory, "list_cognitive_experiential_memories", lambda **_: [])
    surface = memory.build_experiential_memory_surface()

    assert surface["active"] is True
    assert surface["status"] == "empty"
    assert surface["summary"] == "No experiential memories yet"


def test_unscoped_surface_is_explicitly_unavailable(monkeypatch):
    from core.services import experiential_memory as memory
    from core.services.scoped_recall_policy import MissingRecallScope

    monkeypatch.setattr(
        memory,
        "list_cognitive_experiential_memories",
        lambda **_: (_ for _ in ()).throw(MissingRecallScope()),
    )
    surface = memory.build_experiential_memory_surface()

    assert surface["active"] is False
    assert surface["status"] == "unscoped"
    assert "authenticated user scope" in surface["summary"]
