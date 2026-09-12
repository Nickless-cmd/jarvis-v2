import asyncio
import json

from core.services import research_orchestrator as orchestrator
from core.services.research_contract import ResearchDecision, ResearchPolicy


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


# --- Fase B1: source_target som rigtigt stop-kriterium (13/9-2026) ---


def test_B1_topup_picks_the_thinnest_track(monkeypatch):
    """Top-up-bølgen skal ramme HULLET — den track der har færrest kilder."""
    _fake_store(monkeypatch, sources=[{"task_id": "t1"}, {"task_id": "t1"}])
    tasks = [
        {"id": "t1", "ordinal": 1, "title": "A", "objective": "om A"},
        {"id": "t2", "ordinal": 2, "title": "B", "objective": "om B"},
    ]
    plan = orchestrator._topup_plan(
        "r", tasks, ResearchPolicy(max_workers=1, source_target=6),
    )
    assert len(plan) == 1
    assert "om B" in plan[0].objective
    assert plan[0].ordinal == 3  # fortsætter nummereringen


def test_B1_topup_stops_when_evidence_is_enough(monkeypatch):
    """Er kilderne nok, er en ekstra bølge bare dobbelt arbejde."""
    _fake_store(monkeypatch)
    monkeypatch.setattr(orchestrator.store, "source_count", lambda rid: 99)
    assert orchestrator._topup_plan(
        "r", [{"id": "t1", "ordinal": 1}], ResearchPolicy(source_target=6),
    ) == []


def test_B1_topup_stops_when_budget_is_gone(monkeypatch):
    """En ekstra bølge er en udgift. Er rådet brugt, kører den ikke."""
    _fake_store(monkeypatch, tool_calls=999)
    assert orchestrator._topup_plan(
        "r", [{"id": "t1", "ordinal": 1}], ResearchPolicy(),
    ) == []


def test_B1_topup_wave_runs_end_to_end(monkeypatch):
    """Er kilderne for få, kører der en ekstra bølge — med NYE tracks."""
    _fake_store(monkeypatch)
    calls = {"n": 0}

    def fake_create_tasks(rid, tasks):
        calls["n"] += 1
        prefix = "t" if calls["n"] == 1 else "u"
        return [
            {"id": f"{prefix}{i}", "ordinal": i, "title": t.title, "objective": t.objective}
            for i, t in enumerate(tasks, 1)
        ]

    monkeypatch.setattr(orchestrator.store, "create_tasks", fake_create_tasks)
    started: list[str] = []

    async def worker(**kwargs):
        started.append(str(kwargs["task"]["id"]))
        return {"text": "f", "status": "completed"}

    events = _events(orchestrator.stream_research_run(
        message="Sammenlign fem leverandører på pris, sikkerhed og drift",
        session_id="s1",
        decision=ResearchDecision(tier="orchestrated", max_workers=2, max_tasks=2, source_target=5),
        visible_factory=_visible,
        worker_factory=worker,
        orchestrator_enabled=True,
    ))
    assert any("topping_up" in event for event in events), events
    assert any(sid.startswith("u") for sid in started), started


def test_B1_topup_does_not_run_after_timeout(monkeypatch):
    """Et run der allerede har brændt sin tid skal IKKE have en ekstra bølge."""
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
    assert not any("topping_up" in event for event in events), events


# --- Fase B2: worker-svaret læses som den struktur det blev bedt om (13/9-2026) ---


def test_B2_parser_laeser_findings_strukturen():
    """Worker'ens result_contract beder om findings/sources/confidence/gaps."""
    text = json.dumps({
        "findings": [
            {
                "claim": "Prisen er 10 kr",
                "sources": ["https://a.example/x"],
                "confidence": "high",
                "gaps": "kun én kilde",
            },
            {"claim": "Driften er stabil", "url": "https://b.example/y"},
        ]
    })
    parsed = orchestrator._parse_findings(text, 3)
    assert [f.claim for f in parsed] == ["Prisen er 10 kr", "Driften er stabil"]
    assert parsed[0].source_urls == ("https://a.example/x",)
    assert parsed[0].confidence == "high"
    assert parsed[0].caveat == "kun én kilde"
    assert parsed[1].source_urls == ("https://b.example/y",)
    assert all(f.task_ordinal == 3 for f in parsed)


def test_B2_parser_laeser_json_i_hegn_og_enkelt_objekt():
    """Modeller pakker ofte JSON i ``` — og nogle gange ét enkelt objekt."""
    fenced = 'Her er mine fund:\n```json\n{"claim": "X er sandt", "url": "https://c.example/z"}\n```'
    parsed = orchestrator._parse_findings(fenced, 1)
    assert len(parsed) == 1
    assert parsed[0].claim == "X er sandt"
    assert parsed[0].source_urls == ("https://c.example/z",)


