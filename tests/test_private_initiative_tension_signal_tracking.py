from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def _insert_visible_work_note(
    db,
    *,
    run_id: str,
    status: str,
    capability_id: str = "workspace-search",
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
                "Follow the current bounded work thread.",
                capability_id,
                "Inspected the current bounded work thread and narrowed the issue.",
                "visible-selected-work-item",
                now,
                now,
            ),
        )
        conn.commit()


def _insert_private_inner_note_signal(db, *, run_id: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_private_inner_note_signal(
        signal_id=f"private-inner-note-signal-{uuid4().hex}",
        signal_type="private-inner-note",
        canonical_key="private-inner-note:work-status:workspace-search",
        status="active",
        title="Private inner note support: workspace search",
        summary="Bounded runtime support remains subordinate to visible work.",
        rationale="Validation private inner note support",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="visible note evidence",
        support_summary="Derived from the latest visible work note and kept non-authoritative. | Visible work note visible-work-note:test",
        status_reason="Validation private inner note support",
        run_id=run_id,
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def _insert_open_loop(db, *, canonical_key: str, status: str = "open") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_open_loop_signal(
        signal_id=f"open-loop-{uuid4().hex}",
        signal_type="persistent-open-loop" if status == "open" else "softening-loop",
        canonical_key=canonical_key,
        status=status,
        title="Open loop: workspace search",
        summary="A bounded loop around workspace search is still unresolved and carrying live pressure.",
        rationale="Validation open loop",
        source_kind="derived-runtime-open-loop",
        confidence="medium",
        evidence_summary="open loop evidence",
        support_summary="open loop support",
        support_count=2,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="The bounded thread is still visibly unresolved.",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_focus(db, *, canonical_key: str, status: str = "active") -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_development_focus(
        focus_id=f"focus-{uuid4().hex}",
        focus_type="communication-calibration",
        canonical_key=canonical_key,
        status=status,
        title="Development focus: workspace search calibration",
        summary="Active focus for workspace search calibration",
        rationale="Validation focus",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="focus evidence",
        support_summary="focus support",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
        status_reason="Validation focus status",
        run_id="test-run",
        session_id="test-session",
    )


def _insert_private_initiative_tension_signal(db, *, status: str, canonical_key: str, title: str) -> None:
    now = datetime.now(UTC).isoformat()
    db.upsert_runtime_private_initiative_tension_signal(
        signal_id=f"private-initiative-tension-signal-{uuid4().hex}",
        signal_type="private-initiative-tension",
        canonical_key=canonical_key,
        status=status,
        title=title,
        summary="Bounded runtime initiative tension is carrying current pressure.",
        rationale="Validation initiative tension support signal",
        source_kind="runtime-derived-support",
        confidence="medium",
        evidence_summary="initiative tension evidence",
        support_summary="Derived from visible work plus bounded runtime support layers.",
        status_reason="Validation bounded initiative tension support",
        run_id="test-run",
        session_id="test-session",
        support_count=1,
        session_count=1,
        created_at=now,
        updated_at=now,
    )


def test_private_initiative_tension_surface_stays_empty_without_relevant_grounding(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.private_initiative_tension_signal_tracking
    db = isolated_runtime.db

    _insert_visible_work_note(db, run_id="visible-run-1", status="completed")

    result = tracking.track_runtime_private_initiative_tension_signals_for_visible_turn(
        session_id="test-session",
        run_id="visible-run-1",
    )
    surface = tracking.build_runtime_private_initiative_tension_signal_surface(limit=8)

    assert result["created"] == 0
    assert result["updated"] == 0
    assert surface["active"] is False
    assert surface["items"] == []
    assert surface["summary"]["active_count"] == 0
    assert surface["summary"]["authority"] == "non-authoritative"


def test_private_initiative_tension_surface_forms_bounded_runtime_support_from_visible_work_and_pressure(
    isolated_runtime,
) -> None:
    tracking = isolated_runtime.private_initiative_tension_signal_tracking
    db = isolated_runtime.db

    _insert_visible_work_note(db, run_id="visible-run-2", status="failed")
    _insert_private_inner_note_signal(db, run_id="visible-run-2")
    _insert_open_loop(
        db,
        canonical_key="open-loop:persistent-open-loop:workspace-search",
        status="open",
    )

    result = tracking.track_runtime_private_initiative_tension_signals_for_visible_turn(
        session_id="test-session",
        run_id="visible-run-2",
    )
    surface = tracking.build_runtime_private_initiative_tension_signal_surface(limit=8)
    item = surface["items"][0]

    assert result["created"] == 1
    assert surface["active"] is True
    assert item["signal_type"] == "private-initiative-tension"
    assert item["tension_type"] == "unresolved"
    assert item["tension_level"] == "medium"
    assert item["authority"] == "non-authoritative"
    assert item["layer_role"] == "runtime-support"
    assert item["status"] == "active"
    assert "execution authority" in item["status_reason"].lower()
    assert "visible-work-note:visible-run-2" in item["source_anchor"]


def test_private_initiative_tension_surface_and_mc_shapes_remain_bounded(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    tracking = isolated_runtime.private_initiative_tension_signal_tracking
    mission_control = isolated_runtime.mission_control

    _insert_private_initiative_tension_signal(
        db,
        status="active",
        canonical_key="private-initiative-tension:unresolved:workspace-search",
        title="Private initiative tension support: workspace search",
    )
    _insert_private_initiative_tension_signal(
        db,
        status="stale",
        canonical_key="private-initiative-tension:retention-pull:visible-work",
        title="Private initiative tension support: visible work",
    )
    _insert_private_initiative_tension_signal(
        db,
        status="superseded",
        canonical_key="private-initiative-tension:curiosity-pull:archive-focus",
        title="Private initiative tension support: archive focus",
    )

    surface = tracking.build_runtime_private_initiative_tension_signal_surface(limit=8)
    jarvis = mission_control.mc_jarvis()
    runtime = mission_control.mc_runtime()
    mc_shape = jarvis["development"]["private_initiative_tension_signals"]
    runtime_shape = runtime["runtime_private_initiative_tension_signals"]

    assert {
        "active_count",
        "stale_count",
        "superseded_count",
        "current_signal",
        "current_status",
        "current_tension_type",
        "current_intensity",
        "current_confidence",
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
        "tension_type",
        "tension_target",
        "tension_level",
        "tension_summary",
        "tension_confidence",
        "source_anchor",
        "authority",
        "layer_role",
    }.issubset(surface["items"][0].keys())
    assert surface["summary"]["active_count"] == 1
    assert surface["summary"]["stale_count"] == 1
    assert surface["summary"]["superseded_count"] == 1
    assert mc_shape["summary"]["authority"] == "non-authoritative"
    assert runtime_shape["summary"]["layer_role"] == "runtime-support"
