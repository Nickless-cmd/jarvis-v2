from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def _insert_remembered_fact_signal(db, *, status: str, signal_type: str, canonical_key: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_remembered_fact_signal(
        signal_id=f"remembered-fact-{uuid4().hex}",
        signal_type=signal_type,
        canonical_key=canonical_key,
        status=status,
        title=f"Remembered fact: {signal_type}",
        summary=f"Signal summary: {signal_type}",
        rationale="Validation remembered-fact signal",
        source_kind="user-explicit",
        confidence="medium",
        evidence_summary="remembered-fact signal evidence",
        support_summary="remembered-fact signal support | Visible user anchor: validation anchor",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation remembered-fact signal status",
        run_id="test-run",
        session_id="test-session",
    )


def test_remembered_fact_surface_stays_empty_without_relevant_grounding(isolated_runtime) -> None:
    tracking = isolated_runtime.remembered_fact_signal_tracking
    chat_sessions = __import__(
        "apps.api.jarvis_api.services.chat_sessions",
        fromlist=["create_chat_session", "append_chat_message"],
    )

    session = chat_sessions.create_chat_session(title="Generic session")
    chat_sessions.append_chat_message(
        session_id=str(session["id"]),
        role="user",
        content="Can you help me debug this endpoint?",
    )

    result = tracking.track_runtime_remembered_fact_signals_for_visible_turn(
        session_id=str(session["id"]),
        run_id="test-run",
        user_message="Can you help me debug this endpoint?",
    )
    surface = tracking.build_runtime_remembered_fact_signal_surface(limit=8)

    assert result["created"] == 0
    assert result["updated"] == 0
    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["summary"]["active_count"] == 0
    assert surface["summary"]["softening_count"] == 0


def test_remembered_fact_surface_forms_small_bounded_signals_from_recent_interaction(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.remembered_fact_signal_tracking
    chat_sessions = __import__(
        "apps.api.jarvis_api.services.chat_sessions",
        fromlist=["create_chat_session", "append_chat_message"],
    )

    session = chat_sessions.create_chat_session(title="Remembered fact session")
    chat_sessions.append_chat_message(
        session_id=str(session["id"]),
        role="user",
        content="Mit navn er Bjorn.",
    )
    chat_sessions.append_chat_message(
        session_id=str(session["id"]),
        role="user",
        content="Vi bygger Jarvis sammen i den her turn.",
    )
    chat_sessions.append_chat_message(
        session_id=str(session["id"]),
        role="user",
        content="Du arbejder i Jarvis v2-repoet lige nu.",
    )

    result = tracking.track_runtime_remembered_fact_signals_for_visible_turn(
        session_id=str(session["id"]),
        run_id="test-run",
        user_message="Du arbejder i Jarvis v2-repoet lige nu.",
    )
    surface = tracking.build_runtime_remembered_fact_signal_surface(limit=8)
    items_by_kind = {item["fact_kind"]: item for item in surface["items"]}

    assert result["created"] == 3
    assert surface["active"] is True
    assert surface["summary"]["active_count"] == 2
    assert surface["summary"]["softening_count"] == 1
    assert items_by_kind["user-name"]["signal_type"] == "explicit-user-fact"
    assert items_by_kind["user-name"]["signal_confidence"] == "high"
    assert items_by_kind["project-anchor"]["signal_type"] == "explicit-project-fact"
    assert items_by_kind["project-anchor"]["status"] == "active"
    assert items_by_kind["repo-context"]["signal_type"] == "explicit-working-context-fact"
    assert items_by_kind["repo-context"]["status"] == "softening"


def test_remembered_fact_surface_recognizes_explicit_repo_path_context(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.remembered_fact_signal_tracking
    chat_sessions = __import__(
        "apps.api.jarvis_api.services.chat_sessions",
        fromlist=["create_chat_session", "append_chat_message"],
    )

    session = chat_sessions.create_chat_session(title="Repo path context")
    message = "Husk at vi arbejder i /media/projects/jarvis-v2 og bruger ~/.jarvis-v2/workspaces/default som workspace."
    chat_sessions.append_chat_message(
        session_id=str(session["id"]),
        role="user",
        content=message,
    )

    result = tracking.track_runtime_remembered_fact_signals_for_visible_turn(
        session_id=str(session["id"]),
        run_id="test-run",
        user_message=message,
    )
    surface = tracking.build_runtime_remembered_fact_signal_surface(limit=8)
    items_by_kind = {item["fact_kind"]: item for item in surface["items"]}

    assert result["created"] >= 1
    assert items_by_kind["repo-context"]["signal_type"] == "explicit-working-context-fact"


def test_remembered_fact_surface_and_mc_shapes_remain_bounded(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.remembered_fact_signal_tracking
    mission_control = isolated_runtime.mission_control

    _insert_remembered_fact_signal(
        db,
        status="active",
        signal_type="explicit-user-fact",
        canonical_key="remembered-fact:explicit-user-fact:user-name",
    )
    _insert_remembered_fact_signal(
        db,
        status="softening",
        signal_type="explicit-working-context-fact",
        canonical_key="remembered-fact:explicit-working-context-fact:repo-context",
    )
    _insert_remembered_fact_signal(
        db,
        status="stale",
        signal_type="explicit-project-fact",
        canonical_key="remembered-fact:explicit-project-fact:project-anchor",
    )
    _insert_remembered_fact_signal(
        db,
        status="superseded",
        signal_type="explicit-project-fact",
        canonical_key="remembered-fact:explicit-project-fact:older-anchor",
    )

    surface = tracking.build_runtime_remembered_fact_signal_surface(limit=8)
    jarvis = mission_control.mc_jarvis()
    runtime = mission_control.mc_runtime()
    mc_shape = jarvis["continuity"]["remembered_fact_signals"]
    runtime_shape = runtime["runtime_remembered_fact_signals"]

    assert {
        "active_count",
        "softening_count",
        "stale_count",
        "superseded_count",
        "current_signal",
        "current_status",
        "current_signal_type",
        "current_signal_confidence",
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
        "fact_kind",
        "fact_summary",
        "signal_confidence",
        "source_anchor",
    }.issubset(surface["items"][0].keys())
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["softening_count"] == 1
    assert surface["summary"]["stale_count"] == 1
    assert surface["summary"]["superseded_count"] == 1
    assert mc_shape["summary"]["current_status"] in {"active", "softening", "stale"}
    assert runtime_shape["summary"]["current_status"] in {"active", "softening", "stale"}
