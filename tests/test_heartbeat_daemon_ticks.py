"""De indre daemoner skal tikke uanset om han har travlt.

Maalt 25/9-2026 paa CT105. `act_phase` slutter saadan:

    # No clear priorities — productive idle.
    idle_result = productive_idle()
    return {"kind": "productive_idle", "result": idle_result}

Er `reflection["priorities"]` tom, returnerer den UDEN at kalde
`run_heartbeat_tick` — og det var det eneste sted de ~30 daemon-tik laa.

    decision_type      antal   sidst
    execute               90   24/9 20:06
    tick_dispatched        7   25/9 08:01
    productive_idle       80   25/9 15:39

Siden kl. 08:01 gik hvert tik den vej. `reboot_markers.json` froes praecis da,
og `proprioception_metrics` havde nul gemte snapshots — mens ledgeren skrev
`tick_status=ok, action_status=executed` paa dem alle.

Hans kompas sagde «Ingen aabne loops». Han havde det godt, og netop derfor
holdt hans proprioception op.
"""
from __future__ import annotations

import core.services.heartbeat_phases as HP
from core.services.heartbeat_daemon_ticks import tik_indre_daemoner


def test_de_tikker_naar_der_INGEN_prioriteter_er(monkeypatch):
    """KERNEN. Den vej der blev taget 80 gange i traek.

    Der maales paa om daemonerne FAKTISK koerte, ikke paa hvordan koden er
    skrevet — en kilde-vagt ville have bestaaet paa den gamle version.
    """
    kaldt: list[dict] = []
    monkeypatch.setattr("core.services.heartbeat_daemon_ticks.tik_indre_daemoner",
                        lambda: kaldt.append({"koert": 7, "fejlet": 0}) or kaldt[-1])
    monkeypatch.setattr(HP, "sense_phase", lambda **kw: {})
    monkeypatch.setattr(HP, "reflect_phase", lambda s: {"priorities": []})
    monkeypatch.setattr(HP, "act_phase",
                        lambda **kw: {"kind": "productive_idle", "result": {}})

    ud = HP.tick_with_phases(name="t", trigger="test")
    assert kaldt, "daemonerne koerte ikke paa et tik uden prioriteter"
    assert ud["indre_daemoner"]["koert"] == 7, (
        "taellingen naaede ikke ud i resultatet — saa kan ingen se om de koerte")


def test_de_tikker_ogsaa_naar_han_HAR_travlt(monkeypatch):
    """Sansningen maa ikke afhaenge af hvilken gren `act_phase` tager."""
    kaldt: list[dict] = []
    monkeypatch.setattr("core.services.heartbeat_daemon_ticks.tik_indre_daemoner",
                        lambda: kaldt.append({"koert": 7, "fejlet": 0}) or kaldt[-1])
    monkeypatch.setattr(HP, "sense_phase", lambda **kw: {})
    monkeypatch.setattr(HP, "reflect_phase", lambda s: {"priorities": ["noget"]})
    monkeypatch.setattr(HP, "act_phase", lambda **kw: {"kind": "tick_dispatched"})
    HP.tick_with_phases(name="t", trigger="test")
    assert len(kaldt) == 1, f"forventede ét tik, fik {len(kaldt)}"


def test_de_tikker_FOER_faserne(monkeypatch):
    """Ellers sanser `sense_phase` paa forrige tiks tal."""
    raekkefoelge: list[str] = []
    monkeypatch.setattr("core.services.heartbeat_daemon_ticks.tik_indre_daemoner",
                        lambda: raekkefoelge.append("daemoner") or {"koert": 1, "fejlet": 0})
    monkeypatch.setattr(HP, "sense_phase",
                        lambda **kw: raekkefoelge.append("sense") or {})
    monkeypatch.setattr(HP, "reflect_phase", lambda s: {"priorities": []})
    monkeypatch.setattr(HP, "act_phase", lambda **kw: {"kind": "productive_idle"})
    HP.tick_with_phases(name="t", trigger="test")
    assert raekkefoelge[:2] == ["daemoner", "sense"], raekkefoelge


