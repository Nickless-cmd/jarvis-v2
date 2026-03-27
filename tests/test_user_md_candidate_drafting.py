from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def _insert_user_md_update_proposal(db, *, status: str, proposal_type: str, canonical_key: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_user_md_update_proposal(
        proposal_id=f"user-md-update-proposal-{uuid4().hex}",
        proposal_type=proposal_type,
        canonical_key=canonical_key,
        status=status,
        title=f"USER.md update proposal: {proposal_type}",
        summary=f"Proposal summary: {proposal_type}",
        rationale="Validation USER.md update proposal",
        source_kind="runtime-derived-support",
        confidence="medium",
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


def test_user_md_update_proposal_can_draft_governed_candidate(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.candidate_tracking

    _insert_user_md_update_proposal(
        db,
        status="fresh",
        proposal_type="preference-update",
        canonical_key="user-md-update-proposal:preference-update:reply-style",
    )

    result = tracking.track_runtime_contract_candidates_from_user_md_update_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    candidates = db.list_runtime_contract_candidates(target_file="USER.md", limit=8)

    assert result["created"] == 1
    assert result["preference_updates"] == 1
    assert candidates[0]["status"] == "proposed"
    assert candidates[0]["target_file"] == "USER.md"
    assert candidates[0]["candidate_type"] == "preference_update"
    assert candidates[0]["source_mode"] == "runtime_user_md_proposal"
    assert candidates[0]["proposed_value"] == "- Reply preference: plain, grounded, and concise replies by default."


def test_user_md_candidate_drafting_does_not_auto_apply(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.candidate_tracking
    mission_control = isolated_runtime.mission_control

    _insert_user_md_update_proposal(
        db,
        status="active",
        proposal_type="workstyle-update",
        canonical_key="user-md-update-proposal:workstyle-update:workstyle",
    )

    tracking.track_runtime_contract_candidates_from_user_md_update_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )

    candidates = db.list_runtime_contract_candidates(target_file="USER.md", limit=8)
    contract = mission_control.mc_runtime_contract()

    assert candidates[0]["status"] == "proposed"
    assert db.recent_runtime_contract_file_writes(limit=8) == []
    assert contract["write_history"]["total"] == 0
    assert contract["pending_writes"]["preference_updates"]["pending_count"] >= 1


def test_user_md_candidate_drafting_is_visible_in_existing_contract_surface(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.candidate_tracking
    mission_control = isolated_runtime.mission_control

    _insert_user_md_update_proposal(
        db,
        status="fresh",
        proposal_type="cadence-preference-update",
        canonical_key="user-md-update-proposal:cadence-preference-update:cadence-preference",
    )
    _insert_user_md_update_proposal(
        db,
        status="active",
        proposal_type="reminder-worthiness-update",
        canonical_key="user-md-update-proposal:reminder-worthiness-update:reminder-worthiness",
    )

    result = tracking.track_runtime_contract_candidates_from_user_md_update_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    contract = mission_control.mc_runtime_contract()
    workflow = contract["pending_writes"]["preference_updates"]
    items = workflow["items"]

    assert result["created"] == 2
    assert workflow["target_file"] == "USER.md"
    assert workflow["pending_count"] >= 2
    assert all(str(item["status"]) == "proposed" for item in items)
    assert any(str(item["canonical_key"]) == "user-preference:review-style:challenge-before-settling" for item in items)
    assert any(str(item["canonical_key"]) == "user-preference:reminders:assumption-caution" for item in items)