def test_B2_parser_falder_tilbage_til_prosa():
    """Svarer worker'en i prosa, tabes evidensen ikke — men tilliden sænkes."""
    med_url = orchestrator._parse_findings("Se https://d.example/q for detaljer.", 2)
    assert len(med_url) == 1
    assert med_url[0].source_urls == ("https://d.example/q",)
    assert med_url[0].confidence == "medium"

    uden_url = orchestrator._parse_findings("Jeg fandt ikke noget brugbart.", 2)
    assert len(uden_url) == 1
    assert uden_url[0].source_urls == ()
    assert uden_url[0].confidence == "low"


def test_B2_parser_kaster_aldrig():
    """Kanter: tomt, skrald, uventede typer — et svar må ikke vælte et run."""
    assert orchestrator._parse_findings("", 1) == []
    assert orchestrator._parse_findings(None, 1) == []
    for skrald in ("{ikke json", "[1, 2, 3]", "{}", json.dumps({"findings": "ikke en liste"})):
        parsed = orchestrator._parse_findings(skrald, 1)
        assert isinstance(parsed, list)  # ingen undtagelse
    # En liste af objekter UDEN claim springes over — men hele teksten reddes.
    parsed = orchestrator._parse_findings(json.dumps({"findings": [{"sources": ["https://e.example"]}]}), 1)
    assert len(parsed) == 1


def test_B2_evidensblokken_nummererer_kilderne():
    """Syntesen skal kunne cite [N] mod præcis den liste gaten måler imod."""
    sources = [
        {"canonical_url": "https://a.example/1", "title": "A"},
        {"url": "https://b.example/2", "title": ""},
    ]
    findings = [
        orchestrator.ResearchFinding(task_ordinal=1, claim="Pris er 10", source_urls=("https://a.example/1",)),
    ]
    block = orchestrator._evidence_block(["rå note"], sources, findings)
    assert "[1] https://a.example/1 — A" in block
    assert "[2] https://b.example/2" in block
    assert "Pris er 10" in block
    assert "rå note" in block


def test_B2_findings_gemmes_og_taelles(monkeypatch):
    """Fundene skal gemmes struktureret — ikke kun som rå tekst."""
    _fake_store(monkeypatch, sources=[{"canonical_url": "https://a.example/1", "title": "A"}])
    gemt = []
    monkeypatch.setattr(
        orchestrator.store, "complete_task",
        lambda task_id, finding, **kw: gemt.append((task_id, finding, kw)) or {"id": task_id},
    )

    async def worker(**_kwargs):
        return {
            "status": "completed",
            "text": json.dumps({
                "findings": [{"claim": "Kilde-båren påstand", "sources": ["https://a.example/1"]}]
            }),
        }

    events = _events(orchestrator.stream_research_run(
        message="Sammenlign fem leverandører på pris, sikkerhed og drift",
        session_id="s1",
        decision=ResearchDecision(tier="orchestrated", max_workers=2, max_tasks=2, source_target=99),
        visible_factory=_visible,
        worker_factory=worker,
        orchestrator_enabled=True,
    ))
    # payloaden til complete_task bærer de parsee fund
    payloads = [f for _tid, f, _kw in gemt if isinstance(f, dict) and f.get("findings")]
    assert payloads, gemt
    assert payloads[0]["findings"][0]["claim"] == "Kilde-båren påstand"
    # og de tælles i det afsluttende event
    assert _completed_payload(events).get("findings", 0) >= 1, events


# --- Fase B3: gap/repair-pass — ÉN critic-runde (13/9-2026) ---


def _fake_store_seq(monkeypatch, *, tool_calls=0):
    """Som `_fake_store`, men `create_tasks` giver GLOBALT unikke id'er.

    Den almindelige fake starter forfra på `t1` ved hvert kald, så critic-opgaven
    ville kollidere med planens id'er og blive filtreret væk — og B3 ville aldrig
    køre i testen. Her får hver opgave sit eget id på tværs af kald.
    """
    counter = {"n": 0}

    def create_tasks(rid, tasks):
        out = []
        for task in tasks:
            counter["n"] += 1
            out.append({
                "id": f"t{counter['n']}",
                "ordinal": task.ordinal,
                "title": task.title,
                "objective": task.objective,
            })
        return out

    statuses = _fake_store(monkeypatch, tool_calls=tool_calls)
    monkeypatch.setattr(orchestrator.store, "create_tasks", create_tasks)
    # B3 testes i isolation: top-up-bølgen (B1) patches væk, så det er critic-
    # rundens opførsel der måles — ikke om der også blev fyldt kilder på.
    monkeypatch.setattr(orchestrator, "_topup_plan", lambda *a, **k: [])
    return statuses


