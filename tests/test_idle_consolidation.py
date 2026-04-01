from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.runtime.db import list_private_brain_records


def test_idle_consolidation_builds_bounded_artifact_from_runtime_inputs(isolated_runtime) -> None:
    consolidation = isolated_runtime.idle_consolidation

    plan = consolidation.build_idle_consolidation_from_inputs(
        private_brain_context={
            "active": True,
            "record_count": 2,
            "continuity_summary": "Private brain carries 2 active records.",
        },
        witness_surface={
            "active": True,
            "summary": {"current_signal": "Witnessed turn: bounded shift"},
        },
        emergent_surface={
            "active": True,
            "summary": {"current_signal": "A small emergent thread is cohering."},
        },
        embodied_state={
            "state": "steady",
            "strain_level": "loaded",
            "recovery_state": "steady",
        },
        loop_runtime={
            "summary": {
                "loop_count": 1,
                "current_loop": "Keep calibration thread alive",
                "current_status": "active",
                "current_kind": "open-loop",
                "current_reason": "open-loop-active",
            },
        },
        inner_voice_state={
            "last_result": {"inner_voice_created": True, "focus": "quiet calibration note"},
        },
    )

    assert plan["eligible"] is True
    assert plan["consolidation_state"] == "holding"
    assert len(plan["source_inputs"]) >= 3
    assert plan["artifact"]["kind"] == "private-brain-sleep-consolidation"
    assert plan["artifact"]["visibility"] == "internal-only"
    assert plan["artifact"]["boundary"] == "not-memory-not-identity-not-action"


def test_idle_consolidation_skips_when_visible_activity_too_recent(isolated_runtime) -> None:
    consolidation = isolated_runtime.idle_consolidation

    recent = (datetime.now(UTC) - timedelta(minutes=2)).isoformat()
    result = consolidation.run_idle_consolidation(trigger="test", last_visible_at=recent)

    assert result["consolidation_created"] is False
    assert result["reason"] == "visible-activity-too-recent"
    assert result["boundary"] == "not-memory-not-identity-not-action"


def test_idle_consolidation_cools_down_after_recent_run(isolated_runtime, monkeypatch) -> None:
    consolidation = isolated_runtime.idle_consolidation
    now = datetime.now(UTC)

    monkeypatch.setattr(
        consolidation,
        "_adjacent_producer_block",
        lambda *, now, trigger: None,
    )
    monkeypatch.setattr(
        consolidation,
        "_load_runtime_inputs",
        lambda: {
            "private_brain_context": {
                "active": True,
                "record_count": 1,
                "continuity_summary": "Private brain carries 1 active record.",
            },
            "witness_surface": {"active": True, "summary": {"current_signal": "Witnessed turn"}},
            "emergent_surface": {"active": True, "summary": {"current_signal": "Emergent thread"}},
            "embodied_state": {"state": "steady", "strain_level": "steady", "recovery_state": "steady"},
            "loop_runtime": {"summary": {"loop_count": 1, "current_loop": "thread", "current_status": "standby", "current_kind": "open-loop", "current_reason": "softening"}},
            "inner_voice_state": {"last_result": {"inner_voice_created": True, "focus": "quiet note"}},
            "emergent_daemon_state": {},
        },
    )

    first = consolidation.run_idle_consolidation(trigger="test")
    second = consolidation.run_idle_consolidation(trigger="test")

    assert first["consolidation_created"] is True
    assert second["consolidation_created"] is False
    assert second["reason"] == "cooldown-active"
    assert second["cadence_state"] == "cooling-down"


def test_idle_consolidation_creates_internal_only_private_brain_artifact_and_surface(isolated_runtime, monkeypatch) -> None:
    consolidation = isolated_runtime.idle_consolidation

    monkeypatch.setattr(
        consolidation,
        "_adjacent_producer_block",
        lambda *, now, trigger: None,
    )
    monkeypatch.setattr(
        consolidation,
        "_load_runtime_inputs",
        lambda: {
            "private_brain_context": {
                "active": True,
                "record_count": 2,
                "continuity_summary": "Private brain carries 2 active records.",
            },
            "witness_surface": {"active": True, "summary": {"current_signal": "Witnessed turn"}},
            "emergent_surface": {"active": False, "summary": {"current_signal": ""}},
            "embodied_state": {"state": "steady", "strain_level": "steady", "recovery_state": "recovering"},
            "loop_runtime": {"summary": {"loop_count": 1, "current_loop": "thread", "current_status": "standby", "current_kind": "quiet-held-loop", "current_reason": "quiet-hold-active"}},
            "inner_voice_state": {"last_result": {"inner_voice_created": True, "focus": "quiet note"}},
            "emergent_daemon_state": {},
        },
    )

    result = consolidation.run_idle_consolidation(trigger="test")
    records = [
        item
        for item in list_private_brain_records(limit=10)
        if item["record_type"] == "sleep-consolidation"
    ]
    surface = consolidation.build_idle_consolidation_surface()

    assert result["consolidation_created"] is True
    assert len(records) == 1
    assert records[0]["layer"] == "private_brain"
    assert records[0]["session_id"] == ""
    assert surface["visibility"] == "internal-only"
    assert surface["boundary"] == "not-memory-not-identity-not-action"
    assert surface["summary"]["latest_record_id"] == records[0]["record_id"]


def test_mission_control_runtime_and_endpoint_expose_idle_consolidation(isolated_runtime, monkeypatch) -> None:
    mission_control = isolated_runtime.mission_control

    runtime_surface = {
        "active": True,
        "authority": "authoritative",
        "visibility": "internal-only",
        "kind": "sleep-consolidation-light",
        "boundary": "not-memory-not-identity-not-action",
        "last_run_at": "2026-04-01T10:00:00+00:00",
        "last_result": {"reason": "consolidated"},
        "latest_artifact": {"record_id": "pb-sleep-1", "summary": "Idle consolidation summary"},
        "summary": {
            "last_state": "settling",
            "last_reason": "consolidated",
            "last_output_kind": "private-brain-sleep-consolidation",
            "source_input_count": 4,
            "latest_record_id": "pb-sleep-1",
            "latest_summary": "Idle consolidation summary",
        },
        "source": "/mc/idle-consolidation",
        "built_at": "2026-04-01T10:00:00+00:00",
    }

    monkeypatch.setattr(
        isolated_runtime.idle_consolidation,
        "build_idle_consolidation_surface",
        lambda: runtime_surface,
    )
    monkeypatch.setattr(mission_control, "build_idle_consolidation_surface", lambda: runtime_surface)

    endpoint = mission_control.mc_idle_consolidation()
    runtime = mission_control.mc_runtime()

    assert endpoint["kind"] == "sleep-consolidation-light"
    assert endpoint["visibility"] == "internal-only"
    assert runtime["runtime_idle_consolidation"]["summary"]["last_state"] == "settling"
    assert runtime["runtime_idle_consolidation"]["boundary"] == "not-memory-not-identity-not-action"
