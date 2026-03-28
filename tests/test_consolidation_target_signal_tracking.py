from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def _insert_metabolism_signal(
    db,
    *,
    focus: str,
    status: str = "active",
    state: str = "consolidating",
    direction: str = "settling-in",
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
        support_summary=f"metabolism-state={state} | metabolism-direction={direction} | metabolism-weight={weight} | metabolism anchor",
        support_count=2,
        session_count=2,
        created_at=now,
        updated_at=now,
        status_reason="Validation metabolism status",
        run_id=run_id,
        session_id="test-session",
    )


def _insert_witness_signal(
    db,
    *,
    focus: str,
    status: str = "carried",
    session_count: int = 2,
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
        support_summary="becoming-direction=becoming-steady | maturation-state=stabilizing | persistence-state=persistent | witness support",
        support_count=2,
        session_count=session_count,
        created_at=now,
        updated_at=now,
        status_reason="Validation witness status",
        run_id=run_id,
        session_id="test-session",
    )


def _insert_chronicle_signal(
    db,
    *,
    focus: str,
    status: str = "active",
    weight: str = "high",
) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_chronicle_consolidation_signal(
        signal_id=f"chronicle-signal-{uuid4().hex}",
        signal_type="chronicle-consolidation",
        canonical_key=f"chronicle-consolidation:carried-thread:{focus}",
        status=status,
        title=f"Chronicle consolidation support: {focus.replace('-', ' ')}",
        summary="Chronicle summary",
        rationale="Validation chronicle signal",
        source_kind="runtime-derived-support",
        confidence="high",
        evidence_summary="chronicle evidence",
        support_summary=f"chronicle-type=carried-thread | chronicle-weight={weight} | chronicle anchor",
        support_count=2,
        session_count=2,
        created_at=now,
        updated_at=now,
        status_reason="Validation chronicle status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_chronicle_brief(
    db,
    *,
    focus: str,
    status: str = "active",
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
        support_summary="brief-focus=danish concise calibration | brief anchor",
        support_count=2,
        session_count=2,
        created_at=now,
        updated_at=now,
        status_reason="Validation chronicle brief status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_release_marker(
    db,
    *,
    focus: str,
    release_state: str = "release-ready",
) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_release_marker_signal(
        signal_id=f"release-{uuid4().hex}",
        signal_type="release-marker",
        canonical_key=f"release-marker:{release_state}:{focus}",
        status="active",
        title=f"Release support: {focus.replace('-', ' ')}",
        summary="Release summary",
        rationale="Validation release",
        source_kind="runtime-derived-support",
        confidence="high",
        evidence_summary="release evidence",
        support_summary=f"release-state={release_state} | release-direction=slipping-free | release-weight=high | release anchor",
        support_count=2,
        session_count=2,
        created_at=now,
        updated_at=now,
        status_reason="Validation release status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_consolidation_target(
    db,
    *,
    status: str,
    canonical_key: str,
    title: str,
    support_summary: str,
) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_consolidation_target_signal(
        signal_id=f"consolidation-target-{uuid4().hex}",
        signal_type="consolidation-target",
        canonical_key=canonical_key,
        status=status,
        title=title,
        summary="Consolidation target summary",
        rationale="Validation consolidation target",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="consolidation evidence",
        support_summary=support_summary,
        support_count=2,
        session_count=2,
        created_at=now,
        updated_at=now,
        status_reason="Validation consolidation target status",
        run_id="test-run",
        session_id="test-session",
    )


