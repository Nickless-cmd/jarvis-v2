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


def test_daemon_insufficient_grounding_when_no_stronger_stream_exists(
    isolated_runtime,
    monkeypatch,
) -> None:
    """Without any grounded runtime stream, daemon should stay in insufficient-grounding fallback."""
    monkeypatch.setattr(
        iv_module,
        "_gather_grounding",
        lambda: {"source_count": 0, "sources": [], "fragments": {}},
    )
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
    recent_witness = (datetime.now(UTC) - timedelta(seconds=30)).isoformat()
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
    assert result["mode"] in {"searching", "circling", "carrying", "pulled", "witness-steady", "work-steady"}
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

    assert note["mode"] in {"searching", "circling", "carrying", "pulled", "witness-steady", "work-steady"}
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
    assert "thinking to yourself" in content.lower()
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


# ---------------------------------------------------------------------------
# Experiential support carry-forward into inner voice
# ---------------------------------------------------------------------------


def test_support_shading_nudges_witness_steady_to_carrying_for_protect_focus() -> None:
    """protect_focus bias should keep the weak witness mode bounded rather than turning it into work-steady."""
    from apps.api.jarvis_api.services.inner_voice_daemon import _apply_support_shading

    result = _apply_support_shading("witness-steady", {
        "experiential_support_bias": "protect_focus",
    })
    assert result == "carrying"


def test_support_shading_nudges_witness_steady_to_carrying() -> None:
    """stabilize_thread bias should nudge the weak witness mode to carrying."""
    from apps.api.jarvis_api.services.inner_voice_daemon import _apply_support_shading

    result = _apply_support_shading("witness-steady", {
        "experiential_support_bias": "stabilize_thread",
    })
    assert result == "carrying"


def test_support_shading_nudges_witness_steady_to_circling() -> None:
    """reopen_context bias should nudge the weak witness mode to circling."""
    from apps.api.jarvis_api.services.inner_voice_daemon import _apply_support_shading

    result = _apply_support_shading("witness-steady", {
        "experiential_support_bias": "reopen_context",
    })
    assert result == "circling"


def test_support_shading_keeps_witness_steady_for_reduce_spread() -> None:
    """reduce_spread should keep the weak witness mode bounded rather than turn it action-like."""
    from apps.api.jarvis_api.services.inner_voice_daemon import _apply_support_shading

    result = _apply_support_shading("witness-steady", {
        "experiential_support_bias": "reduce_spread",
    })
    assert result == "witness-steady"


def test_support_shading_does_not_override_strong_mode() -> None:
    """Support shading must not override grounding-based modes."""
    from apps.api.jarvis_api.services.inner_voice_daemon import _apply_support_shading

    for strong_mode in ("searching", "circling", "carrying", "pulled", "work-steady"):
        result = _apply_support_shading(strong_mode, {
            "experiential_support_bias": "protect_focus",
        })
        assert result == strong_mode, f"Support shading overrode strong mode {strong_mode}"


def test_support_shading_noop_when_bias_is_none() -> None:
    """No shading when support_bias is 'none'."""
    from apps.api.jarvis_api.services.inner_voice_daemon import _apply_support_shading

    result = _apply_support_shading("witness-steady", {
        "experiential_support_bias": "none",
    })
    assert result == "witness-steady"


def test_support_shading_noop_when_no_fragments() -> None:
    """No shading when fragments have no support data."""
    from apps.api.jarvis_api.services.inner_voice_daemon import _apply_support_shading

    result = _apply_support_shading("witness-steady", {})
    assert result == "witness-steady"


def test_deterministic_compose_includes_support_narrative() -> None:
    """When experiential support narrative is present, it should appear in compose output."""
    from apps.api.jarvis_api.services.inner_voice_daemon import _deterministic_compose

    grounding = {
        "source_count": 2,
        "sources": ["experiential-support", "open-loops"],
        "fragments": {
            "open_loop_signal": "An open thread about testing",
            "experiential_support_posture": "carrying",
            "experiential_support_bias": "protect_focus",
            "experiential_support_mode": "weighted",
            "experiential_support_narrative": "Carrying weight, holding focus tight",
        },
    }
    note = _deterministic_compose(grounding)

    assert "Carrying weight" in note["summary"]
    assert note["mode"] == "work-steady"
    assert note["initiative"] is None


