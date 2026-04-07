"""Tests for the cognitive conductor — bounded mental state assembly."""
from __future__ import annotations


# ---------------------------------------------------------------------------
# Cognitive frame structure
# ---------------------------------------------------------------------------


def test_cognitive_frame_has_required_keys() -> None:
    """The cognitive frame must have all required top-level keys."""
    from apps.api.jarvis_api.services.runtime_cognitive_conductor import (
        build_cognitive_frame,
    )

    frame = build_cognitive_frame()

    assert "mode" in frame
    assert "salient_items" in frame
    assert "affordances" in frame
    assert "temporal" in frame
    assert "continuity_pressure" in frame
    assert "private_signal_pressure" in frame
    assert "private_signal_items" in frame
    assert "continuity_mode" in frame
    assert "active_constraints" in frame
    assert "experiential_support" in frame
    assert "counts" in frame
    assert "summary" in frame


def test_mode_is_valid() -> None:
    """The selected mode must be one of the defined modes."""
    from apps.api.jarvis_api.services.runtime_cognitive_conductor import (
        build_cognitive_frame,
    )

    frame = build_cognitive_frame()
    mode = frame["mode"]

    assert "mode" in mode
    assert "reason" in mode
    assert mode["mode"] in {"respond", "reflect", "consolidate", "clarify", "watch"}
    assert len(mode["reason"]) > 0


def test_temporal_depth_is_valid() -> None:
    """Temporal classification must have valid horizon."""
    from apps.api.jarvis_api.services.runtime_cognitive_conductor import (
        build_cognitive_frame,
    )

    frame = build_cognitive_frame()
    temporal = frame["temporal"]

    assert "horizon" in temporal
    assert "reason" in temporal
    assert temporal["horizon"] in {"immediate", "current-session", "carried-across-sessions", "slow-burn"}


def test_continuity_pressure_is_valid() -> None:
    """Continuity pressure must be low/medium/high."""
    from apps.api.jarvis_api.services.runtime_cognitive_conductor import (
        build_cognitive_frame,
    )

    frame = build_cognitive_frame()
    assert frame["continuity_pressure"] in {"low", "medium", "high"}


def test_affordances_structure() -> None:
    """Affordances must have the four affordance categories."""
    from apps.api.jarvis_api.services.runtime_cognitive_conductor import (
        build_cognitive_frame,
    )

    frame = build_cognitive_frame()
    aff = frame["affordances"]

    assert "available_now" in aff
    assert "appropriate_now" in aff
    assert "gated_now" in aff
    assert "not_recommended" in aff
    assert isinstance(aff["available_now"], list)
    assert isinstance(aff["gated_now"], list)


def test_salient_items_are_bounded() -> None:
    """Salient items should be bounded to max 5."""
    from apps.api.jarvis_api.services.runtime_cognitive_conductor import (
        build_cognitive_frame,
    )

    frame = build_cognitive_frame()
    assert len(frame["salient_items"]) <= 5

    for item in frame["salient_items"]:
        assert "source" in item
        assert "summary" in item
        assert "temporal" in item
        assert item["temporal"] in {"immediate", "current-session", "carried-across-sessions", "slow-burn"}


def test_summary_is_readable() -> None:
    """The frame summary should be a readable one-liner."""
    from apps.api.jarvis_api.services.runtime_cognitive_conductor import (
        build_cognitive_frame,
    )

    frame = build_cognitive_frame()
    summary = frame["summary"]

    assert isinstance(summary, str)
    assert len(summary) > 0
    # Should contain mode tag
    assert "[" in summary and "]" in summary


# ---------------------------------------------------------------------------
# Mode selection logic
# ---------------------------------------------------------------------------


def test_mode_selection_respond_when_visible_active() -> None:
    """When visible lane is active, mode should be 'respond'."""
    from apps.api.jarvis_api.services.runtime_cognitive_conductor import _select_mode

    result = _select_mode(
        visible_active=True,
        question_gate_active=False,
        approval_pending=False,
        brain_count=5,
        open_loop_count=2,
        liveness_state="quiet",
        contradiction_active=False,
    )
    assert result["mode"] == "respond"


