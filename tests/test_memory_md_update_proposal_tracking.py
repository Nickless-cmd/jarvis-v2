from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def _insert_open_loop(db, *, status: str, signal_type: str, canonical_key: str, summary: str | None = None) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_open_loop_signal(
        signal_id=f"open-loop-{uuid4().hex}",
        signal_type=signal_type,
        canonical_key=canonical_key,
        status=status,
        title=f"Open loop row: {signal_type}",
        summary=summary or f"Open loop summary: {signal_type}",
        rationale="Validation open loop",
        source_kind="derived-runtime-open-loop",
        confidence="medium",
        evidence_summary="open loop evidence",
        support_summary="open loop support | open loop anchor",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation open loop status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_witness(db, *, status: str, signal_type: str, canonical_key: str, summary: str | None = None) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_witness_signal(
        signal_id=f"witness-{uuid4().hex}",
        signal_type=signal_type,
        canonical_key=canonical_key,
        status=status,
        title=f"Witness row: {signal_type}",
        summary=summary or f"Witness summary: {signal_type}",
        rationale="Validation witness",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="witness evidence",
        support_summary="witness support | witness anchor",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation witness status",
        run_id="test-run",
        session_id="test-session",
    )


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


def _insert_remembered_fact_signal(
    db,
    *,
    status: str,
    signal_type: str,
    canonical_key: str,
    summary: str | None = None,
) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_remembered_fact_signal(
        signal_id=f"remembered-fact-{uuid4().hex}",
        signal_type=signal_type,
        canonical_key=canonical_key,
        status=status,
        title=f"Remembered fact: {signal_type}",
        summary=summary or f"Remembered fact summary: {signal_type}",
        rationale="Validation remembered fact",
        source_kind="user-explicit",
        confidence="high",
        evidence_summary="remembered fact evidence",
        support_summary="remembered fact support | Visible user anchor: validation anchor",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation remembered fact status",
        run_id="test-run",
        session_id="test-session",
    )


def test_memory_md_update_proposal_surface_stays_empty_without_relevant_grounding(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.memory_md_update_proposal_tracking

    _insert_open_loop(
        db,
        status="closed",
        signal_type="softening-loop",
        canonical_key="open-loop:softening-loop:danish-concise-calibration",
    )
    _insert_witness(
        db,
        status="fading",
        signal_type="carried-lesson",
        canonical_key="witness:carried-lesson:danish-concise-calibration",
    )

    result = tracking.track_runtime_memory_md_update_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_memory_md_update_proposal_surface(limit=8)

    assert result["created"] == 0
    assert result["updated"] == 0
    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["summary"]["fresh_count"] == 0
    assert surface["summary"]["active_count"] == 0
    assert surface["summary"]["fading_count"] == 0


def test_memory_md_update_proposal_surface_forms_small_bounded_proposals(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.memory_md_update_proposal_tracking

    _insert_open_loop(
        db,
        status="open",
        signal_type="persistent-open-loop",
        canonical_key="open-loop:persistent-open-loop:danish-concise-calibration",
        summary="A bounded loop around danish concise calibration is still unresolved and carrying live pressure.",
    )
    _insert_open_loop(
        db,
        status="softening",
        signal_type="softening-loop",
        canonical_key="open-loop:softening-loop:workspace-boundary",
        summary="A bounded loop around workspace boundary is still present, but the pressure is easing.",
    )
    _insert_witness(
        db,
        status="carried",
        signal_type="carried-lesson",
        canonical_key="witness:carried-lesson:review-style",
        summary="A bounded lesson around review style now looks carried forward.",
    )

    result = tracking.track_runtime_memory_md_update_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_memory_md_update_proposal_surface(limit=8)
    items_by_type = {item["proposal_type"]: item for item in surface["items"]}

    assert result["created"] == 3
    assert surface["active"] is True
    assert surface["summary"]["fresh_count"] == 1
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["fading_count"] == 1
    assert items_by_type["open-followup-update"]["memory_kind"] == "open-followup"
    assert items_by_type["open-followup-update"]["status"] == "fresh"
    assert items_by_type["carry-forward-thread-update"]["memory_kind"] == "carry-forward-thread"
    assert items_by_type["carry-forward-thread-update"]["status"] == "fading"
    assert items_by_type["stable-context-update"]["memory_kind"] == "stable-context"
    assert items_by_type["stable-context-update"]["status"] == "active"
    assert items_by_type["stable-context-update"]["proposal_reason"] == "A bounded lesson around review style now looks carried forward."
    assert db.recent_runtime_contract_file_writes(limit=8) == []


def test_memory_md_update_proposal_surface_extends_with_remembered_fact_proposals(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.memory_md_update_proposal_tracking

    _insert_open_loop(
        db,
        status="open",
        signal_type="persistent-open-loop",
        canonical_key="open-loop:persistent-open-loop:danish-concise-calibration",
        summary="A bounded loop around danish concise calibration is still unresolved and carrying live pressure.",
    )
    _insert_remembered_fact_signal(
        db,
        status="active",
        signal_type="explicit-user-fact",
        canonical_key="remembered-fact:explicit-user-fact:user-name",
        summary="User explicitly stated their name as Bjorn.",
    )

    result = tracking.track_runtime_memory_md_update_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_memory_md_update_proposal_surface(limit=8)
    items_by_type = {item["proposal_type"]: item for item in surface["items"]}

    assert result["created"] == 2
    assert items_by_type["open-followup-update"]["memory_kind"] == "open-followup"
    assert items_by_type["remembered-fact-update"]["memory_kind"] == "remembered-fact"
    assert items_by_type["remembered-fact-update"]["status"] == "active"
    assert items_by_type["remembered-fact-update"]["proposal_reason"] == "User explicitly stated their name as Bjorn."
    assert items_by_type["remembered-fact-update"]["proposal_confidence"] == "high"


def test_memory_md_update_proposal_surface_does_not_form_fact_proposals_without_relevant_fact_grounding(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.memory_md_update_proposal_tracking

    _insert_remembered_fact_signal(
        db,
        status="stale",
        signal_type="explicit-user-fact",
        canonical_key="remembered-fact:explicit-user-fact:user-name",
        summary="User explicitly stated their name as Bjorn.",
    )

    result = tracking.track_runtime_memory_md_update_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_memory_md_update_proposal_surface(limit=8)

    assert result["created"] == 0
    assert surface["items"] == []


def test_memory_md_update_proposal_surface_and_mc_shapes_remain_bounded(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.memory_md_update_proposal_tracking
    mission_control = isolated_runtime.mission_control

    _insert_memory_md_update_proposal(
        db,
        status="fresh",
        proposal_type="open-followup-update",
        canonical_key="memory-md-update-proposal:open-followup-update:danish-concise-calibration",
    )
    _insert_memory_md_update_proposal(
        db,
        status="active",
        proposal_type="stable-context-update",
        canonical_key="memory-md-update-proposal:stable-context-update:review-style",
    )
    _insert_memory_md_update_proposal(
        db,
        status="fading",
        proposal_type="carry-forward-thread-update",
        canonical_key="memory-md-update-proposal:carry-forward-thread-update:workspace-boundary",
    )
    _insert_memory_md_update_proposal(
        db,
        status="stale",
        proposal_type="open-followup-update",
        canonical_key="memory-md-update-proposal:open-followup-update:old-thread",
    )
    _insert_memory_md_update_proposal(
        db,
        status="superseded",
        proposal_type="stable-context-update",
        canonical_key="memory-md-update-proposal:stable-context-update:older-review-style",
    )
    _insert_memory_md_update_proposal(
        db,
        status="active",
        proposal_type="remembered-fact-update",
        canonical_key="memory-md-update-proposal:remembered-fact-update:user-name",
    )

    surface = tracking.build_runtime_memory_md_update_proposal_surface(limit=8)
    jarvis = mission_control.mc_jarvis()
    runtime = mission_control.mc_runtime()
    mc_shape = jarvis["development"]["memory_md_update_proposals"]
    runtime_shape = runtime["runtime_memory_md_update_proposals"]

    assert {
        "fresh_count",
        "active_count",
        "fading_count",
        "stale_count",
        "superseded_count",
        "current_proposal",
        "current_status",
        "current_proposal_type",
        "current_proposal_confidence",
    }.issubset(surface["summary"].keys())
    assert {
        "proposal_id",
        "proposal_type",
        "canonical_key",
        "status",
        "title",
        "summary",
        "confidence",
        "updated_at",
        "memory_kind",
        "proposed_update",
        "proposal_reason",
        "proposal_confidence",
        "source_anchor",
    }.issubset(surface["items"][0].keys())
    assert surface["summary"]["fresh_count"] == 1
    assert surface["summary"]["active_count"] == 2
    assert surface["summary"]["fading_count"] == 1
    assert surface["summary"]["stale_count"] == 1
    assert surface["summary"]["superseded_count"] == 1
    assert mc_shape["summary"]["current_status"] in {"fresh", "active", "fading", "stale"}
    assert runtime_shape["summary"]["current_status"] in {"fresh", "active", "fading", "stale"}
    assert any(item["memory_kind"] == "remembered-fact" for item in surface["items"])
