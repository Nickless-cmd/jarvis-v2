import asyncio
import json

from core.services import research_orchestrator as orchestrator
from core.services.research_contract import ResearchDecision


def _legacy(name, payload=None):
    return f"event: {name}\ndata: {json.dumps(payload or {})}\n\n"


async def _visible(**_kwargs):
    yield _legacy("delta", {"text": "answer"})
    yield _legacy("done", {})


def _events(iterator):
    async def collect():
        return [item async for item in iterator]
    return asyncio.run(collect())


def _fake_store(monkeypatch):
    statuses = []
    monkeypatch.setattr(orchestrator.store, "create_run", lambda **kw: {"id": "research-1", **kw})
    monkeypatch.setattr(orchestrator.store, "transition_run", lambda rid, status, **kw: statuses.append(status) or {"id": rid, "status": status})
    monkeypatch.setattr(orchestrator.store, "create_tasks", lambda rid, tasks: [
        {"id": f"t{i}", "ordinal": i, "title": task.title, "objective": task.objective}
        for i, task in enumerate(tasks, 1)
    ])
    monkeypatch.setattr(orchestrator.store, "start_task", lambda task_id, **kw: {"id": task_id})
    monkeypatch.setattr(orchestrator.store, "complete_task", lambda task_id, finding, **kw: {"id": task_id})
    monkeypatch.setattr(orchestrator.store, "source_count", lambda rid: 0)
    monkeypatch.setattr(orchestrator.store, "consume_pending_steers", lambda rid: [])
    monkeypatch.setattr(orchestrator.store, "bind_visible_run", lambda rid, visible: None)
    return statuses


def test_inline_research_does_not_spawn_agents(monkeypatch):
    statuses = _fake_store(monkeypatch)
    spawned = []
    events = _events(orchestrator.stream_research_run(
        message="lookup", session_id="s1",
        decision=ResearchDecision(tier="inline"),
        visible_factory=_visible,
        worker_factory=lambda **kw: spawned.append(kw) or "",
    ))
    assert spawned == []
    assert "event: research_started" in events[0]
    assert any("event: research_completed" in event for event in events)
    assert statuses == ["planning", "researching", "verifying", "synthesizing", "completed"]


def test_orchestrated_research_bounds_worker_concurrency(monkeypatch):
    _fake_store(monkeypatch)
    active = 0
    maximum = 0

    async def worker(**kwargs):
        nonlocal active, maximum
        active += 1
        maximum = max(maximum, active)
        await asyncio.sleep(0.01)
        active -= 1
        return {"text": f"finding {kwargs['task']['ordinal']}", "status": "completed"}

    events = _events(orchestrator.stream_research_run(
        message="Sammenlign fem leverandører på pris, sikkerhed og drift i en grundig rapport",
        session_id="s1",
        decision=ResearchDecision(tier="orchestrated", max_workers=3, max_tasks=6),
        visible_factory=_visible,
        worker_factory=worker,
        orchestrator_enabled=True,
    ))
    assert maximum <= 3
    assert any("event: research_plan" in event for event in events)
    assert any("event: research_progress" in event for event in events)
