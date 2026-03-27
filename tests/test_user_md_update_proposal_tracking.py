from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def _insert_user_understanding_signal(
    db,
    *,
    status: str,
    signal_type: str,
    canonical_key: str,
    summary: str | None = None,
) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_user_understanding_signal(
        signal_id=f"user-understanding-{uuid4().hex}",
        signal_type=signal_type,
        canonical_key=canonical_key,
        status=status,
        title=f"User understanding: {signal_type}",
        summary=summary or f"Signal summary: {signal_type}",
        rationale="Validation user-understanding signal",
        source_kind="user-explicit",
        confidence="medium",
        evidence_summary="user-understanding signal evidence",
        support_summary="user-understanding signal support | Visible user anchor: validation anchor",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation user-understanding signal status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_user_md_update_proposal(db, *, status: str, proposal_type: str, canonical_key: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_user_md_update_proposal(
        proposal_id=f"user-md-update-proposal-{uuid4().hex}",
        proposal_type=proposal_type,
        canonical_key=canonical_key,
        status=status,
        title=f"USER.md update proposal: {proposal_type}",
        summary=f"Proposal summary: {proposal_type}",
        rationale="Validation USER.md update proposal",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="USER.md update proposal evidence",
        support_summary="USER.md update proposal support",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation USER.md update proposal status",
        run_id="test-run",
        session_id="test-session",
    )


def test_user_md_update_proposal_surface_stays_empty_without_relevant_prompt_grounding(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.user_md_update_proposal_tracking

    _insert_user_understanding_signal(
        db,
        status="superseded",
        signal_type="preference-signal",
        canonical_key="user-understanding:preference-signal:language-preference",
    )

    result = tracking.track_runtime_user_md_update_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_user_md_update_proposal_surface(limit=8)

    assert result["created"] == 0
    assert result["updated"] == 0
    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["summary"]["fresh_count"] == 0
    assert surface["summary"]["active_count"] == 0
    assert surface["summary"]["fading_count"] == 0


def test_user_md_update_proposal_surface_forms_small_bounded_proposals_from_user_understanding(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.user_md_update_proposal_tracking

    _insert_user_understanding_signal(
        db,
        status="active",
        signal_type="preference-signal",
        canonical_key="user-understanding:preference-signal:reply-style",
        summary="User is explicitly asking for concise, direct replies.",
    )
    _insert_user_understanding_signal(
        db,
        status="active",
        signal_type="workstyle-signal",
        canonical_key="user-understanding:workstyle-signal:workstyle",
        summary="User is steering toward tightly scoped changes with minimal opportunistic cleanup.",
    )
    _insert_user_understanding_signal(
        db,
        status="softening",
        signal_type="cadence-preference-signal",
        canonical_key="user-understanding:cadence-preference-signal:reporting-cadence",
        summary="User prefers a consistent exact reporting shape on scoped turns.",
    )
    _insert_user_understanding_signal(
        db,
        status="active",
        signal_type="reminder-worthiness-signal",
        canonical_key="user-understanding:reminder-worthiness-signal:reminder-worthiness",
        summary="User is marking a collaboration preference as something to carry forward across turns.",
    )

    result = tracking.track_runtime_user_md_update_proposals_for_visible_turn(
        session_id="test-session",
        run_id="test-run",
    )
    surface = tracking.build_runtime_user_md_update_proposal_surface(limit=8)
    items_by_type = {item["proposal_type"]: item for item in surface["items"]}

    assert result["created"] == 4
    assert surface["active"] is True
    assert surface["summary"]["fresh_count"] == 3
    assert surface["summary"]["active_count"] == 0
    assert surface["summary"]["fading_count"] == 1
    assert items_by_type["preference-update"]["user_dimension"] == "reply-style"
    assert items_by_type["preference-update"]["status"] == "fresh"
    assert items_by_type["workstyle-update"]["user_dimension"] == "workstyle"
    assert items_by_type["workstyle-update"]["status"] == "fresh"
    assert items_by_type["cadence-preference-update"]["user_dimension"] == "cadence-preference"
    assert items_by_type["cadence-preference-update"]["status"] == "fading"
    assert items_by_type["reminder-worthiness-update"]["user_dimension"] == "reminder-worthiness"
    assert items_by_type["reminder-worthiness-update"]["proposal_confidence"] == "medium"
    assert items_by_type["preference-update"]["proposal_reason"] == "User is explicitly asking for concise, direct replies."


def test_user_md_update_proposal_surface_and_mc_shapes_remain_bounded(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.user_md_update_proposal_tracking
    mission_control = isolated_runtime.mission_control

    _insert_user_md_update_proposal(
        db,
        status="fresh",
        proposal_type="preference-update",
        canonical_key="user-md-update-proposal:preference-update:reply-style",
    )
    _insert_user_md_update_proposal(
        db,
        status="active",
        proposal_type="workstyle-update",
        canonical_key="user-md-update-proposal:workstyle-update:workstyle",
    )
    _insert_user_md_update_proposal(
        db,
        status="fading",
        proposal_type="cadence-preference-update",
        canonical_key="user-md-update-proposal:cadence-preference-update:cadence-preference",
    )
    _insert_user_md_update_proposal(
        db,
        status="stale",
        proposal_type="reminder-worthiness-update",
        canonical_key="user-md-update-proposal:reminder-worthiness-update:reminder-worthiness",
    )
    _insert_user_md_update_proposal(
        db,
        status="superseded",
        proposal_type="preference-update",
        canonical_key="user-md-update-proposal:preference-update:older-style",
    )

    surface = tracking.build_runtime_user_md_update_proposal_surface(limit=8)
    jarvis = mission_control.mc_jarvis()
    runtime = mission_control.mc_runtime()
    mc_shape = jarvis["development"]["user_md_update_proposals"]
    runtime_shape = runtime["runtime_user_md_update_proposals"]

    assert {
        "fresh_count",
        "active_count",
        "fading_count",
        "stale_count",
        "superseded_count",
        "current_proposal",
        "current_status",
        "current_proposal_type",
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
        "user_dimension",
        "proposed_update",
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
