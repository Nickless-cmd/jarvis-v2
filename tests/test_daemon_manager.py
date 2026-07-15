"""Tests for daemon_manager — registry, state persistence, tick recording."""
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch


def test_registry_contains_all_daemons():
    from core.services import daemon_manager
    names = daemon_manager.get_daemon_names()
    expected = {
        "somatic", "surprise", "aesthetic_taste", "irony", "thought_stream",
        "thought_action_proposal", "conflict", "reflection_cycle", "curiosity",
        "meta_reflection", "experienced_time", "development_narrative",
        "absence", "creative_drift", "existential_wonder", "dream_insight",
        "code_aesthetic", "memory_decay", "user_model", "desire",
        "autonomous_council",
        "council_memory",
    }
    # System has grown beyond the original 22 daemons (43+ as of 2026-05-15).
    # Test intent: verify the 22 known/core daemons are registered. New
    # daemons shouldn't make this test fail — they're additive.
    assert expected.issubset(names), f"missing core daemons: {expected - names}"


def test_get_all_daemon_states_returns_correct_fields(tmp_path):
    from core.services import daemon_manager
    with patch.object(daemon_manager, "_state_file", return_value=tmp_path / "DAEMON_STATE.json"):
        states = daemon_manager.get_all_daemon_states()
    # System has grown to 43+ daemons; assert membership/shape, not count.
    assert len(states) >= 22
    for s in states:
        assert "name" in s
        assert "enabled" in s
        assert "default_cadence_minutes" in s
        assert "effective_cadence_minutes" in s
        assert "interval_minutes_override" in s
        assert "last_run_at" in s
        assert "hours_since_last_run" in s
        assert "last_result_summary" in s


def test_enable_disable_persists(tmp_path):
    from core.services import daemon_manager
    state_file = tmp_path / "DAEMON_STATE.json"
    with patch.object(daemon_manager, "_state_file", return_value=state_file):
        daemon_manager.set_daemon_enabled("curiosity", False)
        assert not daemon_manager.is_enabled("curiosity")
        daemon_manager.set_daemon_enabled("curiosity", True)
        assert daemon_manager.is_enabled("curiosity")
        data = json.loads(state_file.read_text())
        assert data["curiosity"]["enabled"] is True


def test_record_daemon_tick_updates_state(tmp_path):
    from core.services import daemon_manager
    with patch.object(daemon_manager, "_state_file", return_value=tmp_path / "DAEMON_STATE.json"):
        daemon_manager.record_daemon_tick("curiosity", {"generated": True, "curiosity": "why?"})
        states = daemon_manager.get_all_daemon_states()
        c = next(s for s in states if s["name"] == "curiosity")
        assert c["last_run_at"] != ""
        assert c["hours_since_last_run"] is not None
        assert "generated: True" in c["last_result_summary"]


def test_event_trigger_shadow_registered_and_records(tmp_path):
    """2026-07-14: event_trigger_shadow flyttet fra aktivitets-gated _build_influence_trace
    til den ubetingede daemon-sektion. Den SKAL være i registry, ellers er
    record_daemon_tick en no-op (name not in _REGISTRY → return) og cadencen er blind."""
    from core.services import daemon_manager
    assert "event_trigger_shadow" in daemon_manager.get_daemon_names()
    with patch.object(daemon_manager, "_state_file", return_value=tmp_path / "DAEMON_STATE.json"):
        assert daemon_manager.is_enabled("event_trigger_shadow")  # default ON for θ-kalibrering
        assert daemon_manager.get_effective_cadence("event_trigger_shadow") == 3
        daemon_manager.record_daemon_tick(
            "event_trigger_shadow", {"recorded": True, "would_dispatch": False},
        )
        states = daemon_manager.get_all_daemon_states()
        e = next(s for s in states if s["name"] == "event_trigger_shadow")
        assert e["last_run_at"] != ""
        assert "recorded: True" in e["last_result_summary"]


def test_unknown_daemon_raises(tmp_path):
    import pytest
    from core.services import daemon_manager
    with patch.object(daemon_manager, "_state_file", return_value=tmp_path / "DAEMON_STATE.json"):
        with pytest.raises(ValueError, match="unknown daemon"):
            daemon_manager.set_daemon_enabled("nonexistent", True)


def test_set_interval_persists(tmp_path):
    from core.services import daemon_manager
    with patch.object(daemon_manager, "_state_file", return_value=tmp_path / "DAEMON_STATE.json"):
        daemon_manager.control_daemon("curiosity", "set_interval", interval_minutes=15)
        assert daemon_manager.get_effective_cadence("curiosity") == 15
        data = json.loads((tmp_path / "DAEMON_STATE.json").read_text())
        assert data["curiosity"]["interval_minutes_override"] == 15


def test_set_interval_below_one_raises(tmp_path):
    import pytest
    from core.services import daemon_manager
    with patch.object(daemon_manager, "_state_file", return_value=tmp_path / "DAEMON_STATE.json"):
        with pytest.raises(ValueError, match="interval_minutes must be"):
            daemon_manager.control_daemon("curiosity", "set_interval", interval_minutes=0)


def test_restart_clears_state_var(tmp_path):
    from core.services import daemon_manager
    from core.services import curiosity_daemon
    curiosity_daemon._last_tick_at = datetime.now(UTC)
    with patch.object(daemon_manager, "_state_file", return_value=tmp_path / "DAEMON_STATE.json"):
        daemon_manager.control_daemon("curiosity", "restart")
    assert curiosity_daemon._last_tick_at is None


def test_retired_daemons_default_disabled(tmp_path):
    """Fase 6/7 + Lag 6: autonomous_council, code_aesthetic and current_pull are
    retired — registered (code + engine preserved) but not running by default."""
    from core.services import daemon_manager
    retired = ("autonomous_council", "code_aesthetic", "current_pull")
    for name in retired:
        assert name in daemon_manager.get_daemon_names()
        assert daemon_manager._REGISTRY[name].get("default_enabled") is False, name
    with patch.object(daemon_manager, "_state_file", return_value=tmp_path / "DAEMON_STATE.json"):
        for name in retired:
            assert daemon_manager.is_enabled(name) is False, name


def test_unknown_daemon_control_raises(tmp_path):
    import pytest
    from core.services import daemon_manager
    with patch.object(daemon_manager, "_state_file", return_value=tmp_path / "DAEMON_STATE.json"):
        with pytest.raises(ValueError, match="unknown daemon"):
            daemon_manager.control_daemon("ghost_daemon", "enable")


def test_set_interval_requires_minutes_param(tmp_path):
    import pytest
    from core.services import daemon_manager
    with patch.object(daemon_manager, "_state_file", return_value=tmp_path / "DAEMON_STATE.json"):
        with pytest.raises(ValueError, match="interval_minutes required"):
            daemon_manager.control_daemon("curiosity", "set_interval")
