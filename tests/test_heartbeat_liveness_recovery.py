from __future__ import annotations

from datetime import UTC, datetime


def _inactive_surface() -> dict[str, object]:
    return {"active": False, "items": [], "summary": {}}


def test_heartbeat_liveness_stays_quiet_without_runtime_substrate(
    isolated_runtime,
    monkeypatch,
) -> None:
    heartbeat_runtime = isolated_runtime.heartbeat_runtime

    monkeypatch.setattr(heartbeat_runtime, "build_runtime_open_loop_signal_surface", lambda limit=6: _inactive_surface())
    monkeypatch.setattr(heartbeat_runtime, "build_runtime_relation_continuity_signal_surface", lambda limit=6: _inactive_surface())
    monkeypatch.setattr(heartbeat_runtime, "build_runtime_regulation_homeostasis_signal_surface", lambda limit=6: _inactive_surface())
    monkeypatch.setattr(heartbeat_runtime, "build_runtime_witness_signal_surface", lambda limit=6: _inactive_surface())
    monkeypatch.setattr(heartbeat_runtime, "build_runtime_private_state_snapshot_surface", lambda limit=6: _inactive_surface())
    monkeypatch.setattr(heartbeat_runtime, "build_runtime_private_initiative_tension_signal_surface", lambda limit=6: _inactive_surface())
    monkeypatch.setattr(heartbeat_runtime, "build_runtime_chronicle_consolidation_brief_surface", lambda limit=6: _inactive_surface())
    monkeypatch.setattr(heartbeat_runtime, "build_runtime_metabolism_state_signal_surface", lambda limit=6: _inactive_surface())
    monkeypatch.setattr(heartbeat_runtime, "build_runtime_release_marker_signal_surface", lambda limit=6: _inactive_surface())

    signal = heartbeat_runtime._build_heartbeat_liveness_signal(
        merged_state={"due": False},
        trigger="surface",
    )

    assert signal["status"] == "inactive"
    assert signal["liveness_state"] == "quiet"
    assert signal["liveness_pressure"] == "low"
    assert signal["planner_authority_state"] == "not-planner-authority"
    assert signal["canonical_self_state"] == "not-canonical-self-truth"


def test_heartbeat_liveness_forms_from_bounded_runtime_pressure(
    isolated_runtime,
    monkeypatch,
) -> None:
    heartbeat_runtime = isolated_runtime.heartbeat_runtime

    monkeypatch.setattr(
        heartbeat_runtime,
        "build_runtime_open_loop_signal_surface",
        lambda limit=6: {
            "active": True,
            "items": [{"title": "Open loop: review style", "source_anchor": "open-loop anchor"}],
            "summary": {"open_count": 1, "softening_count": 0},
        },
    )
    monkeypatch.setattr(
        heartbeat_runtime,
        "build_runtime_private_initiative_tension_signal_surface",
        lambda limit=6: {
            "active": True,
            "items": [{"title": "Initiative tension", "source_anchor": "tension anchor"}],
            "summary": {"active_count": 1},
        },
    )
    monkeypatch.setattr(
        heartbeat_runtime,
        "build_runtime_private_state_snapshot_surface",
        lambda limit=6: {
            "active": True,
            "items": [{"title": "Private state snapshot", "source_anchor": "private-state anchor"}],
            "summary": {"active_count": 1, "current_pressure": "high"},
        },
    )
    monkeypatch.setattr(
        heartbeat_runtime,
        "build_runtime_relation_continuity_signal_surface",
        lambda limit=6: {
            "active": True,
            "items": [{"title": "Relation continuity", "source_anchor": "relation anchor"}],
            "summary": {"current_weight": "medium"},
        },
    )
    monkeypatch.setattr(
        heartbeat_runtime,
        "build_runtime_witness_signal_surface",
        lambda limit=6: {
            "active": True,
            "items": [{"title": "Witness", "source_anchor": "witness anchor"}],
            "summary": {"carried_count": 1, "current_persistence_state": "persistent"},
        },
    )
    monkeypatch.setattr(heartbeat_runtime, "build_runtime_regulation_homeostasis_signal_surface", lambda limit=6: _inactive_surface())
    monkeypatch.setattr(heartbeat_runtime, "build_runtime_chronicle_consolidation_brief_surface", lambda limit=6: _inactive_surface())
    monkeypatch.setattr(heartbeat_runtime, "build_runtime_metabolism_state_signal_surface", lambda limit=6: _inactive_surface())
    monkeypatch.setattr(heartbeat_runtime, "build_runtime_release_marker_signal_surface", lambda limit=6: _inactive_surface())

    signal = heartbeat_runtime._build_heartbeat_liveness_signal(
        merged_state={"due": True},
        trigger="manual",
    )

    assert signal["status"] == "active"
    assert signal["liveness_state"] in {"responding", "alive-pressure"}
    assert signal["liveness_pressure"] in {"medium", "high"}
    assert signal["source_anchor"]
    assert "Heartbeat appears to have bounded liveness pressure" in signal["liveness_summary"]


