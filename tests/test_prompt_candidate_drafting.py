from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def _insert_self_authored_prompt_proposal(db, *, status: str, proposal_type: str, canonical_key: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_self_authored_prompt_proposal(
        proposal_id=f"self-authored-prompt-proposal-{uuid4().hex}",
        proposal_type=proposal_type,
        canonical_key=canonical_key,
        status=status,
        title=f"Self-authored prompt proposal: {proposal_type}",
        summary=f"Proposal summary: {proposal_type}",
        rationale="Validation self-authored prompt proposal",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="self-authored prompt proposal evidence",
        support_summary="self-authored prompt proposal support",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation self-authored prompt proposal status",
        run_id="test-run",
        session_id="test-session",
    )


def test_self_authored_prompt_proposal_can_draft_governed_prompt_candidate(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.candidate_tracking

    _insert_self_authored_prompt_proposal(
        db,
        status="fresh",
        proposal_type="communication-nudge",
        canonical_key="self-authored-prompt-proposal:communication-nudge:danish-thread",
    )

    result = tracking.track_runtime_contract_candidates_from_self_authored_prompt_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    candidates = db.list_runtime_contract_candidates(target_file="runtime/RUNTIME_FEEDBACK.md", limit=8)

    assert result["created"] == 1
    assert candidates[0]["status"] == "proposed"
    assert candidates[0]["target_file"] == "runtime/RUNTIME_FEEDBACK.md"
    assert candidates[0]["candidate_type"] == "prompt_feedback_update"
    assert candidates[0]["source_mode"] == "runtime_self_authored_prompt_proposal"
    assert candidates[0]["proposed_value"] == "- Communication nudge: keep replies plain, grounded, and slightly more self-calibrating."


def test_prompt_candidate_drafting_does_not_auto_apply(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.candidate_tracking
    mission_control = isolated_runtime.mission_control

    _insert_self_authored_prompt_proposal(
        db,
        status="active",
        proposal_type="focus-nudge",
        canonical_key="self-authored-prompt-proposal:focus-nudge:workflow-thread",
    )

    tracking.track_runtime_contract_candidates_from_self_authored_prompt_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )

    candidates = db.list_runtime_contract_candidates(target_file="runtime/RUNTIME_FEEDBACK.md", limit=8)
    contract = mission_control.mc_runtime_contract()

    assert candidates[0]["status"] == "proposed"
    assert db.recent_runtime_contract_file_writes(limit=8) == []
    assert contract["write_history"]["total"] == 0
    assert contract["pending_writes"]["prompt_feedback_updates"]["pending_count"] >= 1


def test_prompt_candidate_drafting_is_visible_in_existing_contract_surface(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.candidate_tracking
    mission_control = isolated_runtime.mission_control

    _insert_self_authored_prompt_proposal(
        db,
        status="fresh",
        proposal_type="challenge-nudge",
        canonical_key="self-authored-prompt-proposal:challenge-nudge:review-thread",
    )
    _insert_self_authored_prompt_proposal(
        db,
        status="active",
        proposal_type="world-caution-nudge",
        canonical_key="self-authored-prompt-proposal:world-caution-nudge:assumption-thread",
    )

    result = tracking.track_runtime_contract_candidates_from_self_authored_prompt_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    contract = mission_control.mc_runtime_contract()
    workflow = contract["pending_writes"]["prompt_feedback_updates"]
    items = workflow["items"]

    assert result["created"] == 2
    assert workflow["target_file"] == "runtime/RUNTIME_FEEDBACK.md"
    assert workflow["pending_count"] >= 2
    assert all(str(item["status"]) == "proposed" for item in items)
    assert any(str(item["canonical_key"]) == "prompt-feedback:challenge-posture:review-before-settling" for item in items)
    assert any(str(item["canonical_key"]) == "prompt-feedback:world-caution:fragile-context-marker" for item in items)