def test_en_braekket_daemon_standser_ikke_tikket(monkeypatch):
    """Hjerteslaget maa aldrig kunne vaeltes af én daemon."""
    def _braekker():
        raise RuntimeError("i stykker")
    monkeypatch.setattr("core.services.heartbeat_daemon_ticks.tik_indre_daemoner", _braekker)
    monkeypatch.setattr(HP, "sense_phase", lambda **kw: {})
    monkeypatch.setattr(HP, "reflect_phase", lambda s: {"priorities": []})
    monkeypatch.setattr(HP, "act_phase", lambda **kw: {"kind": "productive_idle"})
    ud = HP.tick_with_phases(name="t", trigger="test")
    assert ud["indre_daemoner"] == {"koert": 0, "fejlet": 0}


def test_taellingen_er_aegte_og_ikke_et_tal_der_bare_staar_der():
    """En sluget fejl der TAELLES er en maaling; en der ikke goer er en loegn
    om et sundt hjerteslag. Derfor er `pass` erstattet af `fejlet += 1`."""
    ud = tik_indre_daemoner()
    assert set(ud) == {"koert", "fejlet", "brugere"}
    assert ud["koert"] + ud["fejlet"] >= 25, (
        f"kun {ud['koert'] + ud['fejlet']} daemoner — blokken er skrumpet")


def test_ingen_daemon_slugger_tavst():
    """AST: hvert `except` i blokken skal taelle. Grep duer ikke — ordet
    `pass` staar ogsaa i de daemoner der importeres."""
    import ast
    import inspect

    import core.services.heartbeat_daemon_ticks as D

    traen = ast.parse(inspect.getsource(D))
    tavse = [
        h.lineno for n in ast.walk(traen) if isinstance(n, ast.Try)
        for h in n.handlers
        if len(h.body) == 1 and isinstance(h.body[0], ast.Pass)
    ]
    assert not tavse, f"tavse handlere paa linje {tavse} — de skal taelles"


# ── Forholdet er per bruger (25/9-2026) ──────────────────────────────────
#
# `relation_dynamics` og `relational_warmth` fejlede med `NoUserContextError`
# paa HVERT tik: de kalder `workspace_dir()` uden user_id, og hjerteslaget
# binder ingen bruger. Maalt: deres filer var 82-121 dage gamle, mens
# mind-rapporten viste dem `active: true` med «warmth=1.0» og «trust=0.5» —
# det sidste er defaultvaerdien, ikke en maaling.
#
# Bjoerns valg: per bruger. Hans og Jarvis' til ham, hendes til hende.

def test_de_tre_arbejdsrums_daemoner_tikker_for_HVER_bruger(monkeypatch):
    """KERNEN. Ikke én gang for den der tilfaeldigvis var bundet."""
    import core.services.heartbeat_daemon_ticks as D

    class _Bruger:
        def __init__(self, w, d):
            self.workspace, self.discord_id = w, d

    monkeypatch.setattr("core.identity.users.load_users",
                        lambda: [_Bruger("bjorn", "1"), _Bruger("lotte", "2"),
                                 _Bruger("mikkel", "3")])
    set_for: list[tuple[str, str]] = []
    monkeypatch.setattr("core.identity.workspace_context.set_context",
                        lambda **kw: set_for.append((kw["workspace_name"], kw["user_id"])) or object())
    monkeypatch.setattr("core.identity.workspace_context.reset_context", lambda t: None)

    ud = D.tik_indre_daemoner()
    assert ud["brugere"] == 3, f"tikkede for {ud['brugere']} brugere"
    assert set_for == [("bjorn", "1"), ("lotte", "2"), ("mikkel", "3")], set_for


def test_BAADE_arbejdsrum_og_bruger_id_bindes(monkeypatch):
    """`workspace_override` alene raekker ikke — `workspace_dir()` laeser
    `current_user_id()`, og uden den kaster den. Det var fejlen."""
    import core.services.heartbeat_daemon_ticks as D

    class _Bruger:
        workspace, discord_id = "bjorn", "1246415163603816499"

    monkeypatch.setattr("core.identity.users.load_users", lambda: [_Bruger()])
    set_kw: list[dict] = []
    monkeypatch.setattr("core.identity.workspace_context.set_context",
                        lambda **kw: set_kw.append(kw) or object())
    monkeypatch.setattr("core.identity.workspace_context.reset_context", lambda t: None)
    D.tik_indre_daemoner()
    assert set_kw and set_kw[0].get("user_id") == "1246415163603816499", (
        f"bruger-id blev ikke bundet: {set_kw}")


