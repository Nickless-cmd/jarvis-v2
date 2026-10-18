"""Vagt: runtime-vagten skal rejse runtime — og AFVISE at gøre det når den ikke skal.

BAGGRUND (målt 18/10-2026): `jarvis-runtime` lå død i 55 minutter fordi begge
units har `Restart=on-failure`, og en pæn SIGTERM (exit 0) derfor aldrig rejses
igen. `/health` på 8080 svarede `ok` hele tiden, så intet så det.

## Hvorfor halvdelen af testene handler om at holde igen

En vagt der genstarter for meget er værre end ingen vagt: den skjuler årsagen,
brænder CPU og gør en planlagt genstart til en kamp. Derfor testes de fire
tilstande hver for sig, og særligt den farlige: **systemd siger «inactive», men
porten svarer** — så er det en anden proces på porten, og et «start» ville
fejle på portkollision eller give to processer der slås om den.

Telefonen må ALDRIG nås herfra: `send_notification` patches i alle tests der
kan nå et varsel.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from core.services import runtime_guard as rg


@pytest.fixture(autouse=True)
def _isolér(tmp_path, monkeypatch):
    """Ingen test må skrive i den ægte log eller state-fil."""
    monkeypatch.setattr(rg, "_LOG_STI", tmp_path / "guard.log")
    monkeypatch.setattr(rg, "_STATE_STI", tmp_path / "state.json")
    return tmp_path


@pytest.fixture
def varsler(monkeypatch):
    """Fanger varsler i stedet for at sende dem."""
    sendt: list[dict] = []

    class _Fake:
        @staticmethod
        def send_notification(besked, title=None, priority="default", tags=None):
            sendt.append({"besked": besked, "titel": title})
            return {"status": "ok"}

    monkeypatch.setitem(
        __import__("sys").modules, "core.services.ntfy_gateway", _Fake
    )
    return sendt


# --------------------------------------------------------------------------
# Beslutningsmatrix — fire tilstande, ikke to
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("aktiv", "sund", "forventet"),
    [
        ("active", True, "ok"),          # sund: rør den ikke
        ("inactive", False, "start"),    # død: rejs den
        ("active", False, "restart"),    # hængt: proces kører, svarer ikke
        ("failed", False, "start"),      # systemd gav op: rejs den
    ],
)
def test_beslutningsmatrix(aktiv, sund, forventet):
    assert rg.beslut(aktiv, sund) == forventet


def test_inaktiv_men_porten_svarer_er_blind_ikke_start():
    """Den farlige række: en ANDEN proces holder porten. Vi må ikke starte."""
    assert rg.beslut("inactive", True) == "blind"


@pytest.mark.parametrize("tilstand", ["activating", "deactivating", "reloading"])
def test_planlagt_overgang_er_ikke_en_fejl(tilstand):
    """En genstart af runtime tager ~6 s; et minut-interval rammer vinduet."""
    assert rg.beslut(tilstand, False) == "vent"


def test_ukendt_tilstand_er_blindhed_ikke_doed():
    """Kan vi ikke læse systemd, ved vi ikke om den er død — så gætter vi ikke."""
    assert rg.beslut("unknown", False) == "blind"


# --------------------------------------------------------------------------
# Vagten skal HOLDE IGEN
# --------------------------------------------------------------------------


def test_sund_runtime_bliver_ikke_genstartet(monkeypatch, varsler):
    """Den vigtigste afvisning: en rask runtime skal stå urørt."""
    monkeypatch.setattr(rg, "systemd_tilstand", lambda *a, **k: "active")
    monkeypatch.setattr(rg, "probe_health", lambda *a, **k: True)

    def _kaldt(*a, **k):  # pragma: no cover - må aldrig rammes
        raise AssertionError("sund runtime blev genstartet")

    monkeypatch.setattr(rg, "_rejs", _kaldt)
    resultat = rg.tjek_og_rejs()

    assert resultat["handling"] == "ok"
    assert resultat["udfoert"] is False
    assert varsler == [], "en sund runtime må ikke give en notifikation"


def test_planlagt_overgang_rorer_intet(monkeypatch, varsler):
    monkeypatch.setattr(rg, "systemd_tilstand", lambda *a, **k: "activating")
    monkeypatch.setattr(rg, "probe_health", lambda *a, **k: False)
    monkeypatch.setattr(
        rg, "_rejs", lambda *a, **k: (_ for _ in ()).throw(AssertionError("ramt"))
    )

    resultat = rg.tjek_og_rejs()
    assert resultat["handling"] == "vent"
    assert varsler == []


def test_tor_kørsel_observerer_uden_at_handle(monkeypatch, varsler):
    monkeypatch.setattr(rg, "systemd_tilstand", lambda *a, **k: "inactive")
    monkeypatch.setattr(rg, "probe_health", lambda *a, **k: False)
    monkeypatch.setattr(
        rg, "_rejs", lambda *a, **k: (_ for _ in ()).throw(AssertionError("ramt"))
    )

    resultat = rg.tjek_og_rejs(tør_handle=False)
    assert resultat["handling"] == "start"
    assert resultat["udfoert"] is False
    assert varsler == []


# --------------------------------------------------------------------------
# Rate-limit: vagten må ikke blive problemet
# --------------------------------------------------------------------------


def test_tre_forsoeg_uden_virkning_stopper_den(monkeypatch, varsler):
    """En genstart-loop skjuler årsagen. Efter 3 forsøg melder den og stopper."""
    nu = datetime.now(UTC)
    rg._skriv_state({"forsøg": [(nu - timedelta(minutes=m)).isoformat() for m in (2, 5, 9)]})

    monkeypatch.setattr(rg, "systemd_tilstand", lambda *a, **k: "inactive")
    monkeypatch.setattr(rg, "probe_health", lambda *a, **k: False)
    monkeypatch.setattr(
        rg, "_rejs", lambda *a, **k: (_ for _ in ()).throw(AssertionError("ramt"))
    )

    resultat = rg.tjek_og_rejs()
    assert resultat["udfoert"] is False
    assert "rate-limit" in resultat["detalje"]
    assert len(varsler) == 1, "den skal melde at den giver op"


def test_gamle_forsoeg_taeller_ikke_med(monkeypatch, varsler):
    """Forsøg uden for vinduet skal ikke straffe en ny, urelateret fejl."""
    gammel = (datetime.now(UTC) - timedelta(minutes=90)).isoformat()
    rg._skriv_state({"forsøg": [gammel, gammel, gammel]})

    monkeypatch.setattr(rg, "systemd_tilstand", lambda *a, **k: "inactive")
    monkeypatch.setattr(rg, "probe_health", lambda *a, **k: False)
    monkeypatch.setattr(rg, "_rejs", lambda *a, **k: (True, "systemctl start ok"))
    monkeypatch.setattr(rg, "START_VENT_SEKUNDER", 1)

    resultat = rg.tjek_og_rejs()
    assert resultat["udfoert"] is True, "gamle forsøg må ikke blokere en ny fejl"


def test_sund_tilstand_rydder_rate_limit(monkeypatch, varsler):
    rg._skriv_state({"forsøg": [datetime.now(UTC).isoformat()]})
    monkeypatch.setattr(rg, "systemd_tilstand", lambda *a, **k: "active")
    monkeypatch.setattr(rg, "probe_health", lambda *a, **k: True)

    rg.tjek_og_rejs()
    assert rg._laes_state().get("forsøg") == []


# --------------------------------------------------------------------------
# Varsler: cooldown, og telefoner må ikke ringe i ring
# --------------------------------------------------------------------------


def test_varsel_cooldown_hindrer_spam(monkeypatch, varsler):
    state = {"varsel_rejst": datetime.now(UTC).isoformat()}
    sendt = rg._varsl("igen", "titel", state=state, noegle="rejst")
    assert sendt is False, "to varsler inden for 15 min er spam"
    assert varsler == []


def test_varsel_sendes_naar_cooldown_er_udloebet(monkeypatch, varsler):
    state = {"varsel_rejst": (datetime.now(UTC) - timedelta(minutes=30)).isoformat()}
    sendt = rg._varsl("runtime rejst", "titel", state=state, noegle="rejst")
    assert sendt is True
    assert len(varsler) == 1
    assert "varsel_rejst" in state


# --------------------------------------------------------------------------
# Rejs-stien: «systemctl returnerede 0» er ikke bevis på at den lever
# --------------------------------------------------------------------------


def test_rejst_men_port_svarer_ikke_varsler_sandheden(monkeypatch, varsler):
    """Hele dagens lære: exit 0 fra systemctl betyder ikke at hjertet slår."""
    monkeypatch.setattr(rg, "systemd_tilstand", lambda *a, **k: "inactive")
    monkeypatch.setattr(rg, "probe_health", lambda *a, **k: False)
    monkeypatch.setattr(rg, "_rejs", lambda *a, **k: (True, "systemctl start ok"))
    monkeypatch.setattr(rg, "START_VENT_SEKUNDER", 1)

    resultat = rg.tjek_og_rejs()
    assert resultat["udfoert"] is True
    assert resultat["sund_efter"] is False
    assert len(varsler) == 1
    assert "svarer stadig ikke" in varsler[0]["besked"]


def test_rejst_og_svarer_varsler_kort(monkeypatch, varsler):
    monkeypatch.setattr(rg, "systemd_tilstand", lambda *a, **k: "inactive")
    monkeypatch.setattr(rg, "probe_health", lambda *a, **k: False)
    monkeypatch.setattr(rg, "_rejs", lambda *a, **k: (True, "systemctl start ok"))
    monkeypatch.setattr(rg, "START_VENT_SEKUNDER", 1)

    # Efter rejs svarer porten.
    kald = {"n": 0}

    def _probe(*a, **k):
        kald["n"] += 1
        return kald["n"] > 1

    monkeypatch.setattr(rg, "probe_health", _probe)

    resultat = rg.tjek_og_rejs()
    assert resultat["sund_efter"] is True
    assert "rejste den" in varsler[0]["besked"]


def test_mislykket_rejs_varsler_fejlen(monkeypatch, varsler):
    monkeypatch.setattr(rg, "systemd_tilstand", lambda *a, **k: "inactive")
    monkeypatch.setattr(rg, "probe_health", lambda *a, **k: False)
    monkeypatch.setattr(rg, "_rejs", lambda *a, **k: (False, "Interactive authentication required"))

    resultat = rg.tjek_og_rejs()
    assert resultat["udfoert"] is False
    assert "kunne ikke rejse" in varsler[0]["besked"]


# --------------------------------------------------------------------------
# Loggen må aldrig være tavs
# --------------------------------------------------------------------------


def test_hver_koersel_skriver_en_linje_ogsaa_naar_sund(monkeypatch, varsler, tmp_path):
    """En 0-byte log kan ikke skelne «aldrig kørt» fra «dræbt undervejs»."""
    monkeypatch.setattr(rg, "systemd_tilstand", lambda *a, **k: "active")
    monkeypatch.setattr(rg, "probe_health", lambda *a, **k: True)

    rg.tjek_og_rejs()

    log = (tmp_path / "guard.log").read_text(encoding="utf-8")
    assert "-> ok" in log, "en rask kørsel skal STADIG skrive en linje"


def test_main_crasher_ikke_naar_alt_gaar_galt(monkeypatch, varsler):
    """Vagten selv må aldrig efterlade os blinde med en traceback."""
    monkeypatch.setattr(
        rg, "tjek_og_rejs", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    )
    assert rg.main() == 0


# --------------------------------------------------------------------------
# probe_health: netværksfejl er NEJ, ikke «ved det ikke»
# --------------------------------------------------------------------------


def test_probe_health_fejl_betyder_ikke_sund(monkeypatch):
    import urllib.error

    def _kast(*a, **k):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(rg.urllib.request, "urlopen", _kast)
    assert rg.probe_health() is False
