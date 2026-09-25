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
    assert set(ud) == {"koert", "fejlet"}
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
