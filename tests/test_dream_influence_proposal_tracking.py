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


def _insert_world_model(db, *, canonical_key: str, status: str, signal_type: str, minutes_ago: int = 0) -> None:
    ts = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    db.upsert_runtime_world_model_signal(
        signal_id=f"world-model-{uuid4().hex}",
        signal_type=signal_type,
        canonical_key=canonical_key,
        status=status,
        title=f"World model: {signal_type}",
        summary=f"World model summary: {signal_type}",
        rationale="Validation world model",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="world model evidence",
        support_summary="world model support",
        support_count=2,
        session_count=1,
        created_at=ts.isoformat(),
        updated_at=ts.isoformat(),
        status_reason="Validation world model status",
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


def _insert_dream_influence_proposal(db, *, status: str, proposal_type: str, canonical_key: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_dream_influence_proposal(
        proposal_id=f"dream-influence-proposal-{uuid4().hex}",
        proposal_type=proposal_type,
        canonical_key=canonical_key,
        status=status,
        title=f"Dream influence proposal: {proposal_type}",
        summary=f"Proposal summary: {proposal_type}",
        rationale="Validation dream influence proposal",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="dream influence proposal evidence",
        support_summary="dream influence proposal support",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation dream influence proposal status",
        run_id="test-run",
        session_id="test-session",
    )


def test_dream_influence_proposal_surface_stays_empty_without_relevant_candidate_grounding(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.dream_influence_proposal_tracking

    _insert_dream_hypothesis_signal(
        db,
        status="integrating",
        signal_type="carried-hypothesis",
        canonical_key="dream-hypothesis:carried-hypothesis:danish-concise-calibration",
    )

    result = tracking.track_runtime_dream_influence_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_dream_influence_proposal_surface(limit=8)

    assert result["created"] == 0
    assert result["updated"] == 0
    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["summary"]["fresh_count"] == 0
    assert surface["summary"]["active_count"] == 0
    assert surface["summary"]["fading_count"] == 0


def test_dream_influence_proposal_surface_forms_small_bounded_proposals(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.dream_influence_proposal_tracking

    _insert_dream_adoption_candidate(
        db,
        status="fresh",
        candidate_type="strong-candidate",
        canonical_key="dream-adoption-candidate:strong-candidate:self-thread",
    )
    _insert_dream_hypothesis_signal(
        db,
        status="integrating",
        signal_type="carried-hypothesis",
        canonical_key="dream-hypothesis:carried-hypothesis:self-thread",
    )
    _insert_self_model(
        db,
        canonical_key="self-model:improving:self-thread",
        status="uncertain",
        signal_type="improvement-edge",
        minutes_ago=5,
    )
    _insert_self_review_outcome(
        db,
        status="active",
        outcome_type="carry-forward",
        canonical_key="self-review-outcome:review-pressure:self-thread",
    )

    _insert_dream_adoption_candidate(
        db,
        status="active",
        candidate_type="strong-candidate",
        canonical_key="dream-adoption-candidate:strong-candidate:direction-thread",
    )
    _insert_dream_hypothesis_signal(
        db,
        status="integrating",
        signal_type="carried-hypothesis",
        canonical_key="dream-hypothesis:carried-hypothesis:direction-thread",
    )
    _insert_goal(
        db,
        canonical_key="goal-signal:direction-thread",
        status="active",
        minutes_ago=10,
    )
    _insert_witness(
        db,
        status="carried",
        signal_type="carried-lesson",
        canonical_key="witness-signal:carried-lesson:direction-thread",
    )

    _insert_dream_adoption_candidate(
        db,
        status="fading",
        candidate_type="tentative-candidate",
        canonical_key="dream-adoption-candidate:tentative-candidate:focus-thread",
    )
    _insert_dream_hypothesis_signal(
        db,
        status="fading",
        signal_type="emerging-hypothesis",
        canonical_key="dream-hypothesis:emerging-hypothesis:focus-thread",
    )
    _insert_focus(
        db,
        canonical_key="development-focus:communication:focus-thread",
        minutes_ago=10,
    )

    _insert_dream_adoption_candidate(
        db,
        status="active",
        candidate_type="carried-candidate",
        canonical_key="dream-adoption-candidate:carried-candidate:world-thread",
    )
    _insert_dream_hypothesis_signal(
        db,
        status="active",
        signal_type="tension-hypothesis",
        canonical_key="dream-hypothesis:tension-hypothesis:world-thread",
    )
    _insert_world_model(
        db,
        canonical_key="world-model:project-context:world-thread",
        status="uncertain",
        signal_type="project-context-assumption",
        minutes_ago=5,
    )

    result = tracking.track_runtime_dream_influence_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_dream_influence_proposal_surface(limit=8)
    items_by_domain = {item["domain"]: item for item in surface["items"]}

    assert result["created"] == 4
    assert surface["active"] is True
    assert surface["summary"]["fresh_count"] == 1
    assert surface["summary"]["active_count"] == 2
    assert surface["summary"]["fading_count"] == 1
    assert items_by_domain["self-thread"]["proposal_type"] == "nudge-self-model"
    assert items_by_domain["self-thread"]["status"] == "fresh"
    assert items_by_domain["self-thread"]["influence_target"] == "self-model"
    assert items_by_domain["self-thread"]["influence_confidence"] == "high"
    assert items_by_domain["direction-thread"]["proposal_type"] == "nudge-direction"
    assert items_by_domain["direction-thread"]["status"] == "active"
    assert items_by_domain["direction-thread"]["influence_target"] == "goals"
    assert items_by_domain["focus-thread"]["proposal_type"] == "nudge-focus"
    assert items_by_domain["focus-thread"]["status"] == "fading"
    assert items_by_domain["world-thread"]["proposal_type"] == "nudge-world-view"
    assert items_by_domain["world-thread"]["influence_target"] == "world-model"


def test_dream_influence_proposal_surface_and_mc_shapes_remain_bounded(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.dream_influence_proposal_tracking
    mission_control = isolated_runtime.mission_control

    _insert_dream_influence_proposal(
        db,
        status="fresh",
        proposal_type="nudge-self-model",
        canonical_key="dream-influence-proposal:nudge-self-model:danish-concise-calibration",
    )
    _insert_dream_influence_proposal(
        db,
        status="active",
        proposal_type="nudge-direction",
        canonical_key="dream-influence-proposal:nudge-direction:workspace-boundary",
    )
    _insert_dream_influence_proposal(
        db,
        status="fading",
        proposal_type="nudge-focus",
        canonical_key="dream-influence-proposal:nudge-focus:carried-thread",
    )
    _insert_dream_influence_proposal(
        db,
        status="stale",
        proposal_type="nudge-world-view",
        canonical_key="dream-influence-proposal:nudge-world-view:older-thread",
    )
    _insert_dream_influence_proposal(
        db,
        status="superseded",
        proposal_type="nudge-direction",
        canonical_key="dream-influence-proposal:nudge-direction:oldest-thread",
    )

    surface = tracking.build_runtime_dream_influence_proposal_surface(limit=8)
    jarvis = mission_control.mc_jarvis()
    runtime = mission_control.mc_runtime()
    mc_shape = jarvis["development"]["dream_influence_proposals"]
    runtime_shape = runtime["runtime_dream_influence_proposals"]

    assert {
        "fresh_count",
        "active_count",
        "fading_count",
        "stale_count",
        "superseded_count",
        "current_proposal",
        "current_status",
        "current_proposal_type",
        "current_influence_confidence",
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
        "hypothesis_type",
        "candidate_state",
        "influence_target",
        "influence_confidence",
        "proposal_reason",
        "influence_anchor",
    }.issubset(surface["items"][0].keys())
    assert surface["summary"]["fresh_count"] == 1
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["fading_count"] == 1
    assert surface["summary"]["stale_count"] == 1
    assert surface["summary"]["superseded_count"] == 1
    assert mc_shape["summary"]["current_status"] in {"fresh", "active", "fading", "stale"}
    assert runtime_shape["summary"]["current_status"] in {"fresh", "active", "fading", "stale"}
