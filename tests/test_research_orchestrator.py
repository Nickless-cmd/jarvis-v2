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


def _fake_store(monkeypatch, *, sources=None, findings=None, tool_calls=0):
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
    # Fase C3: dommeren læser fund-antal. Uden denne rammer den den ægte DB og
    # falder i `_judge_quality`s except — et falsk grønt.
    monkeypatch.setattr(orchestrator.store, "list_findings", lambda rid: list(findings or []))
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
    # Ægte legacy-form (`visible_runs.py:1722`): delta bæres i `delta`-nøglen,
    # ikke `text`. Faken SKAL matche producenten — ellers validerer A1-testen
    # en form der ikke findes (og skjuler netop den bug `_delta_text` havde).
    yield _legacy("delta", {"type": "delta", "run_id": "visible-a1", "delta": "Pris er 10 kr [1]"})
    yield _legacy("done", {})


def test_A1_delta_text_laeser_den_aegte_frame():
    """Regression (13/9-2026): `_delta_text` læste `text`, producenten sender `delta`.

    Målt: den returnerede '' på enhver ægte frame, så A1's gate evaluerede en tom
    rapport i produktion. Begge former skal nu give teksten.
    """
    aegte = 'event: delta\ndata: {"type": "delta", "run_id": "r1", "delta": "Pris er 10 kr [1]"}\n\n'
    assert orchestrator._delta_text(aegte) == "Pris er 10 kr [1]"
    # Bagudkompatibilitet: den gamle (fake) form må ikke knække.
    gammel = 'event: delta\ndata: {"text": "Pris er 10 kr [1]"}\n\n'
    assert orchestrator._delta_text(gammel) == "Pris er 10 kr [1]"
    # Andre frames bidrager ikke.
    assert orchestrator._delta_text('event: research_plan\ndata: {}\n\n') == ""


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


# --- Fase C2: indsatsen skal nå hele vejen ned til worker'en (13/9-2026) ---
#
# Speccens §2.2-fund: `spawn_agent_task` TAR `budget_tokens`, og
# `_check_budget_and_expire` kan dræbe en agent der sprænger sit budget — men
# lane'en sendte den aldrig. Målt 13/9-2026: 113 af 138 researcher-kørsler
# havde intet budget, så vagten var inert. Disse tests holder de to led fast.

def test_C2_budgettet_naar_worker_factory(monkeypatch):
    """Beslutningens indsats skal nå worker'en — ellers er tallet uden modtager."""
    _fake_store(monkeypatch)
    seen = []

    async def worker(**kwargs):
        seen.append(kwargs)
        return {"text": "finding [1]", "status": "completed"}

    decision = ResearchDecision(
        tier="orchestrated",
        signals=("comparative_breadth",),
        max_workers=1,
        max_tasks=1,
        max_tool_calls=8,
        wall_time_seconds=180,
        source_target=2,
        worker_max_turns=7,
        worker_token_budget=12_345,
    )
    _events(orchestrator.stream_research_run(
        message="Sammenlign fem leverandører på pris og sikkerhed",
        session_id="s1",
        worker_factory=worker,
        decision=decision,
        orchestrator_enabled=True,
    ))
    assert seen, "ingen workers blev kørt"
    assert any(
        kw["budget_tokens"] == 12_345 and kw["max_turns"] == 7 for kw in seen
    ), f"indsatsen nåede ikke worker'en: {[ (k['max_turns'], k['budget_tokens']) for k in seen ]}"
    # Ingen worker må stå uden loft når beslutningen satte et.
    assert all(kw["budget_tokens"] > 0 for kw in seen), seen


