"""Tests for bounded inner witness daemon light."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

import core.services.witness_signal_tracking as ws_module
from core.services.witness_signal_tracking import (
    run_witness_daemon,
    get_witness_daemon_state,
    _DAEMON_COOLDOWN_MINUTES,
    _DAEMON_VISIBLE_GRACE_MINUTES,
)


@pytest.fixture(autouse=True)
def _reset_daemon_state():
    """Reset daemon state between tests."""
    ws_module._daemon_last_run_at = ""
    ws_module._daemon_last_result = None
    yield
    ws_module._daemon_last_run_at = ""
    ws_module._daemon_last_result = None


# ---------------------------------------------------------------------------
# Basic daemon execution
# ---------------------------------------------------------------------------


def test_daemon_runs_and_returns_result(isolated_runtime) -> None:
    """Daemon should run and return a well-formed result dict."""
    result = run_witness_daemon(trigger="test")

    assert result["daemon_ran"] is True
    assert result["daemon_blocked_reason"] == ""
    assert result["trigger"] == "test"
    assert "daemon_cadence_state" in result


def test_daemon_returns_no_candidates_when_db_empty(isolated_runtime) -> None:
    """Without runtime signals, daemon should run but find no candidates."""
    result = run_witness_daemon(trigger="test")

    assert result["daemon_ran"] is True
    assert result["daemon_cadence_state"] == "ran-no-candidates"
    assert result.get("daemon_created_count", 0) == 0


# ---------------------------------------------------------------------------
# Cooldown cadence
# ---------------------------------------------------------------------------


def test_daemon_respects_cooldown(isolated_runtime) -> None:
    """Daemon should not run again within cooldown period."""
    # First run
    result1 = run_witness_daemon(trigger="test-1")
    assert result1["daemon_ran"] is True

    # Immediate second run — should be blocked
    result2 = run_witness_daemon(trigger="test-2")
    assert result2["daemon_ran"] is False
    assert result2["daemon_blocked_reason"] == "cooldown-active"
    assert result2["daemon_cadence_state"] == "cooling-down"


def test_daemon_runs_after_cooldown_expires(isolated_runtime) -> None:
    """Daemon should run again after cooldown expires."""
    # First run
    run_witness_daemon(trigger="test-1")

    # Fake expired cooldown
    ws_module._daemon_last_run_at = (
        datetime.now(UTC) - timedelta(minutes=_DAEMON_COOLDOWN_MINUTES + 1)
    ).isoformat()

    # Should run again
    result = run_witness_daemon(trigger="test-2")
    assert result["daemon_ran"] is True


# ---------------------------------------------------------------------------
# Visible activity grace period
# ---------------------------------------------------------------------------


def test_daemon_blocked_by_recent_visible_activity(isolated_runtime) -> None:
    """Daemon should not run if visible activity was very recent."""
    recent = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    result = run_witness_daemon(trigger="test", last_visible_at=recent)

    assert result["daemon_ran"] is False
    assert result["daemon_blocked_reason"] == "visible-activity-too-recent"
    assert result["daemon_cadence_state"] == "grace-period"


def test_daemon_runs_after_visible_grace_expires(isolated_runtime) -> None:
    """Daemon should run if visible activity was long enough ago."""
    old_visible = (
        datetime.now(UTC) - timedelta(minutes=_DAEMON_VISIBLE_GRACE_MINUTES + 1)
    ).isoformat()
    result = run_witness_daemon(trigger="test", last_visible_at=old_visible)

    assert result["daemon_ran"] is True


# ---------------------------------------------------------------------------
# Witness signal production with grounding
# ---------------------------------------------------------------------------


def test_daemon_produces_signals_with_grounded_material(isolated_runtime) -> None:
    """Daemon should create witness signals when runtime has grounded material."""
    db = isolated_runtime.db
    from datetime import UTC
    now = datetime.now(UTC).isoformat()

    # Seed the required material: softening recurrence + settled reflection
    # with matching domain keys
    db.upsert_runtime_temporal_recurrence_signal(
        signal_id="recurrence-test-1",
        signal_type="temporal-recurrence",
        canonical_key="temporal-recurrence:runtime:test-domain",
        status="softening",
        title="Softening recurrence: test domain",
        summary="Test recurrence softening",
        rationale="Test",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="test evidence",
        support_summary="test support",
        support_count=2,
        session_count=2,
        created_at=now,
        updated_at=now,
        status_reason="Test",
        run_id="test-run",
        session_id="test-session",
    )

    db.upsert_runtime_reflection_signal(
        signal_id="reflection-test-1",
        signal_type="bounded-reflection",
        canonical_key="bounded-reflection:runtime:test-domain",
        status="settled",
        title="Settled reflection: test domain",
        summary="Test reflection settled",
        rationale="Test",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="test evidence",
        support_summary="test support",
        support_count=2,
        session_count=2,
        created_at=now,
        updated_at=now,
        status_reason="Test",
        run_id="test-run",
        session_id="test-session",
    )

    result = run_witness_daemon(trigger="test-grounded")

    assert result["daemon_ran"] is True
    assert result["daemon_cadence_state"] == "ran-produced"
    assert result["daemon_created_count"] >= 1
    assert len(result.get("daemon_signal_titles", [])) >= 1


# ---------------------------------------------------------------------------
# Existing visible path not broken
# ---------------------------------------------------------------------------


def test_visible_turn_witness_tracking_still_works(isolated_runtime) -> None:
    """The existing visible-turn witness tracking must still work independently."""
    from core.services.witness_signal_tracking import (
        track_runtime_witness_signals_for_visible_turn,
    )

    # Should work without error even with empty DB
    result = track_runtime_witness_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    assert result["created"] == 0
    assert "summary" in result


# ---------------------------------------------------------------------------
# Observability / MC state
# ---------------------------------------------------------------------------


def test_daemon_state_observable(isolated_runtime) -> None:
    """get_witness_daemon_state must return observable state."""
    state = get_witness_daemon_state()
    assert state["last_run_at"] is None
    assert state["last_result"] is None
    assert state["cooldown_minutes"] == _DAEMON_COOLDOWN_MINUTES

    run_witness_daemon(trigger="test-obs")

    state2 = get_witness_daemon_state()
    assert state2["last_run_at"] is not None
    assert state2["last_result"] is not None
    assert state2["last_result"]["daemon_ran"] is True
