from __future__ import annotations


def _import_modules():
    runtime_tasks = __import__(
        "core.services.runtime_tasks",
        fromlist=["create_task"],
    )
    task_worker = __import__(
        "core.services.task_worker",
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


def test_agency_bridge_repair_prepares_brief(monkeypatch) -> None:
    _, task_worker = _import_modules()
    saved = {}

    monkeypatch.setattr(task_worker, "load_json", lambda name, default: {})
    monkeypatch.setattr(task_worker, "save_json", lambda name, data: saved.update({name: data}))
    monkeypatch.setattr(
        task_worker,
        "_matching_agency_edge",
        lambda **kwargs: {
            "id": "executive-tools",
            "title": "Living Executive -> Tools",
            "target": "Living Executive -> Tools",
            "missing_markers": ["living_executive.tool_plan_proposed"],
        },
    )

    task = {
        "task_id": "task-agency",
        "kind": "agency_bridge_repair",
        "goal": "Turn executive recovery plans into runnable tool proposals.",
        "origin": "agency-cartographer",
        "scope": "Living Executive -> Tools",
        "priority": "high",
    }

    result = task_worker._handle_agency_bridge_repair(task)

    assert result["status"] == "blocked"
    assert result["artifact_ref"] == "state:agency_bridge_repair_briefs:task-agency"
    assert "awaiting approved implementation lane" in result["blocked_reason"]
    brief = saved["agency_bridge_repair_briefs"][task["task_id"]]
    assert brief["edge"]["id"] == "executive-tools"
    assert "core/services/living_executive.py" in brief["suggested_files"]


def test_observability_bridge_repair_prepares_brief(monkeypatch) -> None:
    _, task_worker = _import_modules()
    saved = {}

    monkeypatch.setattr(task_worker, "load_json", lambda name, default: {})
    monkeypatch.setattr(task_worker, "save_json", lambda name, data: saved.update({name: data}))

    task = {
        "task_id": "task-observe",
        "kind": "observability_bridge_repair",
        "goal": "Expose identity_composer in Mission Control.",
        "origin": "system-cartographer",
        "scope": "core/services/identity_composer.py",
        "priority": "medium",
    }

    result = task_worker._handle_observability_bridge_repair(task)

    assert result["status"] == "blocked"
    assert result["artifact_ref"] == "state:observability_bridge_repair_briefs:task-observe"
    brief = saved["observability_bridge_repair_briefs"][task["task_id"]]
    assert brief["service"] == "identity_composer"
    assert "core/services/identity_composer.py" in brief["suggested_files"]


def test_theater_refactor_prepares_brief(monkeypatch) -> None:
    _, task_worker = _import_modules()
    saved = {}

    monkeypatch.setattr(task_worker, "load_json", lambda name, default: {})
    monkeypatch.setattr(task_worker, "save_json", lambda name, data: saved.update({name: data}))
    monkeypatch.setattr(
        task_worker,
        "_matching_theater_file",
        lambda **kwargs: {
            "path": "core/services/cognitive_state_assembly.py",
            "risk_score": 250,
            "high_risk": 5,
        },
    )

    task = {
        "task_id": "task-theater",
        "kind": "theater_refactor",
        "goal": "Convert cognitive_state_assembly to appraisal state.",
        "origin": "theater-audit",
        "scope": "core/services/cognitive_state_assembly.py",
        "priority": "high",
    }

    result = task_worker._handle_theater_refactor(task)

    assert result["status"] == "blocked"
    assert result["artifact_ref"] == "state:theater_refactor_briefs:task-theater"
    brief = saved["theater_refactor_briefs"][task["task_id"]]
    assert brief["audit_file"]["risk_score"] == 250
    assert brief["refactor_contract"]["state_before_prose"] is True
    assert "core/services/cognitive_state_assembly.py" in brief["suggested_files"]
