from __future__ import annotations

from datetime import UTC, datetime


def test_load_heartbeat_policy_reads_ping_fields_from_workspace_file(
    isolated_runtime,
) -> None:
    heartbeat_runtime = isolated_runtime.heartbeat_runtime

    policy = heartbeat_runtime.load_heartbeat_policy()

    assert policy["present"] is True
    assert policy["enabled"] is True
    assert policy["allow_propose"] is True
    assert policy["allow_execute"] is True
    assert policy["allow_ping"] is True
    assert policy["ping_channel"] == "webchat"
    assert policy["kill_switch"] == "enabled"


def test_heartbeat_runtime_surface_exposes_loaded_ping_policy(
    isolated_runtime,
) -> None:
    heartbeat_runtime = isolated_runtime.heartbeat_runtime

    surface = heartbeat_runtime.heartbeat_runtime_surface()

    assert surface["policy"]["allow_ping"] is True
    assert surface["policy"]["ping_channel"] == "webchat"
    assert surface["policy"]["kill_switch"] == "enabled"
    assert surface["policy"]["heartbeat_file"].endswith("/HEARTBEAT.md")


def test_merge_runtime_state_recomputes_next_tick_at_from_current_policy_interval(
    isolated_runtime,
) -> None:
    heartbeat_runtime = isolated_runtime.heartbeat_runtime
    last_tick_at = "2026-04-01T17:52:52.146944+00:00"
    stale_next_tick_at = "2026-04-01T20:52:52.146944+00:00"

    merged = heartbeat_runtime._merge_runtime_state(
        policy={
            "enabled": True,
            "kill_switch": "enabled",
            "interval_minutes": 15,
            "budget_status": "bounded-internal-only",
            "summary": "interval=15m",
            "workspace": "/tmp/test-heartbeat-workspace",
        },
        persisted={
            **heartbeat_runtime._default_persisted_state(),
            "last_tick_at": last_tick_at,
            "next_tick_at": stale_next_tick_at,
        },
        now=datetime(2026, 4, 1, 18, 0, tzinfo=UTC),
    )

    assert merged["last_tick_at"] == last_tick_at
    assert merged["next_tick_at"] == "2026-04-01T18:07:52.146944+00:00"
    assert merged["due"] is False


def test_build_heartbeat_context_includes_cognitive_frame_without_name_errors(
    isolated_runtime,
    monkeypatch,
) -> None:
    heartbeat_runtime = isolated_runtime.heartbeat_runtime

    monkeypatch.setattr(heartbeat_runtime, "build_runtime_candidate_workflows", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "runtime_contract_candidate_counts", lambda: {})
    monkeypatch.setattr(
        heartbeat_runtime,
        "recent_runtime_contract_file_writes",
        lambda limit=3: [],
    )
    monkeypatch.setattr(heartbeat_runtime, "visible_session_continuity", lambda: {"active": False})
    monkeypatch.setattr(heartbeat_runtime, "recent_visible_runs", lambda limit=3: [])
    monkeypatch.setattr(heartbeat_runtime, "load_workspace_capabilities", lambda: {})
    monkeypatch.setattr(
        heartbeat_runtime,
        "visible_execution_readiness",
        lambda: {"provider_status": "ready"},
    )
    monkeypatch.setattr(
        heartbeat_runtime,
        "_build_heartbeat_liveness_signal",
        lambda merged_state, trigger: {"liveness_state": "quiet", "liveness_score": 0},
    )
    monkeypatch.setattr(heartbeat_runtime.event_bus, "recent", lambda limit=12: [])
    monkeypatch.setattr(heartbeat_runtime, "build_embodied_state_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_affective_meta_state_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_epistemic_runtime_state_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_loop_runtime_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_prompt_evolution_runtime_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_subagent_ecology_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_council_runtime_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_adaptive_planner_runtime_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_adaptive_reasoning_runtime_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_dream_influence_runtime_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_guided_learning_runtime_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_adaptive_learning_runtime_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_self_system_code_awareness_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_tool_intent_runtime_surface", lambda: {})
    monkeypatch.setattr(
        heartbeat_runtime,
        "_build_heartbeat_cognitive_frame",
        lambda merged_state: {"mode": {"mode": "watch"}},
    )
    monkeypatch.setattr(heartbeat_runtime, "_build_influence_trace", lambda **kwargs: {})

    context = heartbeat_runtime._build_heartbeat_context(
        policy={
            "allow_execute": False,
            "budget_status": "bounded-internal-only",
            "kill_switch": "enabled",
        },
        merged_state={"due": False, "schedule_status": "idle"},
        trigger="manual",
    )

    assert context["schedule_status"] == "idle"
    assert context["cognitive_frame"] == {"mode": {"mode": "watch"}}


def test_build_heartbeat_context_promotes_private_signal_pressure_into_due_items(
    isolated_runtime,
    monkeypatch,
) -> None:
    heartbeat_runtime = isolated_runtime.heartbeat_runtime

    monkeypatch.setattr(heartbeat_runtime, "build_runtime_candidate_workflows", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "runtime_contract_candidate_counts", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "recent_runtime_contract_file_writes", lambda limit=3: [])
    monkeypatch.setattr(heartbeat_runtime, "visible_session_continuity", lambda: {"active": False})
    monkeypatch.setattr(heartbeat_runtime, "recent_visible_runs", lambda limit=3: [])
    monkeypatch.setattr(heartbeat_runtime, "load_workspace_capabilities", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "visible_execution_readiness", lambda: {"provider_status": "ready"})
    monkeypatch.setattr(
        heartbeat_runtime,
        "_build_heartbeat_liveness_signal",
        lambda merged_state, trigger: {"liveness_state": "quiet", "liveness_score": 0},
    )
    monkeypatch.setattr(heartbeat_runtime.event_bus, "recent", lambda limit=12: [])
    monkeypatch.setattr(heartbeat_runtime, "build_embodied_state_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_affective_meta_state_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_epistemic_runtime_state_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_loop_runtime_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_prompt_evolution_runtime_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_subagent_ecology_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_council_runtime_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_adaptive_planner_runtime_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_adaptive_reasoning_runtime_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_dream_influence_runtime_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_guided_learning_runtime_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_adaptive_learning_runtime_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_self_system_code_awareness_surface", lambda: {})
    monkeypatch.setattr(heartbeat_runtime, "build_tool_intent_runtime_surface", lambda: {})
    monkeypatch.setattr(
        heartbeat_runtime,
        "_build_heartbeat_cognitive_frame",
        lambda merged_state: {
            "mode": {"mode": "watch"},
            "private_signal_pressure": "high",
            "private_signal_items": [
                {"source": "initiative-tension", "summary": "Private initiative tension is high around stalled-work."}
            ],
        },
    )
    monkeypatch.setattr(heartbeat_runtime, "_build_influence_trace", lambda **kwargs: {})

    context = heartbeat_runtime._build_heartbeat_context(
        policy={
            "allow_execute": False,
            "budget_status": "bounded-internal-only",
            "kill_switch": "enabled",
        },
        merged_state={"due": False, "schedule_status": "idle"},
        trigger="manual",
    )

    assert context["private_signal_pressure"] == "high"
    assert any("private signal pressure is high" in item for item in context["due_items"])
    assert any("private signal carry:" in item for item in context["open_loops"])
