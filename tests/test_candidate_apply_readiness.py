from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


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
        reason="Validation candidate apply readiness",
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
        write_section="## Validation",
    )


def test_user_md_candidate_gets_bounded_apply_readiness(isolated_runtime) -> None:
    db = isolated_runtime.db
    mission_control = isolated_runtime.mission_control

    _insert_candidate(
        db,
        candidate_type="preference_update",
        target_file="USER.md",
        status="proposed",
        canonical_key="user-preference:language:danish",
        confidence="high",
        evidence_class="repeated_cross_session",
    )

    contract = mission_control.mc_runtime_contract()
    workflow = contract["pending_writes"]["preference_updates"]
    candidate = workflow["items"][0]

    assert candidate["status"] == "proposed"
    assert candidate["apply_readiness"] == "medium"
    assert candidate["apply_reason"] == "bounded-safe"
    assert workflow["current_apply_readiness"] == "medium"
    assert workflow["apply_readiness_medium_count"] >= 1


def test_prompt_candidate_stays_low_readiness_and_never_auto_applies(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    mission_control = isolated_runtime.mission_control

    _insert_candidate(
        db,
        candidate_type="prompt_feedback_update",
        target_file="runtime/RUNTIME_FEEDBACK.md",
        status="proposed",
        canonical_key="prompt-feedback:challenge-posture:review-before-settling",
        confidence="medium",
        evidence_class="single_session_pattern",
    )

    contract = mission_control.mc_runtime_contract()
    workflow = contract["pending_writes"]["prompt_feedback_updates"]
    candidate = workflow["items"][0]

    assert candidate["status"] == "proposed"
    assert candidate["apply_readiness"] == "low"
    assert candidate["apply_reason"] == "needs-review"
    assert workflow["current_apply_readiness"] == "low"
    assert db.recent_runtime_contract_file_writes(limit=8) == []
    assert contract["write_history"]["total"] == 0


def test_approved_chronicle_candidate_gets_medium_readiness_through_specific_gate(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    mission_control = isolated_runtime.mission_control

    _insert_candidate(
        db,
        candidate_type="chronicle_draft",
        target_file="runtime/CHRONICLE.md",
        status="approved",
        canonical_key="chronicle-draft:consolidation-proposal:workspace-search",
        confidence="high",
        evidence_class="runtime_support_only",
    )

    contract = mission_control.mc_runtime_contract()
    workflow = contract["pending_writes"]["chronicle_drafts"]
    candidate = workflow["items"][0]

    assert candidate["status"] == "approved"
    assert candidate["apply_readiness"] == "medium"
    assert candidate["apply_reason"] == "chronicle-approved-gate"
    assert workflow["current_apply_readiness"] == "medium"
    assert workflow["apply_readiness_medium_count"] >= 1


def test_approved_user_md_candidate_surfaces_high_apply_readiness(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    mission_control = isolated_runtime.mission_control

    _insert_candidate(
        db,
        candidate_type="preference_update",
        target_file="USER.md",
        status="approved",
        canonical_key="user-preference:reply-style:concise",
        confidence="high",
        evidence_class="explicit_user_statement",
    )

    contract = mission_control.mc_runtime_contract()
    workflow = contract["pending_writes"]["preference_updates"]
    candidate = workflow["items"][0]

    assert candidate["status"] == "approved"
    assert candidate["apply_readiness"] == "high"
    assert candidate["apply_reason"] == "bounded-safe"
    assert workflow["current_apply_readiness"] == "high"
    assert workflow["apply_readiness_high_count"] >= 1


def test_memory_md_stable_context_candidate_gets_medium_apply_readiness(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    mission_control = isolated_runtime.mission_control

    _insert_candidate(
        db,
        candidate_type="memory_promotion",
        target_file="MEMORY.md",
        status="proposed",
        canonical_key="workspace-memory:stable-context:review-style",
        confidence="medium",
        evidence_class="runtime_support_only",
    )

    contract = mission_control.mc_runtime_contract()
    workflow = contract["pending_writes"]["memory_promotions"]
    candidate = workflow["items"][0]

    assert candidate["status"] == "proposed"
    assert candidate["apply_readiness"] == "medium"
    assert candidate["apply_reason"] == "needs-review"
    assert workflow["current_apply_readiness"] == "medium"
    assert workflow["apply_readiness_medium_count"] >= 1


def test_memory_md_open_followup_candidate_stays_low_readiness_and_never_auto_applies(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    mission_control = isolated_runtime.mission_control

    _insert_candidate(
        db,
        candidate_type="memory_promotion",
        target_file="MEMORY.md",
        status="proposed",
        canonical_key="workspace-memory:open-followup:danish-concise-calibration",
        confidence="medium",
        evidence_class="runtime_support_only",
    )

    contract = mission_control.mc_runtime_contract()
    workflow = contract["pending_writes"]["memory_promotions"]
    candidate = workflow["items"][0]

    assert candidate["status"] == "proposed"
    assert candidate["apply_readiness"] == "low"
    assert candidate["apply_reason"] == "still-tentative"
    assert workflow["current_apply_readiness"] == "low"
    assert db.recent_runtime_contract_file_writes(limit=8) == []
    assert contract["write_history"]["total"] == 0


def test_memory_md_remembered_fact_candidate_gets_medium_readiness_for_high_confidence(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    mission_control = isolated_runtime.mission_control

    _insert_candidate(
        db,
        candidate_type="memory_promotion",
        target_file="MEMORY.md",
        status="proposed",
        canonical_key="workspace-memory:remembered-fact:project-anchor",
        confidence="high",
        evidence_class="runtime_support_only",
    )

    contract = mission_control.mc_runtime_contract()
    workflow = contract["pending_writes"]["memory_promotions"]
    candidate = workflow["items"][0]

    assert candidate["status"] == "proposed"
    assert candidate["apply_readiness"] == "medium"
    assert candidate["apply_reason"] == "factual-memory"
    assert workflow["current_apply_readiness"] == "medium"
    assert workflow["apply_readiness_medium_count"] >= 1


def test_memory_md_remembered_fact_candidate_stays_low_for_low_confidence(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    mission_control = isolated_runtime.mission_control

    _insert_candidate(
        db,
        candidate_type="memory_promotion",
        target_file="MEMORY.md",
        status="proposed",
        canonical_key="workspace-memory:remembered-fact:user-preference",
        confidence="low",
        evidence_class="runtime_support_only",
    )

    contract = mission_control.mc_runtime_contract()
    workflow = contract["pending_writes"]["memory_promotions"]
    candidate = workflow["items"][0]

    assert candidate["status"] == "proposed"
    assert candidate["apply_readiness"] == "low"
    assert candidate["apply_reason"] == "still-tentative"
    assert workflow["current_apply_readiness"] == "low"
    assert db.recent_runtime_contract_file_writes(limit=8) == []
    assert contract["write_history"]["total"] == 0


def test_memory_md_remembered_fact_and_user_md_stay_separated(isolated_runtime) -> None:
    db = isolated_runtime.db
    mission_control = isolated_runtime.mission_control

    _insert_candidate(
        db,
        candidate_type="memory_promotion",
        target_file="MEMORY.md",
        status="proposed",
        canonical_key="workspace-memory:remembered-fact:language-preference",
        confidence="high",
        evidence_class="runtime_support_only",
    )
    _insert_candidate(
        db,
        candidate_type="preference_update",
        target_file="USER.md",
        status="proposed",
        canonical_key="user-preference:language:danish",
        confidence="high",
        evidence_class="repeated_cross_session",
    )

    contract = mission_control.mc_runtime_contract()

    memory_workflow = contract["pending_writes"]["memory_promotions"]
    user_workflow = contract["pending_writes"]["preference_updates"]

    memory_candidate = memory_workflow["items"][0]
    user_candidate = user_workflow["items"][0]

    assert memory_candidate["apply_readiness"] == "medium"
    assert memory_candidate["apply_reason"] == "factual-memory"
    assert user_candidate["apply_readiness"] == "medium"
    assert user_candidate["apply_reason"] == "bounded-safe"

    assert memory_candidate["target_file"] == "MEMORY.md"
    assert user_candidate["target_file"] == "USER.md"
