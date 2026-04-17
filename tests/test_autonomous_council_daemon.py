"""Tests for autonomous_council_daemon signal scoring, gating, and tick."""
from __future__ import annotations

from unittest.mock import patch


def _score(surfaces: dict) -> float:
    from core.services.autonomous_council_daemon import compute_signal_score
    return compute_signal_score(surfaces)


def test_all_zero_surfaces_give_zero_score():
    surfaces = {
        "autonomy_pressure": {"summary": {"active_count": 0}},
        "open_loop": {"summary": {"open_count": 0}},
        "internal_opposition": {"active": False},
        "existential_wonder": {"latest_wonder": ""},
        "creative_drift": {"drift_count_today": 0},
        "desire": {"active_count": 0},
        "conflict": {"last_conflict": ""},
        "hours_since_last_council": None,
    }
    assert _score(surfaces) == 0.0


def test_all_max_surfaces_give_score_above_threshold():
    surfaces = {
        "autonomy_pressure": {"summary": {"active_count": 3}},
        "open_loop": {"summary": {"open_count": 5}},
        "internal_opposition": {"active": True},
        "existential_wonder": {"latest_wonder": "What am I?"},
        "creative_drift": {"drift_count_today": 3},
        "desire": {"active_count": 3},
        "conflict": {"last_conflict": "some conflict"},
        "hours_since_last_council": 48,
    }
    score = _score(surfaces)
    assert score >= 0.55


def test_time_signal_normalized_at_48h():
    surfaces = {
        "autonomy_pressure": {"summary": {"active_count": 0}},
        "open_loop": {"summary": {"open_count": 0}},
        "internal_opposition": {"active": False},
        "existential_wonder": {"latest_wonder": ""},
        "creative_drift": {"drift_count_today": 0},
        "desire": {"active_count": 0},
        "conflict": {"last_conflict": ""},
        "hours_since_last_council": 48,
    }
    score = _score(surfaces)
    # time weight is 0.10; 48h → normalized 1.0 → contributes exactly 0.10
    assert abs(score - 0.10) < 0.001


def test_score_clamped_at_1():
    surfaces = {
        "autonomy_pressure": {"summary": {"active_count": 999}},
        "open_loop": {"summary": {"open_count": 999}},
        "internal_opposition": {"active": True},
        "existential_wonder": {"latest_wonder": "x"},
        "creative_drift": {"drift_count_today": 999},
        "desire": {"active_count": 999},
        "conflict": {"last_conflict": "x"},
        "hours_since_last_council": 999,
    }
    assert _score(surfaces) <= 1.0


def test_cadence_gate_blocks_when_recent():
    from core.services import autonomous_council_daemon as acd
    from datetime import UTC, datetime
    acd._last_council_at = datetime.now(UTC)
    assert acd._cadence_gate_ok() is False
    acd._last_council_at = None  # reset


def test_cadence_gate_passes_when_none():
    from core.services import autonomous_council_daemon as acd
    acd._last_council_at = None
    assert acd._cadence_gate_ok() is True


def test_cooldown_gate_blocks_when_recent():
    from core.services import autonomous_council_daemon as acd
    from datetime import UTC, datetime
    acd._last_concluded_at = datetime.now(UTC)
    assert acd._cooldown_gate_ok() is False
    acd._last_concluded_at = None  # reset


def test_derive_topic_calls_llm():
    from core.services.autonomous_council_daemon import derive_topic
    with patch(
        "core.services.autonomous_council_daemon._call_llm",
        return_value="What limits my autonomy?",
    ):
        topic = derive_topic(top_signals=["autonomy_pressure", "open_loop"])
    assert len(topic) > 0


def test_compose_members_full_council_at_high_score():
    from core.services.autonomous_council_daemon import compose_members
    members = compose_members(score=0.85, top_signals=["autonomy_pressure"])
    assert len(members) >= 4


def test_compose_members_partial_at_normal_score():
    from core.services.autonomous_council_daemon import compose_members
    members = compose_members(score=0.65, top_signals=["existential_wonder"])
    assert 3 <= len(members) <= 4


def test_tick_skips_when_score_below_threshold():
    from core.services import autonomous_council_daemon as acd
    acd._last_council_at = None
    acd._last_concluded_at = None
    result = acd.tick_autonomous_council_daemon(score_override=0.30)
    assert result["triggered"] is False
    assert result["reason"] == "score_below_threshold"


def test_tick_skips_when_cadence_blocked():
    from core.services import autonomous_council_daemon as acd
    from datetime import UTC, datetime
    acd._last_council_at = datetime.now(UTC)
    result = acd.tick_autonomous_council_daemon(score_override=0.80)
    assert result["triggered"] is False
    assert result["reason"] == "cadence_gate"
    acd._last_council_at = None


def test_tick_skips_when_cooldown_blocked():
    from core.services import autonomous_council_daemon as acd
    from datetime import UTC, datetime
    acd._last_concluded_at = datetime.now(UTC)
    result = acd.tick_autonomous_council_daemon(score_override=0.80)
    assert result["triggered"] is False
    assert result["reason"] == "cooldown_gate"
    acd._last_concluded_at = None


def test_tick_triggers_council_when_conditions_met():
    from core.services import autonomous_council_daemon as acd
    acd._last_council_at = None
    acd._last_concluded_at = None
    with (
        patch("core.services.autonomous_council_daemon.derive_topic", return_value="Test topic"),
        patch("core.services.autonomous_council_daemon._run_autonomous_council", return_value={"council_id": "c-123", "conclusion": "test"}),
    ):
        result = acd.tick_autonomous_council_daemon(score_override=0.75)
    assert result["triggered"] is True
    assert result["council_id"] == "c-123"


def test_tick_publishes_eventbus_on_trigger():
    from core.services import autonomous_council_daemon as acd
    from core.eventbus.bus import event_bus
    acd._last_council_at = None
    acd._last_concluded_at = None
    q = event_bus.subscribe()
    with (
        patch("core.services.autonomous_council_daemon.derive_topic", return_value="Test topic"),
        patch("core.services.autonomous_council_daemon._run_autonomous_council", return_value={"council_id": "c-xyz", "conclusion": "done"}),
    ):
        acd.tick_autonomous_council_daemon(score_override=0.75)
    # Drain queue and check for autonomous_triggered event
    events = []
    while not q.empty():
        events.append(q.get_nowait())
    assert any(e and e.get("kind") == "council.autonomous_triggered" for e in events)
