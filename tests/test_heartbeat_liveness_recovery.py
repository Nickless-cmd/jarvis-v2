from __future__ import annotations

from datetime import UTC, datetime, timedelta


def _inactive_surface() -> dict[str, object]:
    return {"active": False, "items": [], "summary": {}}


def _inactive_continuity() -> dict[str, object]:
    return {
        "active": False,
        "latest_run_id": "",
        "latest_status": "",
        "latest_finished_at": "",
        "latest_text_preview": "",
    }


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
    monkeypatch.setattr(heartbeat_runtime, "build_runtime_meaning_significance_signal_surface", lambda limit=6: _inactive_surface())
    monkeypatch.setattr(heartbeat_runtime, "build_runtime_metabolism_state_signal_surface", lambda limit=6: _inactive_surface())
    monkeypatch.setattr(heartbeat_runtime, "build_runtime_release_marker_signal_surface", lambda limit=6: _inactive_surface())
    monkeypatch.setattr(heartbeat_runtime, "visible_session_continuity", lambda: _inactive_continuity())

    signal = heartbeat_runtime._build_heartbeat_liveness_signal(
        merged_state={"due": False},
        trigger="surface",
    )

    assert signal["status"] == "inactive"
    assert signal["liveness_state"] == "quiet"
    assert signal["liveness_pressure"] == "low"
    assert signal["liveness_threshold_state"] == "quiet-threshold"
    assert signal["liveness_score"] == 0
    assert signal["liveness_signal_count"] == 0
    assert signal["liveness_core_pressure_count"] == 0
    assert signal["liveness_propose_gate_count"] == 0
    assert signal["companion_pressure_state"] == "inactive"
    assert signal["companion_pressure_weight"] == 0
    assert signal["idle_presence_state"] == "inactive"
    assert signal["checkin_worthiness"] == "low"
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
    monkeypatch.setattr(heartbeat_runtime, "build_runtime_meaning_significance_signal_surface", lambda limit=6: _inactive_surface())
    monkeypatch.setattr(heartbeat_runtime, "build_runtime_metabolism_state_signal_surface", lambda limit=6: _inactive_surface())
    monkeypatch.setattr(heartbeat_runtime, "build_runtime_release_marker_signal_surface", lambda limit=6: _inactive_surface())
    monkeypatch.setattr(heartbeat_runtime, "visible_session_continuity", lambda: _inactive_continuity())

    signal = heartbeat_runtime._build_heartbeat_liveness_signal(
        merged_state={"due": True},
        trigger="manual",
    )

    assert signal["status"] == "active"
    assert signal["liveness_state"] in {"alive-pressure", "propose-worthy"}
    assert signal["liveness_pressure"] == "high"
    assert signal["liveness_score"] >= 8
    assert signal["liveness_signal_count"] >= 4
    assert signal["liveness_threshold_state"] in {
        "alive-threshold",
        "propose-worthy-threshold",
    }
    assert signal["source_anchor"]
    assert "Heartbeat appears to have bounded liveness pressure" in signal["liveness_summary"]


