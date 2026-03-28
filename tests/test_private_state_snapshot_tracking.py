from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def _insert_private_inner_note_signal(db, *, run_id: str, status: str = "active") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_private_inner_note_signal(
        signal_id=f"private-inner-note-signal-{uuid4().hex}",
        signal_type="private-inner-note",
        canonical_key="private-inner-note:work-status:workspace-search",
        status=status,
        title="Private inner note support: workspace search",
        summary="Bounded runtime support remains subordinate to visible work.",
        rationale="Validation private inner note support",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="visible note evidence",
        support_summary="Derived from the latest visible work note and kept non-authoritative.",
        status_reason="Bounded private inner note remains subordinate to visible/runtime truth.",
        run_id=run_id,
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def _insert_private_initiative_tension_signal(db, *, run_id: str, status: str = "active") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_private_initiative_tension_signal(
        signal_id=f"private-initiative-tension-signal-{uuid4().hex}",
        signal_type="private-initiative-tension",
        canonical_key="private-initiative-tension:unresolved:workspace-search",
        status=status,
        title="Private initiative tension support: workspace search",
        summary="Bounded runtime initiative tension is carrying current pressure.",
        rationale="Validation initiative tension support",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="initiative tension evidence",
        support_summary="Derived from visible work plus bounded runtime support layers.",
        status_reason="Bounded initiative tension remains subordinate to visible/runtime truth and carries no execution authority.",
        run_id=run_id,
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def _insert_private_inner_interplay_signal(db, *, run_id: str, status: str = "active") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_private_inner_interplay_signal(
        signal_id=f"private-inner-interplay-signal-{uuid4().hex}",
        signal_type="private-inner-interplay",
        canonical_key="private-inner-interplay:unresolved-support:workspace-search",
        status=status,
        title="Private inner interplay support: workspace search",
        summary="Bounded runtime inner interplay links note support with initiative tension.",
        rationale="Validation private inner interplay support",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="inner interplay evidence",
        support_summary="Derived from active bounded inner-note and initiative-tension runtime support signals.",
        status_reason="Bounded inner interplay remains subordinate to visible/runtime truth and carries no planner authority.",
        run_id=run_id,
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def _insert_private_state_snapshot(db, *, status: str, canonical_key: str, title: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_private_state_snapshot(
        snapshot_id=f"private-state-snapshot-{uuid4().hex}",
        snapshot_type="private-state-runtime-snapshot",
        canonical_key=canonical_key,
        status=status,
        title=title,
        summary="Bounded runtime private-state snapshot is holding a small inner-state view.",
        rationale="Validation private-state runtime snapshot",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="private state snapshot evidence",
        support_summary="Derived only from active bounded inner-layer runtime support signals.",
        status_reason="Validation bounded private-state snapshot",
        run_id="test-run",
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def test_private_state_snapshot_surface_stays_empty_without_full_inner_grounding(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.private_state_snapshot_tracking
    db = isolated_runtime.db

    _insert_private_inner_note_signal(db, run_id="visible-run-1")
    _insert_private_initiative_tension_signal(db, run_id="visible-run-1")

    result = tracking.track_runtime_private_state_snapshots_for_visible_turn(
        session_id="test-session",
        run_id="visible-run-1",
    )
    surface = tracking.build_runtime_private_state_snapshot_surface(limit=8)

    assert result["created"] == 0
    assert result["updated"] == 0
    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["summary"]["active_count"] == 0
    assert surface["summary"]["authority"] == "non-authoritative"


def test_private_state_snapshot_forms_bounded_runtime_support_from_returned_inner_layers(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.private_state_snapshot_tracking
    db = isolated_runtime.db

    _insert_private_inner_note_signal(db, run_id="visible-run-2")
    _insert_private_initiative_tension_signal(db, run_id="visible-run-2")
    _insert_private_inner_interplay_signal(db, run_id="visible-run-2")

    result = tracking.track_runtime_private_state_snapshots_for_visible_turn(
        session_id="test-session",
        run_id="visible-run-2",
    )
    surface = tracking.build_runtime_private_state_snapshot_surface(limit=8)
    item = surface["items"][0]

    assert result["created"] == 1
    assert surface["active"] is True
    assert item["snapshot_type"] == "private-state-runtime-snapshot"
    assert item["state_tone"] == "steady-pressure"
    assert item["state_pressure"] == "medium"
    assert item["authority"] == "non-authoritative"
    assert item["layer_role"] == "runtime-support"
    assert item["status"] == "active"
    assert "no planner" in item["status_reason"].lower()
    assert item["source_anchor"]


def test_private_state_snapshot_surface_and_mc_shapes_remain_bounded(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.private_state_snapshot_tracking
    mission_control = isolated_runtime.mission_control

    _insert_private_state_snapshot(
        db,
        status="active",
        canonical_key="private-state-snapshot:steady-support:workspace-search",
        title="Private state snapshot: workspace search",
    )
    _insert_private_state_snapshot(
        db,
        status="stale",
        canonical_key="private-state-snapshot:steady-support:visible-work",
        title="Private state snapshot: visible work",
    )
    _insert_private_state_snapshot(
        db,
        status="superseded",
        canonical_key="private-state-snapshot:steady-pressure:archive-focus",
        title="Private state snapshot: archive focus",
    )

    surface = tracking.build_runtime_private_state_snapshot_surface(limit=8)
    jarvis = mission_control.mc_jarvis()
    runtime = mission_control.mc_runtime()
    mc_shape = jarvis["development"]["private_state_snapshots"]
    runtime_shape = runtime["runtime_private_state_snapshots"]

    assert {
        "active_count",
        "stale_count",
        "superseded_count",
        "current_snapshot",
        "current_status",
        "current_tone",
        "current_pressure",
        "current_confidence",
        "authority",
        "layer_role",
    }.issubset(surface["summary"].keys())
    assert {
        "snapshot_id",
        "snapshot_type",
        "canonical_key",
        "status",
        "title",
        "summary",
        "confidence",
        "updated_at",
        "state_tone",
        "state_pressure",
        "state_confidence",
        "state_summary",
        "source_anchor",
        "authority",
        "layer_role",
    }.issubset(surface["items"][0].keys())
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["stale_count"] == 1
    assert surface["summary"]["superseded_count"] == 1
    assert mc_shape["summary"]["authority"] == "non-authoritative"
    assert runtime_shape["summary"]["layer_role"] == "runtime-support"
