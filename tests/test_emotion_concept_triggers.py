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