def test_consolidation_target_stays_empty_without_relevant_metabolism_and_carried_substrate(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.consolidation_target_signal_tracking

    _insert_metabolism_signal(
        db,
        focus="danish-concise-calibration",
        state="releasing",
        direction="bleeding-out",
        weight="medium",
    )

    result = tracking.track_runtime_consolidation_target_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_consolidation_target_signal_surface(limit=8)

    assert result["created"] == 0
    assert surface["active"] is False
    assert surface["items"] == []


def test_consolidation_target_forms_from_metabolism_witness_and_chronicle_substrate(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.consolidation_target_signal_tracking
    focus = "danish-concise-calibration"

    _insert_metabolism_signal(db, focus=focus, state="consolidating", direction="settling-in", weight="high")
    _insert_witness_signal(db, focus=focus, status="carried", session_count=3)
    _insert_chronicle_signal(db, focus=focus, status="active")
    _insert_chronicle_brief(db, focus=focus, status="active")

    result = tracking.track_runtime_consolidation_target_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_consolidation_target_signal_surface(limit=8)
    item = surface["items"][0]

    assert result["created"] == 1
    assert surface["active"] is True
    assert item["consolidation_state"] in {"consolidation-emerging", "consolidation-forming", "consolidation-ready"}
    assert item["consolidation_focus"]
    assert item["consolidation_weight"] in {"low", "medium", "high"}
    assert item["consolidation_confidence"] in {"low", "medium", "high"}
    assert item["authority"] == "non-authoritative"
    assert item["writeback_state"] == "not-writeback"
    assert item["canonical_mutation_state"] == "not-canonical-mutation"
    assert "appears" in item["consolidation_summary"] or "shows signs of" in item["consolidation_summary"]


def test_consolidation_target_is_blocked_by_strong_release_direction(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.consolidation_target_signal_tracking
    focus = "danish-concise-calibration"

    _insert_metabolism_signal(db, focus=focus, state="consolidating")
    _insert_witness_signal(db, focus=focus, status="carried")
    _insert_chronicle_signal(db, focus=focus, status="active")
    _insert_release_marker(db, focus=focus, release_state="release-ready")

    result = tracking.track_runtime_consolidation_target_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_consolidation_target_signal_surface(limit=8)

    assert result["created"] == 0
    assert surface["items"] == []


def test_consolidation_target_surface_and_mc_shapes_remain_bounded(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.consolidation_target_signal_tracking
    mission_control = isolated_runtime.mission_control

    _insert_consolidation_target(
        db,
        status="active",
        canonical_key="consolidation-target:consolidation-ready:danish-concise-calibration",
        title="Consolidation support: Danish concise calibration",
        support_summary="consolidation-state=consolidation-ready | consolidation-focus=danish concise calibration | consolidation-weight=high | consolidation anchor",
    )
    _insert_consolidation_target(
        db,
        status="softening",
        canonical_key="consolidation-target:consolidation-forming:workspace-boundary",
        title="Consolidation support: Workspace boundary",
        support_summary="consolidation-state=consolidation-forming | consolidation-focus=workspace boundary | consolidation-weight=medium | consolidation anchor",
    )
    _insert_consolidation_target(
        db,
        status="stale",
        canonical_key="consolidation-target:consolidation-emerging:runtime-lane",
        title="Consolidation support: Runtime lane",
        support_summary="consolidation-state=consolidation-emerging | consolidation-focus=runtime lane | consolidation-weight=low | consolidation anchor",
    )
    _insert_consolidation_target(
        db,
        status="superseded",
        canonical_key="consolidation-target:consolidation-forming:older-thread",
        title="Consolidation support: Older thread",
        support_summary="consolidation-state=consolidation-forming | consolidation-focus=older thread | consolidation-weight=medium | consolidation anchor",
    )

    surface = tracking.build_runtime_consolidation_target_signal_surface(limit=8)
    jarvis = mission_control.mc_jarvis()
    runtime = mission_control.mc_runtime()
    mc_shape = jarvis["development"]["consolidation_target_signals"]
    runtime_shape = runtime["runtime_consolidation_target_signals"]

    assert {
        "active_count",
        "softening_count",
        "stale_count",
        "superseded_count",
        "current_signal",
        "current_status",
        "current_state",
        "current_focus",
        "current_weight",
        "current_confidence",
        "authority",
        "layer_role",
        "writeback_state",
        "canonical_mutation_state",
    }.issubset(surface["summary"].keys())
    assert {
        "signal_id",
        "signal_type",
        "canonical_key",
        "status",
        "title",
        "summary",
        "consolidation_state",
        "consolidation_focus",
        "consolidation_weight",
        "consolidation_summary",
        "consolidation_confidence",
        "authority",
        "layer_role",
        "writeback_state",
        "canonical_mutation_state",
        "updated_at",
    }.issubset(surface["items"][0].keys())
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["softening_count"] == 1
    assert surface["summary"]["stale_count"] == 1
    assert surface["summary"]["superseded_count"] == 1
    assert mc_shape["summary"]["writeback_state"] == "not-writeback"
    assert runtime_shape["summary"]["canonical_mutation_state"] == "not-canonical-mutation"
