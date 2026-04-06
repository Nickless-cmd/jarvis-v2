from __future__ import annotations


def test_mission_control_exposes_runtime_work(isolated_runtime) -> None:
    runtime_tasks = __import__(
        "apps.api.jarvis_api.services.runtime_tasks",
        fromlist=["create_task"],
    )
    runtime_flows = __import__(
        "apps.api.jarvis_api.services.runtime_flows",
        fromlist=["create_flow"],
    )
    runtime_browser_body = __import__(
        "apps.api.jarvis_api.services.runtime_browser_body",
        fromlist=["ensure_browser_body"],
    )

    task = runtime_tasks.create_task(
        kind="repo-analysis",
        goal="Inspect main repo runtime work surface",
        origin="chat",
        priority="high",
        owner="visible-chat",
    )
    runtime_flows.create_flow(
        task_id=task["task_id"],
        current_step="inspect-runtime-work",
        step_state="queued",
        plan=[{"step": "inspect-runtime-work", "status": "queued"}],
        next_action="Continue repo inspection",
    )
    runtime_browser_body.ensure_browser_body(
        profile_name="jarvis-browser",
        active_task_id=task["task_id"],
    )

    runtime = isolated_runtime.mission_control.mc_runtime()
    jarvis = isolated_runtime.mission_control.mc_jarvis()

    assert "runtime_work" in runtime
    assert runtime["runtime_work"]["summary"]["task_count"] >= 1
    assert runtime["runtime_work"]["summary"]["flow_count"] >= 1
    assert "runtime_work" in jarvis["continuity"]
    assert jarvis["summary"]["continuity"]["runtime_work_count"] != "0"
