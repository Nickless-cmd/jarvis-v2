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


def _fake_store(monkeypatch, *, sources=None, tool_calls=0):
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
    monkeypatch.setattr(orchestrator.store, "list_sources", lambda rid: list(sources or []))
    monkeypatch.setattr(orchestrator.store, "tool_call_count", lambda rid: tool_calls)
    monkeypatch.setattr(orchestrator.store, "consume_pending_steers", lambda rid: [])
    monkeypatch.setattr(orchestrator.store, "bind_visible_run", lambda rid, visible: None)
    return statuses


def _completed_payload(events) -> dict:
    """Payload fra research_completed-eventet (A1's resultat lander her)."""
    for event in events:
        if "event: research_completed" in event:
            return json.loads(event.split("data: ", 1)[1])
    return {}


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


# --- Fase A: de tre koblinger der gjorde budgetterne levende (13/9-2026) ---


async def _visible_with_report(**_kwargs):
    yield _legacy("delta", {"text": "Pris er 10 kr [1]"})
    yield _legacy("done", {})


def test_A1_quality_gate_runs_on_the_real_report(monkeypatch):
    """Gaten skal køre på den FAKTISKE rapport + de indsamlede kilder.

    Før 13/9 gik runnet `verifying → synthesizing → completed` i tre blinde hop:
    statussen blev sat, men gaten der skulle verificere, blev aldrig kaldt.
    """
    _fake_store(monkeypatch, sources=[{"url": "https://example.com", "title": "Example"}])
    events = _events(orchestrator.stream_research_run(
        message="pris",
        session_id="s1",
        decision=ResearchDecision(tier="inline"),
        visible_factory=_visible_with_report,
    ))
    payload = _completed_payload(events)
    assert payload["quality"] == "passed", payload
    assert payload["quality_gates"]["citation_validity"] is True
    assert payload["quality_gates"]["coverage"] is True
    assert payload["quality_failures"] == []


def test_A1_gate_failure_is_marked_not_blocked(monkeypatch):
    """Et failed gate må ALDRIG fjerne svaret (spec §4 A1: markér, bloker ikke)."""
    _fake_store(monkeypatch, sources=[])  # ingen kilder → citation_validity + source_quality fejler
    events = _events(orchestrator.stream_research_run(
        message="pris",
        session_id="s1",
        decision=ResearchDecision(tier="inline"),
        visible_factory=_visible_with_report,
    ))
    payload = _completed_payload(events)
    assert payload["quality"] == "failed"
    assert "citation_validity" in payload["quality_failures"]
    # Svaret selv er stadig sendt videre til klienten.
    assert any("event: delta" in event for event in events)
    assert any("event: done" in event for event in events)


class _FakeClock:
    """Kun orchestratorens ur.

    At patche `orchestrator.time` er at patche det GLOBALE time-modul — det dræber
    event-loopets eget ur (`selectors.poll` venter så i evighed). Vi udskifter derfor
    navnet inde i orchestrator-modulet.
    """

    def __init__(self, *values: float) -> None:
        self._values = list(values)
        self._last = values[-1] if values else 0.0

    def monotonic(self) -> float:
        if self._values:
            self._last = self._values.pop(0)
        return self._last


def test_A2_wall_time_stops_the_wait_and_still_synthesizes(monkeypatch):
    """En hængende worker må ikke hænge hele runnet — og svaret skal stadig komme."""
    _fake_store(monkeypatch)
    monkeypatch.setattr(orchestrator, "time", _FakeClock(0.0, 10_000.0))

    async def slow_worker(**_kwargs):
        await asyncio.sleep(30)
        return {"text": "for sent", "status": "completed"}

    events = _events(orchestrator.stream_research_run(
        message="Sammenlign fem leverandører på pris, sikkerhed og drift",
        session_id="s1",
        decision=ResearchDecision(tier="orchestrated", max_workers=1, max_tasks=2),
        visible_factory=_visible,
        worker_factory=slow_worker,
        orchestrator_enabled=True,
    ))
    assert any("wall_time_exceeded" in event for event in events), events
    assert _completed_payload(events)["timed_out"] is True
    # Trods timeout syntetiseres der videre — brugeren står ikke uden svar.
    assert any("event: research_completed" in event for event in events)


def test_A3_tool_budget_stops_new_workers(monkeypatch):
    """Når loftet over værktøjskald er nået, startes ingen nye workers."""
    _fake_store(monkeypatch, tool_calls=999)
    started = []
    completed = []
    monkeypatch.setattr(
        orchestrator.store, "complete_task",
        lambda task_id, finding, **kw: completed.append((finding, kw)),
    )

    async def worker(**kwargs):
        started.append(kwargs["task"]["ordinal"])
        return {"text": "finding", "status": "completed"}

    events = _events(orchestrator.stream_research_run(
        message="Sammenlign fem leverandører på pris, sikkerhed og drift",
        session_id="s1",
        decision=ResearchDecision(tier="orchestrated", max_workers=2, max_tasks=2),
        visible_factory=_visible,
        worker_factory=worker,
        orchestrator_enabled=True,
    ))
    assert started == [], f"workers blev startet trods brugt budget: {started}"
    # Opgaven skal være markeret — ikke bare lydløst droppet.
    assert any(
        "tool budget exhausted" in str(finding) and kw.get("status") == "failed"
        for finding, kw in completed
    ), completed
    assert any("event: research_completed" in event for event in events)
