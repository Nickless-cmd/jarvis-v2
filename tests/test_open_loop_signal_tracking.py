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


def test_open_loop_surface_stays_empty_without_relevant_pressure(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.open_loop_tracking

    _insert_focus(
        db,
        canonical_key="development-focus:communication:danish-concise-calibration",
        minutes_ago=5,
    )

    tracking.track_runtime_open_loop_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_open_loop_signal_surface(limit=8)

    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["summary"]["open_count"] == 0
    assert surface["summary"]["softening_count"] == 0
    assert surface["summary"]["closed_count"] == 0


def test_open_loop_surface_forms_persistent_open_loop_for_clear_repeated_pressure(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.open_loop_tracking

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

    tracking.track_runtime_open_loop_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_open_loop_signal_surface(limit=8)

    assert surface["active"] is True
    assert surface["summary"]["open_count"] == 1
    assert surface["summary"]["current_status"] == "open"
    assert surface["summary"]["current_closure_confidence"] == "low"
    assert surface["items"][0]["signal_type"] == "persistent-open-loop"
    assert surface["items"][0]["status"] == "open"
    assert surface["items"][0]["closure_readiness"] == "low"
    assert surface["items"][0]["closure_confidence"] == "low"
    assert "blocked-goal pressure" in surface["items"][0]["closure_reason"]
    assert surface["items"][0]["canonical_key"] == "open-loop:persistent-open-loop:danish-concise-calibration"


def test_open_loop_surface_forms_softening_loop_for_easing_domain(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.open_loop_tracking

    _insert_focus(
        db,
        canonical_key="development-focus:communication:danish-concise-calibration",
        minutes_ago=30,
    )
    _insert_goal(
        db,
        canonical_key="goal-signal:danish-concise-calibration",
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

    tracking.track_runtime_open_loop_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_open_loop_signal_surface(limit=8)

    assert surface["active"] is True
    assert surface["summary"]["open_count"] == 0
    assert surface["summary"]["softening_count"] == 1
    assert surface["items"][0]["signal_type"] == "softening-loop"
    assert surface["items"][0]["status"] == "softening"


def test_open_loop_surface_forms_closed_status_only_in_conservative_case(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.open_loop_tracking

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
    _insert_temporal_recurrence(
        db,
        canonical_key="temporal-recurrence:recurring-direction:danish-concise-calibration",
        status="softening",
        signal_type="recurring-direction",
        minutes_ago=5,
    )

    tracking.track_runtime_open_loop_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_open_loop_signal_surface(limit=8)

    assert surface["active"] is True
    assert surface["summary"]["closed_count"] == 1
    assert surface["items"][0]["status"] == "closed"
    assert surface["items"][0]["signal_type"] == "softening-loop"
    assert surface["summary"]["current_status"] == "closed"
    assert surface["summary"]["ready_count"] == 1
    assert surface["summary"]["current_closure_confidence"] == "high"
    assert surface["items"][0]["closure_readiness"] == "high"
    assert surface["items"][0]["closure_confidence"] == "high"
    assert "conservatively closed" in surface["items"][0]["closure_reason"]


def test_open_loop_surface_can_raise_closure_confidence_without_auto_closing_loop(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.open_loop_tracking

    _insert_focus(
        db,
        canonical_key="development-focus:communication:danish-concise-calibration",
        minutes_ago=30,
    )
    _insert_goal(
        db,
        canonical_key="goal-signal:danish-concise-calibration",
        status="active",
        minutes_ago=20,
    )
    _insert_reflection(
        db,
        canonical_key="reflection-signal:settled-thread:danish-concise-calibration",
        status="settled",
        signal_type="settled-thread",
        minutes_ago=10,
    )
    _insert_temporal_recurrence(
        db,
        canonical_key="temporal-recurrence:recurring-direction:danish-concise-calibration",
        status="softening",
        signal_type="recurring-direction",
        minutes_ago=5,
    )

    tracking.track_runtime_open_loop_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_open_loop_signal_surface(limit=8)

    assert surface["active"] is True
    assert surface["summary"]["softening_count"] == 1
    assert surface["summary"]["closed_count"] == 0
    assert surface["summary"]["ready_count"] == 1
    assert surface["summary"]["current_status"] == "softening"
    assert surface["summary"]["current_closure_confidence"] == "high"
    assert surface["items"][0]["status"] == "softening"
    assert surface["items"][0]["closure_readiness"] == "high"
    assert surface["items"][0]["closure_confidence"] == "high"
    assert "likely closure readiness" in surface["items"][0]["closure_reason"]


def test_open_loop_surface_and_mc_shapes_remain_bounded(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.open_loop_tracking
    mission_control = isolated_runtime.mission_control

    _insert_open_loop(
        db,
        status="open",
        signal_type="persistent-open-loop",
        canonical_key="open-loop:persistent-open-loop:danish-concise-calibration",
    )
    _insert_open_loop(
        db,
        status="softening",
        signal_type="softening-loop",
        canonical_key="open-loop:softening-loop:workspace-boundary",
    )
    _insert_open_loop(
        db,
        status="closed",
        signal_type="softening-loop",
        canonical_key="open-loop:softening-loop:runtime-lane",
    )
    _insert_open_loop(
        db,
        status="stale",
        signal_type="open-loop",
        canonical_key="open-loop:open-loop:old-thread",
    )
    _insert_open_loop(
        db,
        status="superseded",
        signal_type="open-loop",
        canonical_key="open-loop:open-loop:older-thread",
    )

    surface = tracking.build_runtime_open_loop_signal_surface(limit=8)
    jarvis = mission_control.mc_jarvis()
    runtime = mission_control.mc_runtime()
    mc_shape = jarvis["development"]["open_loop_signals"]
    runtime_shape = runtime["runtime_open_loop_signals"]

    assert {
        "open_count",
        "softening_count",
        "closed_count",
        "stale_count",
        "superseded_count",
        "ready_count",
        "current_signal",
        "current_status",
        "current_closure_confidence",
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
        "closure_readiness",
        "closure_confidence",
        "closure_reason",
    }.issubset(surface["items"][0].keys())
    assert surface["summary"]["open_count"] == 1
    assert surface["summary"]["softening_count"] == 1
    assert surface["summary"]["closed_count"] == 1
    assert surface["summary"]["stale_count"] == 1
    assert surface["summary"]["superseded_count"] == 1
    assert surface["summary"]["ready_count"] == 1
    assert mc_shape["summary"]["current_status"] in {"open", "softening", "closed"}
    assert runtime_shape["summary"]["current_status"] in {"open", "softening", "closed"}
    assert "current_closure_confidence" in mc_shape["summary"]
    assert "current_closure_confidence" in runtime_shape["summary"]
