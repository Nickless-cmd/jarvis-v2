from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def _insert_relation_continuity(
    db,
    *,
    focus: str,
    status: str = "active",
    weight: str = "high",
    run_id: str = "test-run",
) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_relation_continuity_signal(
        signal_id=f"relation-continuity-{uuid4().hex}",
        signal_type="relation-continuity",
        canonical_key=f"relation-continuity:carried-thread:{focus}",
        status=status,
        title=f"Relation continuity support: {focus.replace('-', ' ')}",
        summary="Relation continuity summary",
        rationale="Validation relation continuity",
        source_kind="runtime-derived-support",
        confidence="high",
        evidence_summary="relation continuity evidence",
        support_summary=f"continuity-state=carried-forward | continuity-weight={weight} | source-anchor=relation-anchor",
        support_count=2,
        session_count=2,
        created_at=now,
        updated_at=now,
        status_reason="Validation relation continuity status",
        run_id=run_id,
        session_id="test-session",
    )


def _insert_meaning(
    db,
    *,
    focus: str,
    status: str = "active",
    weight: str = "high",
    run_id: str = "test-run",
) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_meaning_significance_signal(
        signal_id=f"meaning-{uuid4().hex}",
        signal_type="meaning-significance",
        canonical_key=f"meaning-significance:developmental-significance:{focus}",
        status=status,
        title=f"Meaning significance support: {focus.replace('-', ' ')}",
        summary="Meaning summary",
        rationale="Validation meaning",
        source_kind="runtime-derived-support",
        confidence="high",
        evidence_summary="meaning evidence",
        support_summary=f"meaning-weight={weight} | source-anchor=meaning-anchor",
        support_count=2,
        session_count=2,
        created_at=now,
        updated_at=now,
        status_reason="Validation meaning status",
        run_id=run_id,
        session_id="test-session",
    )


def _insert_witness(
    db,
    *,
    focus: str,
    status: str = "carried",
    persistence_state: str = "persistent",
    run_id: str = "test-run",
) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_witness_signal(
        signal_id=f"witness-{uuid4().hex}",
        signal_type="carried-lesson",
        canonical_key=f"witness-signal:carried-lesson:{focus}",
        status=status,
        title=f"Carried lesson: {focus.replace('-', ' ')}",
        summary="Witness summary",
        rationale="Validation witness",
        source_kind="runtime-derived-support",
        confidence="high",
        evidence_summary="witness evidence",
        support_summary=f"persistence-state={persistence_state} | source-anchor=witness-anchor",
        support_count=2,
        session_count=3,
        created_at=now,
        updated_at=now,
        status_reason="Validation witness status",
        run_id=run_id,
        session_id="test-session",
    )


def _insert_attachment_topology(
    db,
    *,
    focus: str,
    state: str = "attachment-central",
    weight: str = "high",
    confidence: str = "high",
    run_id: str = "test-run",
) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_attachment_topology_signal(
        signal_id=f"attachment-topology-{uuid4().hex}",
        signal_type="attachment-topology",
        canonical_key=f"attachment-topology:{state}:{focus}",
        status="active",
        title=f"Attachment topology: {focus.replace('-', ' ')}",
        summary="Bounded attachment-topology runtime support appears to hold the focus as a more central carried thread.",
        rationale="Validation attachment topology",
        source_kind="runtime-derived-support",
        confidence=confidence,
        evidence_summary="attachment evidence",
        support_summary=(
            f"attachment-state={state} | attachment-focus={focus} | attachment-weight={weight} | "
            f"attachment-confidence={confidence} | source-anchor=attachment-anchor"
        ),
        support_count=2,
        session_count=3,
        created_at=now,
        updated_at=now,
        status_reason="Validation attachment topology status",
        run_id=run_id,
        session_id="test-session",
    )