def test_C2_intet_budget_bevarer_gammel_adfaerd(monkeypatch):
    """0 = ubegrænset. En kalder der ikke sætter et loft må ikke få et."""
    _fake_store(monkeypatch)
    seen = []

    async def worker(**kwargs):
        seen.append(kwargs)
        return {"text": "finding", "status": "completed"}

    decision = ResearchDecision(
        tier="orchestrated", max_workers=1, max_tasks=1,
        worker_max_turns=8, worker_token_budget=0,
    )
    _events(orchestrator.stream_research_run(
        message="Sammenlign fem leverandører på pris og sikkerhed",
        session_id="s1",
        worker_factory=worker,
        decision=decision,
        orchestrator_enabled=True,
    ))
    assert seen
    assert all(kw["budget_tokens"] == 0 for kw in seen), seen


def test_C2_default_worker_sender_budgettet_til_spawn(monkeypatch):
    """Den dybeste led. Uden dette kald er hele C2 kosmetisk: budgettet står i
    policy'en, men `spawn_agent_task` hører det aldrig, og vagten forbliver død."""
    import core.runtime.db as db_mod
    import core.services.agent_runtime_spawn as spawn_mod

    captured = {}

    def fake_spawn(**kwargs):
        captured.update(kwargs)
        return {"agent_id": "a1", "status": "completed"}

    monkeypatch.setattr(spawn_mod, "spawn_agent_task", fake_spawn)
    monkeypatch.setattr(db_mod, "list_agent_messages", lambda **kwargs: [])

    orchestrator._default_worker_sync(
        task={"id": "t1", "objective": "undersøg pris"},
        run_id="r1",
        skill_instructions="",
        max_turns=7,
        budget_tokens=12_345,
    )
    assert captured.get("budget_tokens") == 12_345, captured
    assert captured.get("max_turns") == 7, captured
    # Worker'en skal stadig være read-only — budgettet må ikke have ændret det.
    assert captured.get("tool_policy") == "read-only-runtime"


# --- Fase C1: LLM-planlægger med regex-fallback (13/9-2026) ---
#
# Planneren må fejle på alle måder uden at runnet dør. Regex-planen er
# kontrakten: er flaget slået fra, eller svarer planneren ikke, er outputtet
# byte-identisk med `_plan()`.

def test_C1_parse_plan_former():
    """Plannerens svar i de former en model faktisk kan svare i."""
    clean = orchestrator._parse_plan(
        '[{"title": "Pris", "objective": "Find priser"}, {"title": "Drift", "objective": "Find driftsdata"}]',
        6,
    )
    assert [t.title for t in clean] == ["Pris", "Drift"]
    assert [t.ordinal for t in clean] == [1, 2]

    fenced = orchestrator._parse_plan(
        'Sure!\n```json\n[{"title": "A", "objective": "a"}, {"title": "B", "objective": "b"}]\n```',
        6,
    )
    assert [t.title for t in fenced] == ["A", "B"]

    wrapped = orchestrator._parse_plan(
        '{"tasks": [{"title": "A", "objective": "a"}, {"title": "B", "objective": "b"}]}',
        6,
    )
    assert [t.title for t in wrapped] == ["A", "B"]


def test_C1_parse_plan_afviser_soepla():
    """Garbage og for tynde planer giver [] — så kalderen falder til regex."""
    assert orchestrator._parse_plan("jeg ved det ikke", 6) == []
    assert orchestrator._parse_plan("", 6) == []
    # Én track er ikke en plan — et orchestrated run med ét spor er inline.
    assert orchestrator._parse_plan('[{"title": "A", "objective": "a"}]', 6) == []
    # Manglende objective falder tilbage til titlen — en tynd opgave er bedre
    # end et kasseret spor (speccen: planen skal fejle TILBAGE, ikke væk).
    fallback = orchestrator._parse_plan('[{"title": "A"}, {"title": "B"}]', 6)
    assert [t.objective for t in fallback] == ["A", "B"]
    # Men et spor helt uden titel er ubrugeligt og kasseres.
    assert orchestrator._parse_plan('[{"objective": "a"}, {"objective": "b"}]', 6) == []


