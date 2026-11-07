"""Tests for den samlede daemon- og runtime-flade (7/11-2026).

Måler KOBLINGEN: at aggregatoren kalder hver producent i listen, at en kastende
producent isoleres uden at skjule de øvrige, og at routen faktisk eksponerer den.

Baggrund: 464 ``build_*_surface`` findes i core/services. Efter de seks første
indgange stod 283 uden nogen indgang. De 105 her er resten — det der kører.
En flade ingen indgang har, er stadig mørk for både Jarvis og operatøren.
"""
from __future__ import annotations

import pytest

from core.services import daemon_state_surface as agg

EXPECTED_GROUPS = ["daemoner", "laering", "kontinuitet", "taenkning"]


@pytest.fixture(scope="module")
def flade() -> dict:
    """Ét kald, delt af alle tests.

    MAALT 7/11-2026: ét kald tager ~6,5 s (105 producenter, hver med DB- og
    fil-læsning). 105 parametriserede kald ville være 11 minutters testtid for
    det samme bevis.
    """
    return agg.build_daemon_state_surface()


def test_alle_producenter_er_registreret() -> None:
    """Antallet er målt, ikke gættet: 105 flader svarede da listen blev skrevet."""
    navne = agg.producer_names()
    assert len(navne) == 105, f"listen ændrede sig: {len(navne)} producenter"
    assert len(set(navne)) == len(navne), "en producent er registreret to gange"


def test_grupperne_er_de_forventede() -> None:
    assert agg.group_names() == EXPECTED_GROUPS


def test_aggregatoren_svarer_og_grupperer(flade: dict) -> None:
    assert flade["mode"] == "daemon-state-v1"
    assert set(flade["groups"]) == set(EXPECTED_GROUPS)
    i_alt = sum(g["count"] for g in flade["groups"].values())
    assert i_alt == 105, f"grupperne dækker {i_alt} flader, ikke 105"
    assert flade["taxse"] == [], f"tavse flader: {flade['taxse']}"
    assert len(flade["svarer"]) == 105


def test_hver_producent_kaldes_og_svarer(flade: dict) -> None:
    """Den ægte kobling: hver registreret producent skal have givet indhold."""
    alle: dict = {}
    for g in flade["groups"].values():
        alle.update(g["surfaces"])
    manglende = [n for n in agg.producer_names() if n not in alle]
    assert not manglende, f"blev ikke kaldt: {manglende}"
    tomme = [n for n, s in alle.items() if not isinstance(s, dict) or not s]
    assert not tomme, f"svarede tomt: {tomme}"
    assert flade["taxse"] == [], f"tavse: {flade['taxse']}"


def test_kastende_producent_isoleres(monkeypatch) -> None:
    """Én defekt producent må ikke skjule de øvrige.

    Fejlen skal opstå INDE i producenten — ikke i ``_call``, som netop er det
    lag der fanger den. Patcher vi ``_call``, måler vi ingenting.
    """
    import core.services.action_router as ægte_modul

    def boom():
        raise RuntimeError("bevidst fejl i test")

    monkeypatch.setattr(ægte_modul, "build_action_router_surface", boom)
    d = agg.build_daemon_state_surface()
    assert "action_router" in d["taxse"], "den kastende producent blev ikke isoleret"
    assert len(d["svarer"]) == 104, "de øvrige 104 skulle stadig svare"


def test_ruten_er_mountet() -> None:
    """En aggregator uden rute er stadig mørk — ruten er indgangen."""
    from apps.api.jarvis_api.routes import central

    ruter = {r.path for r in central.router.routes}
    assert "/central/daemon-state" in ruter, (
        f"ruten mangler; findes: {sorted(p for p in ruter if 'state' in p)}"
    )


def test_ruten_kalder_aggregatoren(monkeypatch) -> None:
    """Ruten skal kalde aggregatoren — ikke en kopi af den."""
    import asyncio

    from apps.api.jarvis_api.routes import central

    kaldt = {}

    def fake_build():
        kaldt["ja"] = True
        return {"mode": "daemon-state-v1", "groups": {}, "svarer": [], "active": [], "taxse": []}

    monkeypatch.setattr(central, "_require_owner", lambda: None)
    monkeypatch.setattr(
        "core.services.daemon_state_surface.build_daemon_state_surface", fake_build
    )
    ud = asyncio.run(central.central_daemon_state())
    assert kaldt.get("ja") is True, "ruten kaldte ikke aggregatoren"
    assert ud["mode"] == "daemon-state-v1"
