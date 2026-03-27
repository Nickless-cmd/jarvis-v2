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


def _insert_dream_hypothesis_signal(db, *, status: str, signal_type: str, canonical_key: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_dream_hypothesis_signal(
        signal_id=f"dream-hypothesis-{uuid4().hex}",
        signal_type=signal_type,
        canonical_key=canonical_key,
        status=status,
        title=f"Dream hypothesis: {signal_type}",
        summary=f"Hypothesis summary: {signal_type}",
        rationale="Validation dream hypothesis",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="dream hypothesis evidence",
        support_summary="dream hypothesis support",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation dream hypothesis status",
        run_id="test-run",
        session_id="test-session",
    )


def test_dream_hypothesis_surface_stays_empty_without_relevant_pattern(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.dream_hypothesis_tracking

    _insert_focus(
        db,
        canonical_key="development-focus:communication:danish-concise-calibration",
        minutes_ago=10,
    )
    _insert_self_review_outcome(
        db,
        status="active",
        outcome_type="watch-closely",
        canonical_key="self-review-outcome:review-pressure:danish-concise-calibration",
    )

    result = tracking.track_runtime_dream_hypothesis_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_dream_hypothesis_signal_surface(limit=8)

    assert result["created"] == 0
    assert result["updated"] == 0
    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["summary"]["active_count"] == 0
    assert surface["summary"]["integrating_count"] == 0
    assert surface["summary"]["fading_count"] == 0


def test_dream_hypothesis_surface_forms_small_bounded_private_hypotheses(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.dream_hypothesis_tracking

    _insert_focus(
        db,
        canonical_key="development-focus:communication:tension-thread",
        minutes_ago=20,
    )
    _insert_temporal_recurrence(
        db,
        canonical_key="temporal-recurrence:recurring-tension:tension-thread",
        status="active",
        signal_type="recurring-tension",
        minutes_ago=10,
    )
    _insert_self_review_outcome(
        db,
        status="active",
        outcome_type="challenge-further",
        canonical_key="self-review-outcome:review-pressure:tension-thread",
    )

    _insert_focus(
        db,
        canonical_key="development-focus:communication:carried-thread",
        minutes_ago=20,
    )
    _insert_temporal_recurrence(
        db,
        canonical_key="temporal-recurrence:recurring-direction:carried-thread",
        status="softening",
        signal_type="recurring-direction",
        minutes_ago=10,
    )
    _insert_witness(
        db,
        status="carried",
        signal_type="carried-lesson",
        canonical_key="witness-signal:carried-lesson:carried-thread",
    )
    _insert_self_review_outcome(
        db,
        status="active",
        outcome_type="carry-forward",
        canonical_key="self-review-outcome:review-pressure:carried-thread",
    )

    _insert_focus(
        db,
        canonical_key="development-focus:communication:emerging-thread",
        minutes_ago=20,
    )
    _insert_temporal_recurrence(
        db,
        canonical_key="temporal-recurrence:recurring-direction:emerging-thread",
        status="softening",
        signal_type="recurring-direction",
        minutes_ago=10,
    )
    _insert_self_review_outcome(
        db,
        status="active",
        outcome_type="watch-closely",
        canonical_key="self-review-outcome:review-pressure:emerging-thread",
    )
    _insert_self_review_cadence_signal(
        db,
        status="softening",
        canonical_key="self-review-cadence:review-pressure:emerging-thread",
        summary="This review-pressure thread was reviewed recently and can stay quiet for now.",
    )

    result = tracking.track_runtime_dream_hypothesis_signals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_dream_hypothesis_signal_surface(limit=8)
    items_by_domain = {item["domain"]: item for item in surface["items"]}

    assert result["created"] == 3
    assert surface["active"] is True
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["integrating_count"] == 1
    assert surface["summary"]["fading_count"] == 1
    assert items_by_domain["tension-thread"]["hypothesis_type"] == "tension-hypothesis"
    assert items_by_domain["tension-thread"]["status"] == "active"
    assert items_by_domain["carried-thread"]["hypothesis_type"] == "carried-hypothesis"
    assert items_by_domain["carried-thread"]["status"] == "integrating"
    assert "carried-lesson" in items_by_domain["carried-thread"]["hypothesis_anchor"]
    assert items_by_domain["emerging-thread"]["hypothesis_type"] == "emerging-hypothesis"
    assert items_by_domain["emerging-thread"]["status"] == "fading"


def test_dream_hypothesis_surface_and_mc_shapes_remain_bounded(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.dream_hypothesis_tracking
    mission_control = isolated_runtime.mission_control

    _insert_dream_hypothesis_signal(
        db,
        status="active",
        signal_type="tension-hypothesis",
        canonical_key="dream-hypothesis:tension-hypothesis:danish-concise-calibration",
    )
    _insert_dream_hypothesis_signal(
        db,
        status="integrating",
        signal_type="carried-hypothesis",
        canonical_key="dream-hypothesis:carried-hypothesis:workspace-boundary",
    )
    _insert_dream_hypothesis_signal(
        db,
        status="fading",
        signal_type="emerging-hypothesis",
        canonical_key="dream-hypothesis:emerging-hypothesis:carried-thread",
    )
    _insert_dream_hypothesis_signal(
        db,
        status="stale",
        signal_type="emerging-hypothesis",
        canonical_key="dream-hypothesis:emerging-hypothesis:older-thread",
    )
    _insert_dream_hypothesis_signal(
        db,
        status="superseded",
        signal_type="carried-hypothesis",
        canonical_key="dream-hypothesis:carried-hypothesis:oldest-thread",
    )

    surface = tracking.build_runtime_dream_hypothesis_signal_surface(limit=8)
    jarvis = mission_control.mc_jarvis()
    runtime = mission_control.mc_runtime()
    mc_shape = jarvis["development"]["dream_hypothesis_signals"]
    runtime_shape = runtime["runtime_dream_hypothesis_signals"]

    assert {
        "active_count",
        "integrating_count",
        "fading_count",
        "stale_count",
        "superseded_count",
        "current_signal",
        "current_status",
        "current_hypothesis_type",
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
        "hypothesis_type",
        "hypothesis_note",
        "hypothesis_anchor",
    }.issubset(surface["items"][0].keys())
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["integrating_count"] == 1
    assert surface["summary"]["fading_count"] == 1
    assert surface["summary"]["stale_count"] == 1
    assert surface["summary"]["superseded_count"] == 1
    assert mc_shape["summary"]["current_status"] in {"active", "integrating", "fading", "stale"}
    assert runtime_shape["summary"]["current_status"] in {"active", "integrating", "fading", "stale"}
