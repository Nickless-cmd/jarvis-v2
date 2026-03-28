from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def _insert_self_review_outcome(
    db,
    *,
    status: str = "fresh",
    canonical_key: str = "self-review-outcome:review-pressure:workspace-search",
) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_self_review_outcome(
        outcome_id=f"self-review-outcome-{uuid4().hex}",
        outcome_type="watch-closely",
        canonical_key=canonical_key,
        status=status,
        title="Self-review outcome: workspace search",
        summary="Bounded self-review suggests this thread should be watched closely.",
        rationale="Validation self-review outcome support",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="self-review outcome evidence",
        support_summary="Derived from bounded self-review chain.",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation bounded self-review outcome.",
        review_run_id="test-review-run",
        session_id="test-session",
    )


def _insert_self_review_cadence_signal(
    db,
    *,
    run_id: str,
    status: str = "active",
    canonical_key: str = "self-review-cadence:self-review:workspace-search",
) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_self_review_cadence_signal(
        signal_id=f"self-review-cadence-{uuid4().hex}",
        signal_type="review-cadence",
        canonical_key=canonical_key,
        status=status,
        title="Self-review cadence: workspace search",
        summary="This bounded self-review thread now looks due for re-checking.",
        rationale="Validation self-review cadence support",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="self-review cadence evidence",
        support_summary="Derived from bounded self-review outcomes and timing.",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation bounded self-review cadence support.",
        run_id=run_id,
        session_id="test-session",
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
        evidence_summary="private-state evidence",
        support_summary="Derived only from active bounded inner-layer runtime support signals.",
        status_reason="Validation bounded private-state snapshot.",
        run_id=run_id,
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def _insert_private_temporal_promotion_signal(db, *, run_id: str, status: str = "active") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_private_temporal_promotion_signal(
        signal_id=f"private-temporal-promotion-signal-{uuid4().hex}",
        signal_type="private-temporal-promotion",
        canonical_key="private-temporal-promotion:carry-forward:workspace-search",
        status=status,
        title="Private temporal promotion support: workspace search",
        summary="Bounded runtime temporal promotion is carrying a small maturation pull around workspace search.",
        rationale="Validation temporal promotion runtime support",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="temporal promotion evidence",
        support_summary="Derived only from bounded temporal-curiosity and private-state runtime support.",
        status_reason="Validation bounded temporal promotion support.",
        run_id=run_id,
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def _insert_chronicle_consolidation_signal(db, *, status: str, canonical_key: str, title: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_chronicle_consolidation_signal(
        signal_id=f"chronicle-consolidation-signal-{uuid4().hex}",
        signal_type="chronicle-consolidation",
        canonical_key=canonical_key,
        status=status,
        title=title,
        summary="Bounded chronicle/consolidation support is marking a small carry-forward thread.",
        rationale="Validation chronicle/consolidation runtime layer",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="chronicle consolidation evidence",
        support_summary="Derived only from bounded self-review outcome/cadence and optional state/promotion support.",
        status_reason="Validation bounded chronicle/consolidation support with no canonical-file writeback.",
        run_id="test-run",
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def test_chronicle_consolidation_stays_empty_without_self_review_grounding(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.chronicle_consolidation_signal_tracking
    db = isolated_runtime.db

    _insert_private_state_snapshot(db, run_id="visible-run-1")

    result = tracking.track_runtime_chronicle_consolidation_signals_for_visible_turn(
        session_id="test-session",
        run_id="visible-run-1",
    )
    surface = tracking.build_runtime_chronicle_consolidation_signal_surface(limit=8)

    assert result["created"] == 0
    assert result["updated"] == 0
    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["summary"]["active_count"] == 0
    assert surface["summary"]["authority"] == "non-authoritative"


def test_chronicle_consolidation_forms_bounded_runtime_support_from_review_and_cadence(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.chronicle_consolidation_signal_tracking
    db = isolated_runtime.db

    _insert_self_review_outcome(db)
    _insert_self_review_cadence_signal(db, run_id="visible-run-2")
    _insert_private_state_snapshot(db, run_id="visible-run-2")
    _insert_private_temporal_promotion_signal(db, run_id="visible-run-2")

    result = tracking.track_runtime_chronicle_consolidation_signals_for_visible_turn(
        session_id="test-session",
        run_id="visible-run-2",
    )
    surface = tracking.build_runtime_chronicle_consolidation_signal_surface(limit=8)
    item = surface["items"][0]

    assert result["created"] == 1
    assert surface["active"] is True
    assert item["signal_type"] == "chronicle-consolidation"
    assert item["chronicle_type"] in {
        "chronicle-worthy",
        "consolidation-worthy",
        "carry-forward-thread",
        "anchored-thread",
    }
    assert item["chronicle_weight"] in {"medium", "high"}
    assert item["authority"] == "non-authoritative"
    assert item["layer_role"] == "runtime-support"
    assert item["writeback_state"] == "not-writing-to-canonical-files"
    assert "not yet writing to chronicle or memory files" in item["status_reason"].lower()
    assert item["source_anchor"]


def test_chronicle_consolidation_surface_and_mc_shapes_remain_bounded(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.chronicle_consolidation_signal_tracking
    mission_control = isolated_runtime.mission_control

    _insert_chronicle_consolidation_signal(
        db,
        status="active",
        canonical_key="chronicle-consolidation:consolidation-worthy:workspace-search",
        title="Chronicle consolidation support: workspace search",
    )
    _insert_chronicle_consolidation_signal(
        db,
        status="softening",
        canonical_key="chronicle-consolidation:carry-forward-thread:visible-work",
        title="Chronicle consolidation support: visible work",
    )
    _insert_chronicle_consolidation_signal(
        db,
        status="superseded",
        canonical_key="chronicle-consolidation:chronicle-worthy:archive-focus",
        title="Chronicle consolidation support: archive focus",
    )

    surface = tracking.build_runtime_chronicle_consolidation_signal_surface(limit=8)
    jarvis = mission_control.mc_jarvis()
    runtime = mission_control.mc_runtime()
    mc_shape = jarvis["development"]["chronicle_consolidation_signals"]
    runtime_shape = runtime["runtime_chronicle_consolidation_signals"]

    assert {
        "active_count",
        "softening_count",
        "stale_count",
        "superseded_count",
        "current_signal",
        "current_status",
        "current_chronicle_type",
        "current_weight",
        "current_confidence",
        "authority",
        "layer_role",
        "writeback_state",
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
        "chronicle_type",
        "chronicle_focus",
        "chronicle_weight",
        "chronicle_summary",
        "chronicle_confidence",
        "source_anchor",
        "grounding_mode",
        "writeback_state",
        "authority",
        "layer_role",
    }.issubset(surface["items"][0].keys())
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["softening_count"] == 1
    assert surface["summary"]["superseded_count"] == 1
    assert mc_shape["summary"]["authority"] == "non-authoritative"
    assert runtime_shape["summary"]["writeback_state"] == "not-writing-to-canonical-files"
