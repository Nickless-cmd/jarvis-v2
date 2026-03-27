from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest


def _insert_selfhood_proposal(
    db,
    *,
    status: str,
    proposal_type: str,
    canonical_key: str,
    confidence: str = "high",
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


def test_canonical_self_candidate_cannot_apply_without_explicit_approval(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.candidate_tracking
    candidate_workflow = __import__(
        "core.identity.candidate_workflow",
        fromlist=["apply_runtime_contract_candidate"],
    )

    _insert_selfhood_proposal(
        db,
        status="fresh",
        proposal_type="voice-shift-proposal",
        canonical_key="selfhood-proposal:voice-shift-proposal:voice-thread",
    )

    tracking.track_runtime_contract_candidates_from_selfhood_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    candidate = db.list_runtime_contract_candidates(target_file="SOUL.md", limit=8)[0]

    with pytest.raises(ValueError, match="Candidate must be in one of: approved"):
        candidate_workflow.apply_runtime_contract_candidate(str(candidate["candidate_id"]))

    refreshed = db.get_runtime_contract_candidate(str(candidate["candidate_id"]))
    assert refreshed is not None
    assert refreshed["status"] == "proposed"
    assert db.recent_runtime_contract_file_writes(limit=8) == []


def test_explicitly_approved_soul_candidate_can_apply_to_soul_md(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.candidate_tracking
    mission_control = isolated_runtime.mission_control
    workspace_dir = isolated_runtime.workspace_bootstrap.ensure_default_workspace()
    candidate_workflow = __import__(
        "core.identity.candidate_workflow",
        fromlist=["approve_runtime_contract_candidate", "apply_runtime_contract_candidate"],
    )

    _insert_selfhood_proposal(
        db,
        status="active",
        proposal_type="voice-shift-proposal",
        canonical_key="selfhood-proposal:voice-shift-proposal:voice-thread",
    )

    tracking.track_runtime_contract_candidates_from_selfhood_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    candidate = db.list_runtime_contract_candidates(target_file="SOUL.md", limit=8)[0]

    approved = candidate_workflow.approve_runtime_contract_candidate(str(candidate["candidate_id"]))
    applied = candidate_workflow.apply_runtime_contract_candidate(str(candidate["candidate_id"]))
    soul_text = (workspace_dir / "SOUL.md").read_text(encoding="utf-8")
    contract = mission_control.mc_runtime_contract()

    assert approved["status"] == "approved"
    assert "explicit user approval" in str(approved["status_reason"]).lower()
    assert applied["candidate"]["status"] == "applied"
    assert "canonical self file" in str(applied["candidate"]["status_reason"]).lower()
    assert applied["write"]["target_file"] == "SOUL.md"
    assert str(candidate["proposed_value"]) in soul_text
    assert contract["pending_writes"]["soul_updates"]["applied_count"] >= 1
    assert contract["write_history"]["items"][0]["target_file"] == "SOUL.md"


def test_explicitly_approved_identity_candidate_applies_to_identity_md_and_surfaces_history(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.candidate_tracking
    mission_control = isolated_runtime.mission_control
    workspace_dir = isolated_runtime.workspace_bootstrap.ensure_default_workspace()
    candidate_workflow = __import__(
        "core.identity.candidate_workflow",
        fromlist=["approve_runtime_contract_candidate", "apply_runtime_contract_candidate"],
    )

    _insert_selfhood_proposal(
        db,
        status="fresh",
        proposal_type="challenge-style-proposal",
        canonical_key="selfhood-proposal:challenge-style-proposal:challenge-thread",
    )

    tracking.track_runtime_contract_candidates_from_selfhood_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    candidate = db.list_runtime_contract_candidates(target_file="IDENTITY.md", limit=8)[0]

    candidate_workflow.approve_runtime_contract_candidate(str(candidate["candidate_id"]))
    applied = candidate_workflow.apply_runtime_contract_candidate(str(candidate["candidate_id"]))
    contract = mission_control.mc_runtime_contract()
    identity_text = (workspace_dir / "IDENTITY.md").read_text(encoding="utf-8")

    assert applied["candidate"]["status"] == "applied"
    assert applied["write"]["target_file"] == "IDENTITY.md"
    assert str(candidate["proposed_value"]) in identity_text
    assert contract["pending_writes"]["identity_updates"]["applied_count"] >= 1
    assert contract["write_history"]["total"] >= 1
    assert any(
        str(item.get("target_file") or "") == "IDENTITY.md"
        for item in contract["write_history"]["items"]
    )
