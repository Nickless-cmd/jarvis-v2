from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def _insert_memory_md_update_proposal(db, *, status: str, proposal_type: str, canonical_key: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_memory_md_update_proposal(
        proposal_id=f"memory-md-update-proposal-{uuid4().hex}",
        proposal_type=proposal_type,
        canonical_key=canonical_key,
        status=status,
        title=f"MEMORY.md update proposal: {proposal_type}",
        summary=f"Proposal summary: {proposal_type}",
        rationale="Validation MEMORY.md update proposal",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="MEMORY.md update proposal evidence",
        support_summary="MEMORY.md update proposal support | Visible memory anchor: validation anchor",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation MEMORY.md update proposal status",
        run_id="test-run",
        session_id="test-session",
    )


def test_memory_md_update_proposal_can_draft_governed_candidate(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.candidate_tracking

    _insert_memory_md_update_proposal(
        db,
        status="fresh",
        proposal_type="open-followup-update",
        canonical_key="memory-md-update-proposal:open-followup-update:danish-concise-calibration",
    )

    result = tracking.track_runtime_contract_candidates_from_memory_md_update_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    candidates = db.list_runtime_contract_candidates(target_file="MEMORY.md", limit=8)

    assert result["created"] == 1
    assert result["memory_promotions"] == 1
    assert candidates[0]["status"] == "proposed"
    assert candidates[0]["target_file"] == "MEMORY.md"
    assert candidates[0]["candidate_type"] == "memory_promotion"
    assert candidates[0]["source_mode"] == "runtime_memory_md_proposal"
    assert candidates[0]["canonical_key"] == "workspace-memory:open-followup:danish-concise-calibration"


def test_memory_md_candidate_drafting_does_not_auto_apply(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.candidate_tracking
    mission_control = isolated_runtime.mission_control

    _insert_memory_md_update_proposal(
        db,
        status="active",
        proposal_type="stable-context-update",
        canonical_key="memory-md-update-proposal:stable-context-update:review-style",
    )

    tracking.track_runtime_contract_candidates_from_memory_md_update_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )

    candidates = db.list_runtime_contract_candidates(target_file="MEMORY.md", limit=8)
    contract = mission_control.mc_runtime_contract()

    assert candidates[0]["status"] == "proposed"
    assert db.recent_runtime_contract_file_writes(limit=8) == []
    assert contract["write_history"]["total"] == 0
    assert contract["pending_writes"]["memory_promotions"]["pending_count"] >= 1


def test_memory_md_candidate_drafting_is_visible_in_existing_contract_surface(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.candidate_tracking
    mission_control = isolated_runtime.mission_control

    _insert_memory_md_update_proposal(
        db,
        status="fresh",
        proposal_type="open-followup-update",
        canonical_key="memory-md-update-proposal:open-followup-update:danish-concise-calibration",
    )
    _insert_memory_md_update_proposal(
        db,
        status="fading",
        proposal_type="carry-forward-thread-update",
        canonical_key="memory-md-update-proposal:carry-forward-thread-update:workspace-boundary",
    )

    result = tracking.track_runtime_contract_candidates_from_memory_md_update_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    contract = mission_control.mc_runtime_contract()
    workflow = contract["pending_writes"]["memory_promotions"]
    items = workflow["items"]

    assert result["created"] == 2
    assert workflow["target_file"] == "MEMORY.md"
    assert workflow["pending_count"] >= 2
    assert all(str(item["status"]) == "proposed" for item in items)
    assert "open-followup" in workflow["proposal_types"]
    assert "carry-forward-thread" in workflow["proposal_types"]
    assert all(str(item["target_file"]) == "MEMORY.md" for item in items)


def test_memory_md_remembered_fact_proposal_can_draft_governed_candidate(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.candidate_tracking

    _insert_memory_md_update_proposal(
        db,
        status="active",
        proposal_type="remembered-fact-update",
        canonical_key="memory-md-update-proposal:remembered-fact-update:user-name",
    )

    result = tracking.track_runtime_contract_candidates_from_memory_md_update_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    candidates = db.list_runtime_contract_candidates(target_file="MEMORY.md", limit=8)

    assert result["created"] == 1
    assert result["memory_promotions"] == 1
    assert candidates[0]["candidate_type"] == "memory_promotion"
    assert candidates[0]["target_file"] == "MEMORY.md"
    assert candidates[0]["canonical_key"] == "workspace-memory:remembered-fact:user-name"
    assert candidates[0]["status"] == "proposed"
