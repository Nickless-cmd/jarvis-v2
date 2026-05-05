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


def test_detect_cluster_dominance_signal(isolated_runtime) -> None:
    from core.services.concept_baseline_tracker import (
        record_concept_trigger,
        _detect_drift,
        _aggregate_clusters,
    )

    for _ in range(12):
        record_concept_trigger(
            concept="joy", intensity=0.5,
            triggered_at="2026-05-05T10:00:00+00:00", source="t",
        )
    for _ in range(8):
        record_concept_trigger(
            concept="frustration_blocked", intensity=0.5,
            triggered_at="2026-05-05T10:00:00+00:00", source="t",
        )

    clusters = _aggregate_clusters()
    signals = _detect_drift(clusters, [])
    dominance = [s for s in signals if s["type"] == "cluster_dominance"]
    assert len(dominance) == 1
    assert dominance[0]["cluster"] == "JOY_APPROACH"


def test_detect_no_signal_when_balanced(isolated_runtime) -> None:
    from core.services.concept_baseline_tracker import (
        record_concept_trigger,
        _detect_drift,
        _aggregate_clusters,
    )

    for _ in range(10):
        record_concept_trigger(
            concept="joy", intensity=0.5,
            triggered_at="2026-05-05T10:00:00+00:00", source="t",
        )
    for _ in range(10):
        record_concept_trigger(
            concept="warmth", intensity=0.5,
            triggered_at="2026-05-05T10:00:00+00:00", source="t",
        )

    clusters = _aggregate_clusters()
    signals = _detect_drift(clusters, [])
    dominance = [s for s in signals if s["type"] == "cluster_dominance"]
    assert dominance == []


def test_write_concept_baseline_md_creates_file(
    isolated_runtime, monkeypatch, tmp_path,
) -> None:
    from core.services import concept_baseline_tracker as cbt
    from core.services.concept_baseline_tracker import (
        record_concept_trigger,
        _write_concept_baseline_md,
        _aggregate_clusters,
    )
    from core.runtime.db import list_concept_baseline_stats

    workspace = tmp_path / "ws"
    workspace.mkdir()
    monkeypatch.setattr(cbt, "_workspace_dir", lambda: workspace)

    for _ in range(3):
        record_concept_trigger(
            concept="joy", intensity=0.5,
            triggered_at="2026-05-05T10:00:00+00:00", source="t",
        )

    cluster_stats = _aggregate_clusters()
    _write_concept_baseline_md(cluster_stats, list_concept_baseline_stats())

    md = workspace / "CONCEPT_BASELINE.md"
    assert md.exists()
    content = md.read_text()
    assert "Emotional Baseline" in content
    assert "JOY_APPROACH" in content
    assert "joy" in content


def test_evaluate_calls_proposer_when_signal_stable(
    isolated_runtime, monkeypatch, tmp_path,
) -> None:
    from core.services import concept_baseline_tracker as cbt

    workspace = tmp_path / "ws"
    workspace.mkdir()
    monkeypatch.setattr(cbt, "_workspace_dir", lambda: workspace)

    proposer_calls = []
    monkeypatch.setattr(
        cbt, "_propose_identity_update",
        lambda signal: proposer_calls.append(signal),
    )

    for _ in range(12):
        cbt.record_concept_trigger(
            concept="joy", intensity=0.5,
            triggered_at="2026-05-05T10:00:00+00:00", source="t",
        )
    for _ in range(8):
        cbt.record_concept_trigger(
            concept="frustration_blocked", intensity=0.5,
            triggered_at="2026-05-05T10:00:00+00:00", source="t",
        )

    result = cbt.evaluate_baseline_drift()
    assert result.get("skipped") is not True
    assert "drift_signals" in result
    assert any(s["type"] == "cluster_dominance" for s in result["drift_signals"])


def test_evaluate_disabled_returns_skipped(
    isolated_runtime, monkeypatch,
) -> None:
    from core.runtime import settings as settings_mod
    from core.services import concept_baseline_tracker as cbt

    original = settings_mod.load_settings
    def patched():
        s = original()
        s.concept_baseline_tracker_enabled = False
        return s
    monkeypatch.setattr(settings_mod, "load_settings", patched)

    result = cbt.evaluate_baseline_drift()
    assert result.get("skipped") is True


def test_build_concept_baseline_surface_returns_overview(
    isolated_runtime,
) -> None:
    from core.services.concept_baseline_tracker import (
        record_concept_trigger,
        build_concept_baseline_surface,
    )

    record_concept_trigger(
        concept="joy", intensity=0.6,
        triggered_at="2026-05-05T10:00:00+00:00", source="t",
    )
    surface = build_concept_baseline_surface()
    assert surface["enabled"] is True
    assert surface["concept_count"] >= 1
    assert "cluster_stats" in surface
