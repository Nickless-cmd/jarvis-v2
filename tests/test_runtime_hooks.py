from __future__ import annotations

from core.eventbus.bus import event_bus


def test_runtime_hooks_dispatch_initiative_events_into_tasks_and_flows(isolated_runtime) -> None:
    runtime_hooks = __import__(
        "apps.api.jarvis_api.services.runtime_hooks",
        fromlist=["dispatch_unhandled_hook_events"],
    )

    event_bus.publish(
        "heartbeat.initiative_pushed",
        {
            "initiative_id": "init-123",
            "focus": "Investigate repo capability drift",
            "source": "inner-voice",
            "priority": "high",
        },
    )

    dispatches = runtime_hooks.dispatch_unhandled_hook_events()

    assert len(dispatches) == 1
    dispatch = dispatches[0]
    assert dispatch["event_kind"] == "heartbeat.initiative_pushed"
    assert dispatch["status"] == "dispatched"

    task = isolated_runtime.db.get_runtime_task(dispatch["task_id"])
    flow = isolated_runtime.db.get_runtime_flow(dispatch["flow_id"])
    assert task is not None
    assert flow is not None
    assert task["kind"] == "initiative-followup"
    assert flow["task_id"] == task["task_id"]


def test_runtime_hooks_dispatch_blocked_heartbeat_ticks_into_followup_work(isolated_runtime) -> None:
    runtime_hooks = __import__(
        "apps.api.jarvis_api.services.runtime_hooks",
        fromlist=["dispatch_unhandled_hook_events"],
    )

    event_bus.publish(
        "heartbeat.tick_completed",
        {
            "tick_id": "heartbeat-tick:abc",
            "summary": "Heartbeat could not inspect repo context with the current capability runtime.",
            "action_type": "inspect_repo_context",
            "action_status": "blocked",
        },
    )

    dispatches = runtime_hooks.dispatch_unhandled_hook_events()

    assert len(dispatches) == 1
    dispatch = dispatches[0]
    assert dispatch["event_kind"] == "heartbeat.tick_completed"
    assert dispatch["status"] == "dispatched"

    task = isolated_runtime.db.get_runtime_task(dispatch["task_id"])
    assert task is not None
    assert task["kind"] == "heartbeat-followup"
    assert task["run_id"] == "heartbeat-tick:abc"
