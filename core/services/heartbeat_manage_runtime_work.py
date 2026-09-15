"""Hjerteslagets `manage_runtime_work`-handling — udskilt fra heartbeat_runtime.

Udskilt 15/9-2026 efter Boy Scout-reglen: heartbeat_runtime.py var 7.573
linjer, og en rettelse i denne gren kraevede at den naermeste naturlige enhed
flyttede ud foerst. Grenen er én handling med ét ansvar: flyt koeet runtime-
arbejde (opgaver, flows, hook-events, laeringsplan) ind i aktiv orkestrering,
eller fald videre til en anden handling naar der intet er.

`heartbeat_runtime._execute_heartbeat_internal_action` delegerer hertil, saa
kaldere ser praecis det samme som foer.
"""
from __future__ import annotations

import json
from pathlib import Path


def execute_manage_runtime_work(*, tick_id: str, workspace_dir: Path) -> dict[str, str]:
    from core.services.heartbeat_runtime import (
        _heartbeat_runtime_bias_from_recent_work as _bias,
    )

    from core.services.runtime_browser_body import (
        ensure_browser_body,
    )
    from core.services.runtime_flows import list_flows, update_flow
    from core.services.runtime_hooks import (
        dispatch_unhandled_hook_events,
    )
    from core.services.runtime_tasks import list_tasks, update_task

    experiment_observation = {
        "observed": 0,
        "running": 0,
        "skipped": 0,
        "items": [],
        "summary": "",
    }
    curriculum_materialization = {
        "created": 0,
        "skipped": 0,
        "task_ids": [],
        "flow_ids": [],
        "items": [],
        "summary": "",
    }
    try:
        from core.services.self_experiments import (
            materialize_learning_curriculum_tasks,
            observe_recent_visible_runs_for_self_experiments,
        )

        experiment_observation = observe_recent_visible_runs_for_self_experiments(
            limit=6
        )
        curriculum_materialization = materialize_learning_curriculum_tasks(
            limit=3,
            origin="heartbeat:curriculum",
            owner="heartbeat-runtime",
            run_id=tick_id,
        )
    except Exception:
        pass

    dispatched = dispatch_unhandled_hook_events(limit=4)
    queued_tasks = list_tasks(status="queued", limit=4)
    queued_flows = list_flows(status="queued", limit=4)
    running_flows = list_flows(status="running", limit=4)

    active_task_id = (
        str((queued_tasks[0] or {}).get("task_id") or "") if queued_tasks else ""
    )
    active_flow_id = (
        str((queued_flows[0] or {}).get("flow_id") or "") if queued_flows else ""
    )

    if active_task_id:
        update_task(
            active_task_id,
            status="running",
            result_summary="Heartbeat moved queued runtime work into active orchestration.",
            artifact_ref=f"heartbeat:{tick_id}",
        )
    if active_flow_id:
        update_flow(
            active_flow_id,
            status="running",
            step_state="running",
            attempt_count=int((queued_flows[0] or {}).get("attempt_count") or 0)
            + 1,
        )

    browser_body = ensure_browser_body(
        profile_name="jarvis-browser",
        active_task_id=active_task_id,
        active_flow_id=active_flow_id
        # Tom liste var en IndexError (15/9-2026): uden koeede OG uden koerende
        # flows kastede handlingen i stedet for at melde «intet at goere». Latent i
        # drift, fordi der altid laa koeede flows; testen ramte den.
        or (str((running_flows[0] or {}).get("flow_id") or "") if running_flows else ""),
    )

    if (
        dispatched
        or queued_tasks
        or queued_flows
        or running_flows
        or int(experiment_observation.get("observed") or 0) > 0
        or int(curriculum_materialization.get("created") or 0) > 0
    ):
        artifact = json.dumps(
            {
                "dispatch_count": len(dispatched),
                "experiment_observation": experiment_observation,
                "curriculum_materialization": curriculum_materialization,
                "queued_task_ids": [
                    str(item.get("task_id") or "")
                    for item in queued_tasks[:4]
                    if str(item.get("task_id") or "")
                ],
                "queued_flow_ids": [
                    str(item.get("flow_id") or "")
                    for item in queued_flows[:4]
                    if str(item.get("flow_id") or "")
                ],
                "running_flow_ids": [
                    str(item.get("flow_id") or "")
                    for item in running_flows[:4]
                    if str(item.get("flow_id") or "")
                ],
                "browser_body_id": str(browser_body.get("body_id") or ""),
                "active_task_id": str(browser_body.get("active_task_id") or ""),
                "active_flow_id": str(browser_body.get("active_flow_id") or ""),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        return {
            "status": "executed",
            "summary": (
                f"Heartbeat orchestrated runtime work across {len(dispatched)} hook dispatches, "
                f"{int(experiment_observation.get('observed') or 0)} experiment observations, "
                f"{int(curriculum_materialization.get('created') or 0)} curriculum tasks, "
                f"{len(queued_tasks)} queued tasks, {len(queued_flows)} queued flows, and "
                f"{len(running_flows)} active flows."
            ),
            "artifact": artifact,
            "blocked_reason": "",
        }

    next_action = (
        "inspect_repo_context"
        if _bias(kind="repo")
        else (
            "gather_system_context"
            if _bias(kind="system")
            else "refresh_memory_context"
        )
    )
    from core.services.heartbeat_runtime import _execute_heartbeat_internal_action

    return _execute_heartbeat_internal_action(
        action_type=next_action,
        tick_id=tick_id,
        workspace_dir=workspace_dir,
    )
