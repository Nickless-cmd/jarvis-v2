"""Regression tests for Jarvis' own initiative-queue decline disposition."""
from __future__ import annotations


def _push(initiative_queue, *, focus: str) -> str:
    return initiative_queue.push_initiative(
        focus=focus,
        source="jarvis-tool",
        priority="high",
    )


def test_declined_initiative_leaves_pending_with_explicit_reason(isolated_runtime) -> None:
    from core.services import initiative_queue

    initiative_id = _push(
        initiative_queue,
        focus="Inspect a queue item Jarvis deliberately declines",
    )

    assert initiative_queue.decline_initiative(
        initiative_id,
        reason="The premise is no longer true.",
    )

    state = initiative_queue.get_initiative_queue_state()
    stored = isolated_runtime.db.get_runtime_initiative(initiative_id)

    assert not any(item["initiative_id"] == initiative_id for item in state["pending"])
    assert stored is not None
    assert stored["status"] == "declined"
    assert stored["disposition"] == "declined"
    assert stored["disposition_reason"] == "The premise is no longer true."


def test_declined_initiative_is_never_projected_as_acted(isolated_runtime) -> None:
    from core.services import initiative_queue

    initiative_id = _push(
        initiative_queue,
        focus="Separate a declined queue item from acted work",
    )
    assert initiative_queue.decline_initiative(
        initiative_id,
        reason="Jarvis chooses not to do this.",
    )

    state = initiative_queue.get_initiative_queue_state()
    declined = next(
        item for item in state["recent_declined"]
        if item["initiative_id"] == initiative_id
    )

    assert state["declined_count"] == 1
    assert declined["acted_at"] == ""
    assert declined["action_summary"] == ""
    assert not any(
        item["initiative_id"] == initiative_id for item in state["recent_acted"]
    )


def test_mark_acted_keeps_the_existing_acted_disposition(isolated_runtime) -> None:
    from core.services import initiative_queue

    initiative_id = _push(
        initiative_queue,
        focus="Actually perform this initiative",
    )
    assert initiative_queue.mark_acted(
        initiative_id,
        action_summary="Performed the bounded action.",
    )

    state = initiative_queue.get_initiative_queue_state()
    acted = next(
        item for item in state["recent_acted"]
        if item["initiative_id"] == initiative_id
    )

    assert acted["status"] == "acted"
    assert acted["disposition"] == "acted"
    assert acted["action_summary"] == "Performed the bounded action."
    assert acted["acted_at"]
    assert not any(
        item["initiative_id"] == initiative_id for item in state["recent_declined"]
    )
