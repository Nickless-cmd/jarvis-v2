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


def _insert_open_loop(
    db,
    *,
    status: str,
    signal_type: str,
    canonical_key: str,
    closure_readiness: str = "low",
    closure_confidence: str = "low",
    closure_reason: str = "Validation closure reason",
) -> None:
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
        status_reason=closure_reason,
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


def _insert_witness(db, *, status: str, signal_type: str, canonical_key: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_witness_signal(
        signal_id=f"witness-{uuid4().hex}",
        signal_type=signal_type,
        canonical_key=canonical_key,
        status=status,
        title=f"Witness row: {signal_type}",
        summary=f"Witness summary: {signal_type}",
        rationale="Validation witness",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="witness evidence",
        support_summary="witness support",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation witness status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_self_review_signal(db, *, status: str, signal_type: str, canonical_key: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_self_review_signal(
        signal_id=f"self-review-{uuid4().hex}",
        signal_type=signal_type,
        canonical_key=canonical_key,
        status=status,
        title=f"Self review row: {signal_type}",
        summary=f"Self review summary: {signal_type}",
        rationale="Validation self review",
        source_kind="runtime-derived-support",
        confidence="high",
        evidence_summary="self review evidence",
        support_summary="self review support",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation self review status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_self_review_record(db, *, status: str, record_type: str, canonical_key: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_self_review_record(
        record_id=f"self-review-record-{uuid4().hex}",
        record_type=record_type,
        canonical_key=canonical_key,
        status=status,
        title=f"Self review brief: {record_type}",
        summary=f"Self review brief summary: {record_type}",
        rationale="Validation self review brief",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="self review brief evidence",
        support_summary="self review brief support",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation self review brief status",
        run_id="test-run",
        session_id="test-session",
    )


def test_self_review_record_surface_stays_empty_without_signal_or_domain_grounding(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.self_review_record_tracking

    _insert_focus(
        db,
        canonical_key="development-focus:communication:danish-concise-calibration",
        minutes_ago=5,
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

    tracking.track_runtime_self_review_records_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_self_review_record_surface(limit=8)

    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["summary"]["fresh_count"] == 0
    assert surface["summary"]["active_count"] == 0


def test_self_review_record_surface_requires_domain_grounding_even_when_signal_exists(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.self_review_record_tracking

    _insert_self_review_signal(
        db,
        status="active",
        signal_type="review-pressure",
        canonical_key="self-review:review-pressure:danish-concise-calibration",
    )

    tracking.track_runtime_self_review_records_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_self_review_record_surface(limit=8)

    assert surface["active"] is False
    assert surface["items"] == []


def test_self_review_record_surface_forms_fresh_brief_for_active_self_review_signal(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.self_review_record_tracking

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
        closure_reason="blocked-goal pressure still visible",
    )
    _insert_internal_opposition(
        db,
        status="active",
        signal_type="challenge-direction",
        canonical_key="internal-opposition:challenge-direction:danish-concise-calibration",
    )
    _insert_self_review_signal(
        db,
        status="active",
        signal_type="review-pressure",
        canonical_key="self-review:review-pressure:danish-concise-calibration",
    )

    tracking.track_runtime_self_review_records_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_self_review_record_surface(limit=8)
    item = surface["items"][0]

    assert surface["active"] is True
    assert surface["summary"]["fresh_count"] == 1
    assert surface["summary"]["current_status"] == "fresh"
    assert item["record_type"] == "review-pressure"
    assert item["status"] == "fresh"
    assert item["review_type"] == "review-pressure"
    assert item["domain"] == "danish-concise-calibration"
    assert item["open_loop_status"] == "open"
    assert item["opposition_status"] == "active"
    assert item["closure_readiness"] == "low"
    assert item["closure_confidence"] == "low"
    assert "blocked-goal pressure" in item["short_reason"]
    assert item["canonical_key"] == "self-review-record:review-pressure:danish-concise-calibration"


def test_self_review_record_surface_forms_fading_brief_for_softening_signal(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.self_review_record_tracking

    _insert_focus(
        db,
        canonical_key="development-focus:communication:danish-concise-calibration",
        minutes_ago=20,
    )
    _insert_witness(
        db,
        status="carried",
        signal_type="carried-lesson",
        canonical_key="witness-signal:carried-lesson:danish-concise-calibration",
    )
    _insert_open_loop(
        db,
        status="softening",
        signal_type="softening-loop",
        canonical_key="open-loop:softening-loop:danish-concise-calibration",
        closure_reason="softening recurrence still visible",
    )
    _insert_self_review_signal(
        db,
        status="softening",
        signal_type="review-carried-thread",
        canonical_key="self-review:review-carried-thread:danish-concise-calibration",
    )

    tracking.track_runtime_self_review_records_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_self_review_record_surface(limit=8)

    assert surface["active"] is True
    assert surface["summary"]["fresh_count"] == 0
    assert surface["summary"]["fading_count"] == 1
    assert surface["items"][0]["record_type"] == "review-carried-thread"
    assert surface["items"][0]["status"] == "fading"
    assert surface["items"][0]["open_loop_status"] == "softening"
    assert surface["items"][0]["opposition_status"] == "none"


def test_self_review_record_surface_and_mc_shapes_remain_bounded(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.self_review_record_tracking
    mission_control = isolated_runtime.mission_control

    _insert_self_review_record(
        db,
        status="fresh",
        record_type="review-pressure",
        canonical_key="self-review-record:review-pressure:danish-concise-calibration",
    )
    _insert_self_review_record(
        db,
        status="active",
        record_type="review-due-by-recurrence",
        canonical_key="self-review-record:review-due-by-recurrence:workspace-boundary",
    )
    _insert_self_review_record(
        db,
        status="fading",
        record_type="review-carried-thread",
        canonical_key="self-review-record:review-carried-thread:carried-thread",
    )
    _insert_self_review_record(
        db,
        status="stale",
        record_type="review-pressure",
        canonical_key="self-review-record:review-pressure:older-thread",
    )
    _insert_self_review_record(
        db,
        status="superseded",
        record_type="review-pressure",
        canonical_key="self-review-record:review-pressure:oldest-thread",
    )

    surface = tracking.build_runtime_self_review_record_surface(limit=8)
    jarvis = mission_control.mc_jarvis()
    runtime = mission_control.mc_runtime()
    mc_shape = jarvis["development"]["self_review_records"]
    runtime_shape = runtime["runtime_self_review_records"]

    assert {
        "fresh_count",
        "active_count",
        "fading_count",
        "stale_count",
        "superseded_count",
        "current_record",
        "current_status",
        "current_review_type",
    }.issubset(surface["summary"].keys())
    assert {
        "record_id",
        "record_type",
        "canonical_key",
        "status",
        "title",
        "summary",
        "confidence",
        "updated_at",
        "review_type",
        "domain",
        "open_loop_status",
        "opposition_status",
        "closure_readiness",
        "closure_confidence",
        "short_reason",
    }.issubset(surface["items"][0].keys())
    assert surface["summary"]["fresh_count"] == 1
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["fading_count"] == 1
    assert surface["summary"]["stale_count"] == 1
    assert surface["summary"]["superseded_count"] == 1
    assert mc_shape["summary"]["current_status"] in {"fresh", "active", "fading", "stale"}
    assert runtime_shape["summary"]["current_status"] in {"fresh", "active", "fading", "stale"}
