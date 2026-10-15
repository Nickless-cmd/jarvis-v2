import time

import pytest


def _make_async_iter(items):
    async def _gen():
        for item in items:
            yield item
    return _gen()


def _patch(monkeypatch, frames):
    import core.services.run_event_log as rel
    import core.services.visible_runs as vr
    import core.services.visible_runs_sse_v2 as v2
    created, appended, done = [], [], []
    monkeypatch.setattr(rel, "create", lambda rid, sid: created.append((rid, sid)))
    monkeypatch.setattr(rel, "append", lambda rid, f: appended.append((rid, f)))
    monkeypatch.setattr(rel, "mark_done", lambda rid: done.append(rid))
    monkeypatch.setattr(rel, "prune", lambda: None)
    monkeypatch.setattr(vr, "start_visible_run", lambda **kw: _make_async_iter([]))
    monkeypatch.setattr(v2, "translate_to_v2", lambda it, **kw: _make_async_iter(frames))
    return created, appended, done


def test_detached_run_creates_log_appends_and_marks_done(monkeypatch):
    created, appended, done = _patch(monkeypatch, ["a", "b", "c"])
    from core.services.visible_runs_sections.detached_run import start_user_run_detached
    rid = start_user_run_detached(
        message="hej", session_id="s1", eff_model="m", eff_provider="p", lane="l"
    )
    assert rid and created and created[0][1] == "s1"
    assert created[0][0] == rid
    for _ in range(60):
        if len(appended) >= 3 and done:
            break
        time.sleep(0.05)
    assert [f for _r, f in appended] == ["a", "b", "c"]
    assert done and done[0] == rid


def test_detached_run_selects_research_iterator_when_requested(monkeypatch):
    created, appended, done = _patch(monkeypatch, ["research-frame"])
    import core.services.research_orchestrator as research
    calls = []
    monkeypatch.setattr(research, "research_enabled", lambda: True)
    monkeypatch.setattr(
        research,
        "stream_research_run",
        lambda **kwargs: calls.append(kwargs) or _make_async_iter([]),
    )
    from core.services.visible_runs_sections.detached_run import start_user_run_detached
    rid = start_user_run_detached(
        message="model message", original_message="original", session_id="s1",
        eff_model="m", eff_provider="p", lane="l", research_mode=True,
    )
    for _ in range(60):
        if calls and done:
            break
        time.sleep(0.05)
    assert calls[0]["message"] == "model message"
    assert calls[0]["original_query"] == "original"
    assert calls[0]["visible_run_id"] == rid


def test_genoptaget_tur_lukker_opgaven_fra_synkron_journal(monkeypatch):
    from core.services.visible_runs_sections import detached_run as d
    from core.services import in_flight_runs as ifr
    closed = []
    monkeypatch.setattr(ifr, "get_record", lambda rid: {"status": "completed"})
    monkeypatch.setattr(ifr, "current_owner", lambda: "owner-1")
    monkeypatch.setattr(ifr, "settle_terminal",
                        lambda *args, **kw: closed.append((args, kw)))
    monkeypatch.setattr("core.services.visible_runs_outcomes.run_er_terminal",
                        lambda rid: False)
    d._afregn_genoptaget_run("task-1", "inner-1", generation=1, wrapper_run_id="inner-1")
    assert closed == [(("task-1",), {
        "status": "completed", "reason": "recovery-run-terminal",
        "expected_generation": 1, "expected_owner": "owner-1",
    })]


def test_faerdigt_svar_lukker_opgaven_selv_om_in_flight_stadig_staar_running(monkeypatch):
    """En forsinket journal-finalisering må ikke købe samme svar igen efter lejen."""
    from core.services.visible_runs_sections import detached_run as d
    from core.services import in_flight_runs as ifr
    closed = []
    monkeypatch.setattr(ifr, "get_record", lambda rid: {"status": "running"})
    monkeypatch.setattr(ifr, "current_owner", lambda: "owner-1")
    monkeypatch.setattr(ifr, "settle_terminal",
                        lambda *args, **kw: closed.append((args, kw)))
    monkeypatch.setattr("core.services.visible_runs_outcomes.run_er_terminal",
                        lambda rid: True)

    d._afregn_genoptaget_run("task-1", "inner-1", generation=1, wrapper_run_id="inner-1")

    assert len(closed) == 1
    assert closed[0][0] == ("task-1",)
    assert closed[0][1]["expected_generation"] == 1


