from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def _insert_user_understanding_signal(db, *, status: str, signal_type: str, canonical_key: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_user_understanding_signal(
        signal_id=f"user-understanding-{uuid4().hex}",
        signal_type=signal_type,
        canonical_key=canonical_key,
        status=status,
        title=f"User understanding: {signal_type}",
        summary=f"Signal summary: {signal_type}",
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


def test_user_understanding_surface_stays_empty_without_relevant_grounding(isolated_runtime) -> None:
    tracking = isolated_runtime.user_understanding_signal_tracking
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

    result = tracking.track_runtime_user_understanding_signals_for_visible_turn(
        session_id=str(session["id"]),
        run_id="test-run",
        user_message="Can you help me debug this endpoint?",
    )
    surface = tracking.build_runtime_user_understanding_signal_surface(limit=8)

    assert result["created"] == 0
    assert result["updated"] == 0
    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["summary"]["active_count"] == 0
    assert surface["summary"]["softening_count"] == 0


def test_user_understanding_surface_forms_small_bounded_signals_from_recent_interaction(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.user_understanding_signal_tracking
    chat_sessions = __import__(
        "apps.api.jarvis_api.services.chat_sessions",
        fromlist=["create_chat_session", "append_chat_message"],
    )

    session = chat_sessions.create_chat_session(title="Preference session")
    chat_sessions.append_chat_message(
        session_id=str(session["id"]),
        role="user",
        content="jeg vil gerne have du snakker dansk osse selv hvis jeg skriver på eng.",
    )
    chat_sessions.append_chat_message(
        session_id=str(session["id"]),
        role="user",
        content="hold blokken lille og ingen opportunistiske refactors.",
    )
    chat_sessions.append_chat_message(
        session_id=str(session["id"]),
        role="user",
        content="rapportér præcist hver turn med exact files inspected/changed.",
    )

    result = tracking.track_runtime_user_understanding_signals_for_visible_turn(
        session_id=str(session["id"]),
        run_id="test-run",
        user_message="rapportér præcist hver turn med exact files inspected/changed.",
    )
    surface = tracking.build_runtime_user_understanding_signal_surface(limit=8)
    items_by_dimension = {item["user_dimension"]: item for item in surface["items"]}

    assert result["created"] == 4
    assert surface["active"] is True
    assert surface["summary"]["active_count"] == 3
    assert surface["summary"]["softening_count"] == 1
    assert items_by_dimension["language-preference"]["signal_type"] == "preference-signal"
    assert items_by_dimension["language-preference"]["signal_confidence"] == "high"
    assert items_by_dimension["workstyle"]["signal_type"] == "workstyle-signal"
    assert items_by_dimension["workstyle"]["status"] == "active"
    assert items_by_dimension["reminder-worthiness"]["signal_type"] == "reminder-worthiness-signal"
    assert items_by_dimension["reporting-cadence"]["signal_type"] == "cadence-preference-signal"
    assert items_by_dimension["reporting-cadence"]["status"] == "softening"


def test_user_understanding_surface_and_mc_shapes_remain_bounded(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.user_understanding_signal_tracking
    mission_control = isolated_runtime.mission_control

    _insert_user_understanding_signal(
        db,
        status="active",
        signal_type="preference-signal",
        canonical_key="user-understanding:preference-signal:language-preference",
    )
    _insert_user_understanding_signal(
        db,
        status="softening",
        signal_type="workstyle-signal",
        canonical_key="user-understanding:workstyle-signal:workstyle",
    )
    _insert_user_understanding_signal(
        db,
        status="stale",
        signal_type="cadence-preference-signal",
        canonical_key="user-understanding:cadence-preference-signal:reporting-cadence",
    )
    _insert_user_understanding_signal(
        db,
        status="superseded",
        signal_type="reminder-worthiness-signal",
        canonical_key="user-understanding:reminder-worthiness-signal:reminder-worthiness",
    )

    surface = tracking.build_runtime_user_understanding_signal_surface(limit=8)
    jarvis = mission_control.mc_jarvis()
    runtime = mission_control.mc_runtime()
    mc_shape = jarvis["development"]["user_understanding_signals"]
    runtime_shape = runtime["runtime_user_understanding_signals"]

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
        "user_dimension",
        "signal_summary",
        "signal_confidence",
        "source_anchor",
    }.issubset(surface["items"][0].keys())
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["softening_count"] == 1
    assert surface["summary"]["stale_count"] == 1
    assert surface["summary"]["superseded_count"] == 1
    assert mc_shape["summary"]["current_status"] in {"active", "softening", "stale"}
    assert runtime_shape["summary"]["current_status"] in {"active", "softening", "stale"}