def test_select_mode_prefers_living_carry_over_work_steady_when_candidate_pull_is_live() -> None:
    """Mixed work signals should still allow private carry to win when the stream is hesitant and unresolved."""
    from apps.api.jarvis_api.services.inner_voice_daemon import _select_inner_voice_mode

    grounding = {
        "source_count": 4,
        "sources": ["open-loops", "development-focus", "private-brain", "experiential-continuity"],
        "fragments": {
            "open_loop_signal": "visible work thread still hanging around",
            "dev_focus": "active backend repair focus",
            "brain_top_focus": "a half-formed private thread",
            "brain_continuity": "an unresolved thread is still being carried",
            "experiential_initiative_shading": "hesitant",
            "experiential_continuity_state": "lingering",
            "experiential_attentional_posture": "guarded",
            "experiential_cognitive_bearing": "loaded",
            "conductor_mode": "watch",
        },
    }

    mode = _select_inner_voice_mode(
        grounding,
        thought="There is something half-formed here that has not settled into a task.",
    )

    assert mode == "carrying"


def test_derive_focus_prefers_private_carry_for_living_modes() -> None:
    """Living modes should anchor on private carry before visible-work salience."""
    from apps.api.jarvis_api.services.inner_voice_daemon import _derive_inner_voice_focus

    grounding = {
        "fragments": {
            "salient_top": "Visible work: active repair thread",
            "open_loop_signal": "Open loop: active repair",
            "dev_focus": "Backend patching",
            "brain_top_focus": "a quieter unresolved line",
            "witness_signal": "a small witness trace",
        }
    }

    focus = _derive_inner_voice_focus(grounding, mode="carrying")

    assert focus == "a quieter unresolved line"


def test_deterministic_compose_no_support_when_baseline() -> None:
    """No support line when support data is absent."""
    from apps.api.jarvis_api.services.inner_voice_daemon import _deterministic_compose

    grounding = {
        "source_count": 2,
        "sources": ["open-loops", "development-focus"],
        "fragments": {
            "open_loop_signal": "Test loop",
            "dev_focus": "Test focus",
        },
    }
    note = _deterministic_compose(grounding)

    assert "Support:" not in note["summary"]


def test_deterministic_compose_allows_searching_candidate_without_action() -> None:
    """Half-formed experiential pulls should stay as candidate thought instead of collapsing into action."""
    from apps.api.jarvis_api.services.inner_voice_daemon import _deterministic_compose

    grounding = {
        "source_count": 2,
        "sources": ["experiential-continuity", "private-brain"],
        "fragments": {
            "brain_top_focus": "an old line of thought",
            "brain_continuity": "the shape of a longer unresolved thread",
            "experiential_continuity_state": "lingering",
            "experiential_initiative_shading": "hesitant",
            "experiential_influence_narrative": "Cognition carries some weight; initiative feels hesitant.",
        },
    }

    note = _deterministic_compose(grounding)

    assert note["mode"] in {"searching", "circling", "carrying"}
    assert note["initiative"] is None
    assert "candidate thought" in note["summary"].lower() or "hesitant" in note["summary"].lower()


def test_deterministic_compose_does_not_collapse_mixed_candidate_stream_into_work_steady() -> None:
    """Open loops and dev focus should not dominate when the inner stream is still tentative and private."""
    from apps.api.jarvis_api.services.inner_voice_daemon import _deterministic_compose

    grounding = {
        "source_count": 4,
        "sources": ["open-loops", "development-focus", "private-brain", "experiential-continuity"],
        "fragments": {
            "open_loop_signal": "Open loop: visible work",
            "dev_focus": "repair backend path",
            "brain_top_focus": "a quieter unresolved line",
            "brain_continuity": "the thread is still there but not decided",
            "experiential_continuity_state": "lingering",
            "experiential_initiative_shading": "hesitant",
            "experiential_attentional_posture": "guarded",
            "experiential_cognitive_bearing": "loaded",
        },
    }

    note = _deterministic_compose(grounding)

    assert note["mode"] in {"carrying", "circling", "searching"}
    assert note["mode"] != "work-steady"
    assert note["initiative"] is None


def test_deterministic_compose_keeps_open_loop_non_actionable_without_clarify_pressure() -> None:
    """Open loops alone should not auto-create initiative anymore."""
    from apps.api.jarvis_api.services.inner_voice_daemon import _deterministic_compose

    grounding = {
        "source_count": 2,
        "sources": ["open-loops", "witness"],
        "fragments": {
            "open_loop_signal": "a loose unresolved thread",
            "witness_signal": "a small witness trace",
            "conductor_mode": "watch",
        },
    }

    note = _deterministic_compose(grounding)

    assert note["mode"] in {"work-steady", "witness-steady", "circling"}
    assert note["initiative"] is None