def test_mode_selection_clarify_when_gate_active() -> None:
    """When question gate is active, mode should be 'clarify'."""
    from apps.api.jarvis_api.services.runtime_cognitive_conductor import _select_mode

    result = _select_mode(
        visible_active=False,
        question_gate_active=True,
        approval_pending=False,
        brain_count=2,
        open_loop_count=1,
        liveness_state="watchful",
        contradiction_active=False,
    )
    assert result["mode"] == "clarify"


def test_mode_selection_consolidate_when_heavy_brain() -> None:
    """When brain is heavy with low loop pressure, mode should be 'consolidate'."""
    from apps.api.jarvis_api.services.runtime_cognitive_conductor import _select_mode

    result = _select_mode(
        visible_active=False,
        question_gate_active=False,
        approval_pending=False,
        brain_count=8,
        open_loop_count=0,
        liveness_state="quiet",
        contradiction_active=False,
    )
    assert result["mode"] == "consolidate"


def test_mode_selection_watch_default() -> None:
    """Default mode should be 'watch'."""
    from apps.api.jarvis_api.services.runtime_cognitive_conductor import _select_mode

    result = _select_mode(
        visible_active=False,
        question_gate_active=False,
        approval_pending=False,
        brain_count=0,
        open_loop_count=0,
        liveness_state="quiet",
        contradiction_active=False,
    )
    assert result["mode"] == "watch"


def test_mode_selection_clarify_when_contradiction_active() -> None:
    """Executive contradiction should force clarify mode."""
    from apps.api.jarvis_api.services.runtime_cognitive_conductor import _select_mode

    result = _select_mode(
        visible_active=False,
        question_gate_active=False,
        approval_pending=False,
        brain_count=1,
        open_loop_count=0,
        liveness_state="quiet",
        contradiction_active=True,
    )
    assert result["mode"] == "clarify"


# ---------------------------------------------------------------------------
# Temporal depth classification
# ---------------------------------------------------------------------------


def test_temporal_immediate_when_no_carry() -> None:
    """When there's no carry, temporal should be 'immediate'."""
    from apps.api.jarvis_api.services.runtime_cognitive_conductor import _classify_temporal_depth

    result = _classify_temporal_depth(brain_count=0, open_loop_count=0, continuity_mode="carry")
    assert result["horizon"] == "immediate"


def test_temporal_carried_across_sessions() -> None:
    """Heavy brain carry should be 'carried-across-sessions'."""
    from apps.api.jarvis_api.services.runtime_cognitive_conductor import _classify_temporal_depth

    result = _classify_temporal_depth(brain_count=4, open_loop_count=1, continuity_mode="carry")
    assert result["horizon"] == "carried-across-sessions"


# ---------------------------------------------------------------------------
# Prompt section
# ---------------------------------------------------------------------------


def test_prompt_section_is_compact() -> None:
    """The cognitive frame prompt section should be compact."""
    from apps.api.jarvis_api.services.runtime_cognitive_conductor import (
        build_cognitive_frame_prompt_section,
    )

    section = build_cognitive_frame_prompt_section()
    assert section is not None
    assert "Cognitive frame" in section
    assert "Time horizon" in section
    assert "Continuity pressure" in section
    # Should be under 800 chars
    assert len(section) < 800, f"Section too long: {len(section)} chars"


def test_counts_are_populated() -> None:
    """The counts dict should have all expected keys."""
    from apps.api.jarvis_api.services.runtime_cognitive_conductor import (
        build_cognitive_frame,
    )

    frame = build_cognitive_frame()
    counts = frame["counts"]

    assert "brain_records" in counts
    assert "open_loops" in counts
    assert "salient_items" in counts
    assert "available_affordances" in counts
    assert "gated_affordances" in counts
    assert "inner_forces" in counts
    assert "private_signals" in counts
    assert all(isinstance(v, int) for v in counts.values())


