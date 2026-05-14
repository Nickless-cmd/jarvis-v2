"""Tests for decision_signal_telemetry — heed-tracking parallel to r2."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.services import decision_signal_telemetry as dst


@pytest.fixture(autouse=True)
def _isolated_telemetry(tmp_path, monkeypatch):
    """Point state_store at a tmp dir per test to avoid leakage."""
    import core.runtime.state_store as ss
    monkeypatch.setattr(ss, "_STATE_DIR", tmp_path)
    yield


def test_record_surface_persists():
    dst.record_surface(decision_id="d1", trigger_name="loop_nudge_5_rounds")
    data = dst._load()
    assert len(data["surfaces"]) == 1
    assert data["surfaces"][0]["decision_id"] == "d1"
    assert data["surfaces"][0]["resolved"] is False


def test_record_surface_dedups_within_5s():
    dst.record_surface(decision_id="d1", trigger_name="t1")
    dst.record_surface(decision_id="d1", trigger_name="t1")  # immediate dup
    data = dst._load()
    assert len(data["surfaces"]) == 1


def test_record_heed_marks_recent_surface():
    dst.record_surface(decision_id="d1", trigger_name="loop_nudge")
    dst.record_heed(tool="bash")
    data = dst._load()
    assert data["surfaces"][0]["resolved"] is True
    assert data["surfaces"][0]["heeded_by_tool"] == "bash"
    assert any(r["verdict"] == "heeded" for r in data["reactions"])


def test_record_heed_ignores_surfaces_outside_window():
    old = datetime.now(UTC) - timedelta(seconds=200)
    dst.record_surface(decision_id="d1", trigger_name="t1", at=old)
    dst.record_heed(tool="bash")
    data = dst._load()
    # Surface not resolved — heed too late
    assert data["surfaces"][0]["resolved"] is False


def test_sweep_marks_expired_as_ignored():
    old = datetime.now(UTC) - timedelta(seconds=200)
    dst.record_surface(decision_id="d1", trigger_name="t1", at=old)
    n = dst.sweep_expired_surfaces()
    assert n == 1
    data = dst._load()
    assert data["surfaces"][0]["resolved"] is True
    assert data["surfaces"][0].get("ignored_at")


def test_summary_aggregates():
    # 3 surfaces, 2 heeded, 1 still open (within window)
    dst.record_surface(decision_id="d1", trigger_name="loop_nudge")
    dst.record_heed(tool="bash")
    dst.record_surface(decision_id="d2", trigger_name="loop_nudge")
    dst.record_heed(tool="read_file")
    dst.record_surface(decision_id="d3", trigger_name="backend_unresolved")

    s = dst.get_telemetry_summary(hours=24)
    assert s["surfaced_total"] == 3
    assert s["heeded_total"] == 2
    assert s["heed_rate"] == pytest.approx(2 / 3, abs=0.01)
    assert s["by_trigger"]["loop_nudge"]["surfaced"] == 2
    assert s["by_trigger"]["loop_nudge"]["heeded"] == 2


def test_telemetry_section_returns_none_below_5_surfaces():
    for i in range(3):
        dst.record_surface(decision_id=f"d{i}", trigger_name="t")
    assert dst.telemetry_section() is None


def test_telemetry_section_flags_under_40_pct():
    # 10 surfaces, 2 heeded → 20% (under 40%)
    for i in range(10):
        dst.record_surface(decision_id=f"d{i}", trigger_name="t")
    dst.record_heed(tool="bash")
    section = dst.telemetry_section()
    assert section is not None
    assert "under 40%" in section
