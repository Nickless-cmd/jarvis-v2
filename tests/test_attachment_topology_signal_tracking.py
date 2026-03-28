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
        support_summary=f"continuity-state=carried-forward | continuity-weight={weight} | continuity anchor",
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
        support_summary=f"meaning-weight={weight} | meaning anchor",
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
    session_count: int = 3,
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
        support_summary=f"persistence-state={persistence_state} | witness support",
        support_count=2,
        session_count=session_count,
        created_at=now,
        updated_at=now,
        status_reason="Validation witness status",
        run_id=run_id,
        session_id="test-session",
    )


def _insert_chronicle_brief(
    db,
    *,
    focus: str,
    status: str = "active",
    weight: str = "high",
    run_id: str = "test-run",
) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_chronicle_consolidation_brief(
        brief_id=f"chronicle-brief-{uuid4().hex}",
        brief_type="continuity-brief",
        canonical_key=f"chronicle-consolidation-brief:continuity-brief:{focus}",
        status=status,
        title=f"Chronicle brief: {focus.replace('-', ' ')}",
        summary="Chronicle brief summary",
        rationale="Validation chronicle brief",
        source_kind="runtime-derived-support",
        confidence="high",
        evidence_summary="chronicle brief evidence",
        support_summary=f"brief-weight={weight} | brief anchor",
        support_count=2,
        session_count=2,
        created_at=now,
        updated_at=now,
        status_reason="Validation chronicle brief status",
        run_id=run_id,
        session_id="test-session",
    )


def _insert_metabolism(
    db,
    *,
    focus: str,
    status: str = "active",
    state: str = "active-retaining",
    weight: str = "high",
    run_id: str = "test-run",
) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_metabolism_state_signal(
        signal_id=f"metabolism-{uuid4().hex}",
        signal_type="metabolism-state",
        canonical_key=f"metabolism-state:{state}:{focus}",
        status=status,
        title=f"Metabolism support: {focus.replace('-', ' ')}",
        summary="Metabolism summary",
        rationale="Validation metabolism",
        source_kind="runtime-derived-support",
        confidence="high",
        evidence_summary="metabolism evidence",
        support_summary=f"metabolism-state={state} | metabolism-weight={weight} | metabolism anchor",
        support_count=2,
        session_count=2,
        created_at=now,
        updated_at=now,
        status_reason="Validation metabolism status",
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
        support_summary=f"forgetting-candidate-state={state} | forgetting anchor",
        support_count=2,
        session_count=2,
        created_at=now,
        updated_at=now,
        status_reason="Validation forgetting candidate status",
        run_id="test-run",
        session_id="test-session",
    )


def test_attachment_topology_stays_empty_without_relation_meaning_and_carried_substrate(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.attachment_topology_signal_tracking

    _insert_relation_continuity(db, focus="danish-concise-calibration")

    result = tracking.track_runtime_attachment_topology_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_attachment_topology_signal_surface(limit=8)

    assert result["created"] == 0
    assert surface["active"] is False
    assert surface["items"] == []


def test_attachment_topology_forms_from_relation_meaning_and_carried_substrate(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.attachment_topology_signal_tracking
    focus = "danish-concise-calibration"

    _insert_relation_continuity(db, focus=focus, weight="high")
    _insert_meaning(db, focus=focus, weight="high")
    _insert_witness(db, focus=focus, status="carried", persistence_state="persistent", session_count=3)
    _insert_chronicle_brief(db, focus=focus, weight="high")
    _insert_metabolism(db, focus=focus, state="active-retaining", weight="high")

    result = tracking.track_runtime_attachment_topology_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_attachment_topology_signal_surface(limit=8)
    item = surface["items"][0]

    assert result["created"] == 1
    assert surface["active"] is True
    assert item["attachment_state"] in {"attachment-emerging", "attachment-held", "attachment-central"}
    assert item["attachment_focus"] == "danish concise calibration"
    assert item["attachment_weight"] in {"low", "medium", "high"}
    assert item["attachment_confidence"] in {"low", "medium", "high"}
    assert item["authority"] == "non-authoritative"
    assert item["planner_priority_state"] == "not-planner-priority"
    assert item["canonical_preference_state"] == "not-canonical-preference-truth"
    assert "appears" in item["attachment_summary"] or "shows signs of" in item["attachment_summary"]


def test_attachment_topology_runtime_surface_is_exposed_in_mission_control(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    mission_control = isolated_runtime.mission_control

    _insert_relation_continuity(db, focus="danish-concise-calibration")
    _insert_meaning(db, focus="danish-concise-calibration")
    _insert_witness(db, focus="danish-concise-calibration")
    _insert_metabolism(db, focus="danish-concise-calibration")

    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_attachment_topology_signal(
        signal_id=f"attachment-topology-{uuid4().hex}",
        signal_type="attachment-topology",
        canonical_key="attachment-topology:attachment-central:danish-concise-calibration",
        status="active",
        title="Attachment topology: danish concise calibration",
        summary="Bounded attachment-topology runtime support appears to hold danish concise calibration as a more central carried thread.",
        rationale="Validation attachment topology",
        source_kind="runtime-derived-support",
        confidence="high",
        evidence_summary="attachment topology evidence",
        support_summary="attachment-state=attachment-central | attachment-focus=danish-concise-calibration | attachment-weight=high | attachment-confidence=high | source-anchor=validation",
        support_count=2,
        session_count=3,
        created_at=now,
        updated_at=now,
        status_reason="Validation attachment topology status",
        run_id="test-run",
        session_id="test-session",
    )

    development = mission_control.mc_jarvis()["development"]["attachment_topology_signals"]
    runtime = mission_control.mc_runtime()["runtime_attachment_topology_signals"]

    assert development["active"] is True
    assert runtime["active"] is True
    assert development["summary"]["current_state"] == "attachment-central"
    assert runtime["summary"]["current_focus"] == "danish concise calibration"
    assert development["summary"]["planner_priority_state"] == "not-planner-priority"
    assert runtime["summary"]["canonical_preference_state"] == "not-canonical-preference-truth"


def test_attachment_topology_is_softened_by_active_forgetting_pressure(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.attachment_topology_signal_tracking
    focus = "danish-concise-calibration"

    _insert_relation_continuity(db, focus=focus, weight="high")
    _insert_meaning(db, focus=focus, weight="high")
    _insert_witness(db, focus=focus, status="carried", persistence_state="persistent")
    _insert_metabolism(db, focus=focus, state="active-retaining", weight="high")
    _insert_forgetting_candidate(db, focus=focus, state="candidate-ready")

    tracking.track_runtime_attachment_topology_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_attachment_topology_signal_surface(limit=8)
    item = surface["items"][0]

    assert item["attachment_weight"] in {"medium", "high"}
    assert "release pressure" in item["attachment_summary"]