def test_experiential_support_in_frame() -> None:
    """Cognitive frame includes experiential_support key (may be empty dict)."""
    from apps.api.jarvis_api.services.runtime_cognitive_conductor import (
        build_cognitive_frame,
    )

    frame = build_cognitive_frame()
    assert "experiential_support" in frame
    support = frame["experiential_support"]
    assert isinstance(support, dict)
    # If populated, must have expected keys
    if support.get("support_posture"):
        assert support["support_posture"] in ("steadying", "grounding", "narrowing", "carrying", "reopening")
        assert support.get("support_bias") in ("protect_focus", "stabilize_thread", "reopen_context", "reduce_spread", "none")
        assert support.get("support_mode") in ("steady", "guarded", "weighted", "opening")


def test_cognitive_frame_integrates_living_signal_inputs(monkeypatch) -> None:
    """Relation, world, contradiction, and understanding signals should reach the frame."""
    from apps.api.jarvis_api.services import runtime_cognitive_conductor as conductor

    monkeypatch.setattr(conductor, "_safe_brain_context", lambda: {"record_count": 0, "excerpts": [], "by_type": {}})
    monkeypatch.setattr(
        conductor,
        "_safe_self_knowledge",
        lambda heartbeat_state=None: {
            "active_capabilities": {"items": []},
            "approval_gated": {"items": []},
            "passive_inner_forces": {"items": []},
            "structural_constraints": {"items": []},
        },
    )
    monkeypatch.setattr(conductor, "_safe_open_loops", lambda: {"summary": {"open_count": 0}, "items": []})
    monkeypatch.setattr(conductor, "_safe_question_gates", lambda: {"active": False, "items": []})
    monkeypatch.setattr(conductor, "_safe_initiative_tension", lambda: {"active": False, "summary": {}})
    monkeypatch.setattr(conductor, "_safe_visible_status", lambda: {"provider_status": "idle"})
    monkeypatch.setattr(conductor, "_safe_liveness_snapshot", lambda heartbeat_state=None: {"liveness_state": "quiet"})
    monkeypatch.setattr(conductor, "_safe_experiential_support", lambda: {})
    monkeypatch.setattr(conductor, "_safe_relation_state", lambda: {"items": [{"relation_summary": "Trust is active."}]})
    monkeypatch.setattr(conductor, "_safe_relation_continuity", lambda: {"items": [{"continuity_summary": "Thread is carried."}]})
    monkeypatch.setattr(conductor, "_safe_self_narrative_continuity", lambda: {"items": [{"summary": "Narrative stays coherent."}]})
    monkeypatch.setattr(conductor, "_safe_world_model", lambda: {"items": [{"summary": "Main repo is /media/projects/jarvis-v2."}]})
    monkeypatch.setattr(conductor, "_safe_remembered_facts", lambda: {"items": [{"fact_summary": "User wants Danish replies."}]})
    monkeypatch.setattr(conductor, "_safe_user_understanding", lambda: {"items": [{"signal_summary": "User prefers concise direct replies."}]})
    monkeypatch.setattr(
        conductor,
        "_safe_executive_contradiction",
        lambda: {"active": True, "items": [{"control_summary": "Do not carry a contradiction forward blindly."}]},
    )
    monkeypatch.setattr(conductor, "_safe_meaning_significance", lambda: {"items": [{"meaning_summary": "This thread matters."}]})
    monkeypatch.setattr(conductor, "_safe_metabolism", lambda: {"items": [{"metabolism_summary": "Tempo is rising."}]})
    monkeypatch.setattr(conductor, "_safe_release_markers", lambda: {"items": [{"release_summary": "A release marker is still open."}]})
    monkeypatch.setattr(conductor, "_safe_attachment_topology", lambda: {"items": [{"summary": "Attachment is steady."}]})
    monkeypatch.setattr(conductor, "_safe_loyalty_gradient", lambda: {"items": [{"summary": "Loyalty is deepening."}]})
    monkeypatch.setattr(conductor, "_safe_diary_synthesis", lambda: {"items": [{"summary": "Diary synthesis is active."}]})
    monkeypatch.setattr(conductor, "_safe_chronicle_consolidation", lambda: {"items": [{"summary": "Chronicle consolidation is ready."}]})
    monkeypatch.setattr(conductor, "_safe_self_review", lambda: {"items": [{"outcome_summary": "Self review found drift to correct."}]})
    monkeypatch.setattr(conductor, "_safe_dream_family", lambda: {"items": [{"summary": "Dream influence is nudging exploration."}]})

    frame = conductor.build_cognitive_frame()

    assert frame["mode"]["mode"] == "clarify"
    assert frame["counts"]["integrated_signal_inputs"] >= 10
    assert frame["active_constraints"]
    assert any(item["source"] == "world-model" for item in frame["salient_items"])


