from __future__ import annotations


def test_runtime_tasks_persist_and_update(isolated_runtime) -> None:
    runtime_tasks = __import__(
        "apps.api.jarvis_api.services.runtime_tasks",
        fromlist=["create_task"],
    )

    task = runtime_tasks.create_task(
        kind="repo-analysis",
        goal="Analyze main repo entrypoints and core services",
        origin="chat",
        scope="/media/projects/jarvis-v2",
        priority="high",
        session_id="session-123",
        run_id="run-123",
        owner="visible-chat",
    )

    assert task["status"] == "queued"
    assert task["kind"] == "repo-analysis"
    assert task["origin"] == "chat"
    assert task["scope"] == "/media/projects/jarvis-v2"
    assert task["priority"] == "high"

    updated = runtime_tasks.update_task(
        task["task_id"],
        status="running",
        flow_id="flow-abc",
        result_summary="Reading routes and services",
        artifact_ref="trace:run-123",
    )

    assert updated is not None
    assert updated["status"] == "running"
    assert updated["flow_id"] == "flow-abc"
    assert updated["result_summary"] == "Reading routes and services"
    assert updated["artifact_ref"] == "trace:run-123"

    fetched = runtime_tasks.get_task(task["task_id"])
    assert fetched is not None
    assert fetched["task_id"] == task["task_id"]
    assert fetched["status"] == "running"

    tasks = runtime_tasks.list_tasks(status="running")
    assert any(item["task_id"] == task["task_id"] for item in tasks)


def test_runtime_tasks_priority_uses_standing_orders_and_daily_memory(isolated_runtime) -> None:
    runtime_tasks = __import__(
        "apps.api.jarvis_api.services.runtime_tasks",
        fromlist=["create_task"],
    )
    paths = isolated_runtime.workspace_bootstrap.workspace_memory_paths()

    paths["daily_memory"].unlink(missing_ok=True)
    standing_orders_path = paths["workspace_dir"] / "STANDING_ORDERS.md"
    standing_orders_path.write_text(
        "Maintain memory continuity.\nFollow repo work proactively.\n",
        encoding="utf-8",
    )

    task = runtime_tasks.create_task(
        kind="memory-continuity",
        goal="Maintain memory continuity for the repo",
        origin="hook:heartbeat.tick_completed",
        priority="medium",
        owner="test",
    )

    assert task["priority"] == "high"