def _insert_forgetting_candidate(
    db,
    *,
    focus: str,
    state: str = "candidate-ready",
) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_selective_forgetting_candidate(
        signal_id=f"forgetting-{uuid4().hex}",
        signal_type="selective-forgetting-candidate",
        canonical_key=f"selective-forgetting-candidate:{state}:{focus}",
        status="active",
        title=f"Forgetting candidate: {focus.replace('-', ' ')}",
        summary="Forgetting candidate summary",
        rationale="Validation forgetting candidate",
        source_kind="runtime-derived-support",
        confidence="high",
        evidence_summary="forgetting evidence",
        support_summary=f"forgetting-candidate-state={state} | source-anchor=forgetting-anchor",
        support_count=2,
        session_count=2,
        created_at=now,
        updated_at=now,
        status_reason="Validation forgetting candidate status",
        run_id="test-run",
        session_id="test-session",
    )


def test_loyalty_gradient_stays_empty_without_attachment_topology_substrate(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.loyalty_gradient_signal_tracking

    _insert_relation_continuity(db, focus="danish-concise-calibration")
    _insert_meaning(db, focus="danish-concise-calibration")
    _insert_witness(db, focus="danish-concise-calibration")

    result = tracking.track_runtime_loyalty_gradient_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_loyalty_gradient_signal_surface(limit=8)

    assert result["created"] == 0
    assert surface["active"] is False
    assert surface["items"] == []


def test_loyalty_gradient_forms_as_bounded_non_authoritative_runtime_support(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.loyalty_gradient_signal_tracking
    focus = "danish-concise-calibration"

    _insert_relation_continuity(db, focus=focus)
    _insert_meaning(db, focus=focus)
    _insert_witness(db, focus=focus)
    _insert_attachment_topology(db, focus=focus)

    result = tracking.track_runtime_loyalty_gradient_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_loyalty_gradient_signal_surface(limit=8)
    item = surface["items"][0]

    assert result["created"] == 1
    assert surface["active"] is True
    assert item["gradient_state"] in {"loyalty-emerging", "loyalty-held", "loyalty-central", "loyalty-peripheral"}
    assert item["gradient_focus"] == "danish concise calibration"
    assert item["gradient_rank"] == 1
    assert item["gradient_weight"] in {"low", "medium", "high"}
    assert item["gradient_confidence"] in {"low", "medium", "high"}
    assert item["authority"] == "non-authoritative"
    assert item["planner_priority_state"] == "not-planner-priority"
    assert item["canonical_preference_state"] == "not-canonical-preference-truth"
    assert item["prompt_inclusion_state"] == "not-prompt-included"
    assert item["workflow_bridge_state"] == "not-workflow-bridge"
    assert "not planner priority" in item["gradient_summary"] or "not planner priority" in item["summary"]
    assert db.runtime_contract_file_write_counts() == {}


def test_loyalty_gradient_surface_is_exposed_in_mission_control_runtime(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    mission_control = isolated_runtime.mission_control

    _insert_relation_continuity(db, focus="danish-concise-calibration")
    _insert_meaning(db, focus="danish-concise-calibration")
    _insert_witness(db, focus="danish-concise-calibration")
    _insert_attachment_topology(db, focus="danish-concise-calibration")
    _insert_forgetting_candidate(db, focus="danish-concise-calibration")

    tracking = isolated_runtime.loyalty_gradient_signal_tracking
    tracking.track_runtime_loyalty_gradient_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )

    development = mission_control.mc_jarvis()["development"]["loyalty_gradient_signals"]
    runtime = mission_control.mc_runtime()["runtime_loyalty_gradient_signals"]

    assert development["active"] is True
    assert runtime["active"] is True
    assert development["summary"]["current_focus"] == "danish concise calibration"
    assert runtime["summary"]["planner_priority_state"] == "not-planner-priority"
    assert runtime["summary"]["canonical_preference_state"] == "not-canonical-preference-truth"
    assert runtime["summary"]["prompt_inclusion_state"] == "not-prompt-included"
    assert runtime["summary"]["workflow_bridge_state"] == "not-workflow-bridge"