def test_afbrudt_genoptagelse_giver_samme_krav_tilbage(monkeypatch):
    from core.services.visible_runs_sections import detached_run as d
    from core.services import in_flight_runs as ifr
    released = []
    monkeypatch.setattr(ifr, "get_record", lambda rid: {
        "status": "recovering", "exit_reason": "budget-opbrugt",
    })
    monkeypatch.setattr(ifr, "current_owner", lambda: "owner-1")
    monkeypatch.setattr(ifr, "release_recovery_claim",
                        lambda *args, **kw: released.append((args, kw)) or True)
    d._afregn_genoptaget_run("task-1", "inner-1", generation=2, wrapper_run_id="inner-1")
    assert released == [(("task-1", 2), {
        "owner": "owner-1", "reason": "budget-opbrugt", "retry_after_s": 30.0,
    })]


def test_providerens_http_400_genstarter_ikke_samme_opgave(monkeypatch):
    from core.services.visible_runs_sections import detached_run as d
    from core.services import in_flight_runs as ifr
    closed, released = [], []
    monkeypatch.setattr(ifr, "get_record", lambda rid: {
        "status": "recovering",
        "exit_reason": "interrupted:followup-round-1-provider-error: HTTP 400: invalid tool_calls",
    })
    monkeypatch.setattr(ifr, "current_owner", lambda: "owner-1")
    monkeypatch.setattr(ifr, "settle_terminal",
                        lambda *args, **kw: closed.append((args, kw)))
    monkeypatch.setattr(ifr, "release_recovery_claim",
                        lambda *args, **kw: released.append((args, kw)))

    d._afregn_genoptaget_run("task-1", "inner-1", generation=2, wrapper_run_id="inner-1")

    assert len(closed) == 1
    assert closed[0][1]["status"] == "failed_terminal"
    assert closed[0][1]["expected_generation"] == 2
    assert released == []


def test_genoptaget_tur_opretter_ikke_et_nyt_krav(monkeypatch):
    _patch(monkeypatch, ["frame"])
    from core.services.visible_runs_sections import detached_run as d
    settled = []
    monkeypatch.setattr(d, "_afregn_genoptaget_run", lambda *a, **kw: settled.append(a))
    d.start_user_run_detached(message="fortsæt", session_id="s1",
                              recovery_task_id="task-1", recovery_generation=2)
    for _ in range(60):
        if settled:
            break
        time.sleep(0.05)
    assert settled


def test_genoptaget_opgave_lukkes_foer_runlog_slippes(monkeypatch):
    """Dispatcheren må ikke se en fri session med et uafregnet krav."""
    import core.services.run_event_log as rel
    from core.services.visible_runs_sections import detached_run as d
    _patch(monkeypatch, [])
    raekkefoelge = []
    monkeypatch.setattr(rel, "mark_done", lambda rid: raekkefoelge.append("run-done"))
    monkeypatch.setattr(d, "_afregn_genoptaget_run",
                        lambda *args, **kw: raekkefoelge.append("task-settled"))
    d.start_user_run_detached(message="fortsæt", session_id="s1",
                              recovery_task_id="task-1", recovery_generation=1)
    for _ in range(60):
        if "run-done" in raekkefoelge:
            break
        time.sleep(0.05)
    assert raekkefoelge[:2] == ["task-settled", "run-done"]


def _vaer_vores(monkeypatch, *, status="running", owner="owner-1", generation=2):
    """Stub journal-posten saa den ER vores — ellers fødes tråden ikke."""
    from core.services import in_flight_runs as ifr
    monkeypatch.setattr(ifr, "get_record", lambda _t: {
        "status": status, "recovery_owner": owner,
        "recovery_generation": generation,
    })


def test_levende_fortsaettelse_holder_sit_krav_fra_at_udloebe(monkeypatch):
    """Et run over 120 sekunder må ikke blive taget igen mens det arbejder."""
    from core.services.visible_runs_sections import detached_run as d
    from core.services import in_flight_runs as ifr
    _vaer_vores(monkeypatch)
    kald = []
    monkeypatch.setattr(ifr, "renew_recovery_lease",
                        lambda *args, **kw: kald.append((args, kw)) or True)

    class StopEfterEtTick:
        antal = 0

        def wait(self, _sekunder):
            self.antal += 1
            return self.antal > 1

    d._hold_recovery_lease("task-1", 2, "owner-1", StopEfterEtTick())
    assert kald == [(('task-1', 2), {'owner': 'owner-1', 'lease_seconds': 120.0})]


