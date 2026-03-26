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


def _insert_critic(db, *, canonical_key: str, status: str, minutes_ago: int = 0) -> None:
    ts = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    db.upsert_runtime_reflective_critic(
        critic_id=f"critic-{uuid4().hex}",
        critic_type="development-focus-mismatch",
        canonical_key=canonical_key,
        status=status,
        title="Active focus is not landing yet: Danish concise calibration",
        summary="Repeated correction still conflicts with the active focus.",
        rationale="Validation critic",
        source_kind="focus-mismatch",
        confidence="high",
        evidence_summary="critic evidence",
        support_summary="critic support",
        support_count=2,
        session_count=1,
        created_at=ts.isoformat(),
        updated_at=ts.isoformat(),
        status_reason="Validation critic status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_temporal_recurrence(db, *, canonical_key: str, status: str, signal_type: str, minutes_ago: int = 0) -> None:
    ts = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    title = (
        "Recurring tension: Danish concise calibration"
        if signal_type == "recurring-tension"
        else "Recurring direction: Danish concise calibration"
    )
    db.upsert_runtime_temporal_recurrence_signal(
        signal_id=f"recurrence-{uuid4().hex}",
        signal_type=signal_type,
        canonical_key=canonical_key,
        status=status,
        title=title,
        summary=title,
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


def _insert_self_review(db, *, status: str, signal_type: str, canonical_key: str) -> None:
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
        confidence="medium",
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


def test_self_review_surface_stays_empty_without_review_worthy_composition(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.self_review_tracking

    _insert_focus(
        db,
        canonical_key="development-focus:communication:danish-concise-calibration",
        minutes_ago=5,
    )

    tracking.track_runtime_self_review_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_self_review_signal_surface(limit=8)

    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["summary"]["active_count"] == 0
    assert surface["summary"]["softening_count"] == 0


def test_self_review_surface_forms_review_pressure_for_live_loop_and_opposition(isolated_runtime) -> None:
    db = isolated_runtime.db
    open_loop_tracking = isolated_runtime.open_loop_tracking
    internal_opposition_tracking = isolated_runtime.internal_opposition_tracking
    tracking = isolated_runtime.self_review_tracking

    _insert_focus(
        db,
        canonical_key="development-focus:communication:danish-concise-calibration",
        minutes_ago=30,
    )
    _insert_critic(
        db,
        canonical_key="reflective-critic:mismatch:development-focus:communication:danish-concise-calibration",
        status="active",
        minutes_ago=20,
    )
    _insert_goal(
        db,
        canonical_key="goal-signal:danish-concise-calibration",
        status="blocked",
        minutes_ago=15,
    )
    _insert_temporal_recurrence(
        db,
        canonical_key="temporal-recurrence:recurring-tension:danish-concise-calibration",
        status="active",
        signal_type="recurring-tension",
        minutes_ago=10,
    )

    open_loop_tracking.track_runtime_open_loop_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    internal_opposition_tracking.track_runtime_internal_opposition_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    tracking.track_runtime_self_review_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_self_review_signal_surface(limit=8)

    assert surface["active"] is True
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["current_status"] == "active"
    assert surface["items"][0]["signal_type"] == "review-pressure"
    assert surface["items"][0]["status"] == "active"
    assert surface["items"][0]["canonical_key"] == "self-review:review-pressure:danish-concise-calibration"


def test_self_review_surface_forms_review_due_by_recurrence_for_returning_unresolved_thread(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.self_review_tracking

    _insert_goal(
        db,
        canonical_key="goal-signal:danish-concise-calibration",
        status="active",
        minutes_ago=20,
    )
    _insert_temporal_recurrence(
        db,
        canonical_key="temporal-recurrence:recurring-tension:danish-concise-calibration",
        status="active",
        signal_type="recurring-tension",
        minutes_ago=10,
    )
    _insert_internal_opposition(
        db,
        status="active",
        signal_type="challenge-direction",
        canonical_key="internal-opposition:challenge-direction:danish-concise-calibration",
    )

    tracking.track_runtime_self_review_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_self_review_signal_surface(limit=8)

    assert surface["active"] is True
    assert surface["summary"]["active_count"] == 1
    assert surface["items"][0]["signal_type"] == "review-due-by-recurrence"
    assert surface["items"][0]["status"] == "active"
    assert surface["items"][0]["canonical_key"] == "self-review:review-due-by-recurrence:danish-concise-calibration"


def test_self_review_surface_forms_review_carried_thread_for_softening_carried_domain(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.self_review_tracking

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
    )

    tracking.track_runtime_self_review_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_self_review_signal_surface(limit=8)

    assert surface["active"] is True
    assert surface["summary"]["active_count"] == 0
    assert surface["summary"]["softening_count"] == 1
    assert surface["items"][0]["signal_type"] == "review-carried-thread"
    assert surface["items"][0]["status"] == "softening"
    assert surface["items"][0]["canonical_key"] == "self-review:review-carried-thread:danish-concise-calibration"


def test_self_review_surface_and_mc_shapes_remain_bounded(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.self_review_tracking
    mission_control = isolated_runtime.mission_control

    _insert_self_review(
        db,
        status="active",
        signal_type="review-pressure",
        canonical_key="self-review:review-pressure:danish-concise-calibration",
    )
    _insert_self_review(
        db,
        status="softening",
        signal_type="review-carried-thread",
        canonical_key="self-review:review-carried-thread:workspace-boundary",
    )
    _insert_self_review(
        db,
        status="stale",
        signal_type="review-due-by-recurrence",
        canonical_key="self-review:review-due-by-recurrence:recurring-thread",
    )
    _insert_self_review(
        db,
        status="superseded",
        signal_type="review-pressure",
        canonical_key="self-review:review-pressure:older-thread",
    )

    surface = tracking.build_runtime_self_review_signal_surface(limit=8)
    jarvis = mission_control.mc_jarvis()
    runtime = mission_control.mc_runtime()
    mc_shape = jarvis["development"]["self_review_signals"]
    runtime_shape = runtime["runtime_self_review_signals"]

    assert {
        "active_count",
        "softening_count",
        "stale_count",
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
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["softening_count"] == 1
    assert surface["summary"]["stale_count"] == 1
    assert surface["summary"]["superseded_count"] == 1
    assert mc_shape["summary"]["current_status"] in {"active", "softening", "stale"}
    assert runtime_shape["summary"]["current_status"] in {"active", "softening", "stale"}
