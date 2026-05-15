"""Tests for dream_bias_engine — validation, accumulate, formatter."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest


@pytest.fixture
def fresh_db(monkeypatch, tmp_path):
    db_path = tmp_path / "jarvis.db"
    from core.runtime import db as db_mod
    from core.runtime import db_core
    # Post-2026-05-15 split: patch begge facade + db_core (kilden).
    monkeypatch.setattr(db_mod, "DB_PATH", db_path)
    monkeypatch.setattr(db_core, "DB_PATH", db_path)
    db_mod.init_db()
    return db_path


# ── Vocabulary + validation ────────────────────────────────────────


def test_validate_accepts_clean_output(fresh_db):
    from core.services.dream_bias_engine import _validate_dream_output
    out = _validate_dream_output({
        "dream_text": "Stilheden var lang.",
        "attention_bias": {"unfinished_business": 0.4},
        "threshold_bias": {"loop_persistence": 0.2},
        "intensity": 0.6,
    })
    assert out is not None
    assert out["dream_text"] == "Stilheden var lang."
    assert out["attention_bias"] == {"unfinished_business": 0.4}
    assert out["threshold_bias"] == {"loop_persistence": 0.2}
    assert out["intensity"] == 0.6


def test_validate_drops_unknown_keys(fresh_db):
    from core.services.dream_bias_engine import _validate_dream_output
    out = _validate_dream_output({
        "dream_text": "x",
        "attention_bias": {"unfinished_business": 0.3, "fake_key": 0.5},
        "threshold_bias": {"loop_persistence": 0.1, "made_up": 0.9},
        "intensity": 0.5,
    })
    assert "fake_key" not in out["attention_bias"]
    assert "made_up" not in out["threshold_bias"]


def test_validate_clamps_to_unit_range(fresh_db):
    from core.services.dream_bias_engine import _validate_dream_output
    out = _validate_dream_output({
        "dream_text": "x",
        "attention_bias": {"unfinished_business": 5.0, "regret_threads": -3.0},
        "threshold_bias": {},
        "intensity": 0.5,
    })
    assert out["attention_bias"]["unfinished_business"] == 1.0
    assert out["attention_bias"]["regret_threads"] == -1.0


def test_validate_forces_self_critique_volume_non_positive(fresh_db):
    """Hard guard: dreams may only soften self-criticism, not sharpen it."""
    from core.services.dream_bias_engine import _validate_dream_output
    out = _validate_dream_output({
        "dream_text": "x",
        "attention_bias": {},
        "threshold_bias": {"self_critique_volume": 0.7},
        "intensity": 0.5,
    })
    assert out["threshold_bias"]["self_critique_volume"] == 0.0


def test_validate_returns_none_for_empty_output(fresh_db):
    from core.services.dream_bias_engine import _validate_dream_output
    out = _validate_dream_output({
        "dream_text": "",
        "attention_bias": {},
        "threshold_bias": {},
        "intensity": 0.5,
    })
    assert out is None


def test_validate_defaults_invalid_intensity(fresh_db):
    from core.services.dream_bias_engine import _validate_dream_output
    out = _validate_dream_output({
        "dream_text": "x",
        "attention_bias": {"unfinished_business": 0.3},
        "threshold_bias": {},
        "intensity": "not-a-number",
    })
    assert out["intensity"] == 0.5


# ── Accumulate ────────────────────────────────────────────────────


def test_accumulate_sums_with_intensity_multiplier(fresh_db):
    from core.services.dream_bias_engine import accumulate_bias
    prior = {"unfinished_business": 0.3}
    new = {"unfinished_business": 0.5}
    out = accumulate_bias(prior, new, intensity=0.4)
    assert abs(out["unfinished_business"] - 0.5) < 0.0001


def test_accumulate_clamps_to_unit_range(fresh_db):
    from core.services.dream_bias_engine import accumulate_bias
    prior = {"unfinished_business": 0.9}
    new = {"unfinished_business": 0.8}
    out = accumulate_bias(prior, new, intensity=1.0)
    assert out["unfinished_business"] == 1.0


def test_accumulate_drops_unknown_keys(fresh_db):
    from core.services.dream_bias_engine import accumulate_bias
    out = accumulate_bias({}, {"fake_key": 0.5}, intensity=1.0)
    assert "fake_key" not in out


# ── Kill-switch ───────────────────────────────────────────────────


def test_get_active_dream_bias_returns_none_when_disabled(fresh_db, monkeypatch):
    from core.runtime.db_dream_bias import insert_new_bias
    from core.services.dream_bias_engine import get_active_dream_bias

    insert_new_bias(
        workspace_id="default",
        attention_bias={"unfinished_business": 0.4},
        threshold_bias={},
        intensity=0.6,
        ttl_hours=8,
        dream_text="x",
        source_event_ids=[],
        source_kinds=[],
    )

    class _FakeSettings:
        dream_bias_enabled = False

    monkeypatch.setattr(
        "core.services.dream_bias_engine.load_settings",
        lambda: _FakeSettings(),
    )

    bias = get_active_dream_bias(workspace_id="default")
    assert bias is None


def test_get_active_dream_bias_returns_data_when_enabled(fresh_db, monkeypatch):
    from core.runtime.db_dream_bias import insert_new_bias
    from core.services.dream_bias_engine import get_active_dream_bias

    insert_new_bias(
        workspace_id="default",
        attention_bias={"regret_threads": 0.4},
        threshold_bias={"loop_persistence": -0.2},
        intensity=0.5,
        ttl_hours=8,
        dream_text="test",
        source_event_ids=["e1"],
        source_kinds=["self_review_outcome"],
    )

    class _FakeSettings:
        dream_bias_enabled = True

    monkeypatch.setattr(
        "core.services.dream_bias_engine.load_settings",
        lambda: _FakeSettings(),
    )

    bias = get_active_dream_bias(workspace_id="default")
    assert bias is not None
    assert bias["attention_bias"]["regret_threads"] == 0.4
    assert bias["threshold_bias"]["loop_persistence"] == -0.2
    assert bias["intensity"] == 0.5


# ── Heartbeat formatter ───────────────────────────────────────────


def test_heartbeat_formatter_returns_empty_when_no_bias(fresh_db, monkeypatch):
    class _FakeSettings:
        dream_bias_enabled = True
    monkeypatch.setattr(
        "core.services.dream_bias_engine.load_settings",
        lambda: _FakeSettings(),
    )
    from core.services.dream_bias_engine import format_dream_bias_for_heartbeat
    out = format_dream_bias_for_heartbeat(workspace_id="default")
    assert out == ""


def test_heartbeat_formatter_skips_low_intensity(fresh_db, monkeypatch):
    """Intensity < 0.1 should produce empty render — too weak to surface."""
    from core.runtime.db_dream_bias import insert_new_bias
    from core.services.dream_bias_engine import format_dream_bias_for_heartbeat

    insert_new_bias(
        workspace_id="default",
        attention_bias={"unfinished_business": 0.4},
        threshold_bias={},
        intensity=0.05,
        ttl_hours=8,
        dream_text="x",
        source_event_ids=[],
        source_kinds=[],
    )

    class _FakeSettings:
        dream_bias_enabled = True
    monkeypatch.setattr(
        "core.services.dream_bias_engine.load_settings",
        lambda: _FakeSettings(),
    )

    out = format_dream_bias_for_heartbeat(workspace_id="default")
    assert out == ""


def test_heartbeat_formatter_renders_active_bias(fresh_db, monkeypatch):
    from core.runtime.db_dream_bias import insert_new_bias
    from core.services.dream_bias_engine import format_dream_bias_for_heartbeat

    insert_new_bias(
        workspace_id="default",
        attention_bias={"unfinished_business": 0.4, "regret_threads": 0.3},
        threshold_bias={"loop_persistence": -0.2},
        intensity=0.7,
        ttl_hours=8,
        dream_text="Stilheden var lang.",
        source_event_ids=["e1"],
        source_kinds=["self_review_outcome"],
    )

    class _FakeSettings:
        dream_bias_enabled = True
    monkeypatch.setattr(
        "core.services.dream_bias_engine.load_settings",
        lambda: _FakeSettings(),
    )

    out = format_dream_bias_for_heartbeat(workspace_id="default")
    assert "dream_bias active" in out
    assert "unfinished_business" in out
    assert "regret_threads" in out
    assert "loop_persistence" in out
    assert "Stilheden" in out
