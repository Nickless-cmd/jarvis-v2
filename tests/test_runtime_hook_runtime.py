from __future__ import annotations

import time


def test_runtime_hook_runtime_dispatches_live_events(isolated_runtime) -> None:
    event_bus = __import__("core.eventbus.bus", fromlist=["event_bus"]).event_bus
    hook_runtime = __import__(
        "core.services.runtime_hook_runtime",
        fromlist=["start_runtime_hook_runtime", "stop_runtime_hook_runtime"],
    )

    hook_runtime.start_runtime_hook_runtime()
    try:
        event_bus.publish(
            "heartbeat.initiative_pushed",
            {
                "initiative_id": "init-live-1",
                "focus": "Investigate live hook dispatch",
                "priority": "high",
            },
        )

        deadline = time.time() + 2.0
        dispatch = None
        while time.time() < deadline:
            rows = isolated_runtime.db.list_runtime_hook_dispatches(limit=5)
            dispatch = next((item for item in rows if item["event_kind"] == "heartbeat.initiative_pushed"), None)
            if dispatch is not None:
                break
            time.sleep(0.05)

        assert dispatch is not None
        assert dispatch["status"] == "dispatched"
        assert isolated_runtime.db.get_runtime_task(dispatch["task_id"]) is not None
        assert isolated_runtime.db.get_runtime_flow(dispatch["flow_id"]) is not None
    finally:
        hook_runtime.stop_runtime_hook_runtime()