def test_C1_parse_plan_respekterer_loftet():
    many = json.dumps([{"title": f"T{i}", "objective": f"o{i}"} for i in range(9)])
    assert len(orchestrator._parse_plan(many, 4)) == 4


def test_C1_flag_off_er_byte_identisk(monkeypatch):
    """Uden flaget må planlægningen være præcis regex-planen — uden netværk."""
    called = []
    monkeypatch.setattr(
        "core.services.cheap_provider_runtime.execute_public_safe_cheap_lane",
        lambda **kw: called.append(kw) or {"status": "completed", "text": "[]"},
    )
    tasks = asyncio.run(
        orchestrator._plan_tasks("Sammenlign fem leverandører", 6, planner_enabled=False)
    )
    assert called == [], "planneren blev kaldt selv om flaget var slået fra"
    assert [t.title for t in tasks] == [t.title for t in orchestrator._plan("Sammenlign fem leverandører", 6)]


def test_C1_planner_bruges_naar_flag_on(monkeypatch):
    monkeypatch.setattr(
        "core.services.cheap_provider_runtime.execute_public_safe_cheap_lane",
        lambda **kw: {
            "status": "completed",
            "text": '[{"title": "Planner A", "objective": "aa"}, {"title": "Planner B", "objective": "bb"}]',
        },
    )
    tasks = asyncio.run(
        orchestrator._plan_tasks("Sammenlign fem leverandører", 6, planner_enabled=True)
    )
    assert [t.title for t in tasks] == ["Planner A", "Planner B"]


def test_C1_planner_fejl_falder_til_regex(monkeypatch):
    """En død planner må ikke koste planen — regex overtager."""
    def boom(**kw):
        raise RuntimeError("public-safe local fallback unavailable")

    monkeypatch.setattr("core.services.cheap_provider_runtime.execute_public_safe_cheap_lane", boom)
    tasks = asyncio.run(
        orchestrator._plan_tasks("Sammenlign fem leverandører", 6, planner_enabled=True)
    )
    assert [t.title for t in tasks] == [t.title for t in orchestrator._plan("Sammenlign fem leverandører", 6)]


def test_C1_planner_tomt_svar_falder_til_regex(monkeypatch):
    monkeypatch.setattr(
        "core.services.cheap_provider_runtime.execute_public_safe_cheap_lane",
        lambda **kw: {"status": "completed", "text": "   "},
    )
    tasks = asyncio.run(
        orchestrator._plan_tasks("Sammenlign fem leverandører", 6, planner_enabled=True)
    )
    assert [t.title for t in tasks] == [t.title for t in orchestrator._plan("Sammenlign fem leverandører", 6)]


def test_C1_plannerens_plan_naar_create_tasks(monkeypatch):
    """Dybeste test: planen fra planneren skal hele vejen til create_tasks."""
    _fake_store(monkeypatch)
    monkeypatch.setattr(orchestrator, "_topup_plan", lambda *a, **k: [])
    monkeypatch.setattr(
        orchestrator,
        "_setting",
        lambda name, default: True if name == "research_llm_planner_enabled" else default,
    )
    monkeypatch.setattr(
        "core.services.cheap_provider_runtime.execute_public_safe_cheap_lane",
        lambda **kw: {
            "status": "completed",
            "text": '[{"title": "Planner A", "objective": "aa"}, {"title": "Planner B", "objective": "bb"}]',
        },
    )
    seen: list[list[str]] = []
    real_create = orchestrator.store.create_tasks
    monkeypatch.setattr(
        orchestrator.store,
        "create_tasks",
        lambda rid, tasks: seen.append([t.title for t in tasks]) or real_create(rid, tasks),
    )

    events = _events(orchestrator.stream_research_run(
        message="Sammenlign fem leverandører på pris, sikkerhed og drift",
        session_id="s1",
        decision=ResearchDecision(tier="orchestrated", max_workers=2, max_tasks=2),
        visible_factory=_visible,
        worker_factory=lambda **kw: {"text": "x", "status": "completed"},
        orchestrator_enabled=True,
    ))
    assert any("event: research_completed" in e for e in events), events
    assert seen and seen[0] == ["Planner A", "Planner B"], seen