def test_heartbeat_liveness_recovery_prevents_empty_noop_when_pressure_exists(
    isolated_runtime,
) -> None:
    heartbeat_runtime = isolated_runtime.heartbeat_runtime

    recovered = heartbeat_runtime._recover_bounded_heartbeat_liveness_decision(
        decision={
            "decision_type": "noop",
            "summary": "No current due work was detected.",
            "reason": "",
            "proposed_action": "",
            "ping_text": "",
            "execute_action": "",
        },
        policy={"allow_propose": True},
        liveness={
            "liveness_state": "responding",
            "liveness_pressure": "medium",
            "liveness_reason": "open-loop continuity is still live",
            "liveness_summary": "Heartbeat appears to have bounded liveness pressure because open-loop continuity is still live.",
        },
    )

    assert recovered["decision_type"] == "propose"
    assert "bounded-liveness-recovery" in recovered["reason"]
    assert "liveness pressure" in recovered["summary"].lower()


def test_heartbeat_runtime_surface_exposes_liveness_fields(
    isolated_runtime,
    monkeypatch,
) -> None:
    db = isolated_runtime.db
    heartbeat_runtime = isolated_runtime.heartbeat_runtime
    now = datetime.now(UTC).isoformat()
    db.upsert_heartbeat_runtime_state(
        state_id="default",
        last_tick_id="heartbeat-tick:test",
        last_tick_at=now,
        next_tick_at=now,
        schedule_state="scheduled",
        due=False,
        last_decision_type="noop",
        last_result="Heartbeat is idle.",
        blocked_reason="",
        currently_ticking=False,
        last_trigger_source="manual",
        scheduler_active=False,
        scheduler_started_at="",
        scheduler_stopped_at="",
        scheduler_health="manual-only",
        recovery_status="idle",
        last_recovery_at="",
        provider="ollama",
        model="qwen3.5:9b",
        lane="local",
        model_source="runtime.settings.visible_model_name",
        resolution_status="runtime-selected-local",
        fallback_used=False,
        execution_status="success",
        parse_status="success",
        budget_status="bounded-internal-only",
        last_ping_eligible=False,
        last_ping_result="not-checked",
        last_action_type="",
        last_action_status="noop",
        last_action_summary="Heartbeat is idle.",
        last_action_artifact="",
        updated_at=now,
    )
    monkeypatch.setattr(
        heartbeat_runtime,
        "_build_heartbeat_liveness_signal",
        lambda merged_state, trigger: {
            "liveness_state": "responding",
            "liveness_pressure": "medium",
            "liveness_reason": "witness continuity is still being carried",
            "liveness_summary": "Heartbeat appears to have bounded liveness pressure because witness continuity is still being carried.",
            "liveness_confidence": "medium",
            "source_anchor": "witness anchor",
            "status": "active",
            "authority": "non-authoritative",
            "layer_role": "runtime-support",
            "planner_authority_state": "not-planner-authority",
            "canonical_self_state": "not-canonical-self-truth",
        },
    )

    surface = heartbeat_runtime.heartbeat_runtime_surface()
    state = surface["state"]

    assert state["liveness_state"] == "responding"
    assert state["liveness_pressure"] == "medium"
    assert state["planner_authority_state"] == "not-planner-authority"
    assert state["canonical_self_state"] == "not-canonical-self-truth"
