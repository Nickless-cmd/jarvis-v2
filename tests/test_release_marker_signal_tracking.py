from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def _insert_metabolism_signal(
    db,
    *,
    focus: str,
    status: str = "active",
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


def _insert_witness_signal(db, *, focus: str, status: str = "fading", run_id: str = "test-run") -> None:
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
        run_id=run_id,
        session_id="test-session",
    )


def _insert_meaning_signal(db, *, focus: str, status: str = "stale", run_id: str = "test-run") -> None:
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
        run_id=run_id,
        session_id="test-session",
    )


def _insert_release_marker_signal(
    db,
    *,
    status: str,
    canonical_key: str,
    title: str,
    support_summary: str,
) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_release_marker_signal(
        signal_id=f"release-marker-{uuid4().hex}",
        signal_type="release-marker",
        canonical_key=canonical_key,
        status=status,
        title=title,
        summary="Release summary",
        rationale="Validation release marker",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="release evidence",
        support_summary=support_summary,
        support_count=2,
        session_count=2,
        created_at=now,
        updated_at=now,
        status_reason="Validation release status",
        run_id="test-run",
        session_id="test-session",
    )


def test_release_marker_stays_empty_without_relevant_metabolism_and_lifecycle_substrate(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.release_marker_signal_tracking

    _insert_metabolism_signal(
        db,
        focus="danish-concise-calibration",
        state="active-retaining",
        direction="holding-shape",
        weight="high",
    )

    result = tracking.track_runtime_release_marker_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_release_marker_signal_surface(limit=8)

    assert result["created"] == 0
    assert surface["active"] is False
    assert surface["items"] == []


def test_release_marker_forms_bounded_runtime_support_from_metabolism_and_lifecycle_release_substrate(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.release_marker_signal_tracking
    focus = "danish-concise-calibration"

    _insert_metabolism_signal(db, focus=focus, state="releasing", direction="bleeding-out", weight="medium")
    _insert_witness_signal(db, focus=focus, status="fading")
    _insert_meaning_signal(db, focus=focus, status="stale")

    result = tracking.track_runtime_release_marker_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_release_marker_signal_surface(limit=8)
    item = surface["items"][0]

    assert result["created"] == 1
    assert surface["active"] is True
    assert item["release_state"] in {"release-emerging", "release-leaning", "release-ready"}
    assert item["release_direction"] in {"slipping-free", "falling-away", "lightening", "loosening", "softening-out"}
    assert item["release_weight"] in {"low", "medium", "high"}
    assert item["release_confidence"] in {"low", "medium", "high"}
    assert item["authority"] == "non-authoritative"
    assert item["canonical_delete_state"] == "not-canonical-deletion"
    assert item["self_erasure_state"] == "not-self-erasure"
    assert item["selective_forgetting_state"] == "not-selective-forgetting-execution"
    assert "appears" in item["release_summary"] or "shows signs of" in item["release_summary"]


def test_release_marker_surface_and_mc_shapes_remain_bounded(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.release_marker_signal_tracking
    mission_control = isolated_runtime.mission_control

    _insert_release_marker_signal(
        db,
        status="active",
        canonical_key="release-marker:release-ready:danish-concise-calibration",
        title="Release support: Danish concise calibration",
        support_summary="release-state=release-ready | release-direction=slipping-free | release-weight=high | release anchor",
    )
    _insert_release_marker_signal(
        db,
        status="softening",
        canonical_key="release-marker:release-leaning:workspace-boundary",
        title="Release support: Workspace boundary",
        support_summary="release-state=release-leaning | release-direction=lightening | release-weight=medium | release anchor",
    )
    _insert_release_marker_signal(
        db,
        status="stale",
        canonical_key="release-marker:release-emerging:runtime-lane",
        title="Release support: Runtime lane",
        support_summary="release-state=release-emerging | release-direction=softening-out | release-weight=low | release anchor",
    )
    _insert_release_marker_signal(
        db,
        status="superseded",
        canonical_key="release-marker:release-leaning:older-thread",
        title="Release support: Older thread",
        support_summary="release-state=release-leaning | release-direction=loosening | release-weight=medium | release anchor",
    )

    surface = tracking.build_runtime_release_marker_signal_surface(limit=8)
    jarvis = mission_control.mc_jarvis()
    runtime = mission_control.mc_runtime()
    mc_shape = jarvis["development"]["release_marker_signals"]
    runtime_shape = runtime["runtime_release_marker_signals"]

    assert {
        "active_count",
        "softening_count",
        "stale_count",
        "superseded_count",
        "current_signal",
        "current_status",
        "current_state",
        "current_direction",
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
        "release_state",
        "release_direction",
        "release_weight",
        "release_summary",
        "release_confidence",
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
    assert mc_shape["summary"]["canonical_delete_state"] == "not-canonical-deletion"
    assert runtime_shape["summary"]["selective_forgetting_state"] == "not-selective-forgetting-execution"
