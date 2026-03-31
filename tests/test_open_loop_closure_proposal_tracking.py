from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4


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


def _insert_self_review_cadence(db, *, status: str, canonical_key: str, summary: str) -> None:
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


def _insert_open_loop_closure_proposal(db, *, status: str, proposal_type: str, canonical_key: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_open_loop_closure_proposal(
        proposal_id=f"open-loop-closure-proposal-{uuid4().hex}",
        proposal_type=proposal_type,
        canonical_key=canonical_key,
        status=status,
        title=f"Loop closure proposal: {proposal_type}",
        summary=f"Proposal summary: {proposal_type}",
        rationale="Validation closure proposal",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="closure proposal evidence",
        support_summary="closure proposal support",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation closure proposal status",
        run_id="test-run",
        session_id="test-session",
    )


def test_open_loop_closure_proposal_surface_stays_empty_without_relevant_closure_grounding(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.open_loop_closure_proposal_tracking

    _insert_open_loop(
        db,
        status="open",
        signal_type="persistent-open-loop",
        canonical_key="open-loop:persistent-open-loop:danish-concise-calibration",
    )

    result = tracking.track_runtime_open_loop_closure_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_open_loop_closure_proposal_surface(limit=8)

    assert result["created"] == 0
    assert result["updated"] == 0
    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["summary"]["fresh_count"] == 0
    assert surface["summary"]["active_count"] == 0
    assert surface["summary"]["fading_count"] == 0


def test_open_loop_closure_proposal_surface_forms_small_bounded_proposals_for_ready_loops(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.open_loop_closure_proposal_tracking

    _insert_open_loop(
        db,
        status="softening",
        signal_type="softening-loop",
        canonical_key="open-loop:softening-loop:close-thread",
    )
    _insert_reflection(
        db,
        canonical_key="reflection-signal:settled-thread:close-thread",
        status="settled",
        signal_type="settled-thread",
        minutes_ago=10,
    )
    _insert_temporal_recurrence(
        db,
        canonical_key="temporal-recurrence:recurring-direction:close-thread",
        status="softening",
        signal_type="recurring-direction",
        minutes_ago=10,
    )
    _insert_witness(
        db,
        status="carried",
        signal_type="carried-lesson",
        canonical_key="witness-signal:carried-lesson:close-thread",
    )

    _insert_open_loop(
        db,
        status="softening",
        signal_type="softening-loop",
        canonical_key="open-loop:softening-loop:revisit-thread",
    )
    _insert_reflection(
        db,
        canonical_key="reflection-signal:settled-thread:revisit-thread",
        status="settled",
        signal_type="settled-thread",
        minutes_ago=10,
    )
    _insert_temporal_recurrence(
        db,
        canonical_key="temporal-recurrence:recurring-direction:revisit-thread",
        status="softening",
        signal_type="recurring-direction",
        minutes_ago=10,
    )
    _insert_self_review_outcome(
        db,
        status="active",
        outcome_type="challenge-further",
        canonical_key="self-review-outcome:review-pressure:revisit-thread",
    )
    _insert_self_review_cadence(
        db,
        status="active",
        canonical_key="self-review-cadence:review-pressure:revisit-thread",
        summary="This review-pressure thread now looks due for another bounded review pass.",
    )

    _insert_open_loop(
        db,
        status="open",
        signal_type="persistent-open-loop",
        canonical_key="open-loop:persistent-open-loop:hold-thread",
    )
    _insert_critic(
        db,
        canonical_key="reflective-critic:mismatch:development-focus:communication:hold-thread",
        status="active",
        minutes_ago=15,
    )
    _insert_reflection(
        db,
        canonical_key="reflection-signal:settled-thread:hold-thread",
        status="settled",
        signal_type="settled-thread",
        minutes_ago=10,
    )

    result = tracking.track_runtime_open_loop_closure_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_open_loop_closure_proposal_surface(limit=8)
    items_by_domain = {item["domain"]: item for item in surface["items"]}

    assert result["created"] == 3
    assert surface["active"] is True
    assert surface["summary"]["fresh_count"] == 1
    assert surface["summary"]["active_count"] == 2
    assert surface["summary"]["fading_count"] == 0
    assert items_by_domain["close-thread"]["proposal_type"] == "close-candidate"
    assert items_by_domain["close-thread"]["status"] == "fresh"
    assert items_by_domain["close-thread"]["closure_confidence"] == "high"
    assert items_by_domain["revisit-thread"]["proposal_type"] == "revisit-before-close"
    assert items_by_domain["revisit-thread"]["status"] == "active"
    assert "challenge-further" in items_by_domain["revisit-thread"]["review_anchor"]
    assert items_by_domain["hold-thread"]["proposal_type"] == "hold-open"
    assert items_by_domain["hold-thread"]["status"] == "active"
    assert items_by_domain["hold-thread"]["closure_confidence"] == "medium"


def test_open_loop_closure_proposal_surface_and_mc_shapes_remain_bounded(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.open_loop_closure_proposal_tracking
    mission_control = isolated_runtime.mission_control

    _insert_open_loop_closure_proposal(
        db,
        status="fresh",
        proposal_type="close-candidate",
        canonical_key="open-loop-closure-proposal:close-candidate:danish-concise-calibration",
    )
    _insert_open_loop_closure_proposal(
        db,
        status="active",
        proposal_type="revisit-before-close",
        canonical_key="open-loop-closure-proposal:revisit-before-close:workspace-boundary",
    )
    _insert_open_loop_closure_proposal(
        db,
        status="fading",
        proposal_type="hold-open",
        canonical_key="open-loop-closure-proposal:hold-open:carried-thread",
    )
    _insert_open_loop_closure_proposal(
        db,
        status="stale",
        proposal_type="hold-open",
        canonical_key="open-loop-closure-proposal:hold-open:older-thread",
    )
    _insert_open_loop_closure_proposal(
        db,
        status="superseded",
        proposal_type="close-candidate",
        canonical_key="open-loop-closure-proposal:close-candidate:oldest-thread",
    )

    surface = tracking.build_runtime_open_loop_closure_proposal_surface(limit=8)
    jarvis = mission_control.mc_jarvis()
    runtime = mission_control.mc_runtime()
    mc_shape = jarvis["development"]["open_loop_closure_proposals"]
    runtime_shape = runtime["runtime_open_loop_closure_proposals"]

    assert {
        "fresh_count",
        "active_count",
        "fading_count",
        "stale_count",
        "superseded_count",
        "current_proposal",
        "current_status",
        "current_proposal_type",
        "current_closure_confidence",
    }.issubset(surface["summary"].keys())
    assert {
        "proposal_id",
        "proposal_type",
        "canonical_key",
        "status",
        "title",
        "summary",
        "confidence",
        "updated_at",
        "domain",
        "loop_status",
        "closure_confidence",
        "closure_readiness",
        "proposal_reason",
        "review_anchor",
    }.issubset(surface["items"][0].keys())
    assert surface["summary"]["fresh_count"] == 1
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["fading_count"] == 1
    assert surface["summary"]["stale_count"] == 1
    assert surface["summary"]["superseded_count"] == 1
    assert mc_shape["summary"]["current_status"] in {"fresh", "active", "fading", "stale"}
    assert runtime_shape["summary"]["current_status"] in {"fresh", "active", "fading", "stale"}


def test_softening_loop_produces_hold_open_proposal_even_without_medium_closure_confidence(isolated_runtime) -> None:
    """A softening loop should produce a hold-open proposal even when closure_confidence
    is still low, because the open→softening transition is itself maturation evidence."""
    db = isolated_runtime.db
    tracking = isolated_runtime.open_loop_closure_proposal_tracking

    _insert_open_loop(
        db,
        status="softening",
        signal_type="softening-loop",
        canonical_key="open-loop:softening-loop:maturing-thread",
    )

    result = tracking.track_runtime_open_loop_closure_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_open_loop_closure_proposal_surface(limit=8)

    assert result["created"] == 1
    assert surface["active"] is True
    item = surface["items"][0]
    assert item["proposal_type"] == "hold-open"
    assert item["domain"] == "maturing-thread"
    assert "softening" in item["proposal_reason"].lower()


def test_open_loop_without_softening_or_closure_evidence_produces_no_proposal(isolated_runtime) -> None:
    """An open loop with low closure_confidence and no softening should NOT produce proposals."""
    db = isolated_runtime.db
    tracking = isolated_runtime.open_loop_closure_proposal_tracking

    _insert_open_loop(
        db,
        status="open",
        signal_type="persistent-open-loop",
        canonical_key="open-loop:persistent-open-loop:still-active-thread",
    )

    result = tracking.track_runtime_open_loop_closure_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_open_loop_closure_proposal_surface(limit=8)

    assert result["created"] == 0
    assert surface["active"] is False


def test_closure_proposal_reason_includes_loop_focus(isolated_runtime) -> None:
    """Proposal reasons should reference the specific loop focus for grounded summaries."""
    db = isolated_runtime.db
    tracking = isolated_runtime.open_loop_closure_proposal_tracking

    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_open_loop_signal(
        signal_id=f"open-loop-{uuid4().hex}",
        signal_type="softening-loop",
        canonical_key="open-loop:softening-loop:danish-concise-calibration",
        status="softening",
        title="Open loop: Danish concise calibration",
        summary="Softening loop",
        rationale="Validation",
        source_kind="derived-runtime-open-loop",
        confidence="medium",
        evidence_summary="evidence",
        support_summary="support",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation",
        run_id="test-run",
        session_id="test-session",
    )

    tracking.track_runtime_open_loop_closure_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_open_loop_closure_proposal_surface(limit=8)

    assert surface["active"] is True
    item = surface["items"][0]
    assert "Danish concise calibration" in item["proposal_reason"]
