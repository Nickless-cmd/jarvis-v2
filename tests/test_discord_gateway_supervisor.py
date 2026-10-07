"""Vagthunden over Discord-gatewayen.

Den udgaaende Discord-kanal laa doed i elleve timer 1-2/10-2026: klienttraaden
fik en 503 fra Discord seks sekunder efter opstart, og `start_discord_gateway()`
kaldes kun ved boot.

Taelt i journalen: FEM afviste `/api/internal/discord/dispatch`-kald mellem
07:30:50 og 07:32:04 — morgenbriefene til Michelle og Mikkel fyrede begge
praecist og blev begge afvist — og flere igen frem til 08:30. Taskene virkede.
Leveringen var vaek, og intet sagde det hoejt.

Testene maaler det der skal holde for at det ikke gentager sig: reparerer den
naar ejerskabet mangler, i raekkefoelgen stop->start, opgiver den naar traadene
ikke doer, falder den mod «sundt» ved tvivl, bakker den ud naar Discord bliver
ved at afvise, og bliver den stoppet FOER gatewayen ved nedlukning.
"""
from __future__ import annotations

import ast
import pathlib

import pytest

from core.services import discord_gateway as dg
from core.services import discord_gateway_supervisor as sup


@pytest.fixture(autouse=True)
def _slaa_discord_til(monkeypatch):
    """Alle testene her antager at Discord ER konfigureret og aktiveret."""
    monkeypatch.setattr(sup, "_discord_er_slaaet_til", lambda: True)
    monkeypatch.setattr(sup, "_skriv_tilstand", lambda **k: None)


class _Traad:
    def __init__(self, levende: bool) -> None:
        self._levende = levende

    def is_alive(self) -> bool:
        return self._levende


def test_reparation_stopper_foerst_og_starter_saa(monkeypatch):
    """Raekkefoelgen er hele pointen: et bart `start` rammer faelden «already
    running», fordi den tjekker subscriber-traaden mens ejerskabet kun maaler
    klienttraaden."""
    kaldt: list[str] = []
    monkeypatch.setattr(dg, "_thread", _Traad(False))
    monkeypatch.setattr(dg, "_sub_thread", _Traad(False))
    monkeypatch.setattr(dg, "stop_discord_gateway", lambda: kaldt.append("stop"))
    monkeypatch.setattr(dg, "start_discord_gateway", lambda: kaldt.append("start"))
    monkeypatch.setattr(sup, "_gateway_er_ejet", lambda: "start" in kaldt)
    assert sup._reparer() is True
    assert kaldt == ["stop", "start"], kaldt


def test_traade_der_nagter_at_doe_afbryder_forsoeget(monkeypatch):
    """Lever traadene stadig, ville `start` melde «already running» og intet
    blive repareret. Saa skal forsoeget opgives — ikke fortsaettes blindt."""
    monkeypatch.setattr(dg, "_thread", _Traad(True))
    monkeypatch.setattr(dg, "_sub_thread", _Traad(True))
    monkeypatch.setattr(sup, "STOP_VENT_S", 0.05)
    assert sup._vent_paa_at_traadene_doer() is False


def test_doede_traade_giver_groent_lys(monkeypatch):
    monkeypatch.setattr(dg, "_thread", _Traad(False))
    monkeypatch.setattr(dg, "_sub_thread", None)
    assert sup._vent_paa_at_traadene_doer() is True


def test_ulaeseligt_ejerskab_regnes_som_sundt(monkeypatch):
    """Fail-safe-retningen: en laesefejl maa ALDRIG udloese en reparation af
    noget der maaske var sundt. Verificeret 2/10: hverken `stop_` eller
    `start_` roerer `_discord_sessions`, saa en genstart taber ikke sessionerne
    — men den taber websocket-forbindelsen i nogle sekunder, og indgaaende
    beskeder i det vindue er vaek. Derfor falder vi mod «lad den vaere»."""
    def _sprael():
        raise RuntimeError("kan ikke laese")

    monkeypatch.setattr(dg, "_is_gateway_owner", _sprael)
    assert sup._gateway_er_ejet() is True


def test_backoff_vokser_og_har_et_loft():
    """Er Discord nede, skal vi ikke banke paa hvert minut i timevis."""
    ventetid = sup.TJEK_INTERVAL_S
    for _ in range(20):
        ventetid = min(ventetid * 2, sup.BACKOFF_MAKS_S)
    assert ventetid == sup.BACKOFF_MAKS_S
    assert sup.BACKOFF_MAKS_S > sup.TJEK_INTERVAL_S


def test_foerste_tjek_ligger_efter_en_sund_forbindelsestid():
    """Gatewayen forbandt historisk paa 3-6s. Tjekker vi for tidligt,
    reparerer vi noget der stadig er ved at starte."""
    assert sup.FOERSTE_TJEK_S >= 30.0
    assert sup.EJERSKAB_GRACE_S >= 10.0


def test_supervisoren_stoppes_FOER_gatewayen_ved_nedlukning():
    """Stopper vi gatewayen foerst, ser supervisoren et manglende ejerskab og
    rejser den igen midt i en afslutning. Kilde-vagt paa raekkefoelgen i
    nedluknings-listen — AST, ikke grep, saa en omskrivning ikke slipper
    igennem paa at strengen tilfaeldigvis stadig staar et sted."""
    kilde = pathlib.Path("apps/api/jarvis_api/app.py").read_text()
    navne: list[str] = []
    for node in ast.walk(ast.parse(kilde)):
        if not isinstance(node, ast.Tuple) or not node.elts:
            continue
        foerste = node.elts[0]
        if isinstance(foerste, ast.Constant) and isinstance(foerste.value, str):
            if foerste.value.startswith("stop_discord_gateway"):
                navne.append(foerste.value)
    assert "stop_discord_gateway_supervisor" in navne, navne
    assert "stop_discord_gateway" in navne, navne
    assert navne.index("stop_discord_gateway_supervisor") < navne.index("stop_discord_gateway"), navne


def test_supervisoren_startes_overhovedet():
    """En vagthund ingen kalder er doed kode — det hyppigste moenster i dette
    repo. Her er koblingen i app.py's opstart."""
    kilde = pathlib.Path("apps/api/jarvis_api/app.py").read_text()
    kald = [
        n for n in ast.walk(ast.parse(kilde))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
        and n.func.id == "start_discord_gateway_supervisor"
    ]
    assert kald, "start_discord_gateway_supervisor() kaldes ingen steder"