def test_B3_gap_pass_runs_exactly_once(monkeypatch):
    """Critic'en skal køre ÉN gang — ikke i en løkke (spec princip 5)."""
    _fake_store_seq(monkeypatch)
    titles = []

    async def worker(**kwargs):
        task = kwargs["task"]
        titles.append(task["title"])
        if task["title"] == "Gap check":
            return {"text": json.dumps({"gaps": ["Pris mangler for leverandør 3"]}), "status": "completed"}
        return {
            "text": json.dumps({"findings": [{"claim": "A koster 10", "sources": ["https://a.example"]}]}),
            "status": "completed",
        }

    events = _events(orchestrator.stream_research_run(
        message="Sammenlign fem leverandører på pris, sikkerhed og drift",
        session_id="s1",
        decision=ResearchDecision(tier="orchestrated", max_workers=2, max_tasks=2),
        visible_factory=_visible,
        worker_factory=worker,
        orchestrator_enabled=True,
    ))
    assert titles.count("Gap check") == 1, titles
    assert any("gap_check" in event for event in events), events
    assert _completed_payload(events).get("gaps") == 1, events


def test_B3_skipped_after_timeout(monkeypatch):
    """Et run der allerede har overskredet sin væg-tid må ikke starte flere workers."""
    _fake_store_seq(monkeypatch)
    monkeypatch.setattr(orchestrator, "time", _FakeClock(0.0, 10_000.0))
    titles = []

    async def worker(**kwargs):
        titles.append(kwargs["task"]["title"])
        await asyncio.sleep(30)
        return {"text": "for sent", "status": "completed"}

    events = _events(orchestrator.stream_research_run(
        message="Sammenlign fem leverandører på pris, sikkerhed og drift",
        session_id="s1",
        decision=ResearchDecision(tier="orchestrated", max_workers=1, max_tasks=1),
        visible_factory=_visible,
        worker_factory=worker,
        orchestrator_enabled=True,
    ))
    assert "Gap check" not in titles, titles
    assert not any("gap_check" in event for event in events), events


def test_B3_skipped_when_budget_exhausted(monkeypatch):
    """Er værktøjs-budgettet brugt, har critic'en ikke råd til at køre."""
    _fake_store_seq(monkeypatch, tool_calls=999)
    titles = []

    async def worker(**kwargs):
        titles.append(kwargs["task"]["title"])
        return {"text": "x", "status": "completed"}

    events = _events(orchestrator.stream_research_run(
        message="Sammenlign fem leverandører på pris, sikkerhed og drift",
        session_id="s1",
        decision=ResearchDecision(tier="orchestrated", max_workers=1, max_tasks=1),
        visible_factory=_visible,
        worker_factory=worker,
        orchestrator_enabled=True,
    ))
    assert "Gap check" not in titles, titles
    assert not any("gap_check" in event for event in events), events


def test_B3_critic_failure_does_not_kill_the_run(monkeypatch):
    """Critic'en er et supplement, ikke et krav: fejler den, kommer svaret stadig."""
    _fake_store_seq(monkeypatch)

    async def worker(**kwargs):
        task = kwargs["task"]
        if task["title"] == "Gap check":
            raise RuntimeError("critic døde")
        return {
            "text": json.dumps({"findings": [{"claim": "A koster 10", "sources": ["https://a.example"]}]}),
            "status": "completed",
        }

    events = _events(orchestrator.stream_research_run(
        message="Sammenlign fem leverandører på pris, sikkerhed og drift",
        session_id="s1",
        decision=ResearchDecision(tier="orchestrated", max_workers=2, max_tasks=2),
        visible_factory=_visible,
        worker_factory=worker,
        orchestrator_enabled=True,
    ))
    assert any("event: research_completed" in event for event in events), events
    assert _completed_payload(events).get("gaps") == 0, events


def test_B3_parse_gaps_former():
    """Critic-svaret i de former en worker faktisk kan svare i."""
    assert orchestrator._parse_gaps('{"gaps": ["a", "b"]}') == ["a", "b"]
    assert orchestrator._parse_gaps('```json\n{"gaps": ["c"]}\n```') == ["c"]
    assert orchestrator._parse_gaps("linje en\nlinje to") == ["linje en", "linje to"]
    # Et gyldigt svar uden huller giver nul huller — ikke hele svaret som ét hul.
    assert orchestrator._parse_gaps("[]") == []
    assert orchestrator._parse_gaps('{"gaps": []}') == []
    assert orchestrator._parse_gaps("") == []
    assert orchestrator._parse_gaps("ikke json") == ["ikke json"]


def test_B3_gaps_naar_evidensblokken():
    """Hullerne skal stå i den evidens syntesen får — ellers er de uden virkning."""
    block = orchestrator._evidence_block(
        [], [{"canonical_url": "https://a.dk", "title": "A"}], [], ["Pris mangler for 3"]
    )
    assert "Known gaps" in block
    assert "Pris mangler for 3" in block
    # Uden huller må sektionen ikke stå tom og støjende.
    assert "Known gaps" not in orchestrator._evidence_block([], [], [], [])
