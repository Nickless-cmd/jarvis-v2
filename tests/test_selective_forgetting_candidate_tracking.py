from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def _insert_metabolism_signal(
    db,
    *,
    focus: str,
    state: str = "releasing",
    direction: str = "bleeding-out",
    weight: str = "medium",
    run_id: str = "test-run",
) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_metabolism_state_signal(
        signal_id=f"metabolism-{uuid4().hex}",
        signal_type="metabolism-state",
        canonical_key=f"metabolism-state:{state}:{focus}",
        status="active",
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


def _insert_release_marker(
    db,
    *,
    focus: str,
    release_state: str = "release-ready",
    release_direction: str = "slipping-free",
    release_weight: str = "high",
) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_release_marker_signal(
        signal_id=f"release-{uuid4().hex}",
        signal_type="release-marker",
        canonical_key=f"release-marker:{release_state}:{focus}",
        status="active",
        title=f"Release support: {focus.replace('-', ' ')}",
        summary="Release summary",
        rationale="Validation release marker",
        source_kind="runtime-derived-support",
        confidence="high",
        evidence_summary="release evidence",
        support_summary=f"release-state={release_state} | release-direction={release_direction} | release-weight={release_weight} | release anchor",
        support_count=2,
        session_count=2,
        created_at=now,
        updated_at=now,
        status_reason="Validation release marker status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_witness(
    db,
    *,
    focus: str,
    status: str = "fading",
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
        support_summary="witness support",
        support_count=2,
        session_count=2,
        created_at=now,
        updated_at=now,
        status_reason="Validation witness status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_meaning(
    db,
    *,
    focus: str,
    status: str = "stale",
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
        confidence="medium",
        evidence_summary="meaning evidence",
        support_summary="meaning support",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation meaning status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_consolidation_target(db, *, focus: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_consolidation_target_signal(
        signal_id=f"consolidation-target-{uuid4().hex}",
        signal_type="consolidation-target",
        canonical_key=f"consolidation-target:consolidation-ready:{focus}",
        status="active",
        title=f"Consolidation support: {focus.replace('-', ' ')}",
        summary="Consolidation summary",
        rationale="Validation consolidation",
        source_kind="runtime-derived-support",
        confidence="high",
        evidence_summary="consolidation evidence",
        support_summary="consolidation-state=consolidation-ready | consolidation-focus=danish concise calibration | consolidation-weight=high | consolidation anchor",
        support_count=2,
        session_count=2,
        created_at=now,
        updated_at=now,
        status_reason="Validation consolidation status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_candidate(
    db,
    *,
    status: str,
    canonical_key: str,
    title: str,
    support_summary: str,
) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_selective_forgetting_candidate(
        signal_id=f"forgetting-candidate-{uuid4().hex}",
        signal_type="selective-forgetting-candidate",
        canonical_key=canonical_key,
        status=status,
        title=title,
        summary="Forgetting candidate summary",
        rationale="Validation forgetting candidate",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="candidate evidence",
        support_summary=support_summary,
        support_count=2,
        session_count=2,
        created_at=now,
        updated_at=now,
        status_reason="Validation candidate status",
        run_id="test-run",
        session_id="test-session",
    )


def test_forgetting_candidate_stays_empty_without_relevant_metabolism_and_release_substrate(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.selective_forgetting_candidate_tracking

    _insert_metabolism_signal(db, focus="danish-concise-calibration", state="active-retaining", direction="holding-shape")

    result = tracking.track_runtime_selective_forgetting_candidates_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_selective_forgetting_candidate_surface(limit=8)

    assert result["created"] == 0
    assert surface["active"] is False
    assert surface["items"] == []


def test_forgetting_candidate_forms_from_metabolism_release_and_fading_substrate(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.selective_forgetting_candidate_tracking
    focus = "danish-concise-calibration"

    _insert_metabolism_signal(db, focus=focus, state="releasing")
    _insert_release_marker(db, focus=focus, release_state="release-ready")
    _insert_witness(db, focus=focus, status="fading")
    _insert_meaning(db, focus=focus, status="stale")

    result = tracking.track_runtime_selective_forgetting_candidates_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_selective_forgetting_candidate_surface(limit=8)
    item = surface["items"][0]

    assert result["created"] == 1
    assert surface["active"] is True
    assert item["forgetting_candidate_state"] in {"candidate-emerging", "candidate-leaning", "candidate-ready"}
    assert item["forgetting_candidate_reason"] in {"witness-fading", "carried-weight-thinned", "release-direction-held", "support-softening"}
    assert item["forgetting_candidate_weight"] in {"low", "medium", "high"}
    assert item["forgetting_candidate_confidence"] in {"low", "medium", "high"}
    assert item["authority"] == "non-authoritative"
    assert item["canonical_delete_state"] == "not-deletion"
    assert item["self_erasure_state"] == "not-self-erasure"
    assert item["selective_forgetting_state"] == "not-selective-forgetting-execution"
    assert "appears" in item["forgetting_candidate_summary"] or "shows signs of" in item["forgetting_candidate_summary"]


def test_forgetting_candidate_is_blocked_when_consolidation_remains_active(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.selective_forgetting_candidate_tracking
    focus = "danish-concise-calibration"

    _insert_metabolism_signal(db, focus=focus, state="releasing")
    _insert_release_marker(db, focus=focus, release_state="release-ready")
    _insert_witness(db, focus=focus, status="fading")
    _insert_consolidation_target(db, focus=focus)

    result = tracking.track_runtime_selective_forgetting_candidates_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_selective_forgetting_candidate_surface(limit=8)

    assert result["created"] == 0
    assert surface["items"] == []


def test_forgetting_candidate_surface_and_mc_shapes_remain_bounded(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.selective_forgetting_candidate_tracking
    mission_control = isolated_runtime.mission_control

    _insert_candidate(
        db,
        status="active",
        canonical_key="selective-forgetting-candidate:candidate-ready:danish-concise-calibration",
        title="Forgetting candidate support: Danish concise calibration",
        support_summary="forgetting-candidate-state=candidate-ready | forgetting-candidate-reason=witness-fading | forgetting-candidate-weight=high | candidate anchor",
    )
    _insert_candidate(
        db,
        status="softening",
        canonical_key="selective-forgetting-candidate:candidate-leaning:workspace-boundary",
        title="Forgetting candidate support: Workspace boundary",
        support_summary="forgetting-candidate-state=candidate-leaning | forgetting-candidate-reason=support-softening | forgetting-candidate-weight=medium | candidate anchor",
    )
    _insert_candidate(
        db,
        status="stale",
        canonical_key="selective-forgetting-candidate:candidate-emerging:runtime-lane",
        title="Forgetting candidate support: Runtime lane",
        support_summary="forgetting-candidate-state=candidate-emerging | forgetting-candidate-reason=carried-weight-thinned | forgetting-candidate-weight=low | candidate anchor",
    )
    _insert_candidate(
        db,
        status="superseded",
        canonical_key="selective-forgetting-candidate:candidate-leaning:older-thread",
        title="Forgetting candidate support: Older thread",
        support_summary="forgetting-candidate-state=candidate-leaning | forgetting-candidate-reason=release-direction-held | forgetting-candidate-weight=medium | candidate anchor",
    )

    surface = tracking.build_runtime_selective_forgetting_candidate_surface(limit=8)
    jarvis = mission_control.mc_jarvis()
    runtime = mission_control.mc_runtime()
    mc_shape = jarvis["development"]["selective_forgetting_candidates"]
    runtime_shape = runtime["runtime_selective_forgetting_candidates"]

    assert {
        "active_count",
        "softening_count",
        "stale_count",
        "superseded_count",
        "current_signal",
        "current_status",
        "current_state",
        "current_reason",
        "current_weight",
        "current_confidence",
        "authority",
        "layer_role",
        "canonical_delete_state",
        "self_erasure_state",
        "selective_forgetting_state",
    }.issubset(surface["summary"].keys())
    assert {
        "signal_id",
        "signal_type",
        "canonical_key",
        "status",
        "title",
        "summary",
        "forgetting_candidate_state",
        "forgetting_candidate_reason",
        "forgetting_candidate_weight",
        "forgetting_candidate_summary",
        "forgetting_candidate_confidence",
        "authority",
        "layer_role",
        "canonical_delete_state",
        "self_erasure_state",
        "selective_forgetting_state",
        "updated_at",
    }.issubset(surface["items"][0].keys())
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["softening_count"] == 1
    assert surface["summary"]["stale_count"] == 1
    assert surface["summary"]["superseded_count"] == 1
    assert mc_shape["summary"]["canonical_delete_state"] == "not-deletion"
    assert runtime_shape["summary"]["selective_forgetting_state"] == "not-selective-forgetting-execution"