def test_heartbeat_liveness_separates_watchful_presence_from_propose_worthy_pressure(
    isolated_runtime,
    monkeypatch,
) -> None:
    heartbeat_runtime = isolated_runtime.heartbeat_runtime

    monkeypatch.setattr(heartbeat_runtime, "build_runtime_open_loop_signal_surface", lambda limit=6: _inactive_surface())
    monkeypatch.setattr(
        heartbeat_runtime,
        "build_runtime_private_initiative_tension_signal_surface",
        lambda limit=6: {
            "active": True,
            "items": [{"title": "Initiative tension", "source_anchor": "tension anchor"}],
            "summary": {"active_count": 1, "current_intensity": "low"},
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
    monkeypatch.setattr(heartbeat_runtime, "build_runtime_regulation_homeostasis_signal_surface", lambda limit=6: _inactive_surface())
    monkeypatch.setattr(heartbeat_runtime, "build_runtime_witness_signal_surface", lambda limit=6: _inactive_surface())
    monkeypatch.setattr(heartbeat_runtime, "build_runtime_private_state_snapshot_surface", lambda limit=6: _inactive_surface())
    monkeypatch.setattr(heartbeat_runtime, "build_runtime_chronicle_consolidation_brief_surface", lambda limit=6: _inactive_surface())
    monkeypatch.setattr(heartbeat_runtime, "build_runtime_meaning_significance_signal_surface", lambda limit=6: _inactive_surface())
    monkeypatch.setattr(heartbeat_runtime, "build_runtime_metabolism_state_signal_surface", lambda limit=6: _inactive_surface())
    monkeypatch.setattr(heartbeat_runtime, "build_runtime_release_marker_signal_surface", lambda limit=6: _inactive_surface())
    monkeypatch.setattr(heartbeat_runtime, "visible_session_continuity", lambda: _inactive_continuity())

    signal = heartbeat_runtime._build_heartbeat_liveness_signal(
        merged_state={"due": False},
        trigger="surface",
    )

    assert signal["status"] == "active"
    assert signal["liveness_state"] == "watchful"
    assert signal["liveness_pressure"] == "medium"
    assert signal["liveness_threshold_state"] == "watchful-threshold"


def test_heartbeat_liveness_adds_bounded_companion_pressure_under_silence(
    isolated_runtime,
    monkeypatch,
) -> None:
    heartbeat_runtime = isolated_runtime.heartbeat_runtime
    older_than_day = (datetime.now(UTC) - timedelta(hours=30)).isoformat()

    monkeypatch.setattr(heartbeat_runtime, "build_runtime_open_loop_signal_surface", lambda limit=6: _inactive_surface())
    monkeypatch.setattr(heartbeat_runtime, "build_runtime_private_initiative_tension_signal_surface", lambda limit=6: _inactive_surface())
    monkeypatch.setattr(heartbeat_runtime, "build_runtime_private_state_snapshot_surface", lambda limit=6: _inactive_surface())
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
    monkeypatch.setattr(heartbeat_runtime, "build_runtime_meaning_significance_signal_surface", lambda limit=6: _inactive_surface())
    monkeypatch.setattr(heartbeat_runtime, "build_runtime_metabolism_state_signal_surface", lambda limit=6: _inactive_surface())
    monkeypatch.setattr(heartbeat_runtime, "build_runtime_release_marker_signal_surface", lambda limit=6: _inactive_surface())
    monkeypatch.setattr(
        heartbeat_runtime,
        "visible_session_continuity",
        lambda: {
            "active": True,
            "latest_run_id": "run-1",
            "latest_status": "success",
            "latest_finished_at": older_than_day,
            "latest_text_preview": "Last visible contact was a while ago.",
        },
    )

    signal = heartbeat_runtime._build_heartbeat_liveness_signal(
        merged_state={"due": False},
        trigger="surface",
    )

    assert signal["status"] == "active"
    assert signal["liveness_state"] == "alive-pressure"
    assert signal["companion_pressure_state"] == "present"
    assert signal["companion_pressure_weight"] >= 3
    assert signal["idle_presence_state"] == "sustained"
    assert signal["checkin_worthiness"] == "medium"
    assert signal["companion_pressure_reason"] in {
        "relation continuity is holding bounded distance under silence",
        "witness continuity is persisting without a recent outlet",
    }
    assert signal["liveness_propose_gate_count"] == 0


def test_heartbeat_liveness_uses_relation_meaning_and_witness_chronicle_as_propose_gates(
    isolated_runtime,
    monkeypatch,
) -> None:
    heartbeat_runtime = isolated_runtime.heartbeat_runtime

    monkeypatch.setattr(heartbeat_runtime, "build_runtime_open_loop_signal_surface", lambda limit=6: _inactive_surface())
    monkeypatch.setattr(heartbeat_runtime, "build_runtime_private_initiative_tension_signal_surface", lambda limit=6: _inactive_surface())
    monkeypatch.setattr(heartbeat_runtime, "build_runtime_private_state_snapshot_surface", lambda limit=6: _inactive_surface())
    monkeypatch.setattr(heartbeat_runtime, "build_runtime_regulation_homeostasis_signal_surface", lambda limit=6: _inactive_surface())
    monkeypatch.setattr(heartbeat_runtime, "build_runtime_metabolism_state_signal_surface", lambda limit=6: _inactive_surface())
    monkeypatch.setattr(heartbeat_runtime, "build_runtime_release_marker_signal_surface", lambda limit=6: _inactive_surface())
    monkeypatch.setattr(heartbeat_runtime, "visible_session_continuity", lambda: _inactive_continuity())
    monkeypatch.setattr(
        heartbeat_runtime,
        "build_runtime_relation_continuity_signal_surface",
        lambda limit=6: {
            "active": True,
            "items": [{"title": "Relation continuity", "source_anchor": "relation anchor"}],
            "summary": {"current_weight": "high"},
        },
    )
    monkeypatch.setattr(
        heartbeat_runtime,
        "build_runtime_meaning_significance_signal_surface",
        lambda limit=6: {
            "active": True,
            "items": [{"title": "Meaning significance", "source_anchor": "meaning anchor"}],
            "summary": {"current_weight": "high"},
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
    monkeypatch.setattr(
        heartbeat_runtime,
        "build_runtime_chronicle_consolidation_brief_surface",
        lambda limit=6: {
            "active": True,
            "items": [{"title": "Chronicle brief", "source_anchor": "chronicle anchor"}],
            "summary": {"current_weight": "high"},
        },
    )

    signal = heartbeat_runtime._build_heartbeat_liveness_signal(
        merged_state={"due": False},
        trigger="surface",
    )

    assert signal["status"] == "active"
    assert signal["liveness_state"] == "propose-worthy"
    assert signal["liveness_threshold_state"] == "propose-worthy-threshold"
    assert signal["liveness_propose_gate_count"] >= 2
    assert signal["liveness_core_pressure_count"] >= 2
    assert signal["liveness_reason"] in {
        "relation continuity is still holding weight",
        "relation and meaning continuity are cohering as one carried thread",
        "witnessed continuity is still being carried into chronicle",
    }


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
            "liveness_state": "propose-worthy",
            "liveness_pressure": "high",
            "liveness_reason": "open-loop continuity is still live",
            "liveness_summary": "Heartbeat appears to have bounded liveness pressure because open-loop continuity is still live.",
            "liveness_threshold_state": "propose-worthy-threshold",
        },
    )

    assert recovered["decision_type"] == "propose"
    assert "bounded-liveness-recovery" in recovered["reason"]
    assert "liveness pressure" in recovered["summary"].lower()


def test_heartbeat_liveness_recovery_does_not_promote_watchful_presence_to_propose(
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
            "liveness_state": "watchful",
            "liveness_pressure": "medium",
            "liveness_reason": "relation continuity is still holding weight",
            "liveness_summary": "Heartbeat appears to have bounded liveness pressure because relation continuity is still holding weight.",
            "liveness_threshold_state": "watchful-threshold",
        },
    )

    assert recovered["decision_type"] == "noop"


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
            "liveness_state": "watchful",
            "liveness_pressure": "medium",
            "liveness_reason": "witness continuity is still being carried",
            "liveness_summary": "Heartbeat appears to have bounded liveness pressure because witness continuity is still being carried.",
            "liveness_confidence": "medium",
            "liveness_threshold_state": "watchful-threshold",
            "liveness_score": 3,
            "liveness_signal_count": 2,
            "liveness_core_pressure_count": 1,
            "liveness_propose_gate_count": 0,
            "companion_pressure_state": "light",
            "companion_pressure_reason": "witness continuity is persisting without a recent outlet",
            "companion_pressure_weight": 1,
            "idle_presence_state": "present",
            "checkin_worthiness": "low-present",
            "liveness_debug_summary": "score=3 signals=2 core_pressure=1 propose_gates=0 companion=1/light idle=present",
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

    assert state["liveness_state"] == "watchful"
    assert state["liveness_pressure"] == "medium"
    assert state["liveness_threshold_state"] == "watchful-threshold"
    assert state["liveness_score"] == 3
    assert state["liveness_signal_count"] == 2
    assert state["liveness_core_pressure_count"] == 1
    assert state["liveness_propose_gate_count"] == 0
    assert state["companion_pressure_state"] == "light"
    assert state["companion_pressure_weight"] == 1
    assert state["idle_presence_state"] == "present"
    assert state["checkin_worthiness"] == "low-present"
    assert state["planner_authority_state"] == "not-planner-authority"
    assert state["canonical_self_state"] == "not-canonical-self-truth"
