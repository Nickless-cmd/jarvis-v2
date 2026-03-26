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


def _insert_goal(db, *, canonical_key: str, status: str = "completed", minutes_ago: int = 0) -> None:
    ts = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    db.upsert_runtime_goal_signal(
        goal_id=f"goal-{uuid4().hex}",
        goal_type="development-direction",
        canonical_key=canonical_key,
        status=status,
        title="Current direction: Danish concise calibration",
        summary="Current direction: Danish concise calibration",
        rationale="Validation goal",
        source_kind="focus-derived",
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


def _insert_reflection(db, *, canonical_key: str, status: str = "settled", minutes_ago: int = 0) -> None:
    ts = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    db.upsert_runtime_reflection_signal(
        signal_id=f"reflection-{uuid4().hex}",
        signal_type="settled-thread",
        canonical_key=canonical_key,
        status=status,
        title="Settled reflection thread: Danish concise calibration",
        summary="Settled reflection thread: Danish concise calibration",
        rationale="Validation reflection",
        source_kind="multi-signal-runtime-derivation",
        confidence="high",
        evidence_summary="reflection evidence",
        support_summary="reflection support",
        support_count=3,
        session_count=2,
        created_at=ts.isoformat(),
        updated_at=ts.isoformat(),
        status_reason="Validation reflection status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_temporal_recurrence(db, *, canonical_key: str, status: str = "softening", minutes_ago: int = 0) -> None:
    ts = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    db.upsert_runtime_temporal_recurrence_signal(
        signal_id=f"recurrence-{uuid4().hex}",
        signal_type="recurring-direction",
        canonical_key=canonical_key,
        status=status,
        title="Recurring direction: Danish concise calibration",
        summary="Recurring direction: Danish concise calibration",
        rationale="Validation temporal recurrence",
        source_kind="multi-signal-runtime-derivation",
        confidence="high",
        evidence_summary="recurrence evidence",
        support_summary="recurrence support",
        support_count=3,
        session_count=1,
        created_at=ts.isoformat(),
        updated_at=ts.isoformat(),
        status_reason="Validation temporal recurrence status",
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
        source_kind="derived-runtime-witness",
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


def test_witness_surface_stays_empty_without_relevant_transition(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.witness_tracking

    _insert_reflection(
        db,
        canonical_key="reflection-signal:settled-thread:danish-concise-calibration",
        minutes_ago=10,
    )
    _insert_focus(
        db,
        canonical_key="development-focus:communication:danish-concise-calibration",
        minutes_ago=5,
    )

    tracking.track_runtime_witness_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_witness_signal_surface(limit=6)

    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["summary"]["fresh_count"] == 0
    assert surface["summary"]["carried_count"] == 0


def test_witness_surface_forms_carried_lesson_when_transition_is_still_being_carried(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.witness_tracking

    _insert_temporal_recurrence(
        db,
        canonical_key="temporal-recurrence:recurring-direction:danish-concise-calibration",
        minutes_ago=30,
    )
    _insert_reflection(
        db,
        canonical_key="reflection-signal:settled-thread:danish-concise-calibration",
        minutes_ago=20,
    )
    _insert_focus(
        db,
        canonical_key="development-focus:communication:danish-concise-calibration",
        minutes_ago=10,
    )

    tracking.track_runtime_witness_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_witness_signal_surface(limit=6)

    assert surface["active"] is True
    assert surface["summary"]["fresh_count"] == 1
    assert surface["summary"]["current_status"] == "fresh"
    assert surface["items"][0]["signal_type"] == "carried-lesson"
    assert surface["items"][0]["status"] == "fresh"
    assert surface["items"][0]["canonical_key"] == "witness-signal:carried-lesson:danish-concise-calibration"


def test_witness_surface_forms_witnessed_turn_without_continued_carrying(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.witness_tracking

    _insert_temporal_recurrence(
        db,
        canonical_key="temporal-recurrence:recurring-direction:danish-concise-calibration",
        minutes_ago=30,
    )
    _insert_reflection(
        db,
        canonical_key="reflection-signal:settled-thread:danish-concise-calibration",
        minutes_ago=20,
    )

    tracking.track_runtime_witness_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_witness_signal_surface(limit=6)

    assert surface["active"] is True
    assert surface["summary"]["fresh_count"] == 1
    assert surface["items"][0]["signal_type"] == "settled-turn"
    assert surface["items"][0]["status"] == "fresh"
    assert surface["items"][0]["canonical_key"] == "witness-signal:settled-turn:danish-concise-calibration"


def test_witness_surface_and_mc_shape_remain_bounded(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.witness_tracking
    mission_control = isolated_runtime.mission_control

    _insert_witness(
        db,
        status="fresh",
        signal_type="carried-lesson",
        canonical_key="witness-signal:carried-lesson:danish-concise-calibration",
    )
    _insert_witness(
        db,
        status="carried",
        signal_type="carried-lesson",
        canonical_key="witness-signal:carried-lesson:workspace-boundary",
    )
    _insert_witness(
        db,
        status="fading",
        signal_type="settled-turn",
        canonical_key="witness-signal:settled-turn:runtime-lane",
    )
    _insert_witness(
        db,
        status="superseded",
        signal_type="settled-turn",
        canonical_key="witness-signal:settled-turn:older-turn",
    )

    surface = tracking.build_runtime_witness_signal_surface(limit=6)
    jarvis = mission_control.mc_jarvis()
    runtime = mission_control.mc_runtime()
    mc_shape = jarvis["development"]["witness_signals"]
    runtime_shape = runtime["runtime_witness_signals"]

    assert {
        "fresh_count",
        "carried_count",
        "fading_count",
        "superseded_count",
        "current_signal",
        "current_status",
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
    }.issubset(surface["items"][0].keys())
    assert surface["summary"]["fresh_count"] == 1
    assert surface["summary"]["carried_count"] == 1
    assert surface["summary"]["fading_count"] == 1
    assert surface["summary"]["superseded_count"] == 1
    assert mc_shape["summary"]["current_status"] in {"fresh", "carried"}
    assert runtime_shape["summary"]["current_status"] in {"fresh", "carried"}