def test_lease_traaden_efterlader_et_spor(monkeypatch, caplog):
    """Trådens fødsel, hver fornyelse og dens død skal kunne læses i loggen.

    Målt-behov 14/10-2026: et lejemaal udløb midt i et kørende run
    (`visible-a8323914`), og uden spor kunne tre forløb ikke skelnes —
    tråden blev aldrig født, den fornyede i det stille, eller den døde i sit
    første tick. Fraværet af en advarsel betød både «alt gik godt» og «løkken
    kørte aldrig», og netop derfor kunne målingen ikke afsluttes.
    """
    from core.services.visible_runs_sections import detached_run as d
    from core.services import in_flight_runs as ifr
    _vaer_vores(monkeypatch)
    monkeypatch.setattr(ifr, "renew_recovery_lease", lambda *a, **kw: True)

    class StopEfterToTick:
        antal = 0

        def wait(self, _sekunder):
            self.antal += 1
            return self.antal > 2

    with caplog.at_level("INFO"):
        d._hold_recovery_lease("task-1", 2, "owner-1", StopEfterToTick())

    tekst = caplog.text
    assert "lease-traad startet for opgave task-1" in tekst
    assert "lease fornyet for opgave task-1 (#1" in tekst
    assert "lease fornyet for opgave task-1 (#2" in tekst
    assert "lease-traad stoppet for opgave task-1 (fornyelser i alt: 2)" in tekst


def test_lease_traaden_siger_hvor_mange_fornyelser_den_naaede(monkeypatch, caplog):
    """Taber tråden kravet, skal advarslen bære TALLET — ikke kun beskeden.

    Uden tallet kan «mistede sit lejemaal» ikke skelnes fra et run der døde i
    sit første tick, og det var præcis den tvetydighed der gjorde målingen
    14/10-2026 umulig at afslutte. Et run der dør efter én fornyelse og et der
    aldrig fornyede efterlader samme ord i loggen — men ikke samme tal.
    """
    from core.services.visible_runs_sections import detached_run as d
    from core.services import in_flight_runs as ifr
    _vaer_vores(monkeypatch, owner="owner-9", generation=3)
    kald = {"n": 0}

    def _forny(*a, **kw):
        kald["n"] += 1
        return kald["n"] < 2          # første tick fornyer, andet taber kravet

    monkeypatch.setattr(ifr, "renew_recovery_lease", _forny)

    class StopEfterFemTick:
        antal = 0

        def wait(self, _sekunder):
            self.antal += 1
            return self.antal > 5

    with caplog.at_level("INFO"):
        d._hold_recovery_lease("task-9", 3, "owner-9", StopEfterFemTick())

    assert "mistede sit recovery-lejemaal (fornyelser i alt: 1" in caplog.text
    # Taber tråden kravet, vender den hjem FØR stop — derfor ingen stop-linje.
    assert "lease-traad stoppet" not in caplog.text


def test_lease_traaden_foedes_ikke_paa_et_krav_der_ikke_er_vores(monkeypatch, caplog):
    """Er posten givet tilbage, er der intet at holde — tråden skal ikke fødes.

    Målt 15/10-2026: en genoptagelse (`78dee41e`) blev født 07:01:27 på en
    opgave der var givet tilbage fire sekunder før (status `recovering`, ejer
    ryddet). Dens første fornyelse måtte fejle, og advarslen fyrede korrekt med
    0 fornyelser — men tråden var DØDSDØMT FRA FØDSELEN, og det så ud som en
    fejl i fornyelsen i stedet for i fødslen. De to forløb må ikke se ens ud.
    """
    from core.services.visible_runs_sections import detached_run as d
    from core.services import in_flight_runs as ifr
    _vaer_vores(monkeypatch, status="recovering", owner="")
    kald = []
    monkeypatch.setattr(ifr, "renew_recovery_lease",
                        lambda *a, **kw: kald.append(1) or True)

    class StopEfterEtTick:
        antal = 0

        def wait(self, _sekunder):
            self.antal += 1
            return self.antal > 1

    with caplog.at_level("INFO"):
        d._hold_recovery_lease("task-1", 2, "owner-1", StopEfterEtTick())

    assert kald == []                       # ingen fornyelse forsøgt
    assert "lease-traad IKKE foedt" in caplog.text
    assert "lease-traad startet" not in caplog.text


def test_lease_traaden_foedes_ikke_paa_en_fremmed_generation(monkeypatch, caplog):
    """En post der er overtaget af en NYERE generation er heller ikke vores."""
    from core.services.visible_runs_sections import detached_run as d
    from core.services import in_flight_runs as ifr
    _vaer_vores(monkeypatch, generation=5)   # posten er rykket videre
    kald = []
    monkeypatch.setattr(ifr, "renew_recovery_lease",
                        lambda *a, **kw: kald.append(1) or True)

    class StopEfterEtTick:
        antal = 0

        def wait(self, _sekunder):
            self.antal += 1
            return self.antal > 1

    with caplog.at_level("INFO"):
        d._hold_recovery_lease("task-1", 2, "owner-1", StopEfterEtTick())

    assert kald == []
    assert "lease-traad IKKE foedt" in caplog.text


