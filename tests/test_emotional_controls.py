from __future__ import annotations

from datetime import UTC, datetime


def test_repeated_failures_of_one_tool_are_one_fatigue_signal(monkeypatch):
    from core.services import emotional_controls as ec

    now = datetime.now(UTC).isoformat()
    events = [
        {"kind": "tool.completed", "created_at": now,
         "payload": {"tool": "operator_bash", "status": "error"}}
        for _ in range(20)
    ]
    monkeypatch.setattr(ec.event_bus, "recent", lambda limit: events)

    assert ec._recent_tool_errors_last_10min() == 1


def test_failures_of_different_tools_remain_distinct_signals(monkeypatch):
    from core.services import emotional_controls as ec

    now = datetime.now(UTC).isoformat()
    events = [
        {"kind": "tool.completed", "created_at": now,
         "payload": {"tool": tool, "status": "error"}}
        for tool in ("operator_bash", "edit_file", "schedule_task")
    ]
    monkeypatch.setattr(ec.event_bus, "recent", lambda limit: events)

    assert ec._recent_tool_errors_last_10min() == 3


def test_joy_cannot_lift_low_confidence_for_irreversible_action(monkeypatch):
    """Removing the irreversible-risk check must reopen the unsafe execute path."""
    from core.services import emotional_controls as ec
    from core.services.task_tool_mapping import TIER_IRREVERSIBLE

    monkeypatch.setattr(
        "core.services.emotion_concepts.get_active_emotion_concepts",
        lambda: [{"concept": "joy", "intensity": 0.9}],
    )
    snapshot = ec.EmotionalSnapshot(
        frustration=0.0,
        confidence=0.2,
        fatigue=0.0,
        primary_mood="euphoric",
        intensity=0.9,
    )

    action, reason = ec.apply_emotional_controls(
        kernel_action="execute",
        snapshot=snapshot,
        risk=TIER_IRREVERSIBLE,
    )

    assert (action, reason) == ("verify_first", "low_confidence_guard")
