from __future__ import annotations

import importlib


def test_scheduled_tasks_service_also_fires_agent_schedules(isolated_runtime, monkeypatch) -> None:
    scheduled_tasks = importlib.import_module("apps.api.jarvis_api.services.scheduled_tasks")
    scheduled_tasks = importlib.reload(scheduled_tasks)

    seen: dict[str, object] = {}

    def fake_run_due_agent_schedules(*, limit: int = 10) -> dict[str, object]:
        seen["limit"] = limit
        return {"triggered_count": 2, "agents": [{"agent_id": "a1"}, {"agent_id": "a2"}]}

    monkeypatch.setattr(
        importlib.import_module("apps.api.jarvis_api.services.agent_runtime"),
        "run_due_agent_schedules",
        fake_run_due_agent_schedules,
    )

    monkeypatch.setattr(isolated_runtime.db, "get_due_scheduled_tasks", lambda now_iso: [])

    scheduled_tasks._fire_due_tasks()

    assert seen["limit"] == 10
