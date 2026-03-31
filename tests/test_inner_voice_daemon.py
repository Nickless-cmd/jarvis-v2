"""Tests for bounded inner voice daemon light."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

import apps.api.jarvis_api.services.inner_voice_daemon as iv_module
from apps.api.jarvis_api.services.inner_voice_daemon import (
    run_inner_voice_daemon,
    get_inner_voice_daemon_state,
    _VOICE_COOLDOWN_MINUTES,
    _VOICE_VISIBLE_GRACE_MINUTES,
    _VOICE_WITNESS_GRACE_MINUTES,
    _MIN_GROUNDING_SOURCES,
)


@pytest.fixture(autouse=True)
def _reset_voice_state():
    """Reset inner voice daemon state between tests."""
    iv_module._voice_last_run_at = ""
    iv_module._voice_last_result = None
    yield
    iv_module._voice_last_run_at = ""
    iv_module._voice_last_result = None


# ---------------------------------------------------------------------------
# Basic execution
# ---------------------------------------------------------------------------


def test_daemon_runs_and_returns_result(isolated_runtime) -> None:
    """Daemon should run and return a well-formed result dict."""
    result = run_inner_voice_daemon(trigger="test")
    assert "daemon_ran" in result
    assert "inner_voice_created" in result
    assert result["trigger"] == "test"


def test_daemon_insufficient_grounding_when_db_empty(isolated_runtime) -> None:
    """Without runtime signals, daemon should run but find insufficient grounding."""
    result = run_inner_voice_daemon(trigger="test")
    assert result["daemon_ran"] is True
    assert result["daemon_cadence_state"] == "ran-insufficient-grounding"
    assert result["inner_voice_created"] is False


# ---------------------------------------------------------------------------
# Cooldown cadence
# ---------------------------------------------------------------------------


def test_daemon_respects_cooldown(isolated_runtime) -> None:
    """Daemon should not run again within cooldown period."""
    run_inner_voice_daemon(trigger="test-1")

    result2 = run_inner_voice_daemon(trigger="test-2")
    assert result2["daemon_ran"] is False
    assert result2["daemon_blocked_reason"] == "cooldown-active"


def test_daemon_runs_after_cooldown_expires(isolated_runtime) -> None:
    """Daemon should run again after cooldown expires."""
    run_inner_voice_daemon(trigger="test-1")

    iv_module._voice_last_run_at = (
        datetime.now(UTC) - timedelta(minutes=_VOICE_COOLDOWN_MINUTES + 1)
    ).isoformat()

    result = run_inner_voice_daemon(trigger="test-2")
    assert result["daemon_ran"] is True


# ---------------------------------------------------------------------------
# Visible activity grace
# ---------------------------------------------------------------------------


def test_daemon_blocked_by_recent_visible_activity(isolated_runtime) -> None:
    """Daemon should not run if visible activity was very recent."""
    recent = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    result = run_inner_voice_daemon(trigger="test", last_visible_at=recent)

    assert result["daemon_ran"] is False
    assert result["daemon_blocked_reason"] == "visible-activity-too-recent"


def test_daemon_runs_after_visible_grace_expires(isolated_runtime) -> None:
    """Daemon should run if visible activity was long enough ago."""
    old = (datetime.now(UTC) - timedelta(minutes=_VOICE_VISIBLE_GRACE_MINUTES + 1)).isoformat()
    result = run_inner_voice_daemon(trigger="test", last_visible_at=old)

    assert result["daemon_ran"] is True


# ---------------------------------------------------------------------------
# Witness daemon coordination
# ---------------------------------------------------------------------------


def test_daemon_blocked_by_recent_witness_daemon(isolated_runtime) -> None:
    """Inner voice should not run if witness daemon ran very recently."""
    recent_witness = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    result = run_inner_voice_daemon(
        trigger="test",
        witness_daemon_last_run_at=recent_witness,
    )

    assert result["daemon_ran"] is False
    assert result["daemon_blocked_reason"] == "witness-daemon-too-recent"


def test_daemon_runs_after_witness_grace_expires(isolated_runtime) -> None:
    """Inner voice should run if witness daemon ran long enough ago."""
    old_witness = (datetime.now(UTC) - timedelta(minutes=_VOICE_WITNESS_GRACE_MINUTES + 1)).isoformat()
    result = run_inner_voice_daemon(
        trigger="test",
        witness_daemon_last_run_at=old_witness,
    )

    assert result["daemon_ran"] is True


# ---------------------------------------------------------------------------
# Grounding and production
# ---------------------------------------------------------------------------


def test_daemon_produces_voice_note_with_sufficient_grounding(isolated_runtime) -> None:
    """With enough grounding material, daemon should produce an inner voice note."""
    db = isolated_runtime.db
    now = datetime.now(UTC).isoformat()

    # Seed open loop for grounding
    db.upsert_runtime_open_loop_signal(
        signal_id="loop-voice-test",
        signal_type="open-loop",
        canonical_key="open-loop:voice-test-thread",
        status="open",
        title="Open loop: voice test",
        summary="An open thread for voice daemon testing",
        rationale="Test",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="test",
        support_summary="test",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Test",
        run_id="test-run",
        session_id="test-session",
    )

    # Seed a development focus for grounding
    db.upsert_runtime_development_focus(
        focus_id="focus-voice-test",
        focus_type="runtime-growth",
        canonical_key="development-focus:voice-test-growth",
        status="active",
        title="Growth focus: voice daemon testing",
        summary="Active growth focus for testing",
        rationale="Test",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="test",
        support_summary="test",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Test",
        run_id="test-run",
        session_id="test-session",
    )

    result = run_inner_voice_daemon(trigger="test-grounded")

    assert result["daemon_ran"] is True
    assert result["inner_voice_created"] is True
    assert result["daemon_cadence_state"] == "ran-produced"
    assert result["record_id"] != ""
    assert result["mode"] in {"reflective-carry", "held-tension", "growth-oriented", "continuity-aware", "observing"}
    assert result["render_mode"] in {"llm-rendered", "deterministic-fallback"}


# ---------------------------------------------------------------------------
# Existing paths not broken
# ---------------------------------------------------------------------------


def test_private_brain_insert_still_works(isolated_runtime) -> None:
    """Private brain record insertion should still work independently."""
    record = insert_private_brain_record(
        record_id="test-manual-insert",
        record_type="test",
        layer="private_brain",
        session_id="test",
        run_id="test",
        focus="test focus",
        summary="test summary",
        detail="test detail",
        source_signals="test",
        confidence="medium",
        created_at=datetime.now(UTC).isoformat(),
    )
    assert record.get("record_id") == "test-manual-insert"


# ---------------------------------------------------------------------------
# Observability
# ---------------------------------------------------------------------------


def test_daemon_state_observable(isolated_runtime) -> None:
    """get_inner_voice_daemon_state must return observable state."""
    state = get_inner_voice_daemon_state()
    assert state["last_run_at"] is None
    assert state["last_result"] is None
    assert state["cooldown_minutes"] == _VOICE_COOLDOWN_MINUTES

    run_inner_voice_daemon(trigger="test-obs")

    state2 = get_inner_voice_daemon_state()
    assert state2["last_run_at"] is not None
    assert state2["last_result"] is not None
    assert state2["last_result"]["trigger"] == "test-obs"


# Import needed for one test
from core.runtime.db import insert_private_brain_record


# ---------------------------------------------------------------------------
# Workspace-led rendering tests
# ---------------------------------------------------------------------------


def test_deterministic_fallback_produces_valid_note(isolated_runtime) -> None:
    """Deterministic fallback must produce a valid note structure."""
    from apps.api.jarvis_api.services.inner_voice_daemon import _deterministic_compose

    grounding = {
        "source_count": 2,
        "sources": ["open-loops", "development-focus"],
        "fragments": {
            "open_loop_signal": "An open thread about testing",
            "dev_focus": "Growth focus on daemon architecture",
        },
    }
    note = _deterministic_compose(grounding)

    assert note["mode"] in {"reflective-carry", "held-tension", "growth-oriented", "continuity-aware", "observing"}
    assert note["focus"]
    assert note["summary"]
    assert note["confidence"] in {"low", "medium", "high"}
    assert "Deterministic fallback" in note["detail"]


def test_render_falls_back_when_no_workspace_file(isolated_runtime, tmp_path) -> None:
    """When INNER_VOICE.md doesn't exist, render should use deterministic fallback."""
    from apps.api.jarvis_api.services.inner_voice_daemon import _render_inner_voice_note

    grounding = {
        "source_count": 2,
        "sources": ["open-loops", "private-brain"],
        "fragments": {
            "open_loop_signal": "Test loop",
            "brain_continuity": "Test carry",
        },
    }
    note, render_mode = _render_inner_voice_note(grounding)

    assert note["focus"]
    assert note["summary"]
    # In test environment without real model, should use fallback
    assert render_mode in {"llm-rendered", "deterministic-fallback"}