def test_konteksten_nulstilles_ogsaa_naar_en_daemon_braekker(monkeypatch):
    """Et laek ville lade naeste brugers daemoner skrive i forkert arbejdsrum."""
    import core.services.heartbeat_daemon_ticks as D

    class _Bruger:
        workspace, discord_id = "bjorn", "1"

    monkeypatch.setattr("core.identity.users.load_users", lambda: [_Bruger()])
    nulstillet: list[int] = []
    monkeypatch.setattr("core.identity.workspace_context.set_context", lambda **kw: object())
    monkeypatch.setattr("core.identity.workspace_context.reset_context",
                        lambda t: nulstillet.append(1))
    monkeypatch.setattr("core.services.relation_dynamics.tick",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("i stykker")))
    D.tik_indre_daemoner()
    assert nulstillet, "konteksten blev ikke nulstillet"


def test_de_tre_daemoner_staar_paa_listen():
    """En fjerde arbejdsrums-daemon skal opdages her, ikke i produktionen."""
    import ast
    import inspect
    import pathlib

    import core.services.heartbeat_daemon_ticks as D

    traen = ast.parse(inspect.getsource(D))
    moduler = {n.module.split(".")[-1] for n in ast.walk(traen)
               if isinstance(n, ast.ImportFrom) and n.module
               and n.module.startswith("core.services.")}
    arbejdsrums_bundne = {
        m for m in moduler
        if (p := pathlib.Path(f"core/services/{m}.py")).exists()
        and "workspace_dir()" in p.read_text(encoding="utf-8")
    }
    assert arbejdsrums_bundne == set(D.PR_BRUGER), (
        f"en arbejdsrums-bundet daemon staar ikke paa PR_BRUGER-listen og vil "
        f"kaste NoUserContextError i stilhed: {arbejdsrums_bundne ^ set(D.PR_BRUGER)}")


# ── Det maalte mellemrum (25/9-2026) ────────────────────────────────────────


def test_foerste_tik_giver_nul_og_naeste_giver_det_maalte_mellemrum():
    from datetime import UTC, datetime, timedelta

    from core.runtime import state_store
    from core.services.heartbeat_daemon_ticks import (
        _SIDSTE_TIK_FIL,
        _forloebet_sekunder,
    )

    state_store.save_json(_SIDSTE_TIK_FIL, {})
    assert _forloebet_sekunder() == 0.0

    state_store.save_json(
        _SIDSTE_TIK_FIL,
        {"ved": (datetime.now(UTC) - timedelta(seconds=1800)).isoformat()},
    )
    forloebet = _forloebet_sekunder()
    assert 1795 <= forloebet <= 1810


def test_et_ulaeseligt_tidsstempel_giver_nul_frem_for_at_kaste():
    from core.runtime import state_store
    from core.services.heartbeat_daemon_ticks import (
        _SIDSTE_TIK_FIL,
        _forloebet_sekunder,
    )

    state_store.save_json(_SIDSTE_TIK_FIL, {"ved": "ikke-et-tidsstempel"})
    assert _forloebet_sekunder() == 0.0


def test_livs_tjenesterne_faar_det_maalte_tal_ikke_en_konstant():
    """Blokken kaldte alle fire med `seconds=30`.

    Tikket kommer fra `wakeup_dispatcher` med variabelt interval, saa de 30
    var et gaet. For `continuity_kernel` var gaettet selvmodsigende:
    `should_express_continuity()` er `gap >= 300`, saa et konstant gap paa 30
    gjorde prompt-strengen tom for altid.
    """
    import ast

    kilde = open("core/services/heartbeat_daemon_ticks.py").read()
    traeet = ast.parse(kilde)

    kald: dict[str, ast.Call] = {}
    for n in ast.walk(traeet):
        if not isinstance(n, ast.Call) or not isinstance(n.func, ast.Name):
            continue
        if n.func.id in {
            "record_tick_elapsed",
            "evolve_dreams",
            "accumulate_wants",
            "add_boredom",
        }:
            kald[n.func.id] = n

    assert set(kald) == {
        "record_tick_elapsed",
        "evolve_dreams",
        "accumulate_wants",
        "add_boredom",
    }, f"mangler kald: {kald.keys()}"

    for navn, n in kald.items():
        for kw in n.keywords:
            assert not isinstance(kw.value, ast.Constant), (
                f"{navn} faar en konstant varighed — den skal maales"
            )

    # `continuity_kernel` skal have det SANDE tal, ikke det loftede: dens
    # eneste opgave er at beskrive mellemrummet.
    kw = kald["record_tick_elapsed"].keywords[0]
    assert isinstance(kw.value, ast.Name) and kw.value.id == "forloebet"