def test_lease_traaden_foedes_ikke_naar_posten_er_vaek(monkeypatch, caplog):
    """Findes posten ikke, er der intet at holde — og det skal siges højt."""
    from core.services.visible_runs_sections import detached_run as d
    from core.services import in_flight_runs as ifr
    monkeypatch.setattr(ifr, "get_record", lambda _t: None)
    kald = []
    monkeypatch.setattr(ifr, "renew_recovery_lease",
                        lambda *a, **kw: kald.append(1) or True)

    class StopEfterEtTick:
        antal = 0

        def wait(self, _sekunder):
            self.antal += 1
            return self.antal > 1

    with caplog.at_level("INFO"):
        d._hold_recovery_lease("task-1", 2, "owner-1", StopEfterEtTick())

    assert kald == []
    assert "posten findes ikke" in caplog.text


@pytest.mark.xfail(
    strict=True,
    reason=(
        "KENDT HUL, MAALT 14/10-2026: _consume() afviser kun FOREIGN, saa en "
        "UNKNOWN ramme faar lov at binde aliaset — og bagefter svarer "
        "ramme_ejerskab 'owned', fordi rammen selv satte det. Kontrollen er "
        "CIRKULAER. Hullet kan IKKE lukkes ved at afvise alle ukendte id'er: et "
        "NYT indre run er unknown pr. konstruktion (start_visible_run laver sit "
        "eget id, visible_runs.py:964). Maalt: et strengt 'owned'-krav blinder "
        "den aegte vej — 'opgave opg-A kan ikke afregnes endnu: run visible-gen "
        "status=mangler' — og opgaven brænder sit forsoegs-loft op. Den aegte "
        "binding skal komme fra OPRETTELSESPUNKTET. Se "
        "docs/audits/2026-10-14-run-ejerskab-oprettelse-til-afregning.md. "
        "strict=True: naar hullet lukkes, fejler denne som XPASS og skal "
        "opdateres."
    ),
)
def test_ukendt_ramme_maa_ikke_etablere_ejerskab(monkeypatch):
    """UNKNOWN maa ikke blive OWNED (ChatGPT's femte indvending, 14/10-2026).

    Rammer den VIRKELIGE ``_consume()``-vej. En ``system_event(kind=run)``-ramme
    hvis id hverken findes i ``_RUNS`` eller ``_ALIASER`` er UKENDT — ikke vores.
    Faar den lov at oprette aliaset, svarer ``ramme_ejerskab`` bagefter
    ``owned``: kontrollen er cirkulaer, fordi den bekraefter et alias rammen
    selv satte. Maalt 14/10-2026: ``_ALIASER`` fik
    ``{'visible-fremmed-ukendt': '<vores wrapper>'}``.

    Testen FEJLER i dag og staar derfor som ``xfail``. Den er kravet, ikke
    tilstanden.
    """
    import core.services.run_event_log as rel
    import core.services.visible_runs as vr
    import core.services.visible_runs_sse_v2 as v2
    from core.services.visible_runs_sections import detached_run as d

    for _d in (rel._RUNS, rel._ALIASER, rel._ALIASER_OMVENDT):
        _d.clear()

    fremmed = (
        'event: system_event\n'
        'data: {"type": "system_event", "kind": "run", '
        '"payload": {"run_id": "visible-fremmed-ukendt"}}\n'
    )
    monkeypatch.setattr(rel, "create", lambda rid, sid: rel._RUNS.__setitem__(
        rid, {"session_id": sid}))
    monkeypatch.setattr(rel, "append", lambda rid, f: None)
    monkeypatch.setattr(rel, "mark_done", lambda rid: None)
    monkeypatch.setattr(rel, "prune", lambda: None)
    monkeypatch.setattr(vr, "start_visible_run", lambda **kw: _make_async_iter([]))
    monkeypatch.setattr(v2, "translate_to_v2", lambda it, **kw: _make_async_iter([fremmed]))

    rid = d.start_user_run_detached(message="fortsæt", session_id="s1",
                                    recovery_task_id="task-1", recovery_generation=1)
    # Vent til _consume har set rammen: aliaset ville vaere sat nu hvis den fik lov.
    for _ in range(60):
        if rel._ALIASER or rel._ALIASER_OMVENDT:
            break
        time.sleep(0.05)

    assert "visible-fremmed-ukendt" not in rel._ALIASER, (
        "en UKENDT ramme maa ikke etablere ejerskab — ellers bliver "
        "afregnings-tjekket cirkulaert"
    )
    assert rel.ramme_ejerskab("visible-fremmed-ukendt", rid) != rel.EJERSKAB_OWNED, (
        "et ukendt id maa ikke blive 'owned' ved at rammen selv satte aliaset"
    )