def test_C1_flag_off_kalder_aldrig_planneren_i_run(monkeypatch):
    """Hele runnet med flaget fra: planneren må ikke kaldes én eneste gang."""
    _fake_store(monkeypatch)
    monkeypatch.setattr(orchestrator, "_topup_plan", lambda *a, **k: [])
    called = []
    monkeypatch.setattr(
        "core.services.cheap_provider_runtime.execute_public_safe_cheap_lane",
        lambda **kw: called.append(kw) or {"status": "completed", "text": "[]"},
    )
    events = _events(orchestrator.stream_research_run(
        message="Sammenlign fem leverandører på pris, sikkerhed og drift",
        session_id="s1",
        decision=ResearchDecision(tier="orchestrated", max_workers=2, max_tasks=2),
        visible_factory=_visible,
        worker_factory=lambda **kw: {"text": "x", "status": "completed"},
        orchestrator_enabled=True,
    ))
    assert any("event: research_completed" in e for e in events), events
    assert called == [], "planneren blev kaldt i et run hvor flaget var slået fra"


# --- Fase C3: LLM-dommer mod rubric (13/9-2026) ---
#
# Dommeren er et SUPPLEMENT til de deterministiske gates. Den kan fejle frit,
# den må aldrig ændre `quality["status"]`, og flag-off må ikke røre netværket.

def _judge_flag(monkeypatch, *, enabled: bool = True):
    """Slå KUN dommer-flaget til/fra; andre flag beholder deres default."""
    monkeypatch.setattr(
        orchestrator,
        "_setting",
        lambda name, default: enabled if name == "research_llm_judge_enabled" else default,
    )


def _fake_cheap_lane(monkeypatch, *, verdict: str = "pass", raise_exc: bool = False):
    """Stub den billige lane. Registrerer kald, så vi kan bevise at den (ikke) kørte."""
    import core.services.cheap_provider_runtime as cheap_runtime

    calls: list[str] = []

    def _fake(*, message: str):
        # KUN dommerens kald taeller (15/9-2026). Stubben er modul-global, saa
        # en baggrundstraad fra en tidligere test — «Extract 3-5 key
        # topics…» — landede ogsaa her, og «praecis ét kald» fejlede efter
        # hvem der koerte foer. Dommerens prompt beder altid om rubrikken.
        if "answers_question" in message:
            calls.append(message)
        if raise_exc:
            raise RuntimeError("cheap lane nede")
        payload = {
            "answers_question": True,
            "evidence_separated": True,
            "uncertainty_honest": True,
            "no_unsupported_claims": verdict == "pass",
            "reason": "vurderet",
        }
        return {"status": "completed", "text": json.dumps(payload)}

    monkeypatch.setattr(cheap_runtime, "execute_public_safe_cheap_lane", _fake)
    return calls


def test_C3_parse_verdict_binaer():
    """Alle fire ja → pass; ét nej → fail; et halvt svar er ikke en dom."""
    ok = json.dumps({
        "answers_question": True, "evidence_separated": True,
        "uncertainty_honest": True, "no_unsupported_claims": True,
        "reason": "solid",
    })
    verdict = orchestrator._parse_verdict(ok)
    assert verdict["verdict"] == "pass"
    assert all(verdict["criteria"].values())

    one_no = json.dumps({
        "answers_question": True, "evidence_separated": False,
        "uncertainty_honest": True, "no_unsupported_claims": True,
    })
    failed = orchestrator._parse_verdict(one_no)
    assert failed["verdict"] == "fail"
    assert failed["criteria"]["evidence_separated"] is False

    # Manglende kriterium → None. Et ufuldstændigt svar må ikke ligne en dom.
    assert orchestrator._parse_verdict('{"answers_question": true}') is None
    # Ikke-boolean → None.
    assert orchestrator._parse_verdict(json.dumps({
        "answers_question": "yes", "evidence_separated": True,
        "uncertainty_honest": True, "no_unsupported_claims": True,
    })) is None
    # Garbage → None.
    assert orchestrator._parse_verdict("jeg ved det ikke") is None
    assert orchestrator._parse_verdict("") is None
    # Fenced JSON parses.
    assert orchestrator._parse_verdict(f"```json\n{ok}\n```")["verdict"] == "pass"


