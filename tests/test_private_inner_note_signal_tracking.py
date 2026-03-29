from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4


def _insert_visible_work_note(
    db, *, run_id: str, status: str, capability_id: str = "workspace-search"
) -> None:
    now = datetime.now(UTC).isoformat()
    with db.connect() as conn:
        conn.execute(
            """
            INSERT INTO visible_work_notes (
                note_id, work_id, run_id, status, lane, provider, model,
                user_message_preview, capability_id, work_preview,
                projection_source, created_at, finished_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"visible-work-note:{run_id}",
                f"visible-work:{run_id}",
                run_id,
                status,
                "local",
                "ollama",
                "qwen3.5:9b",
                "Find the failing endpoint and explain it.",
                capability_id,
                "Investigated the visible work unit and narrowed the failing endpoint path.",
                "visible-selected-work-item",
                now,
                now,
            ),
        )
        conn.commit()


def _insert_private_inner_note_signal(
    db, *, status: str, canonical_key: str, title: str
) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_private_inner_note_signal(
        signal_id=f"private-inner-note-signal-{uuid4().hex}",
        signal_type="private-inner-note",
        canonical_key=canonical_key,
        status=status,
        title=title,
        summary="Bounded runtime support remains subordinate to visible work.",
        rationale="Validation private inner note support signal",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary='"Investigated the visible work unit and narrowed the failing endpoint path."',
        support_summary="Derived from the latest visible work note and kept non-authoritative.",
        status_reason="Validation bounded private inner note support",
        run_id="test-run",
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def test_private_inner_note_surface_stays_empty_without_visible_grounding(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.private_inner_note_signal_tracking

    result = tracking.track_runtime_private_inner_note_signals_for_visible_turn(
        session_id="test-session",
        run_id="missing-run",
    )
    surface = tracking.build_runtime_private_inner_note_signal_surface(limit=8)

    assert result["created"] == 0
    assert result["updated"] == 0
    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["summary"]["active_count"] == 0
    assert surface["summary"]["authority"] == "non-authoritative"


def test_private_inner_note_surface_forms_bounded_runtime_support_from_visible_work(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.private_inner_note_signal_tracking
    db = isolated_runtime.db

    _insert_visible_work_note(db, run_id="visible-run-1", status="completed")
    result = tracking.track_runtime_private_inner_note_signals_for_visible_turn(
        session_id="test-session",
        run_id="visible-run-1",
    )
    surface = tracking.build_runtime_private_inner_note_signal_surface(limit=8)
    item = surface["items"][0]

    assert result["created"] == 1
    assert surface["active"] is True
    assert item["signal_type"] == "private-inner-note"
    assert item["note_type"] == "work-status-signal"
    assert item["identity_alignment"] == "subordinate-to-visible"
    assert item["authority"] == "non-authoritative"
    assert item["layer_role"] == "runtime-support"
    assert item["status"] == "active"
    assert item["note_confidence"] in {"low", "medium"}
    assert "visible-work-note:visible-run-1" in item["source_anchor"]
    assert item["inner_voice_source_state"] == "private-runtime-grounded"
    assert item["contamination_state"] == "decontaminated-from-visible-summary"
    assert "Find the failing endpoint and explain it." not in item["note_summary"]
    assert "Investigated the visible work unit" not in item["note_summary"]
    assert "kind=" not in item["note_summary"]
    assert "status=" not in item["note_summary"]
    assert (
        "bounded" in item["support_summary"].lower()
        or "subordinate" in item["support_summary"].lower()
    )


def test_private_inner_note_surface_and_mc_shapes_remain_bounded(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.private_inner_note_signal_tracking
    mission_control = isolated_runtime.mission_control

    _insert_private_inner_note_signal(
        db,
        status="active",
        canonical_key="private-inner-note:work-status:workspace-search",
        title="Private inner note support: workspace search",
    )
    _insert_private_inner_note_signal(
        db,
        status="stale",
        canonical_key="private-inner-note:work-status:visible-work",
        title="Private inner note support: visible work",
    )
    _insert_private_inner_note_signal(
        db,
        status="superseded",
        canonical_key="private-inner-note:work-status:archive-focus",
        title="Private inner note support: archive focus",
    )

    surface = tracking.build_runtime_private_inner_note_signal_surface(limit=8)
    jarvis = mission_control.mc_jarvis()
    runtime = mission_control.mc_runtime()
    mc_shape = jarvis["development"]["private_inner_note_signals"]
    runtime_shape = runtime["runtime_private_inner_note_signals"]

    assert {
        "active_count",
        "stale_count",
        "superseded_count",
        "current_signal",
        "current_status",
        "current_note_type",
        "current_confidence",
        "current_source_state",
        "current_contamination_state",
        "authority",
        "layer_role",
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
        "note_type",
        "note_summary",
        "note_confidence",
        "source_anchor",
        "inner_voice_source_state",
        "contamination_state",
        "authority",
        "layer_role",
    }.issubset(surface["items"][0].keys())
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["stale_count"] == 1
    assert surface["summary"]["superseded_count"] == 1
    assert mc_shape["summary"]["authority"] == "non-authoritative"
    assert runtime_shape["summary"]["layer_role"] == "runtime-support"
