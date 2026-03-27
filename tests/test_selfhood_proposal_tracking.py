from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def _insert_self_authored_prompt_proposal(db, *, status: str, proposal_type: str, canonical_key: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_self_authored_prompt_proposal(
        proposal_id=f"self-authored-prompt-proposal-{uuid4().hex}",
        proposal_type=proposal_type,
        canonical_key=canonical_key,
        status=status,
        title=f"Self-authored prompt proposal: {proposal_type}",
        summary=f"Proposal summary: {proposal_type}",
        rationale="Validation self-authored prompt proposal",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="self-authored prompt proposal evidence",
        support_summary="self-authored prompt proposal support",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation self-authored prompt proposal status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_self_model(db, *, canonical_key: str, status: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_self_model_signal(
        signal_id=f"self-model-{uuid4().hex}",
        signal_type="improvement-edge",
        canonical_key=canonical_key,
        status=status,
        title="Self model: improvement edge",
        summary="Self model summary",
        rationale="Validation self model",
        source_kind="critic-supported",
        confidence="medium",
        evidence_summary="self model evidence",
        support_summary="self model support",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation self model status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_self_review_outcome(db, *, canonical_key: str, status: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_self_review_outcome(
        outcome_id=f"self-review-outcome-{uuid4().hex}",
        outcome_type="challenge-further",
        canonical_key=canonical_key,
        status=status,
        title="Self-review outcome: challenge-further",
        summary="Outcome summary",
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


def _insert_dream_influence_proposal(db, *, canonical_key: str, status: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_dream_influence_proposal(
        proposal_id=f"dream-influence-proposal-{uuid4().hex}",
        proposal_type="nudge-world-view",
        canonical_key=canonical_key,
        status=status,
        title="Dream influence proposal: nudge-world-view",
        summary="Dream influence summary",
        rationale="Validation dream influence proposal",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="dream influence evidence",
        support_summary="dream influence support",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation dream influence status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_selfhood_proposal(db, *, status: str, proposal_type: str, canonical_key: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_selfhood_proposal(
        proposal_id=f"selfhood-proposal-{uuid4().hex}",
        proposal_type=proposal_type,
        canonical_key=canonical_key,
        status=status,
        title=f"Selfhood proposal: {proposal_type}",
        summary=f"A bounded {proposal_type} now points toward IDENTITY.md while proposal confidence stays medium. Explicit user approval is required before any canonical self change.",
        rationale="Validation selfhood proposal",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="selfhood proposal evidence",
        support_summary="selfhood proposal support | selfhood anchor | bounded proposed shift",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation selfhood proposal status",
        run_id="test-run",
        session_id="test-session",
    )


def test_selfhood_proposal_surface_stays_empty_without_relevant_grounding(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.selfhood_proposal_tracking

    _insert_self_authored_prompt_proposal(
        db,
        status="fresh",
        proposal_type="communication-nudge",
        canonical_key="self-authored-prompt-proposal:communication-nudge:voice-thread",
    )

    result = tracking.track_runtime_selfhood_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_selfhood_proposal_surface(limit=8)

    assert result["created"] == 0
    assert result["updated"] == 0
    assert surface["active"] is False
    assert surface["items"] == []


def test_selfhood_proposal_surface_forms_small_bounded_proposals(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.selfhood_proposal_tracking

    _insert_self_authored_prompt_proposal(
        db,
        status="fresh",
        proposal_type="communication-nudge",
        canonical_key="self-authored-prompt-proposal:communication-nudge:voice-thread",
    )
    _insert_self_model(
        db,
        canonical_key="self-model:improving:voice-thread",
        status="uncertain",
    )

    _insert_self_authored_prompt_proposal(
        db,
        status="active",
        proposal_type="challenge-nudge",
        canonical_key="self-authored-prompt-proposal:challenge-nudge:challenge-thread",
    )
    _insert_self_review_outcome(
        db,
        canonical_key="self-review-outcome:review-pressure:challenge-thread",
        status="active",
    )

    _insert_self_authored_prompt_proposal(
        db,
        status="fading",
        proposal_type="world-caution-nudge",
        canonical_key="self-authored-prompt-proposal:world-caution-nudge:caution-thread",
    )
    _insert_dream_influence_proposal(
        db,
        canonical_key="dream-influence-proposal:nudge-world-view:caution-thread",
        status="active",
    )

    result = tracking.track_runtime_selfhood_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_selfhood_proposal_surface(limit=8)
    items_by_type = {item["proposal_type"]: item for item in surface["items"]}

    assert result["created"] == 3
    assert surface["active"] is True
    assert items_by_type["voice-shift-proposal"]["selfhood_target"] == "SOUL.md"
    assert items_by_type["challenge-style-proposal"]["status"] == "active"
    assert items_by_type["challenge-style-proposal"]["selfhood_target"] == "IDENTITY.md"
    assert items_by_type["caution-shift-proposal"]["status"] == "fading"
    assert all("Explicit user approval is required" in str(item["proposal_reason"]) for item in surface["items"])


def test_selfhood_proposal_surface_and_mc_shapes_remain_bounded(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.selfhood_proposal_tracking
    mission_control = isolated_runtime.mission_control

    _insert_selfhood_proposal(
        db,
        status="fresh",
        proposal_type="voice-shift-proposal",
        canonical_key="selfhood-proposal:voice-shift-proposal:voice-thread",
    )
    _insert_selfhood_proposal(
        db,
        status="active",
        proposal_type="challenge-style-proposal",
        canonical_key="selfhood-proposal:challenge-style-proposal:challenge-thread",
    )
    _insert_selfhood_proposal(
        db,
        status="fading",
        proposal_type="caution-shift-proposal",
        canonical_key="selfhood-proposal:caution-shift-proposal:caution-thread",
    )
    _insert_selfhood_proposal(
        db,
        status="stale",
        proposal_type="posture-shift-proposal",
        canonical_key="selfhood-proposal:posture-shift-proposal:posture-thread",
    )
    _insert_selfhood_proposal(
        db,
        status="superseded",
        proposal_type="voice-shift-proposal",
        canonical_key="selfhood-proposal:voice-shift-proposal:older-thread",
    )

    surface = tracking.build_runtime_selfhood_proposal_surface(limit=8)
    jarvis = mission_control.mc_jarvis()
    runtime = mission_control.mc_runtime()
    mc_shape = jarvis["development"]["selfhood_proposals"]
    runtime_shape = runtime["runtime_selfhood_proposals"]

    assert {
        "fresh_count",
        "active_count",
        "fading_count",
        "stale_count",
        "superseded_count",
        "current_proposal",
        "current_status",
        "current_proposal_type",
        "current_selfhood_target",
        "current_proposal_confidence",
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
        "selfhood_target",
        "proposed_shift",
        "proposal_reason",
        "proposal_confidence",
        "source_anchor",
    }.issubset(surface["items"][0].keys())
    assert surface["summary"]["fresh_count"] == 1
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["fading_count"] == 1
    assert surface["summary"]["stale_count"] == 1
    assert surface["summary"]["superseded_count"] == 1
    assert mc_shape["summary"]["current_status"] in {"fresh", "active", "fading", "stale"}
    assert runtime_shape["summary"]["current_status"] in {"fresh", "active", "fading", "stale"}
    assert isolated_runtime.db.list_runtime_contract_candidates(target_file="IDENTITY.md", limit=8) == []
    assert isolated_runtime.db.list_runtime_contract_candidates(target_file="SOUL.md", limit=8) == []
