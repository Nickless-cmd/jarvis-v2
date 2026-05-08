from __future__ import annotations


def test_system_cartographer_builds_broad_inventory() -> None:
    from core.services.system_cartographer import build_system_cartographer_surface

    surface = build_system_cartographer_surface()

    assert surface["mode"] == "system-cartographer-v1"
    assert surface["summary"]["services"] > 50
    assert surface["summary"]["daemons"] > 10
    assert surface["summary"]["edges"] > 0
    assert "observed_events" in surface["summary"]
    assert "observed_causal_edges" in surface["summary"]
    assert surface["causalRuntime"]["mode"] in {
        "causal-runtime-v1",
        "causal-runtime-unavailable",
    }
    assert "services" in surface["nodes"]
    assert "event_families" in surface["nodes"]
    task = surface["recommendedObservabilityTask"]
    assert task is None or task["task_kind"] == "observability_bridge_repair"
    assert "coverage" in surface
    assert "systemHealth" in surface
    assert "autoTask" in surface
    assert "theaterAutoTask" in surface
    assert "theaterAudit" in surface
    assert "theater_findings" in surface["summary"]
    assert surface["theaterAudit"]["mode"] in {
        "theater-audit-v1",
        "theater-audit-unavailable",
    }


def test_system_cartographer_finds_dark_edges() -> None:
    from core.services.system_cartographer import build_system_cartographer_surface

    surface = build_system_cartographer_surface()

    assert isinstance(surface["darkEdges"], list)
    assert all("service" in item for item in surface["darkEdges"])
    if surface["darkEdges"]:
        assert "priority_score" in surface["darkEdges"][0]
        assert surface["darkEdges"][0]["priority_score"] >= surface["darkEdges"][-1]["priority_score"]


def test_system_cartographer_auto_enqueues_observability_task(monkeypatch):
    from core.services import system_cartographer as cart
    from core.services import runtime_tasks

    created = []

    def fake_create_task(**kwargs):
        task = {"task_id": "task-observe", "status": "queued", **kwargs}
        created.append(task)
        return task

    monkeypatch.setattr(cart, "_find_existing_observability_task", lambda candidate: None)
    monkeypatch.setattr(runtime_tasks, "create_task", fake_create_task)

    surface = cart.build_system_cartographer_surface(auto_enqueue=True)

    assert surface["autoTask"]["status"] in {"enqueued", "no-candidate", "below-threshold"}
    if surface["autoTask"]["status"] == "enqueued":
        assert created[0]["kind"] == "observability_bridge_repair"
        assert created[0]["origin"] == "system-cartographer"


def test_system_cartographer_auto_enqueues_theater_task(monkeypatch):
    from core.services import system_cartographer as cart
    from core.services import runtime_tasks

    created = []

    def fake_create_task(**kwargs):
        task = {"task_id": "task-theater", "status": "queued", **kwargs}
        created.append(task)
        return task

    monkeypatch.setattr(cart, "_find_existing_observability_task", lambda candidate: {"task_id": "existing"})
    monkeypatch.setattr(cart, "_find_existing_theater_task", lambda candidate: None)
    monkeypatch.setattr(runtime_tasks, "create_task", fake_create_task)

    surface = cart.build_system_cartographer_surface(auto_enqueue=True)

    assert surface["theaterAutoTask"]["status"] in {"enqueued", "no-candidate", "below-threshold"}
    if surface["theaterAutoTask"]["status"] == "enqueued":
        assert created[0]["kind"] == "theater_refactor"
        assert created[0]["origin"] == "theater-audit"
