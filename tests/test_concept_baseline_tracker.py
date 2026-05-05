from __future__ import annotations


def test_record_trigger_creates_first_event(isolated_runtime) -> None:
    from core.runtime.db import get_concept_baseline_stat
    from core.services.concept_baseline_tracker import record_concept_trigger

    record_concept_trigger(
        concept="joy",
        intensity=0.5,
        triggered_at="2026-05-05T10:00:00+00:00",
        source="test",
    )
    row = get_concept_baseline_stat("joy")
    assert row is not None
    assert row["cluster"] == "JOY_APPROACH"
    assert row["total_triggers"] == 1
    assert row["last_triggered_at"] == "2026-05-05T10:00:00+00:00"


def test_record_trigger_increments_total(isolated_runtime) -> None:
    from core.runtime.db import get_concept_baseline_stat
    from core.services.concept_baseline_tracker import record_concept_trigger

    for i in range(5):
        record_concept_trigger(
            concept="warmth",
            intensity=0.4,
            triggered_at=f"2026-05-05T10:0{i}:00+00:00",
            source="test",
        )
    row = get_concept_baseline_stat("warmth")
    assert row["total_triggers"] == 5
    assert row["last_triggered_at"] == "2026-05-05T10:04:00+00:00"


def test_record_trigger_unknown_concept_uses_unknown_cluster(
    isolated_runtime,
) -> None:
    from core.runtime.db import get_concept_baseline_stat
    from core.services.concept_baseline_tracker import record_concept_trigger

    record_concept_trigger(
        concept="not_a_real_concept",
        intensity=0.5,
        triggered_at="2026-05-05T10:00:00+00:00",
        source="test",
    )
    row = get_concept_baseline_stat("not_a_real_concept")
    assert row is not None
    assert row["cluster"] == "UNKNOWN"


def test_aggregate_clusters_returns_share_per_cluster(isolated_runtime) -> None:
    from core.services.concept_baseline_tracker import (
        record_concept_trigger,
        _aggregate_clusters,
    )

    for _ in range(4):
        record_concept_trigger(
            concept="joy", intensity=0.5,
            triggered_at="2026-05-05T10:00:00+00:00", source="t",
        )
    for _ in range(4):
        record_concept_trigger(
            concept="wonder", intensity=0.5,
            triggered_at="2026-05-05T10:00:00+00:00", source="t",
        )
    for _ in range(2):
        record_concept_trigger(
            concept="frustration_blocked", intensity=0.5,
            triggered_at="2026-05-05T10:00:00+00:00", source="t",
        )

    clusters = _aggregate_clusters()
    assert abs(clusters["JOY_APPROACH"]["share"] - 0.8) < 0.01
    assert abs(clusters["DISTRESS_AVOIDANCE"]["share"] - 0.2) < 0.01


def test_record_trigger_disabled_is_noop(isolated_runtime, monkeypatch) -> None:
    from core.runtime import settings as settings_mod
    from core.runtime.db import get_concept_baseline_stat
    from core.services.concept_baseline_tracker import record_concept_trigger

    original = settings_mod.load_settings
    def patched():
        s = original()
        s.concept_baseline_tracker_enabled = False
        return s
    monkeypatch.setattr(settings_mod, "load_settings", patched)

    record_concept_trigger(
        concept="joy", intensity=0.5,
        triggered_at="2026-05-05T10:00:00+00:00", source="test",
    )
    assert get_concept_baseline_stat("joy") is None
