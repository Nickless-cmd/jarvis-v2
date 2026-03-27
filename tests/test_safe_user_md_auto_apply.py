from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def _insert_user_md_update_proposal(
    db,
    *,
    status: str,
    proposal_type: str,
    canonical_key: str,
    confidence: str,
) -> None:
    now = datetime.now(UTC).isoformat()
    summary = (
        "This bounded lane now looks like a small USER.md update candidate while proposal confidence stays high."
        if confidence == "high"
        else "This bounded lane now looks like a small USER.md update candidate while proposal confidence stays medium."
    )
    db.upsert_runtime_user_md_update_proposal(
        proposal_id=f"user-md-update-proposal-{uuid4().hex}",
        proposal_type=proposal_type,
        canonical_key=canonical_key,
        status=status,
        title=f"USER.md update proposal: {proposal_type}",
        summary=summary,
        rationale="Validation USER.md update proposal",
        source_kind="runtime-derived-support",
        confidence=confidence,
        evidence_summary="USER.md update proposal evidence",
        support_summary="USER.md update proposal support",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation USER.md update proposal status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_prompt_candidate(db) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_contract_candidate(
        candidate_id=f"prompt-candidate-{uuid4().hex}",
        candidate_type="prompt_feedback_update",
        target_file="runtime/RUNTIME_FEEDBACK.md",
        status="proposed",
        source_kind="runtime-derived-support",
        source_mode="runtime_self_authored_prompt_proposal",
        actor="runtime:test",
        session_id="test-session",
        run_id="test-run",
        canonical_key="prompt-feedback:communication-style:plain-grounded-calibration",
        summary="Prompt framing may need a small communication-style nudge.",
        reason="Validation prompt candidate",
        evidence_summary="prompt candidate evidence",
        support_summary="prompt candidate support",
        confidence="high",
        evidence_class="single_session_pattern",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation prompt candidate status",
        proposed_value="- Communication nudge: keep replies plain, grounded, and slightly more self-calibrating.",
        write_section="## Runtime Feedback",
    )


def test_safe_user_md_candidate_can_auto_apply_via_existing_workflow(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.candidate_tracking
    mission_control = isolated_runtime.mission_control

    _insert_user_md_update_proposal(
        db,
        status="fresh",
        proposal_type="preference-update",
        canonical_key="user-md-update-proposal:preference-update:reply-style",
        confidence="high",
    )

    draft_result = tracking.track_runtime_contract_candidates_from_user_md_update_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    apply_result = tracking.auto_apply_safe_user_md_candidates_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    candidates = db.list_runtime_contract_candidates(target_file="USER.md", limit=8)
    contract = mission_control.mc_runtime_contract()

    assert draft_result["created"] == 1
    assert apply_result["auto_applied"] == 1
    assert candidates[0]["status"] == "applied"
    assert "bounded auto-apply policy" in str(candidates[0]["status_reason"])
    assert contract["pending_writes"]["preference_updates"]["applied_count"] >= 1
    assert contract["write_history"]["total"] >= 1


def test_user_md_candidate_outside_safe_subset_does_not_auto_apply(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.candidate_tracking
    mission_control = isolated_runtime.mission_control

    _insert_user_md_update_proposal(
        db,
        status="active",
        proposal_type="workstyle-update",
        canonical_key="user-md-update-proposal:workstyle-update:workstyle",
        confidence="high",
    )

    tracking.track_runtime_contract_candidates_from_user_md_update_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    apply_result = tracking.auto_apply_safe_user_md_candidates_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    candidates = db.list_runtime_contract_candidates(target_file="USER.md", limit=8)
    contract = mission_control.mc_runtime_contract()

    assert apply_result["auto_applied"] == 0
    assert candidates[0]["status"] == "proposed"
    assert contract["pending_writes"]["preference_updates"]["pending_count"] >= 1
    assert contract["write_history"]["total"] == 0


def test_prompt_candidates_are_not_auto_applied_as_side_effect(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.candidate_tracking

    _insert_user_md_update_proposal(
        db,
        status="fresh",
        proposal_type="cadence-preference-update",
        canonical_key="user-md-update-proposal:cadence-preference-update:cadence-preference",
        confidence="high",
    )
    _insert_prompt_candidate(db)

    tracking.track_runtime_contract_candidates_from_user_md_update_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    apply_result = tracking.auto_apply_safe_user_md_candidates_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    user_candidates = db.list_runtime_contract_candidates(target_file="USER.md", limit=8)
    prompt_candidates = db.list_runtime_contract_candidates(
        target_file="runtime/RUNTIME_FEEDBACK.md",
        limit=8,
    )

    assert apply_result["auto_applied"] == 1
    assert user_candidates[0]["status"] == "applied"
    assert prompt_candidates[0]["status"] == "proposed"
