"""Tests for autonomous_council_daemon signal scoring, gating, and tick."""
from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _hermetic_durable_counters():
    """Neutralise the durable-counter restore so tests never read a real kv value
    (a stale last_council_at would otherwise trip the cadence gate). Marks restore
    as already-done and clears counters before each test."""
    from core.services import autonomous_council_daemon as acd
    acd._counters_restored = True
    acd._last_council_at = None
    acd._last_concluded_at = None
    acd._daily_council_date = ""
    acd._daily_council_count = 0
    with patch.object(acd, "_persist_durable_counters", lambda: None):
        yield


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
    result = acd.tick_autonomous_council_daemon(score_override=0.10)  # < _THRESHOLD (0.25)
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


# ---------------------------------------------------------------------------
# AKSE 2 — output lands: council initiative reaches the initiative queue
# ---------------------------------------------------------------------------


def test_initiative_lands_in_queue_when_present():
    """A council conclusion carrying an initiative calls push_initiative(source=council)."""
    from core.services import autonomous_council_daemon as acd
    acd._last_council_at = None
    acd._last_concluded_at = None
    with (
        patch("core.services.autonomous_council_daemon.derive_topic", return_value="T"),
        patch(
            "core.services.autonomous_council_daemon._run_autonomous_council",
            return_value={"council_id": "c-1", "conclusion": "done",
                          "initiative": "Undersøg min egen kontinuitet"},
        ),
        patch("core.services.initiative_queue.push_initiative", return_value="init-abc") as push,
    ):
        result = acd.tick_autonomous_council_daemon(score_override=0.75)
    push.assert_called_once()
    assert push.call_args.kwargs["source"] == "council"
    assert push.call_args.kwargs["source_id"] == "c-1"
    assert result["initiative_id"] == "init-abc"


def test_no_initiative_no_queue_push():
    """No initiative field → no push (backward compatible, empty is fine)."""
    from core.services import autonomous_council_daemon as acd
    acd._last_council_at = None
    acd._last_concluded_at = None
    with (
        patch("core.services.autonomous_council_daemon.derive_topic", return_value="T"),
        patch(
            "core.services.autonomous_council_daemon._run_autonomous_council",
            return_value={"council_id": "c-2", "conclusion": "done", "initiative": ""},
        ),
        patch("core.services.initiative_queue.push_initiative", return_value="x") as push,
    ):
        result = acd.tick_autonomous_council_daemon(score_override=0.75)
    push.assert_not_called()
    assert result["initiative_id"] == ""


def test_land_initiative_self_safe_on_failure():
    """A failing push must not raise — _land_initiative returns ''."""
    from core.services import autonomous_council_daemon as acd
    with patch("core.services.initiative_queue.push_initiative", side_effect=RuntimeError("boom")):
        assert acd._land_initiative(initiative="x", council_id="c") == ""


# ---------------------------------------------------------------------------
# AKSE 4 — reason-judge wiring: off keeps legacy gate; on lets judge decide
# ---------------------------------------------------------------------------


def test_judge_off_keeps_legacy_threshold_gate():
    """With judge off, score below threshold still blocks (legacy behaviour)."""
    from core.services import autonomous_council_daemon as acd
    acd._last_council_at = None
    acd._last_concluded_at = None
    with patch("core.services.central_convene_judge.judge_convene",
               return_value={"mode": "off", "convene": False}):
        result = acd.tick_autonomous_council_daemon(score_override=0.10)
    assert result["triggered"] is False
    assert result["reason"] == "score_below_threshold"


def test_judge_on_blocks_when_no_reason():
    """With judge on and convene=False, council is not called even above threshold."""
    from core.services import autonomous_council_daemon as acd
    acd._last_council_at = None
    acd._last_concluded_at = None
    with patch("core.services.central_convene_judge.judge_convene",
               return_value={"mode": "on", "convene": False, "reason": "no_real_movement"}):
        result = acd.tick_autonomous_council_daemon(score_override=0.90)
    assert result["triggered"] is False
    assert result["reason"] == "convene_judge_no_reason"


def test_judge_on_overrides_roles_and_topic():
    """With judge on and convene=True, its dynamic roles + topic hint are used."""
    from core.services import autonomous_council_daemon as acd
    acd._last_council_at = None
    acd._last_concluded_at = None
    captured = {}

    def _fake_run(*, topic, members):
        captured["topic"] = topic
        captured["members"] = members
        return {"council_id": "c-9", "conclusion": "done"}

    with (
        patch("core.services.central_convene_judge.judge_convene",
              return_value={"mode": "on", "convene": True, "reason": "real_movement",
                            "roles": ["filosof", "etiker", "synthesizer"],
                            "topic_hint": "kontinuitet", "top_signals": ["existential_wonder"]}),
        patch("core.services.autonomous_council_daemon.derive_topic",
              side_effect=lambda sig, topic_hint="": f"Q:{topic_hint}"),
        patch("core.services.autonomous_council_daemon._run_autonomous_council",
              side_effect=_fake_run),
    ):
        result = acd.tick_autonomous_council_daemon(score_override=0.10)
    assert result["triggered"] is True
    assert captured["members"] == ["filosof", "etiker", "synthesizer"]
    assert captured["topic"] == "Q:kontinuitet"


# ---------------------------------------------------------------------------
# Durable counters survive a "restart" (reload from kv)
# ---------------------------------------------------------------------------


def test_durable_counters_restore_from_kv():
    from core.services import autonomous_council_daemon as acd
    from datetime import UTC, datetime
    stored = {
        "last_council_at": "",
        "last_concluded_at": "",
        "daily_council_date": datetime.now(UTC).strftime("%Y-%m-%d"),
        "daily_council_count": 2,
    }
    acd._last_council_at = None
    acd._last_concluded_at = None
    acd._daily_council_date = ""
    acd._daily_council_count = 0
    acd._counters_restored = False
    with patch("core.runtime.db_core.get_runtime_state_value", return_value=stored):
        acd._restore_durable_counters()
    assert acd._daily_council_count == 2
    # reset for other tests
    acd._daily_council_date = ""
    acd._daily_council_count = 0
    acd._counters_restored = False
