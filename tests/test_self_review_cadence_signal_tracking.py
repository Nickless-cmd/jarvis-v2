from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4


def _insert_self_review_outcome(
    db,
    *,
    status: str,
    outcome_type: str,
    canonical_key: str,
    days_ago: int = 0,
) -> None:
    ts = datetime.now(UTC) - timedelta(days=days_ago)
    db.upsert_runtime_self_review_outcome(
        outcome_id=f"self-review-outcome-{uuid4().hex}",
        outcome_type=outcome_type,
        canonical_key=canonical_key,
        status=status,
        title=f"Self-review outcome: {outcome_type}",
        summary=f"Outcome summary: {outcome_type}",
        rationale="Validation self review outcome",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="self review outcome evidence",
        support_summary="self review outcome support",
        support_count=2,
        session_count=1,
        created_at=ts.isoformat(),
        updated_at=ts.isoformat(),
        status_reason="Validation self review outcome status",
        review_run_id="test-run",
        session_id="test-session",
    )


def _insert_self_review_cadence_signal(
    db,
    *,
    status: str,
    canonical_key: str,
    summary: str,
) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_self_review_cadence_signal(
        signal_id=f"self-review-cadence-{uuid4().hex}",
        signal_type="review-cadence",
        canonical_key=canonical_key,
        status=status,
        title="Self-review cadence: seeded",
        summary=summary,
        rationale="Validation self review cadence",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="self review cadence evidence",
        support_summary="self review cadence support",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation self review cadence status",
        run_id="test-run",
        session_id="test-session",
    )


def test_self_review_cadence_surface_stays_empty_without_review_outcome(isolated_runtime) -> None:
    tracking = isolated_runtime.self_review_cadence_tracking

    result = tracking.track_runtime_self_review_cadence_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_self_review_cadence_signal_surface(limit=8)

    assert result["created"] == 0
    assert result["updated"] == 0
    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["summary"]["active_count"] == 0
    assert surface["summary"]["softening_count"] == 0


def test_self_review_cadence_surface_forms_bounded_due_states_from_review_freshness(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.self_review_cadence_tracking

    _insert_self_review_outcome(
        db,
        status="active",
        outcome_type="watch-closely",
        canonical_key="self-review-outcome:review-pressure:recent-thread",
        days_ago=0,
    )
    _insert_self_review_outcome(
        db,
        status="active",
        outcome_type="challenge-further",
        canonical_key="self-review-outcome:review-pressure:due-thread",
        days_ago=4,
    )
    _insert_self_review_outcome(
        db,
        status="active",
        outcome_type="carry-forward",
        canonical_key="self-review-outcome:review-pressure:lingering-thread",
        days_ago=10,
    )

    result = tracking.track_runtime_self_review_cadence_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_self_review_cadence_signal_surface(limit=8)
    items_by_domain = {item["domain"]: item for item in surface["items"]}

    assert result["created"] == 3
    assert surface["active"] is True
    assert surface["summary"]["active_count"] == 2
    assert surface["summary"]["softening_count"] == 1
    assert items_by_domain["recent-thread"]["cadence_state"] == "recently-reviewed"
    assert items_by_domain["recent-thread"]["status"] == "softening"
    assert items_by_domain["due-thread"]["cadence_state"] == "due"
    assert items_by_domain["due-thread"]["status"] == "active"
    assert items_by_domain["lingering-thread"]["cadence_state"] == "lingering"
    assert items_by_domain["lingering-thread"]["status"] == "active"


def test_self_review_cadence_surface_and_mc_shapes_remain_bounded(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.self_review_cadence_tracking
    mission_control = isolated_runtime.mission_control

    _insert_self_review_cadence_signal(
        db,
        status="active",
        canonical_key="self-review-cadence:review-pressure:danish-concise-calibration",
        summary="This review-pressure thread now looks due for another bounded review pass.",
    )
    _insert_self_review_cadence_signal(
        db,
        status="softening",
        canonical_key="self-review-cadence:review-due-by-recurrence:workspace-boundary",
        summary="This review-due-by-recurrence thread was reviewed recently and can stay quiet for now.",
    )
    _insert_self_review_cadence_signal(
        db,
        status="stale",
        canonical_key="self-review-cadence:review-carried-thread:carried-thread",
        summary="This review-carried-thread now looks due for another bounded review pass.",
    )
    _insert_self_review_cadence_signal(
        db,
        status="superseded",
        canonical_key="self-review-cadence:review-pressure:older-thread",
        summary="This review-pressure thread has been left too long after review and now looks lingering.",
    )

    surface = tracking.build_runtime_self_review_cadence_signal_surface(limit=8)
    jarvis = mission_control.mc_jarvis()
    runtime = mission_control.mc_runtime()
    mc_shape = jarvis["development"]["self_review_cadence_signals"]
    runtime_shape = runtime["runtime_self_review_cadence_signals"]

    assert {
        "active_count",
        "softening_count",
        "stale_count",
        "superseded_count",
        "current_signal",
        "current_status",
        "current_cadence_state",
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
        "domain",
        "cadence_state",
        "cadence_reason",
        "last_reviewed_at",
        "due_hint",
    }.issubset(surface["items"][0].keys())
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["softening_count"] == 1
    assert surface["summary"]["stale_count"] == 1
    assert surface["summary"]["superseded_count"] == 1
    assert mc_shape["summary"]["current_status"] in {"active", "softening", "stale"}
    assert runtime_shape["summary"]["current_status"] in {"active", "softening", "stale"}