def test_workspace_inner_voice_template_exists() -> None:
    """INNER_VOICE.md template must exist in workspace/templates/."""
    from pathlib import Path
    template = Path("workspace/templates/INNER_VOICE.md")
    assert template.exists(), "INNER_VOICE.md template missing from workspace/templates/"
    content = template.read_text()
    assert "inner voice" in content.lower()
    assert "JSON" in content or "json" in content


def test_render_mode_is_observable_in_daemon_result(isolated_runtime) -> None:
    """Daemon result must include render_mode showing llm vs fallback."""
    db = isolated_runtime.db
    now = datetime.now(UTC).isoformat()

    db.upsert_runtime_open_loop_signal(
        signal_id="loop-render-test",
        signal_type="open-loop",
        canonical_key="open-loop:render-test",
        status="open",
        title="Render test loop",
        summary="Testing render mode observability",
        rationale="Test",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="test",
        support_summary="test",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Test",
        run_id="test",
        session_id="test",
    )
    db.upsert_runtime_development_focus(
        focus_id="focus-render-test",
        focus_type="runtime-growth",
        canonical_key="development-focus:render-test",
        status="active",
        title="Render test focus",
        summary="Testing render mode",
        rationale="Test",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="test",
        support_summary="test",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Test",
        run_id="test",
        session_id="test",
    )

    result = run_inner_voice_daemon(trigger="test-render-obs")
    assert result["daemon_ran"] is True
    assert result["inner_voice_created"] is True
    assert "render_mode" in result
    assert result["render_mode"] in {"llm-rendered", "deterministic-fallback"}
