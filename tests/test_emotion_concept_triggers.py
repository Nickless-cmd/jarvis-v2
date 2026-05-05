from __future__ import annotations


def test_trigger_cooldown_skips_repeat_within_window(
    isolated_runtime, monkeypatch,
) -> None:
    from datetime import UTC, datetime, timedelta
    from core.services import emotion_concepts as ec

    base = datetime(2026, 5, 5, 12, 0, tzinfo=UTC)
    now_holder = {"now": base}

    def fake_now():
        return now_holder["now"]

    monkeypatch.setattr(ec, "_now", fake_now, raising=False)
    # Reset cooldown state per test
    ec._last_trigger_at.clear()

    # First call: succeeds
    r1 = ec.trigger_emotion_concept(
        "joy", intensity=0.5, source="test", trigger="t1",
        min_seconds_since_last_from_same_source=30,
    )
    assert r1 is not None

    # Second call within cooldown: skipped
    now_holder["now"] = base + timedelta(seconds=10)
    r2 = ec.trigger_emotion_concept(
        "joy", intensity=0.5, source="test", trigger="t2",
        min_seconds_since_last_from_same_source=30,
    )
    assert r2 is None

    # Third call after cooldown: succeeds
    now_holder["now"] = base + timedelta(seconds=35)
    r3 = ec.trigger_emotion_concept(
        "joy", intensity=0.5, source="test", trigger="t3",
        min_seconds_since_last_from_same_source=30,
    )
    assert r3 is not None


def test_trigger_cooldown_independent_per_source(
    isolated_runtime, monkeypatch,
) -> None:
    from datetime import UTC, datetime
    from core.services import emotion_concepts as ec

    base = datetime(2026, 5, 5, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(ec, "_now", lambda: base, raising=False)
    ec._last_trigger_at.clear()

    r1 = ec.trigger_emotion_concept(
        "joy", intensity=0.5, source="source-a",
        min_seconds_since_last_from_same_source=30,
    )
    r2 = ec.trigger_emotion_concept(
        "joy", intensity=0.5, source="source-b",
        min_seconds_since_last_from_same_source=30,
    )
    # Different sources → both succeed
    assert r1 is not None
    assert r2 is not None


def test_trigger_concept_records_to_baseline_tracker(isolated_runtime) -> None:
    from core.runtime.db import get_concept_baseline_stat
    from core.services.emotion_concepts import trigger_emotion_concept
    from core.services import emotion_concepts as ec

    # Reset cooldown state
    ec._last_trigger_at.clear()

    trigger_emotion_concept(
        "joy", intensity=0.5, source="integration-test",
    )
    row = get_concept_baseline_stat("joy")
    assert row is not None
    assert row["total_triggers"] == 1


def test_completed_episode_fires_joy(isolated_runtime, monkeypatch) -> None:
    from core.services import emotion_concepts as ec
    from core.services.cognitive_episodes import record_runtime_episode

    ec._last_trigger_at.clear()

    fired = []
    original = ec.trigger_emotion_concept
    monkeypatch.setattr(
        ec, "trigger_emotion_concept",
        lambda *a, **kw: (fired.append((a, kw)) or original(*a, **kw)),
    )

    record_runtime_episode(
        source_run_id="run-1",
        session_id="s",
        trigger="visible-run:test",
        outcome_status="completed",
        summary="ok",
        tool_names=["a"],
    )

    concepts_fired = [a[0][0] for a in fired]
    assert "joy" in concepts_fired


def test_interrupted_episode_fires_frustration_blocked(
    isolated_runtime, monkeypatch,
) -> None:
    from core.services import emotion_concepts as ec
    from core.services.cognitive_episodes import record_runtime_episode

    ec._last_trigger_at.clear()

    fired = []
    original = ec.trigger_emotion_concept
    monkeypatch.setattr(
        ec, "trigger_emotion_concept",
        lambda *a, **kw: (fired.append((a, kw)) or original(*a, **kw)),
    )

    record_runtime_episode(
        source_run_id="run-2", session_id="s",
        trigger="x", outcome_status="interrupted",
        summary="boom", tool_names=[],
        error="upstream timeout",
    )

    concepts_fired = [a[0][0] for a in fired]
    assert "frustration_blocked" in concepts_fired


def test_tool_heavy_completed_fires_pride(isolated_runtime, monkeypatch) -> None:
    from core.services import emotion_concepts as ec
    from core.services.cognitive_episodes import record_runtime_episode

    ec._last_trigger_at.clear()

    fired = []
    original = ec.trigger_emotion_concept
    monkeypatch.setattr(
        ec, "trigger_emotion_concept",
        lambda *a, **kw: (fired.append((a, kw)) or original(*a, **kw)),
    )

    record_runtime_episode(
        source_run_id="run-3", session_id="s",
        trigger="x", outcome_status="completed",
        summary="ok", tool_names=["t1", "t2", "t3"],
    )

    concepts_fired = [a[0][0] for a in fired]
    assert "pride" in concepts_fired


def test_user_message_with_humor_fires_playfulness(
    isolated_runtime, monkeypatch,
) -> None:
    from core.services import emotion_concepts as ec
    from core.services.emotion_concepts_channel_triggers import (
        on_channel_message_appended,
    )

    ec._last_trigger_at.clear()
    fired = []
    monkeypatch.setattr(
        ec, "trigger_emotion_concept",
        lambda *a, **kw: fired.append((a, kw)),
    )

    on_channel_message_appended({
        "session_id": "s",
        "message": {"role": "user", "content": "haha det var sjovt 🤣"},
    })

    concepts = [a[0][0] for a in fired]
    assert "playfulness" in concepts


def test_user_vulnerability_fires_tenderness(
    isolated_runtime, monkeypatch,
) -> None:
    from core.services import emotion_concepts as ec
    from core.services.emotion_concepts_channel_triggers import (
        on_channel_message_appended,
    )

    ec._last_trigger_at.clear()
    fired = []
    monkeypatch.setattr(
        ec, "trigger_emotion_concept",
        lambda *a, **kw: fired.append((a, kw)),
    )

    on_channel_message_appended({
        "session_id": "s",
        "message": {"role": "user", "content": "jeg er ked af det og alene"},
    })

    concepts = [a[0][0] for a in fired]
    assert "tenderness" in concepts


def test_user_message_baseline_fires_warmth(
    isolated_runtime, monkeypatch,
) -> None:
    from core.services import emotion_concepts as ec
    from core.services.emotion_concepts_channel_triggers import (
        on_channel_message_appended,
    )

    ec._last_trigger_at.clear()
    fired = []
    monkeypatch.setattr(
        ec, "trigger_emotion_concept",
        lambda *a, **kw: fired.append((a, kw)),
    )

    on_channel_message_appended({
        "session_id": "s",
        "message": {"role": "user", "content": "godmorgen"},
    })

    concepts = [a[0][0] for a in fired]
    assert "warmth" in concepts
