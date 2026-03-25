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
        title="Sharpen Danish and concise reply calibration",
        summary="Sharpen Danish and concise reply calibration",
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


def _insert_critic(db, *, canonical_key: str, status: str = "active", minutes_ago: int = 0) -> None:
    ts = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    db.upsert_runtime_reflective_critic(
        critic_id=f"critic-{uuid4().hex}",
        critic_type="development-focus-mismatch",
        canonical_key=canonical_key,
        status=status,
        title="Active focus is not landing yet: Sharpen Danish and concise reply calibration",
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


def _insert_reflection(db, *, canonical_key: str, status: str, signal_type: str, minutes_ago: int = 0) -> None:
    ts = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    title = (
        "Persistent reflection tension: Danish concise calibration"
        if signal_type == "persistent-tension"
        else "Slow integration thread: Danish concise calibration"
        if signal_type == "slow-integration"
        else "Settled reflection thread: Danish concise calibration"
    )
    db.upsert_runtime_reflection_signal(
        signal_id=f"reflection-{uuid4().hex}",
        signal_type=signal_type,
        canonical_key=canonical_key,
        status=status,
        title=title,
        summary=title,
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


def test_temporal_recurrence_surface_stays_empty_without_relevant_repetition(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.temporal_recurrence_tracking

    _insert_focus(
        db,
        canonical_key="development-focus:communication:danish-concise-calibration",
        status="active",
    )

    tracking.track_runtime_temporal_recurrence_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_temporal_recurrence_signal_surface(limit=8)

    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["summary"]["active_count"] == 0
    assert surface["summary"]["softening_count"] == 0


def test_temporal_recurrence_surface_forms_recurring_tension_for_repeated_active_domain(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.temporal_recurrence_tracking

    _insert_focus(
        db,
        canonical_key="development-focus:communication:danish-concise-calibration",
        status="active",
        minutes_ago=30,
    )
    _insert_critic(
        db,
        canonical_key="reflective-critic:mismatch:development-focus:communication:danish-concise-calibration",
        status="active",
        minutes_ago=20,
    )
    _insert_reflection(
        db,
        canonical_key="reflection-signal:slow-integration:danish-concise-calibration",
        status="integrating",
        signal_type="slow-integration",
        minutes_ago=10,
    )

    tracking.track_runtime_temporal_recurrence_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_temporal_recurrence_signal_surface(limit=8)

    assert surface["active"] is True
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["current_status"] == "active"
    assert "Recurring tension: Danish concise calibration" == surface["summary"]["current_signal"]

    signal = surface["items"][0]
    assert signal["signal_type"] == "recurring-tension"
    assert signal["status"] == "active"
    assert signal["canonical_key"] == "temporal-recurrence:recurring-tension:danish-concise-calibration"


def test_temporal_recurrence_surface_forms_recurring_direction_for_softening_domain(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.temporal_recurrence_tracking

    _insert_focus(
        db,
        canonical_key="development-focus:communication:danish-concise-calibration",
        status="active",
        minutes_ago=30,
    )
    _insert_goal(
        db,
        canonical_key="goal-signal:danish-concise-calibration",
        status="completed",
        minutes_ago=20,
    )
    _insert_reflection(
        db,
        canonical_key="reflection-signal:settled-thread:danish-concise-calibration",
        status="settled",
        signal_type="settled-thread",
        minutes_ago=10,
    )

    tracking.track_runtime_temporal_recurrence_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_temporal_recurrence_signal_surface(limit=8)

    assert surface["active"] is True
    assert surface["summary"]["active_count"] == 0
    assert surface["summary"]["softening_count"] == 1
    assert surface["summary"]["current_status"] == "softening"
    assert surface["items"][0]["signal_type"] == "recurring-direction"
    assert surface["items"][0]["status"] == "softening"


def test_temporal_recurrence_surface_and_mc_shape_remain_bounded(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.temporal_recurrence_tracking
    mission_control = isolated_runtime.mission_control

    _insert_focus(
        db,
        canonical_key="development-focus:communication:danish-concise-calibration",
        status="active",
        minutes_ago=30,
    )
    _insert_critic(
        db,
        canonical_key="reflective-critic:mismatch:development-focus:communication:danish-concise-calibration",
        status="active",
        minutes_ago=20,
    )
    _insert_reflection(
        db,
        canonical_key="reflection-signal:slow-integration:danish-concise-calibration",
        status="integrating",
        signal_type="slow-integration",
        minutes_ago=10,
    )

    tracking.track_runtime_temporal_recurrence_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_temporal_recurrence_signal_surface(limit=8)
    jarvis = mission_control.mc_jarvis()
    mc_shape = jarvis["development"]["temporal_recurrence_signals"]

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
    assert mc_shape["summary"]["current_status"] in {"active", "softening"}
    assert len(mc_shape["items"]) == 1