def test_C3_flag_off_roerer_aldrig_netvaerket(monkeypatch):
    _fake_store(monkeypatch)
    _judge_flag(monkeypatch, enabled=False)
    calls = _fake_cheap_lane(monkeypatch)
    events = _events(orchestrator.stream_research_run(
        message="Sammenlign fem leverandører på pris, sikkerhed og drift",
        session_id="s1",
        decision=ResearchDecision(tier="orchestrated", max_workers=2, max_tasks=2),
        visible_factory=_visible,
        worker_factory=lambda **kw: {"text": "x", "status": "completed"},
        orchestrator_enabled=True,
    ))
    assert calls == [], "dommeren kaldte netværket selvom flaget var slået fra"
    assert _completed_payload(events)["judge"] == {}


def test_C3_dommen_naar_completed_eventet(monkeypatch):
    _fake_store(monkeypatch)
    _judge_flag(monkeypatch)
    calls = _fake_cheap_lane(monkeypatch, verdict="pass")
    events = _events(orchestrator.stream_research_run(
        message="Sammenlign fem leverandører på pris, sikkerhed og drift",
        session_id="s1",
        decision=ResearchDecision(tier="orchestrated", max_workers=2, max_tasks=2),
        visible_factory=_visible,
        worker_factory=lambda **kw: {"text": "x", "status": "completed"},
        orchestrator_enabled=True,
    ))
    assert len(calls) == 1, calls
    payload = _completed_payload(events)
    assert payload["judge"]["verdict"] == "pass"
    assert payload["judge"]["criteria"]["answers_question"] is True


def test_C3_dommer_fejl_koster_ikke_svaret(monkeypatch):
    """En dommer der kaster må ikke fjerne svaret brugeren venter på."""
    _fake_store(monkeypatch)
    _judge_flag(monkeypatch)
    _fake_cheap_lane(monkeypatch, raise_exc=True)
    events = _events(orchestrator.stream_research_run(
        message="Sammenlign fem leverandører på pris, sikkerhed og drift",
        session_id="s1",
        decision=ResearchDecision(tier="orchestrated", max_workers=2, max_tasks=2),
        visible_factory=_visible,
        worker_factory=lambda **kw: {"text": "x", "status": "completed"},
        orchestrator_enabled=True,
    ))
    assert any("event: research_completed" in e for e in events), events
    assert _completed_payload(events)["judge"] == {}


def test_C3_dommen_aendrer_ikke_gate_status(monkeypatch):
    """Dommeren er et supplement: 'failed' gate forbliver failed, også når dommeren siger pass."""
    _fake_store(monkeypatch, sources=[])  # ingen kilder → citation_validity + source_quality fejler
    _judge_flag(monkeypatch)
    _fake_cheap_lane(monkeypatch, verdict="pass")
    events = _events(orchestrator.stream_research_run(
        message="Sammenlign fem leverandører på pris, sikkerhed og drift",
        session_id="s1",
        decision=ResearchDecision(tier="orchestrated", max_workers=2, max_tasks=2),
        visible_factory=_visible,
        worker_factory=lambda **kw: {"text": "x", "status": "completed"},
        orchestrator_enabled=True,
    ))
    payload = _completed_payload(events)
    assert payload["quality"] == "failed", payload
    assert payload["judge"]["verdict"] == "pass", payload