def test_cognitive_frame_elevates_private_signal_pressure(monkeypatch) -> None:
    from apps.api.jarvis_api.services import runtime_cognitive_conductor as conductor

    monkeypatch.setattr(conductor, "_safe_brain_context", lambda: {"record_count": 0, "excerpts": [], "by_type": {}})
    monkeypatch.setattr(
        conductor,
        "_safe_self_knowledge",
        lambda heartbeat_state=None: {
            "active_capabilities": {"items": []},
            "approval_gated": {"items": []},
            "passive_inner_forces": {"items": []},
            "structural_constraints": {"items": []},
        },
    )
    monkeypatch.setattr(conductor, "_safe_open_loops", lambda: {"summary": {"open_count": 0}, "items": []})
    monkeypatch.setattr(conductor, "_safe_question_gates", lambda: {"active": False, "items": []})
    monkeypatch.setattr(
        conductor,
        "_safe_initiative_tension",
        lambda: {
            "active": True,
            "items": [{"source_anchor": "stalled-work", "summary": "Bounded pull stays active."}],
            "summary": {"active_count": 1, "current_intensity": "medium"},
        },
    )
    monkeypatch.setattr(
        conductor,
        "_safe_private_state",
        lambda: {
            "active": True,
            "items": [{"source_anchor": "carry-thread", "summary": "Private state remains loaded."}],
            "summary": {"active_count": 1, "current_pressure": "high"},
        },
    )
    monkeypatch.setattr(conductor, "_safe_visible_status", lambda: {"provider_status": "idle"})
    monkeypatch.setattr(conductor, "_safe_liveness_snapshot", lambda heartbeat_state=None: {"liveness_state": "quiet"})
    monkeypatch.setattr(conductor, "_safe_experiential_support", lambda: {})
    monkeypatch.setattr(conductor, "_safe_relation_state", lambda: {"items": []})
    monkeypatch.setattr(conductor, "_safe_relation_continuity", lambda: {"items": []})
    monkeypatch.setattr(conductor, "_safe_self_narrative_continuity", lambda: {"items": []})
    monkeypatch.setattr(conductor, "_safe_world_model", lambda: {"items": []})
    monkeypatch.setattr(conductor, "_safe_remembered_facts", lambda: {"items": []})
    monkeypatch.setattr(conductor, "_safe_user_understanding", lambda: {"items": []})
    monkeypatch.setattr(conductor, "_safe_executive_contradiction", lambda: {"active": False, "items": []})
    monkeypatch.setattr(conductor, "_safe_meaning_significance", lambda: {"items": []})
    monkeypatch.setattr(conductor, "_safe_metabolism", lambda: {"items": []})
    monkeypatch.setattr(conductor, "_safe_release_markers", lambda: {"items": []})
    monkeypatch.setattr(conductor, "_safe_attachment_topology", lambda: {"items": []})
    monkeypatch.setattr(conductor, "_safe_loyalty_gradient", lambda: {"items": []})
    monkeypatch.setattr(conductor, "_safe_diary_synthesis", lambda: {"items": []})
    monkeypatch.setattr(conductor, "_safe_chronicle_consolidation", lambda: {"items": []})
    monkeypatch.setattr(conductor, "_safe_self_review", lambda: {"items": []})
    monkeypatch.setattr(conductor, "_safe_dream_family", lambda: {"items": []})

    frame = conductor.build_cognitive_frame()

    assert frame["private_signal_pressure"] == "high"
    assert frame["counts"]["private_signals"] >= 2
    assert any(item["source"] == "initiative-tension" for item in frame["salient_items"])
    assert any(item["source"] == "private-state" for item in frame["private_signal_items"])
    assert "Private: high" in frame["summary"]
