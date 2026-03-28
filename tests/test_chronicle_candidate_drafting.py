from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest


def _insert_chronicle_consolidation_proposal(
    db,
    *,
    status: str,
    proposal_type: str,
    canonical_key: str,
    confidence: str = "medium",
) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_chronicle_consolidation_proposal(
        proposal_id=f"chronicle-consolidation-proposal-{uuid4().hex}",
        proposal_type=proposal_type,
        canonical_key=canonical_key,
        status=status,
        title="Chronicle proposal: workspace search",
        summary="Bounded chronicle proposal is preparing a small future carry-forward candidate.",
        rationale="Validation chronicle proposal runtime layer",
        source_kind="runtime-derived-support",
        confidence=confidence,
        evidence_summary="chronicle proposal evidence",
        support_summary="Derived primarily from an existing bounded chronicle/consolidation brief.",
        status_reason="Validation bounded chronicle proposal with no writeback authority.",
        run_id="test-run",
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def test_chronicle_proposal_can_draft_runtime_contract_candidate(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.candidate_tracking

    _insert_chronicle_consolidation_proposal(
        db,
        status="active",
        proposal_type="consolidation-proposal",
        canonical_key="chronicle-consolidation-proposal:consolidation-proposal:workspace-search",
    )

    result = tracking.track_runtime_contract_candidates_from_chronicle_consolidation_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    candidates = db.list_runtime_contract_candidates(
        candidate_type="chronicle_draft",
        target_file="runtime/CHRONICLE.md",
        limit=8,
    )

    assert result["created"] == 1
    assert result["chronicle_drafts"] == 1
    assert candidates[0]["status"] == "proposed"
    assert candidates[0]["target_file"] == "runtime/CHRONICLE.md"
    assert candidates[0]["candidate_type"] == "chronicle_draft"
    assert candidates[0]["source_mode"] == "runtime_chronicle_consolidation_proposal"
    assert "CHRONICLE.md write or apply has been executed" in str(candidates[0]["support_summary"])


def test_chronicle_candidate_stays_separate_from_user_and_memory_targets(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.candidate_tracking

    _insert_chronicle_consolidation_proposal(
        db,
        status="active",
        proposal_type="carry-forward-proposal",
        canonical_key="chronicle-consolidation-proposal:carry-forward-proposal:visible-work",
        confidence="high",
    )

    tracking.track_runtime_contract_candidates_from_chronicle_consolidation_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )

    chronicle_candidates = db.list_runtime_contract_candidates(
        candidate_type="chronicle_draft",
        target_file="runtime/CHRONICLE.md",
        limit=8,
    )

    assert chronicle_candidates
    assert db.list_runtime_contract_candidates(target_file="USER.md", limit=8) == []
    assert db.list_runtime_contract_candidates(target_file="MEMORY.md", limit=8) == []
    assert all(str(item["target_file"]) == "runtime/CHRONICLE.md" for item in chronicle_candidates)


def test_chronicle_candidate_is_visible_in_runtime_contract_pending_writes(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.candidate_tracking
    mission_control = isolated_runtime.mission_control

    _insert_chronicle_consolidation_proposal(
        db,
        status="active",
        proposal_type="anchored-proposal",
        canonical_key="chronicle-consolidation-proposal:anchored-proposal:archive-focus",
    )

    tracking.track_runtime_contract_candidates_from_chronicle_consolidation_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )

    contract = mission_control.mc_runtime_contract()
    workflow = contract["pending_writes"]["chronicle_drafts"]
    item = workflow["items"][0]

    assert workflow["target_file"] == "runtime/CHRONICLE.md"
    assert workflow["pending_count"] >= 1
    assert workflow["current_apply_readiness"] == "low"
    assert workflow["current_apply_reason"] == "draft-only"
    assert item["candidate_type"] == "chronicle_draft"
    assert item["status"] == "proposed"
    assert item["target_file"] == "runtime/CHRONICLE.md"
    assert db.recent_runtime_contract_file_writes(limit=8) == []
    assert contract["write_history"]["total"] == 0


def test_chronicle_candidate_cannot_apply_without_approval(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.candidate_tracking
    candidate_workflow = __import__(
        "core.identity.candidate_workflow",
        fromlist=["apply_runtime_contract_candidate"],
    )

    _insert_chronicle_consolidation_proposal(
        db,
        status="active",
        proposal_type="consolidation-proposal",
        canonical_key="chronicle-consolidation-proposal:consolidation-proposal:workspace-search",
        confidence="high",
    )

    tracking.track_runtime_contract_candidates_from_chronicle_consolidation_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    candidate = db.list_runtime_contract_candidates(
        candidate_type="chronicle_draft",
        target_file="runtime/CHRONICLE.md",
        limit=8,
    )[0]

    with pytest.raises(ValueError, match="Candidate must be in one of: approved"):
        candidate_workflow.apply_runtime_contract_candidate(str(candidate["candidate_id"]))

    refreshed = db.get_runtime_contract_candidate(str(candidate["candidate_id"]))
    assert refreshed["status"] == "proposed"
    assert db.recent_runtime_contract_file_writes(limit=8) == []


def test_approved_chronicle_candidate_can_apply_via_chronicle_specific_gate(
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

    _insert_chronicle_consolidation_proposal(
        db,
        status="active",
        proposal_type="consolidation-proposal",
        canonical_key="chronicle-consolidation-proposal:consolidation-proposal:workspace-search",
        confidence="high",
    )

    tracking.track_runtime_contract_candidates_from_chronicle_consolidation_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    candidate = db.list_runtime_contract_candidates(
        candidate_type="chronicle_draft",
        target_file="runtime/CHRONICLE.md",
        limit=8,
    )[0]

    approved = candidate_workflow.approve_runtime_contract_candidate(str(candidate["candidate_id"]))
    applied = candidate_workflow.apply_runtime_contract_candidate(str(candidate["candidate_id"]))
    chronicle_text = (workspace_dir / "runtime" / "CHRONICLE.md").read_text(encoding="utf-8")
    contract = mission_control.mc_runtime_contract()
    workflow = contract["pending_writes"]["chronicle_drafts"]

    assert approved["status"] == "approved"
    assert "chronicle-specific gate" in str(approved["status_reason"]).lower()
    assert applied["candidate"]["status"] == "applied"
    assert "runtime chronicle file" in str(applied["candidate"]["status_reason"]).lower()
    assert applied["write"]["target_file"] == "runtime/CHRONICLE.md"
    assert applied["write"]["actor"] == "runtime:chronicle-apply-gate"
    assert str(candidate["proposed_value"]) in chronicle_text
    assert workflow["applied_count"] >= 1
    assert workflow["target_file"] == "runtime/CHRONICLE.md"
    assert any(
        str(item.get("target_file") or "") == "runtime/CHRONICLE.md"
        for item in contract["write_history"]["items"]
    )
