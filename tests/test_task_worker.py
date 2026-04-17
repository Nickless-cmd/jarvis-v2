from __future__ import annotations


def _import_modules():
    runtime_tasks = __import__(
        "apps.api.jarvis_api.services.runtime_tasks",
        fromlist=["create_task"],
    )
    task_worker = __import__(
        "apps.api.jarvis_api.services.task_worker",
        fromlist=["claim_next_task"],
    )
    return runtime_tasks, task_worker


def test_claim_next_task_returns_highest_priority_queued(isolated_runtime) -> None:
    runtime_tasks, task_worker = _import_modules()

    runtime_tasks.create_task(
        kind="generic", goal="low one", origin="test", priority="low"
    )
    high = runtime_tasks.create_task(
        kind="generic", goal="high one", origin="test", priority="high"
    )
    runtime_tasks.create_task(
        kind="generic", goal="med one", origin="test", priority="medium"
    )

    claimed = task_worker.claim_next_task()

    assert claimed is not None
    assert claimed["task_id"] == high["task_id"]
    assert claimed["status"] == "running"


def test_claim_next_task_returns_none_when_no_matching_kind(isolated_runtime) -> None:
    runtime_tasks, task_worker = _import_modules()
    runtime_tasks.create_task(
        kind="some-other-kind", goal="x", origin="test", priority="high"
    )

    claimed = task_worker.claim_next_task(
        kinds=("initiative-followup", "heartbeat-followup"),
    )

    assert claimed is None


def test_execute_task_marks_succeeded_on_known_kind(isolated_runtime) -> None:
    runtime_tasks, task_worker = _import_modules()
    task = runtime_tasks.create_task(
        kind="generic", goal="noop-test", origin="test", priority="low"
    )

    task_worker._execute_task(task)

    reloaded = runtime_tasks.get_task(task["task_id"])
    assert reloaded is not None
    assert reloaded["status"] == "succeeded"
    assert reloaded.get("result_summary")


def test_execute_task_marks_failed_on_unknown_kind(isolated_runtime) -> None:
    runtime_tasks, task_worker = _import_modules()
    task = runtime_tasks.create_task(
        kind="totally-unknown-kind", goal="x", origin="test", priority="low"
    )

    task_worker._execute_task(task)

    reloaded = runtime_tasks.get_task(task["task_id"])
    assert reloaded is not None
    assert reloaded["status"] == "failed"
    assert "unknown kind" in str(reloaded.get("result_summary") or "").lower()


def test_tick_processes_up_to_budget(isolated_runtime) -> None:
    runtime_tasks, task_worker = _import_modules()
    for i in range(5):
        runtime_tasks.create_task(
            kind="generic", goal=f"t{i}", origin="test", priority="medium"
        )

    result = task_worker.tick_task_worker(budget=3)

    assert result["processed"] == 3
    assert result["succeeded"] == 3
    assert result["failed"] == 0
    assert result["remaining_queued"] >= 2


def test_tick_handles_initiative_and_heartbeat_followup(isolated_runtime) -> None:
    runtime_tasks, task_worker = _import_modules()
    runtime_tasks.create_task(
        kind="initiative-followup",
        goal="check memory",
        origin="test",
        priority="high",
    )
    runtime_tasks.create_task(
        kind="heartbeat-followup",
        goal="no-valid-execution-candidate",
        origin="test",
        priority="high",
    )

    result = task_worker.tick_task_worker(budget=5)

    assert result["processed"] == 2
    assert result["succeeded"] == 2
    assert result["failed"] == 0
