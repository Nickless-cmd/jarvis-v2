"""Vagter for scripts/phone_home_auto.py — den vagt der holder telefonens adresse frisk.

Målt 26/10-2026: scriptet havde fejlet hvert andet minut siden 8. september uden
at nogen opdagede det, fordi dets detektion var bygget på `ping` — og ICMP er
blokeret ud af containeren. Det kunne ikke pinge pfsense (10.0.0.1) eller
WiFi-AP'en (10.0.0.60) heller, så `_ping` svarede ALTID nej, og scriptet faldt
hver gang tilbage til en ARP-scan der fandt telefonen og derefter hamrede en
port der for længst var skiftet.

Tre ting pinnes her, fordi de hver især kan smuldre stille:
  1. TCP-proben måler faktisk hvad den påstår (en åben port).
  2. Den samme fejl logges ikke igen og igen — 1.500 gentagelser er en mur, ikke et signal.
  3. State-filen merger, så `sidste_scan_ts` ikke falder ud og scanneren kører for tit.
"""

from __future__ import annotations

import importlib.util
import socket
from pathlib import Path

import pytest

_ROD = Path(__file__).resolve().parent.parent


def _modul(monkeypatch, tmp_path):
    """Indlæs scriptet med log- og state-stier pegende på tmp_path.

    Scriptet er ikke en pakke (det kører fra cron som en fil), så det hentes
    ind via sti. Stierne patches FØR modulen bruges, så intet skriver i
    Bjørns rigtige state-mappe under test.
    """
    spec = importlib.util.spec_from_file_location(
        "phone_home_auto_under_test", _ROD / "scripts" / "phone_home_auto.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "LOG_STI", str(tmp_path / "phone_home_auto.log"))
    monkeypatch.setattr(mod, "STATE_STI", str(tmp_path / "phone_home_auto.json"))
    return mod


def test_tcp_proben_ser_en_aaben_port_og_en_lukket(monkeypatch, tmp_path):
    """Kernen i fixet: proben skal svare ja på en port der lytter, nej på en der ikke gør.

    Det er præcis hvad `_ping` ikke kunne — den svarede nej til alt, også til
    en telefon der stod lige foran den.
    """
    mod = _modul(monkeypatch, tmp_path)

    lytter = socket.socket()
    lytter.bind(("127.0.0.1", 0))
    lytter.listen(1)
    port = lytter.getsockname()[1]
    try:
        assert mod._tcp_aaben("127.0.0.1", str(port)) is True
    finally:
        lytter.close()

    # Samme port, nu lukket: proben skal sige nej, ikke gætte.
    assert mod._tcp_aaben("127.0.0.1", str(port)) is False


def test_samme_besked_logges_kun_en_gang(monkeypatch, tmp_path):
    """En gentaget fejl er ikke et signal. 1.500 identiske linjer var en mur.

    Målt: samme besked stod hvert andet minut fra 8/9 til 26/10-2026.
    """
    mod = _modul(monkeypatch, tmp_path)

    mod._log_hvis_nyt("parringen mangler")
    mod._log_hvis_nyt("parringen mangler")
    mod._log_hvis_nyt("parringen mangler")

    linjer = [
        l for l in Path(mod.LOG_STI).read_text().splitlines() if l.strip()
    ]
    assert len(linjer) == 1, linjer

    # ... men en NY besked skal igennem med det samme.
    mod._log_hvis_nyt("porten er skiftet")
    linjer = [
        l for l in Path(mod.LOG_STI).read_text().splitlines() if l.strip()
    ]
    assert len(linjer) == 2, linjer


def test_state_bevarer_noegler_der_ikke_sendes_med(monkeypatch, tmp_path):
    """`_skriv_state` skal merge, ikke overskrive.

    Da den overskrev, faldt `sidste_scan_ts` ud hver gang en gren ikke sendte
    den med — og så blev SCAN_INTERVAL_S på 5 minutter aldrig respekteret.
    """
    mod = _modul(monkeypatch, tmp_path)

    mod._skriv_state(sidste_scan_ts="111.0", adresse="10.0.0.150:43267")
    # Andet kald uden sidste_scan_ts — den skal overleve.
    mod._skriv_state(forbundet=False, handling="parring-mangler")

    import json

    state = json.loads(Path(mod.STATE_STI).read_text())
    assert state["sidste_scan_ts"] == "111.0", state
    assert state["adresse"] == "10.0.0.150:43267", state
    assert state["handling"] == "parring-mangler", state


def test_startlinje_skrives_naar_loggen_er_tom(monkeypatch, tmp_path):
    """En tom log skal betyde «aldrig startet» — ikke «ved det ikke»."""
    mod = _modul(monkeypatch, tmp_path)

    mod._startlinje()
    tekst = Path(mod.LOG_STI).read_text()
    assert "START" in tekst, tekst

    # Anden kørsel må ikke skrive endnu en startlinje.
    foer = Path(mod.LOG_STI).read_text().count("START")
    mod._startlinje()
    assert Path(mod.LOG_STI).read_text().count("START") == foer
