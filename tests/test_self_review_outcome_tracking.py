from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4


def _insert_focus(db, *, canonical_key: str, status: str = "active", minutes_ago: int = 0) -> None:
    ts = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    db.upsert_runtime_development_focus(
        focus_id=f"focus-{uuid4().hex}",
        focus_type="communication-calibration",
        canonical_key=canonical_key,
        status=status,
        title="Development focus: Danish concise calibration",
        summary="Active focus for Danish concise calibration",
        rationale="Validation focus",
        source_kind="repeated-user-correction",
        confidence="high",
        evidence_summary="focus evidence",
        support_summary="focus support",
        support_count=2,
        session_count=1,
        created_at=ts.isoformat(),
        updated_at=ts.isoformat(),
        status_reason="Validation focus status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_goal(db, *, canonical_key: str, status: str, minutes_ago: int = 0) -> None:
    ts = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    db.upsert_runtime_goal_signal(
        goal_id=f"goal-{uuid4().hex}",
        goal_type="development-direction",
        canonical_key=canonical_key,
        status=status,
        title="Current direction: Danish concise calibration",
        summary="Current direction: Danish concise calibration",
        rationale="Validation goal",
        source_kind="critic-backed" if status == "blocked" else "focus-derived",
        confidence="high",
        evidence_summary="goal evidence",
        support_summary="goal support",
        support_count=2,
        session_count=1,
        created_at=ts.isoformat(),
        updated_at=ts.isoformat(),
        status_reason="Validation goal status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_open_loop(db, *, status: str, signal_type: str, canonical_key: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_open_loop_signal(
        signal_id=f"open-loop-{uuid4().hex}",
        signal_type=signal_type,
        canonical_key=canonical_key,
        status=status,
        title=f"Open loop row: {signal_type}",
        summary=f"Open loop summary: {signal_type}",
        rationale="Validation open loop",
        source_kind="derived-runtime-open-loop",
        confidence="medium",
        evidence_summary="open loop evidence",
        support_summary="open loop support",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation open loop status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_internal_opposition(db, *, status: str, signal_type: str, canonical_key: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_internal_opposition_signal(
        signal_id=f"internal-opposition-{uuid4().hex}",
        signal_type=signal_type,
        canonical_key=canonical_key,
        status=status,
        title=f"Internal opposition row: {signal_type}",
        summary=f"Internal opposition summary: {signal_type}",
        rationale="Validation internal opposition",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="internal opposition evidence",
        support_summary="internal opposition support",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation internal opposition status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_self_review_run(db, *, status: str, run_type: str, canonical_key: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_self_review_run(
        run_id=f"self-review-run-{uuid4().hex}",
        run_type=run_type,
        canonical_key=canonical_key,
        status=status,
        title=f"Self-review snapshot: {run_type}",
        summary=f"Review summary: {run_type}",
        rationale="Validation self review run",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="self review run evidence",
        support_summary="self review run support",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation self review run status",
        record_run_id="test-run",
        session_id="test-session",
    )


def _insert_self_review_outcome(db, *, status: str, outcome_type: str, canonical_key: str) -> None:
    now = datetime.now(UTC).isoformat()
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
        created_at=now,
        updated_at=now,
        status_reason="Validation self review outcome status",
        review_run_id="test-run",
        session_id="test-session",
    )


def test_self_review_outcome_surface_stays_empty_without_relevant_review_run(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.self_review_outcome_tracking

    _insert_focus(
        db,
        canonical_key="development-focus:communication:danish-concise-calibration",
        minutes_ago=10,
    )
    _insert_open_loop(
        db,
        status="open",
        signal_type="persistent-open-loop",
        canonical_key="open-loop:persistent-open-loop:danish-concise-calibration",
    )
    _insert_internal_opposition(
        db,
        status="active",
        signal_type="challenge-direction",
        canonical_key="internal-opposition:challenge-direction:danish-concise-calibration",
    )

    result = tracking.track_runtime_self_review_outcomes_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_self_review_outcome_surface(limit=8)

    assert result["created"] == 0
    assert result["updated"] == 0
    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["summary"]["fresh_count"] == 0
    assert surface["summary"]["active_count"] == 0
    assert surface["summary"]["fading_count"] == 0


def test_self_review_outcome_surface_forms_bounded_judgment_for_active_review_run(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.self_review_outcome_tracking

    _insert_focus(
        db,
        canonical_key="development-focus:communication:danish-concise-calibration",
        minutes_ago=30,
    )
    _insert_goal(
        db,
        canonical_key="goal-signal:danish-concise-calibration",
        status="blocked",
        minutes_ago=20,
    )
    _insert_open_loop(
        db,
        status="open",
        signal_type="persistent-open-loop",
        canonical_key="open-loop:persistent-open-loop:danish-concise-calibration",
    )
    _insert_internal_opposition(
        db,
        status="active",
        signal_type="challenge-direction",
        canonical_key="internal-opposition:challenge-direction:danish-concise-calibration",
    )
    _insert_self_review_run(
        db,
        status="active",
        run_type="review-pressure",
        canonical_key="self-review-run:review-pressure:danish-concise-calibration",
    )

    result = tracking.track_runtime_self_review_outcomes_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_self_review_outcome_surface(limit=8)
    item = surface["items"][0]

    assert result["created"] == 1
    assert result["updated"] == 1
    assert surface["active"] is True
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["current_status"] == "active"
    assert surface["summary"]["current_outcome_type"] == "challenge-further"
    assert surface["summary"]["current_review_focus"] == "open-loop pressure + active opposition + blocked direction"
    assert item["outcome_type"] == "challenge-further"
    assert item["status"] == "active"
    assert item["review_type"] == "review-pressure"
    assert item["review_focus"] == "open-loop pressure + active opposition + blocked direction"
    assert item["domain"] == "danish-concise-calibration"
    assert item["closure_confidence"] == "low"
    assert item["short_outcome"] == "The review still points toward further challenge before this thread should settle."
    assert item["canonical_key"] == "self-review-outcome:review-pressure:danish-concise-calibration"


def test_self_review_outcome_surface_and_mc_shapes_remain_bounded(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.self_review_outcome_tracking
    mission_control = isolated_runtime.mission_control

    _insert_self_review_outcome(
        db,
        status="fresh",
        outcome_type="watch-closely",
        canonical_key="self-review-outcome:review-pressure:danish-concise-calibration",
    )
    _insert_self_review_outcome(
        db,
        status="active",
        outcome_type="challenge-further",
        canonical_key="self-review-outcome:review-due-by-recurrence:workspace-boundary",
    )
    _insert_self_review_outcome(
        db,
        status="fading",
        outcome_type="carry-forward",
        canonical_key="self-review-outcome:review-carried-thread:carried-thread",
    )
    _insert_self_review_outcome(
        db,
        status="stale",
        outcome_type="nearing-closure",
        canonical_key="self-review-outcome:review-pressure:older-thread",
    )
    _insert_self_review_outcome(
        db,
        status="superseded",
        outcome_type="watch-closely",
        canonical_key="self-review-outcome:review-pressure:oldest-thread",
    )

    surface = tracking.build_runtime_self_review_outcome_surface(limit=8)
    jarvis = mission_control.mc_jarvis()
    runtime = mission_control.mc_runtime()
    mc_shape = jarvis["development"]["self_review_outcomes"]
    runtime_shape = runtime["runtime_self_review_outcomes"]

    assert {
        "fresh_count",
        "active_count",
        "fading_count",
        "stale_count",
        "superseded_count",
        "current_outcome",
        "current_status",
        "current_outcome_type",
        "current_review_focus",
    }.issubset(surface["summary"].keys())
    assert {
        "outcome_id",
        "outcome_type",
        "canonical_key",
        "status",
        "title",
        "summary",
        "confidence",
        "updated_at",
        "review_type",
        "review_focus",
        "domain",
        "closure_confidence",
        "short_outcome",
    }.issubset(surface["items"][0].keys())
    assert surface["summary"]["fresh_count"] == 1
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["fading_count"] == 1
    assert surface["summary"]["stale_count"] == 1
    assert surface["summary"]["superseded_count"] == 1
    assert mc_shape["summary"]["current_status"] in {"fresh", "active", "fading", "stale"}
    assert runtime_shape["summary"]["current_status"] in {"fresh", "active", "fading", "stale"}
