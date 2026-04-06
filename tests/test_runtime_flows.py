from __future__ import annotations


def test_runtime_flows_persist_and_link_to_task(isolated_runtime) -> None:
    runtime_tasks = __import__(
        "apps.api.jarvis_api.services.runtime_tasks",
        fromlist=["create_task"],
    )
    runtime_flows = __import__(
        "apps.api.jarvis_api.services.runtime_flows",
        fromlist=["create_flow"],
    )

    task = runtime_tasks.create_task(
        kind="repo-analysis",
        goal="Inspect backend entrypoints and service boundaries",
        origin="heartbeat",
        scope="/media/projects/jarvis-v2",
    )

    flow = runtime_flows.create_flow(
        task_id=task["task_id"],
        current_step="scan-entrypoints",
        step_state="queued",
        plan=[
            {"step": "scan-entrypoints", "status": "queued"},
            {"step": "read-core-services", "status": "pending"},
        ],
        next_action="read app.py and route files",
    )

    assert flow["task_id"] == task["task_id"]
    assert flow["current_step"] == "scan-entrypoints"
    assert flow["step_state"] == "queued"
    assert len(flow["plan"]) == 2

    linked_task = runtime_tasks.get_task(task["task_id"])
    assert linked_task is not None
    assert linked_task["flow_id"] == flow["flow_id"]

    updated = runtime_flows.update_flow(
        flow["flow_id"],
        status="running",
        current_step="read-core-services",
        step_state="running",
        next_action="inspect heartbeat runtime and visible run orchestration",
        last_error="",
        attempt_count=1,
    )

    assert updated is not None
    assert updated["status"] == "running"
    assert updated["current_step"] == "read-core-services"
    assert updated["attempt_count"] == 1

    running_flows = runtime_flows.list_flows(status="running")
    assert any(item["flow_id"] == flow["flow_id"] for item in running_flows)
