from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def _insert_selfhood_proposal(
    db,
    *,
    status: str,
    proposal_type: str,
    canonical_key: str,
    confidence: str = "medium",
) -> None:
    now = datetime.now(UTC).isoformat()
    target = "SOUL.md" if proposal_type in {"voice-shift-proposal", "caution-shift-proposal"} else "IDENTITY.md"
    summary = (
        f"A bounded {proposal_type} now points toward {target} while proposal confidence stays {confidence}. "
        "Explicit user approval is required before any canonical self change."
    )
    db.upsert_runtime_selfhood_proposal(
        proposal_id=f"selfhood-proposal-{uuid4().hex}",
        proposal_type=proposal_type,
        canonical_key=canonical_key,
        status=status,
        title=f"Selfhood proposal: {proposal_type}",
        summary=summary,
        rationale="Validation selfhood proposal",
        source_kind="runtime-derived-support",
        confidence=confidence,
        evidence_summary="selfhood proposal evidence",
        support_summary="selfhood proposal support | selfhood anchor | bounded proposed shift",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation selfhood proposal status",
        run_id="test-run",
        session_id="test-session",
    )


def test_selfhood_proposal_can_draft_governed_canonical_self_candidate(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.candidate_tracking

    _insert_selfhood_proposal(
        db,
        status="fresh",
        proposal_type="voice-shift-proposal",
        canonical_key="selfhood-proposal:voice-shift-proposal:voice-thread",
    )

    result = tracking.track_runtime_contract_candidates_from_selfhood_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    candidates = db.list_runtime_contract_candidates(target_file="SOUL.md", limit=8)

    assert result["created"] == 1
    assert result["canonical_self_updates"] == 1
    assert candidates[0]["status"] == "proposed"
    assert candidates[0]["target_file"] == "SOUL.md"
    assert candidates[0]["candidate_type"] == "soul_update"
    assert candidates[0]["source_mode"] == "runtime_selfhood_proposal"
    assert "Explicit user approval is required" in str(candidates[0]["status_reason"])


def test_canonical_self_candidate_drafting_does_not_auto_apply(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.candidate_tracking
    mission_control = isolated_runtime.mission_control

    _insert_selfhood_proposal(
        db,
        status="active",
        proposal_type="challenge-style-proposal",
        canonical_key="selfhood-proposal:challenge-style-proposal:challenge-thread",
    )

    tracking.track_runtime_contract_candidates_from_selfhood_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )

    candidates = db.list_runtime_contract_candidates(target_file="IDENTITY.md", limit=8)
    contract = mission_control.mc_runtime_contract()

    assert candidates[0]["status"] == "proposed"
    assert db.recent_runtime_contract_file_writes(limit=8) == []
    assert contract["write_history"]["total"] == 0
    assert contract["pending_writes"]["identity_updates"]["pending_count"] >= 1
    assert contract["pending_writes"]["identity_updates"]["current_apply_reason"] == "needs-user-confirmation"


def test_canonical_self_candidate_drafting_is_visible_and_requires_explicit_approval(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.candidate_tracking
    mission_control = isolated_runtime.mission_control

    _insert_selfhood_proposal(
        db,
        status="fresh",
        proposal_type="voice-shift-proposal",
        canonical_key="selfhood-proposal:voice-shift-proposal:voice-thread",
        confidence="high",
    )
    _insert_selfhood_proposal(
        db,
        status="active",
        proposal_type="challenge-style-proposal",
        canonical_key="selfhood-proposal:challenge-style-proposal:challenge-thread",
        confidence="medium",
    )

    result = tracking.track_runtime_contract_candidates_from_selfhood_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    contract = mission_control.mc_runtime_contract()
    soul_workflow = contract["pending_writes"]["soul_updates"]
    identity_workflow = contract["pending_writes"]["identity_updates"]

    assert result["created"] == 2
    assert soul_workflow["target_file"] == "SOUL.md"
    assert identity_workflow["target_file"] == "IDENTITY.md"
    assert soul_workflow["pending_count"] >= 1
    assert identity_workflow["pending_count"] >= 1
    assert soul_workflow["items"][0]["apply_readiness"] == "low"
    assert soul_workflow["items"][0]["apply_reason"] == "needs-user-confirmation"
    assert identity_workflow["items"][0]["apply_readiness"] == "low"
    assert "Explicit user approval is required" in str(soul_workflow["items"][0]["support_summary"])
    assert "Explicit user approval is required" in str(identity_workflow["items"][0]["support_summary"])
