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


def _insert_self_model(db, *, canonical_key: str, status: str, signal_type: str, minutes_ago: int = 0) -> None:
    ts = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    db.upsert_runtime_self_model_signal(
        signal_id=f"self-model-{uuid4().hex}",
        signal_type=signal_type,
        canonical_key=canonical_key,
        status=status,
        title=f"Self model: {signal_type}",
        summary=f"Self model summary: {signal_type}",
        rationale="Validation self model",
        source_kind="critic-supported",
        confidence="medium",
        evidence_summary="self model evidence",
        support_summary="self model support",
        support_count=2,
        session_count=1,
        created_at=ts.isoformat(),
        updated_at=ts.isoformat(),
        status_reason="Validation self model status",
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


def _insert_self_review_cadence_signal(db, *, status: str, canonical_key: str, summary: str) -> None:
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


def _insert_dream_adoption_candidate(db, *, status: str, candidate_type: str, canonical_key: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_dream_adoption_candidate(
        candidate_id=f"dream-adoption-candidate-{uuid4().hex}",
        candidate_type=candidate_type,
        canonical_key=canonical_key,
        status=status,
        title=f"Dream adoption candidate: {candidate_type}",
        summary=f"Candidate summary: {candidate_type}",
        rationale="Validation dream adoption candidate",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="dream adoption candidate evidence",
        support_summary="dream adoption candidate support",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation dream adoption candidate status",
        run_id="test-run",
        session_id="test-session",
    )


def test_dream_adoption_candidate_surface_stays_empty_without_relevant_hypothesis_grounding(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.dream_adoption_candidate_tracking

    _insert_focus(
        db,
        canonical_key="development-focus:communication:danish-concise-calibration",
        minutes_ago=10,
    )
    _insert_self_review_outcome(
        db,
        status="active",
        outcome_type="carry-forward",
        canonical_key="self-review-outcome:review-pressure:danish-concise-calibration",
    )

    result = tracking.track_runtime_dream_adoption_candidates_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_dream_adoption_candidate_surface(limit=8)

    assert result["created"] == 0
    assert result["updated"] == 0
    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["summary"]["fresh_count"] == 0
    assert surface["summary"]["active_count"] == 0
    assert surface["summary"]["fading_count"] == 0


def test_dream_adoption_candidate_surface_forms_small_bounded_candidates(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.dream_adoption_candidate_tracking

    _insert_dream_hypothesis_signal(
        db,
        status="integrating",
        signal_type="carried-hypothesis",
        canonical_key="dream-hypothesis:carried-hypothesis:strong-thread",
    )
    _insert_focus(
        db,
        canonical_key="development-focus:communication:strong-thread",
        minutes_ago=20,
    )
    _insert_goal(
        db,
        canonical_key="goal-signal:strong-thread",
        status="active",
        minutes_ago=10,
    )
    _insert_witness(
        db,
        status="carried",
        signal_type="carried-lesson",
        canonical_key="witness-signal:carried-lesson:strong-thread",
    )
    _insert_self_review_outcome(
        db,
        status="active",
        outcome_type="carry-forward",
        canonical_key="self-review-outcome:review-pressure:strong-thread",
    )

    _insert_dream_hypothesis_signal(
        db,
        status="active",
        signal_type="emerging-hypothesis",
        canonical_key="dream-hypothesis:emerging-hypothesis:carried-thread",
    )
    _insert_focus(
        db,
        canonical_key="development-focus:communication:carried-thread",
        minutes_ago=20,
    )
    _insert_witness(
        db,
        status="fresh",
        signal_type="carried-lesson",
        canonical_key="witness-signal:carried-lesson:carried-thread",
    )
    _insert_goal(
        db,
        canonical_key="goal-signal:carried-thread",
        status="active",
        minutes_ago=10,
    )

    _insert_dream_hypothesis_signal(
        db,
        status="fading",
        signal_type="tension-hypothesis",
        canonical_key="dream-hypothesis:tension-hypothesis:tentative-thread",
    )
    _insert_focus(
        db,
        canonical_key="development-focus:communication:tentative-thread",
        minutes_ago=20,
    )
    _insert_self_review_outcome(
        db,
        status="active",
        outcome_type="challenge-further",
        canonical_key="self-review-outcome:review-pressure:tentative-thread",
    )
    _insert_self_review_cadence_signal(
        db,
        status="softening",
        canonical_key="self-review-cadence:review-pressure:tentative-thread",
        summary="This review-pressure thread was reviewed recently and can stay quiet for now.",
    )
    _insert_self_model(
        db,
        canonical_key="self-model:improving:tentative-thread",
        status="uncertain",
        signal_type="improvement-edge",
        minutes_ago=5,
    )

    result = tracking.track_runtime_dream_adoption_candidates_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_dream_adoption_candidate_surface(limit=8)
    items_by_domain = {item["domain"]: item for item in surface["items"]}

    assert result["created"] == 3
    assert surface["active"] is True
    assert surface["summary"]["fresh_count"] == 1
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["fading_count"] == 1
    assert items_by_domain["strong-thread"]["candidate_type"] == "strong-candidate"
    assert items_by_domain["strong-thread"]["status"] == "fresh"
    assert items_by_domain["strong-thread"]["adoption_confidence"] == "high"
    assert items_by_domain["carried-thread"]["candidate_type"] == "carried-candidate"
    assert items_by_domain["carried-thread"]["status"] == "active"
    assert "carried-lesson" in items_by_domain["carried-thread"]["adoption_anchor"]
    assert items_by_domain["tentative-thread"]["candidate_type"] == "tentative-candidate"
    assert items_by_domain["tentative-thread"]["status"] == "fading"
    assert items_by_domain["tentative-thread"]["adoption_confidence"] == "low"


def test_dream_adoption_candidate_surface_and_mc_shapes_remain_bounded(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.dream_adoption_candidate_tracking
    mission_control = isolated_runtime.mission_control

    _insert_dream_adoption_candidate(
        db,
        status="fresh",
        candidate_type="strong-candidate",
        canonical_key="dream-adoption-candidate:strong-candidate:danish-concise-calibration",
    )
    _insert_dream_adoption_candidate(
        db,
        status="active",
        candidate_type="carried-candidate",
        canonical_key="dream-adoption-candidate:carried-candidate:workspace-boundary",
    )
    _insert_dream_adoption_candidate(
        db,
        status="fading",
        candidate_type="tentative-candidate",
        canonical_key="dream-adoption-candidate:tentative-candidate:carried-thread",
    )
    _insert_dream_adoption_candidate(
        db,
        status="stale",
        candidate_type="tentative-candidate",
        canonical_key="dream-adoption-candidate:tentative-candidate:older-thread",
    )
    _insert_dream_adoption_candidate(
        db,
        status="superseded",
        candidate_type="carried-candidate",
        canonical_key="dream-adoption-candidate:carried-candidate:oldest-thread",
    )

    surface = tracking.build_runtime_dream_adoption_candidate_surface(limit=8)
    jarvis = mission_control.mc_jarvis()
    runtime = mission_control.mc_runtime()
    mc_shape = jarvis["development"]["dream_adoption_candidates"]
    runtime_shape = runtime["runtime_dream_adoption_candidates"]

    assert {
        "fresh_count",
        "active_count",
        "fading_count",
        "stale_count",
        "superseded_count",
        "current_candidate",
        "current_status",
        "current_candidate_type",
        "current_adoption_confidence",
    }.issubset(surface["summary"].keys())
    assert {
        "candidate_id",
        "candidate_type",
        "canonical_key",
        "status",
        "title",
        "summary",
        "confidence",
        "updated_at",
        "domain",
        "hypothesis_type",
        "adoption_state",
        "adoption_reason",
        "adoption_confidence",
        "adoption_anchor",
    }.issubset(surface["items"][0].keys())
    assert surface["summary"]["fresh_count"] == 1
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["fading_count"] == 1
    assert surface["summary"]["stale_count"] == 1
    assert surface["summary"]["superseded_count"] == 1
    assert mc_shape["summary"]["current_status"] in {"fresh", "active", "fading", "stale"}
    assert runtime_shape["summary"]["current_status"] in {"fresh", "active", "fading", "stale"}
