from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def _insert_private_temporal_curiosity_state(
    db,
    *,
    run_id: str,
    status: str = "active",
    curiosity_type: str = "active-observation",
) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_private_temporal_curiosity_state(
        state_id=f"private-temporal-curiosity-state-{uuid4().hex}",
        state_type="private-temporal-curiosity",
        canonical_key=f"private-temporal-curiosity:{curiosity_type}:workspace-search",
        status=status,
        title="Private temporal curiosity support: workspace search",
        summary="Bounded runtime temporal curiosity is keeping a small forward-looking pull.",
        rationale="Validation temporal curiosity runtime support",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="temporal curiosity evidence",
        support_summary="Derived only from active bounded private-state and initiative-tension runtime support.",
        status_reason="Bounded temporal curiosity remains subordinate to visible/runtime truth.",
        run_id=run_id,
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def _insert_private_state_snapshot(db, *, run_id: str, status: str = "active") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_private_state_snapshot(
        snapshot_id=f"private-state-snapshot-{uuid4().hex}",
        snapshot_type="private-state-runtime-snapshot",
        canonical_key="private-state-snapshot:steady-pressure:workspace-search",
        status=status,
        title="Private state snapshot: workspace search",
        summary="Bounded runtime private-state snapshot is holding a small inner-state view.",
        rationale="Validation private-state runtime snapshot",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="private state evidence",
        support_summary="Derived only from active bounded inner-layer runtime support signals.",
        status_reason="Bounded private-state snapshot remains subordinate to visible/runtime truth.",
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
        canonical_key="private-initiative-tension:curiosity-pull:workspace-search",
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


def _insert_private_temporal_promotion_signal(db, *, status: str, canonical_key: str, title: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_private_temporal_promotion_signal(
        signal_id=f"private-temporal-promotion-signal-{uuid4().hex}",
        signal_type="private-temporal-promotion",
        canonical_key=canonical_key,
        status=status,
        title=title,
        summary="Bounded runtime temporal promotion is carrying a small maturation pull.",
        rationale="Validation temporal promotion runtime support",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="temporal promotion evidence",
        support_summary="Derived only from active bounded temporal-curiosity and private-state runtime support.",
        status_reason="Validation bounded temporal promotion support",
        run_id="test-run",
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def test_private_temporal_promotion_surface_stays_empty_without_relevant_grounding(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.private_temporal_promotion_signal_tracking
    db = isolated_runtime.db

    _insert_private_temporal_curiosity_state(db, run_id="visible-run-1")

    result = tracking.track_runtime_private_temporal_promotion_signals_for_visible_turn(
        session_id="test-session",
        run_id="visible-run-1",
    )
    surface = tracking.build_runtime_private_temporal_promotion_signal_surface(limit=8)

    assert result["created"] == 0
    assert result["updated"] == 0
    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["summary"]["active_count"] == 0
    assert surface["summary"]["authority"] == "non-authoritative"


def test_private_temporal_promotion_surface_forms_bounded_runtime_support_from_curiosity_and_state(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.private_temporal_promotion_signal_tracking
    db = isolated_runtime.db

    _insert_private_temporal_curiosity_state(db, run_id="visible-run-2")
    _insert_private_state_snapshot(db, run_id="visible-run-2")
    _insert_private_initiative_tension_signal(db, run_id="visible-run-2")

    result = tracking.track_runtime_private_temporal_promotion_signals_for_visible_turn(
        session_id="test-session",
        run_id="visible-run-2",
    )
    surface = tracking.build_runtime_private_temporal_promotion_signal_surface(limit=8)
    item = surface["items"][0]

    assert result["created"] == 1
    assert surface["active"] is True
    assert item["signal_type"] == "private-temporal-promotion"
    assert item["promotion_type"] == "carry-forward"
    assert item["promotion_pull"] == "medium"
    assert item["authority"] == "non-authoritative"
    assert item["layer_role"] == "runtime-support"
    assert item["status"] == "active"
    assert "no planner" in item["status_reason"].lower()
    assert item["source_anchor"]


def test_private_temporal_promotion_surface_and_mc_shapes_remain_bounded(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.private_temporal_promotion_signal_tracking
    mission_control = isolated_runtime.mission_control

    _insert_private_temporal_promotion_signal(
        db,
        status="active",
        canonical_key="private-temporal-promotion:carry-forward:workspace-search",
        title="Private temporal promotion support: workspace search",
    )
    _insert_private_temporal_promotion_signal(
        db,
        status="stale",
        canonical_key="private-temporal-promotion:watchful-maturation:visible-work",
        title="Private temporal promotion support: visible work",
    )
    _insert_private_temporal_promotion_signal(
        db,
        status="superseded",
        canonical_key="private-temporal-promotion:watchful-maturation:archive-focus",
        title="Private temporal promotion support: archive focus",
    )

    surface = tracking.build_runtime_private_temporal_promotion_signal_surface(limit=8)
    jarvis = mission_control.mc_jarvis()
    runtime = mission_control.mc_runtime()
    mc_shape = jarvis["development"]["private_temporal_promotion_signals"]
    runtime_shape = runtime["runtime_private_temporal_promotion_signals"]

    assert {
        "active_count",
        "stale_count",
        "superseded_count",
        "current_signal",
        "current_status",
        "current_promotion_type",
        "current_pull",
        "current_confidence",
        "authority",
        "layer_role",
    }.issubset(surface["summary"].keys())
    assert {
        "signal_id",
        "signal_type",
        "canonical_key",
        "status",
        "title",
        "summary",
        "confidence",
        "updated_at",
        "promotion_type",
        "promotion_target",
        "promotion_pull",
        "promotion_summary",
        "promotion_confidence",
        "source_anchor",
        "authority",
        "layer_role",
    }.issubset(surface["items"][0].keys())
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["stale_count"] == 1
    assert surface["summary"]["superseded_count"] == 1
    assert mc_shape["summary"]["authority"] == "non-authoritative"
    assert runtime_shape["summary"]["layer_role"] == "runtime-support"
