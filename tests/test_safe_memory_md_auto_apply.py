from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def _insert_memory_md_update_proposal(
    db,
    *,
    status: str,
    proposal_type: str,
    canonical_key: str,
    confidence: str,
) -> None:
    now = datetime.now(UTC).isoformat()
    summary = (
        "This bounded lane now looks like a small MEMORY.md update candidate while proposal confidence stays high."
        if confidence == "high"
        else "This bounded lane now looks like a small MEMORY.md update candidate while proposal confidence stays medium."
    )
    db.upsert_runtime_memory_md_update_proposal(
        proposal_id=f"memory-md-update-proposal-{uuid4().hex}",
        proposal_type=proposal_type,
        canonical_key=canonical_key,
        status=status,
        title=f"MEMORY.md update proposal: {proposal_type}",
        summary=summary,
        rationale="Validation MEMORY.md update proposal",
        source_kind="runtime-derived-support",
        confidence=confidence,
        evidence_summary="MEMORY.md update proposal evidence",
        support_summary="MEMORY.md update proposal support",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation MEMORY.md update proposal status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_candidate(
    db,
    *,
    candidate_type: str,
    target_file: str,
    status: str,
    canonical_key: str,
    confidence: str,
    evidence_class: str,
) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_contract_candidate(
        candidate_id=f"candidate-{uuid4().hex}",
        candidate_type=candidate_type,
        target_file=target_file,
        status=status,
        source_kind="runtime-derived-support",
        source_mode="test-runtime",
        actor="runtime:test",
        session_id="test-session",
        run_id="test-run",
        canonical_key=canonical_key,
        summary=f"Candidate summary: {canonical_key}",
        reason="Validation candidate",
        evidence_summary="candidate evidence",
        support_summary="candidate support",
        confidence=confidence,
        evidence_class=evidence_class,
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation candidate status",
        proposed_value="- bounded candidate value",
        write_section="## Curated Memory",
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


def test_safe_memory_md_candidate_can_auto_apply_via_existing_workflow(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.candidate_tracking
    mission_control = isolated_runtime.mission_control

    _insert_memory_md_update_proposal(
        db,
        status="active",
        proposal_type="stable-context-update",
        canonical_key="memory-md-update-proposal:stable-context-update:review-style",
        confidence="high",
    )

    draft_result = tracking.track_runtime_contract_candidates_from_memory_md_update_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    apply_result = tracking.auto_apply_safe_memory_md_candidates_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    candidates = db.list_runtime_contract_candidates(target_file="MEMORY.md", limit=8)
    contract = mission_control.mc_runtime_contract()

    assert draft_result["created"] == 1
    assert apply_result["auto_applied"] == 1
    assert candidates[0]["status"] == "applied"
    assert "bounded auto-apply policy" in str(candidates[0]["status_reason"])
    assert contract["pending_writes"]["memory_promotions"]["applied_count"] >= 1
    assert contract["write_history"]["total"] >= 1


def test_memory_md_candidate_outside_safe_subset_does_not_auto_apply(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.candidate_tracking
    mission_control = isolated_runtime.mission_control

    _insert_memory_md_update_proposal(
        db,
        status="fresh",
        proposal_type="open-followup-update",
        canonical_key="memory-md-update-proposal:open-followup-update:danish-concise-calibration",
        confidence="high",
    )

    tracking.track_runtime_contract_candidates_from_memory_md_update_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    apply_result = tracking.auto_apply_safe_memory_md_candidates_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    candidates = db.list_runtime_contract_candidates(target_file="MEMORY.md", limit=8)
    contract = mission_control.mc_runtime_contract()

    assert apply_result["auto_applied"] == 0
    assert candidates[0]["status"] == "proposed"
    assert contract["pending_writes"]["memory_promotions"]["pending_count"] >= 1
    assert contract["write_history"]["total"] == 0


def test_other_targets_are_not_auto_applied_as_memory_side_effect(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.candidate_tracking

    _insert_memory_md_update_proposal(
        db,
        status="active",
        proposal_type="stable-context-update",
        canonical_key="memory-md-update-proposal:stable-context-update:review-style",
        confidence="high",
    )
    _insert_prompt_candidate(db)

    tracking.track_runtime_contract_candidates_from_memory_md_update_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    apply_result = tracking.auto_apply_safe_memory_md_candidates_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    memory_candidates = db.list_runtime_contract_candidates(target_file="MEMORY.md", limit=8)
    prompt_candidates = db.list_runtime_contract_candidates(
        target_file="runtime/RUNTIME_FEEDBACK.md",
        limit=8,
    )

    assert apply_result["auto_applied"] == 1
    assert memory_candidates[0]["status"] == "applied"
    assert prompt_candidates[0]["status"] == "proposed"


def test_safe_remembered_fact_project_anchor_can_auto_apply_via_existing_workflow(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.candidate_tracking
    mission_control = isolated_runtime.mission_control

    _insert_memory_md_update_proposal(
        db,
        status="active",
        proposal_type="remembered-fact-update",
        canonical_key="memory-md-update-proposal:remembered-fact-update:project-anchor",
        confidence="high",
    )

    draft_result = tracking.track_runtime_contract_candidates_from_memory_md_update_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    apply_result = tracking.auto_apply_safe_memory_md_candidates_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    candidates = db.list_runtime_contract_candidates(target_file="MEMORY.md", limit=8)
    contract = mission_control.mc_runtime_contract()

    assert draft_result["created"] == 1
    assert apply_result["auto_applied"] == 1
    assert candidates[0]["canonical_key"] == "workspace-memory:remembered-fact:project-anchor"
    assert candidates[0]["status"] == "applied"
    assert "bounded auto-apply policy" in str(candidates[0]["status_reason"])
    assert contract["pending_writes"]["memory_promotions"]["applied_count"] >= 1
    assert contract["write_history"]["total"] >= 1


def test_safe_remembered_fact_repo_context_can_auto_apply_via_existing_workflow(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.candidate_tracking

    _insert_memory_md_update_proposal(
        db,
        status="active",
        proposal_type="remembered-fact-update",
        canonical_key="memory-md-update-proposal:remembered-fact-update:repo-context",
        confidence="high",
    )

    tracking.track_runtime_contract_candidates_from_memory_md_update_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    apply_result = tracking.auto_apply_safe_memory_md_candidates_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    candidates = db.list_runtime_contract_candidates(target_file="MEMORY.md", limit=8)

    assert apply_result["auto_applied"] == 1
    assert candidates[0]["canonical_key"] == "workspace-memory:remembered-fact:repo-context"
    assert candidates[0]["status"] == "applied"


def test_remembered_fact_user_name_does_not_auto_apply(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.candidate_tracking
    mission_control = isolated_runtime.mission_control

    _insert_memory_md_update_proposal(
        db,
        status="active",
        proposal_type="remembered-fact-update",
        canonical_key="memory-md-update-proposal:remembered-fact-update:user-name",
        confidence="high",
    )

    tracking.track_runtime_contract_candidates_from_memory_md_update_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    apply_result = tracking.auto_apply_safe_memory_md_candidates_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    candidates = db.list_runtime_contract_candidates(target_file="MEMORY.md", limit=8)
    contract = mission_control.mc_runtime_contract()

    assert apply_result["auto_applied"] == 0
    assert candidates[0]["canonical_key"] == "workspace-memory:remembered-fact:user-name"
    assert candidates[0]["status"] == "proposed"
    assert contract["pending_writes"]["memory_promotions"]["pending_count"] >= 1
    assert contract["write_history"]["total"] == 0


def test_manual_factual_memory_candidate_outside_safe_subset_does_not_auto_apply(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.candidate_tracking

    _insert_candidate(
        db,
        candidate_type="memory_promotion",
        target_file="MEMORY.md",
        status="proposed",
        canonical_key="workspace-memory:remembered-fact:working-partner-name",
        confidence="high",
        evidence_class="runtime_support_only",
    )

    apply_result = tracking.auto_apply_safe_memory_md_candidates_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    candidates = db.list_runtime_contract_candidates(target_file="MEMORY.md", limit=8)

    assert apply_result["auto_applied"] == 0
    assert candidates[0]["status"] == "proposed"
