"""Ønsket vs. FAKTISK indespærring — Fase 3, K9.

    «every process-producing provider reports requested policy and actual
     enforcement; requested confinement fails before execution when
     unavailable»

Kriteriet kolliderede med en beslutning der ALLEREDE var truffet: `maybe_wrap`
fejler åbent med vilje, fordi «en manglende mekanisme må ikke gøre bash
ubrugelig». Den omgøres ikke. I stedet er de to spørgsmål skilt ad —
rapportering sker altid, håndhævelse er kalderens valg.
"""
from __future__ import annotations

import logging

import pytest

from core.services import bash_sandbox as SB
from core.services.bash_sandbox import ConfinementUnavailable, enforcement


@pytest.fixture
def sandbox(monkeypatch):
    def _saet(*, taendt: bool, tilgaengelig: bool):
        monkeypatch.setattr(SB, "is_enabled", lambda: taendt)
        monkeypatch.setattr(SB, "is_available", lambda: tilgaengelig)
    return _saet


# ── rapporteringen sker ALTID ────────────────────────────────────────────

def test_slukket_giver_hverken_oensket_eller_faktisk(sandbox):
    sandbox(taendt=False, tilgaengelig=True)
    e = enforcement("echo hej", "/tmp")
    assert e.requested is False and e.actual is False and e.honored is True


def test_taendt_og_muligt_giver_faktisk_indespaerring(sandbox):
    sandbox(taendt=True, tilgaengelig=True)
    e = enforcement("echo hej", "/tmp")
    assert e.requested is True and e.actual is True and e.honored is True
    assert e.argv and e.argv[0] == "bwrap"


def test_taendt_men_UMULIGT_er_en_UOPFYLDT_oenske(sandbox):
    """Det er hele forskellen kriteriet handler om."""
    sandbox(taendt=True, tilgaengelig=False)
    e = enforcement("echo hej", "/tmp")
    assert e.requested is True and e.actual is False and e.honored is False
    assert "bwrap" in e.reason


def test_et_uopfyldt_oenske_siges_HOEJT(sandbox, caplog):
    """En kommando der kører frit mens nogen troede den var spærret inde, er
    præcis den forskel der ikke må forsvinde."""
    sandbox(taendt=True, tilgaengelig=False)
    with caplog.at_level(logging.WARNING):
        enforcement("echo hej", "/tmp")
    assert "IKKE håndhævet" in caplog.text


def test_rapporten_kan_serialiseres(sandbox):
    sandbox(taendt=True, tilgaengelig=True)
    d = enforcement("echo hej", "/tmp").as_dict()
    assert set(d) == {"requested", "actual", "available", "enabled", "honored", "reason"}


# ── håndhævelsen er kalderens valg ───────────────────────────────────────

def test_uden_require_er_retningen_UAENDRET_fail_open(sandbox):
    """Den beslutning omgøres ikke under en rapporterings-rettelse."""
    sandbox(taendt=True, tilgaengelig=False)
    e = enforcement("echo hej", "/tmp")          # kaster ikke
    assert e.actual is False


def test_med_require_fejler_den_FOER_eksekvering(sandbox):
    """En fejl bagefter er en kommando der allerede er kørt."""
    sandbox(taendt=True, tilgaengelig=False)
    with pytest.raises(ConfinementUnavailable, match="kunne ikke leveres"):
        enforcement("echo hej", "/tmp", require=True)


def test_require_kaster_ogsaa_naar_sandboxen_er_SLUKKET(sandbox):
    """«Kræv indespærring» betyder kræv — ikke «kræv hvis den er tændt»."""
    sandbox(taendt=False, tilgaengelig=True)
    with pytest.raises(ConfinementUnavailable):
        enforcement("echo hej", "/tmp", require=True)


def test_require_slipper_igennem_naar_indespaerringen_ER_der(sandbox):
    sandbox(taendt=True, tilgaengelig=True)
    assert enforcement("echo hej", "/tmp", require=True).actual is True


# ── rapporten følger med svaret ──────────────────────────────────────────

def test_bash_svaret_baerer_rapporten_naar_der_er_noget_at_sige(sandbox):
    sandbox(taendt=True, tilgaengelig=False)
    from core.tools import simple_tools_web as W
    r = W._exec_bash({"command": "echo hej"})
    assert r["status"] == "ok"
    assert r["confinement"]["requested"] is True and r["confinement"]["actual"] is False


def test_den_VEDVARENDE_shell_siger_at_den_ikke_kan_indespaerres(sandbox):
    """Uden denne linje ville en tændt sandbox SE UD som om den dækkede bash,
    mens den normale vej gik udenom og kun reserve-stien blev indespærret.

    Rapporten er hele forskellen mellem «ikke indespærret» og «troede den var
    det». Den vedvarende shell er Bjørns bagdør og ændres ikke — den beskrives
    bare ærligt."""
    sandbox(taendt=True, tilgaengelig=True)
    from core.tools import simple_tools_web as W
    r = W._exec_bash({"command": "echo hej"})
    c = r.get("confinement") or {}
    assert c.get("requested") is True and c.get("actual") is False
    assert "vedvarende" in c.get("reason", "")


def test_engangs_stien_KAN_indespaerres(sandbox, monkeypatch):
    """Forskellen mellem de to stier skal kunne ses i rapporten."""
    sandbox(taendt=True, tilgaengelig=True)
    from core.tools import simple_tools_web as W
    # tving reserve-stien: ingen vedvarende session
    monkeypatch.setattr(W, "_get_or_open_default_bash_session",
                        lambda: (_ for _ in ()).throw(RuntimeError("ingen daemon")))
    r = W._exec_bash({"command": "echo hej"})
    c = r.get("confinement") or {}
    assert c.get("actual") is True and c.get("honored") is True


def test_bash_svaret_er_UDEN_stoej_naar_intet_var_oensket(sandbox):
    """Et uændret «intet ønsket, intet sket» er støj."""
    sandbox(taendt=False, tilgaengelig=True)
    from core.tools import simple_tools_web as W
    r = W._exec_bash({"command": "echo hej"})
    assert "confinement" not in r
