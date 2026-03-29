from __future__ import annotations

import importlib
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _noop(*args, **kwargs):
    return {}


def _insert_focus(db) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_development_focus(
        focus_id=f"focus-{uuid4().hex}",
        focus_type="runtime-focus",
        canonical_key="development-focus:runtime:visible-work:reinforce-retain",
        status="active",
        title="Stabilize visible-work",
        summary="Development state is pushing toward reinforce:retain around visible work.",
        rationale="Validation focus",
        source_kind="runtime-derived-support",
        confidence="high",
        evidence_summary="focus evidence",
        support_summary="Preferred direction reinforce:retain; identity thread visible-work.",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation focus status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_goal(db) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_goal_signal(
        goal_id=f"goal-{uuid4().hex}",
        goal_type="development-direction",
        canonical_key="goal-signal:runtime-visible-work-reinforce-retain",
        status="active",
        title="Current goal: make stabilize visible-work land visibly",
        summary="Current goal: make stabilize visible-work land visibly",
        rationale="Validation goal",
        source_kind="runtime-derived-support",
        confidence="high",
        evidence_summary="goal evidence",
        support_summary="Preferred direction reinforce:retain; identity thread visible-work.",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation goal status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_initiative_tension(db) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_private_initiative_tension_signal(
        signal_id=f"initiative-{uuid4().hex}",
        signal_type="private-initiative-tension",
        canonical_key="private-initiative-tension:retention-pull:reinforce-retain",
        status="active",
        title="Private initiative tension support: Stabilize visible-work",
        summary="Bounded initiative tension is still carrying directional pressure.",
        rationale="Validation initiative tension",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="initiative tension evidence",
        support_summary=(
            "Derived from visible work plus bounded runtime support layers. | "
            "Stabilize visible-work (development-focus:runtime:visible-work:reinforce-retain) | "
            "identity thread visible-work."
        ),
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation initiative tension status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_regulation(db) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_regulation_homeostasis_signal(
        signal_id=f"regulation-{uuid4().hex}",
        signal_type="regulation-homeostasis",
        canonical_key="regulation-homeostasis:steady-support:visible-work",
        status="active",
        title="Regulation support: visible work",
        summary="Bounded regulation support is holding a small state around visible work.",
        rationale="Validation regulation",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="regulation evidence",
        support_summary=(
            "Derived only from bounded private-state runtime support. | "
            "grounding-mode=private-state+inner-visible-sharpening | "
            "Private state snapshot: visible work [private-state-snapshot:steady-support:visible-work]"
        ),
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation regulation status",
        run_id="test-run",
        session_id="test-session",
    )


def test_current_flow_materializes_open_loop_before_downstream_tracking(
    isolated_runtime,
    monkeypatch,
) -> None:
    db = isolated_runtime.db
    visible_runs = importlib.import_module("apps.api.jarvis_api.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)

    monkeypatch.setattr(visible_runs, "track_runtime_contract_candidates_for_visible_turn", _noop)
    monkeypatch.setattr(
        visible_runs,
        "track_runtime_development_focuses_for_visible_turn",
        lambda **kwargs: _insert_focus(db),
    )
    monkeypatch.setattr(visible_runs, "track_runtime_reflective_critics_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_world_model_signals_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_self_model_signals_for_visible_turn", _noop)
    monkeypatch.setattr(
        visible_runs,
        "track_runtime_goal_signals_for_visible_turn",
        lambda **kwargs: _insert_goal(db),
    )
    monkeypatch.setattr(visible_runs, "track_runtime_awareness_signals_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_reflection_signals_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_temporal_recurrence_signals_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_witness_signals_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_internal_opposition_signals_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_self_review_signals_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_self_review_records_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_self_review_runs_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_self_review_outcomes_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_self_review_cadence_signals_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_dream_hypothesis_signals_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_dream_adoption_candidates_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_dream_influence_proposals_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_self_authored_prompt_proposals_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_user_understanding_signals_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_remembered_fact_signals_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_private_inner_note_signals_for_visible_turn", _noop)
    monkeypatch.setattr(
        visible_runs,
        "track_runtime_private_initiative_tension_signals_for_visible_turn",
        lambda **kwargs: _insert_initiative_tension(db),
    )
    monkeypatch.setattr(visible_runs, "track_runtime_private_inner_interplay_signals_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_private_state_snapshots_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_private_temporal_curiosity_states_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_executive_contradiction_signals_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_inner_visible_support_signals_for_visible_turn", _noop)
    monkeypatch.setattr(
        visible_runs,
        "track_runtime_regulation_homeostasis_signals_for_visible_turn",
        lambda **kwargs: _insert_regulation(db),
    )
    monkeypatch.setattr(visible_runs, "track_runtime_relation_state_signals_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_private_temporal_promotion_signals_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_chronicle_consolidation_signals_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_chronicle_consolidation_briefs_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_relation_continuity_signals_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_chronicle_consolidation_proposals_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_meaning_significance_signals_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_temperament_tendency_signals_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_self_narrative_continuity_signals_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_metabolism_state_signals_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_release_marker_signals_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_consolidation_target_signals_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_selective_forgetting_candidates_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_attachment_topology_signals_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_loyalty_gradient_signals_for_visible_turn", _noop)
    monkeypatch.setattr(
        visible_runs,
        "track_runtime_contract_candidates_from_chronicle_consolidation_proposals_for_visible_turn",
        _noop,
    )
    monkeypatch.setattr(
        visible_runs,
        "track_runtime_contract_candidates_from_self_authored_prompt_proposals_for_visible_turn",
        _noop,
    )
    monkeypatch.setattr(visible_runs, "track_runtime_user_md_update_proposals_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_memory_md_update_proposals_for_visible_turn", _noop)
    monkeypatch.setattr(
        visible_runs,
        "track_runtime_contract_candidates_from_memory_md_update_proposals_for_visible_turn",
        _noop,
    )
    monkeypatch.setattr(visible_runs, "auto_apply_safe_memory_md_candidates_for_visible_turn", _noop)
    monkeypatch.setattr(
        visible_runs,
        "track_runtime_contract_candidates_from_user_md_update_proposals_for_visible_turn",
        _noop,
    )
    monkeypatch.setattr(visible_runs, "auto_apply_safe_user_md_candidates_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_selfhood_proposals_for_visible_turn", _noop)
    monkeypatch.setattr(
        visible_runs,
        "track_runtime_contract_candidates_from_selfhood_proposals_for_visible_turn",
        _noop,
    )
    monkeypatch.setattr(visible_runs, "track_runtime_open_loop_closure_proposals_for_visible_turn", _noop)
    monkeypatch.setattr(visible_runs, "track_runtime_proactive_question_gates_for_visible_turn", _noop)

    run = visible_runs.VisibleRun(
        run_id="test-run",
        lane="local",
        provider="ollama",
        model="llama3.1:8b",
        user_message="test",
        session_id="test-session",
    )

    visible_runs._track_runtime_candidates(run, assistant_text="test")

    open_loops = db.list_runtime_open_loop_signals(limit=8)
    autonomy = db.list_runtime_autonomy_pressure_signals(limit=8)
    lifecycle = db.list_runtime_proactive_loop_lifecycle_signals(limit=8)

    assert len(open_loops) == 1
    assert open_loops[0]["canonical_key"] == "open-loop:open-loop:visible-work"
    assert open_loops[0]["status"] == "open"
    assert "initiative tension" in open_loops[0]["summary"].lower()

    assert len(autonomy) == 1
    assert autonomy[0]["canonical_key"] == "autonomy-pressure:initiative-pressure"
    assert autonomy[0]["status"] == "active"

    assert len(lifecycle) == 1
    assert lifecycle[0]["canonical_key"] == "proactive-loop-lifecycle:initiative-loop:none"
    assert lifecycle[0]["status"] == "active"
