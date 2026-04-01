from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.runtime.db import list_runtime_dream_hypothesis_signals


def test_dream_articulation_builds_bounded_candidate_from_runtime_inputs(isolated_runtime) -> None:
    articulation = isolated_runtime.dream_articulation

    plan = articulation.build_dream_articulation_from_inputs(
        idle_consolidation={
            "summary": {"latest_summary": "Idle consolidation settled a held thread.", "last_state": "settling"},
            "latest_artifact": {"summary": "Idle consolidation settled a held thread."},
        },
        inner_voice_state={
            "last_result": {"inner_voice_created": True, "focus": "quiet calibration image"},
        },
        emergent_surface={
            "active": True,
            "summary": {"current_signal": "A small emergent thread is cohering."},
        },
        witness_surface={
            "active": True,
            "summary": {"current_signal": "Witnessed turn: bounded shift"},
        },
        loop_runtime={
            "summary": {
                "loop_count": 1,
                "current_loop": "Keep calibration alive",
                "current_status": "active",
                "current_kind": "open-loop",
            },
        },
        embodied_state={
            "state": "steady",
            "strain_level": "loaded",
            "recovery_state": "steady",
        },
    )

    assert plan["eligible"] is True
    assert plan["candidate_state"] in {"pressing", "forming", "tentative"}
    assert len(plan["source_inputs"]) >= 3
    assert plan["artifact"]["canonical_key"].startswith("dream-articulation:")


def test_dream_articulation_skips_when_visible_activity_too_recent(isolated_runtime) -> None:
    articulation = isolated_runtime.dream_articulation
    recent = (datetime.now(UTC) - timedelta(minutes=2)).isoformat()

    result = articulation.run_dream_articulation(trigger="test", last_visible_at=recent)

    assert result["candidate_created"] is False
    assert result["reason"] == "visible-activity-too-recent"
    assert result["candidate_truth"] == "candidate-only"


def test_dream_articulation_cools_down_after_recent_run(isolated_runtime, monkeypatch) -> None:
    articulation = isolated_runtime.dream_articulation

    monkeypatch.setattr(
        articulation,
        "_adjacent_producer_block",
        lambda *, now, trigger: None,
    )
    monkeypatch.setattr(
        articulation,
        "_load_runtime_inputs",
        lambda: {
            "idle_consolidation": {
                "summary": {"latest_summary": "Idle consolidation settled a thread.", "last_state": "settling"},
                "latest_artifact": {"summary": "Idle consolidation settled a thread."},
            },
            "inner_voice_state": {"last_result": {"inner_voice_created": True, "focus": "quiet image"}},
            "emergent_surface": {"active": True, "summary": {"current_signal": "Emergent thread"}},
            "witness_surface": {"active": True, "summary": {"current_signal": "Witnessed turn"}},
            "loop_runtime": {"summary": {"loop_count": 1, "current_loop": "thread", "current_status": "standby", "current_kind": "quiet-held-loop"}},
            "embodied_state": {"state": "steady", "strain_level": "steady", "recovery_state": "steady"},
        },
    )

    first = articulation.run_dream_articulation(trigger="test")
    second = articulation.run_dream_articulation(trigger="test")

    assert first["candidate_created"] is True
    assert second["candidate_created"] is False
    assert second["reason"] == "cooldown-active"
    assert second["cadence_state"] == "cooling-down"


def test_dream_articulation_persists_candidate_only_internal_signal_and_surface(isolated_runtime, monkeypatch) -> None:
    articulation = isolated_runtime.dream_articulation

    monkeypatch.setattr(
        articulation,
        "_adjacent_producer_block",
        lambda *, now, trigger: None,
    )
    monkeypatch.setattr(
        articulation,
        "_load_runtime_inputs",
        lambda: {
            "idle_consolidation": {
                "summary": {"latest_summary": "Idle consolidation settled a thread.", "last_state": "holding"},
                "latest_artifact": {"summary": "Idle consolidation settled a thread."},
            },
            "inner_voice_state": {"last_result": {"inner_voice_created": True, "focus": "quiet image"}},
            "emergent_surface": {"active": False, "summary": {"current_signal": ""}},
            "witness_surface": {"active": True, "summary": {"current_signal": "Witnessed turn"}},
            "loop_runtime": {"summary": {"loop_count": 1, "current_loop": "thread", "current_status": "standby", "current_kind": "quiet-held-loop"}},
            "embodied_state": {"state": "steady", "strain_level": "steady", "recovery_state": "recovering"},
        },
    )

    result = articulation.run_dream_articulation(trigger="test")
    items = [
        item
        for item in list_runtime_dream_hypothesis_signals(limit=10)
        if item["source_kind"] == "internal-dream-articulation"
    ]
    surface = articulation.build_dream_articulation_surface()

    assert result["candidate_created"] is True
    assert len(items) == 1
    assert surface["visibility"] == "internal-only"
    assert surface["truth"] == "candidate-only"
    assert surface["boundary"] == "not-memory-not-identity-not-action"
    assert surface["summary"]["latest_signal_id"] == items[0]["signal_id"]


def test_mission_control_runtime_and_endpoint_expose_dream_articulation(isolated_runtime, monkeypatch) -> None:
    mission_control = isolated_runtime.mission_control

    runtime_surface = {
        "active": True,
        "authority": "authoritative-runtime-observability",
        "visibility": "internal-only",
        "truth": "candidate-only",
        "kind": "dream-articulation-light",
        "boundary": "not-memory-not-identity-not-action",
        "last_run_at": "2026-04-01T10:00:00+00:00",
        "last_result": {"reason": "dream-articulated"},
        "latest_artifact": {"signal_id": "dream-1", "summary": "Dream articulation summary", "source_kind": "internal-dream-articulation"},
        "summary": {
            "last_state": "forming",
            "last_reason": "dream-articulated",
            "last_output_kind": "runtime-dream-hypothesis",
            "source_input_count": 4,
            "latest_signal_id": "dream-1",
            "latest_summary": "Dream articulation summary",
            "candidate_truth": "candidate-only",
        },
        "source": "/mc/dream-articulation",
        "built_at": "2026-04-01T10:00:00+00:00",
    }

    monkeypatch.setattr(
        isolated_runtime.dream_articulation,
        "build_dream_articulation_surface",
        lambda: runtime_surface,
    )
    monkeypatch.setattr(mission_control, "build_dream_articulation_surface", lambda: runtime_surface)

    endpoint = mission_control.mc_dream_articulation()
    runtime = mission_control.mc_runtime()

    assert endpoint["kind"] == "dream-articulation-light"
    assert endpoint["truth"] == "candidate-only"
    assert runtime["runtime_dream_articulation"]["summary"]["last_state"] == "forming"
    assert runtime["runtime_dream_articulation"]["boundary"] == "not-memory-not-identity-not-action"
