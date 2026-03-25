from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4


def _insert_reflection_signal(db, *, status: str, signal_type: str, title: str, minutes_ago: int = 0) -> None:
    ts = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    db.upsert_runtime_reflection_signal(
        signal_id=f"reflection-{uuid4().hex}",
        signal_type=signal_type,
        canonical_key=f"reflection-signal:{signal_type}:{uuid4().hex}",
        status=status,
        title=title,
        summary=f"{title} summary",
        rationale=f"{title} rationale",
        source_kind="multi-signal-runtime-derivation",
        confidence="high" if status == "active" else "medium",
        evidence_summary=f"{title} evidence",
        support_summary=f"{title} support",
        support_count=2,
        session_count=1,
        created_at=ts.isoformat(),
        updated_at=ts.isoformat(),
        status_reason=f"{title} status reason",
        run_id="test-run",
        session_id="test-session",
    )


def test_reflection_surface_includes_relevant_signal_and_bounded_history(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.reflection_tracking

    _insert_reflection_signal(
        db,
        status="active",
        signal_type="persistent-tension",
        title="Persistent reflection tension: Danish concise calibration",
        minutes_ago=5,
    )
    for index in range(7):
        _insert_reflection_signal(
            db,
            status="settled",
            signal_type="settled-thread",
            title=f"Settled reflection thread {index}",
            minutes_ago=30 + index,
        )

    surface = tracking.build_runtime_reflection_signal_surface(limit=8)

    assert surface["active"] is True
    assert surface["summary"]["active_count"] == 1
    assert any(item["status"] == "active" for item in surface["items"])
    assert len(surface["recent_history"]) == 6

    history_item = surface["recent_history"][0]
    assert {
        "signal_id",
        "signal_type",
        "title",
        "status",
        "transition",
        "confidence",
        "summary",
        "status_reason",
        "updated_at",
        "created_at",
    }.issubset(history_item.keys())


def test_reflection_surface_tracks_lifecycle_counts_without_promoting_irrelevant_states(isolated_runtime) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.reflection_tracking

    _insert_reflection_signal(db, status="active", signal_type="persistent-tension", title="Active thread")
    _insert_reflection_signal(db, status="integrating", signal_type="slow-integration", title="Integrating thread")
    _insert_reflection_signal(db, status="settled", signal_type="settled-thread", title="Settled thread")
    _insert_reflection_signal(db, status="stale", signal_type="persistent-tension", title="Stale thread")
    _insert_reflection_signal(db, status="superseded", signal_type="settled-thread", title="Superseded thread")

    surface = tracking.build_runtime_reflection_signal_surface(limit=8)

    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["integrating_count"] == 1
    assert surface["summary"]["settled_count"] == 1
    assert surface["summary"]["stale_count"] == 1
    assert surface["summary"]["superseded_count"] == 1
    assert surface["summary"]["current_status"] in {"active", "integrating", "settled"}


def test_reflection_surface_is_bounded_when_no_relevant_signals_exist(isolated_runtime) -> None:
    tracking = isolated_runtime.reflection_tracking

    surface = tracking.build_runtime_reflection_signal_surface(limit=8)

    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["recent_history"] == []
    assert surface["summary"]["active_count"] == 0
    assert surface["summary"]["integrating_count"] == 0
    assert surface["summary"]["settled_count"] == 0
