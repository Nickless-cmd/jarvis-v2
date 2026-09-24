"""Centralen må ikke spørge ti gange oftere end data ændrer sig.

24/9-2026: jeg jagtede en poll-storm mod `/api/internal/runtime-surface/affect`
— 117 kald i minuttet. Hjerteslaget der løb løbsk stod for de fleste, men da
det var rettet, blev der 20 tilbage. Kilden var ikke Jarvis: det var denne HUD
på Bjørns egen maskine.

`refresh_data` lavede FEM API-kald hvert 3. sekund — overview, cost_today,
costs_daily, affect, tone. 100 kald i minuttet, døgnet rundt, fra én åben
Central. Hvert affekt-kald gik videre som et HTTP-hop fra api-processen til
runtime-processen og byggede fladen dér.

`overview` er det der gør billedet levende og bliver på 3 sekunder. De fire
andre ændrer sig i minutter.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from central_cli import hud as H  # noqa: E402


class _Attrap:
    """Minimal stand-in for HUD'en — vi tester kadencen, ikke Textual."""

    _client = object()
    _overview = None
    _cost = None
    _costs_daily = None
    _affect = None
    _tone = None
    _latency_ms = 0
    _connected = False

    def _sync_header(self) -> None: ...
    def _populate_active_tab(self) -> None: ...


def _byg(monkeypatch):
    kald: list[str] = []
    for navn in ("overview", "cost_today", "costs_daily", "affect", "tone"):
        monkeypatch.setattr(
            H.datasource, navn,
            (lambda n: lambda _c: (kald.append(n), {})[1])(navn))
    a = _Attrap()
    a.refresh_data = H.CentralHud.refresh_data.__get__(a, _Attrap)
    return a, kald


def test_foerste_opdatering_henter_alt(monkeypatch) -> None:
    """Ellers står omkostning, affekt og tone tomme i et halvt minut."""
    a, kald = _byg(monkeypatch)
    a.refresh_data()
    assert set(kald) == {"overview", "cost_today", "costs_daily", "affect", "tone"}, (
        f"første opdatering hentede ikke alt: {kald}"
    )


def test_de_langsomme_hentes_ikke_ved_hver_takt(monkeypatch) -> None:
    """Kernen. Fem kald hvert 3. sekund var 100 i minuttet fra én klient."""
    a, kald = _byg(monkeypatch)
    a.refresh_data()          # første: alt
    kald.clear()
    for _ in range(9):        # ni takter mere, altsaa ~27 sekunder
        a.refresh_data()
    assert kald == ["overview"] * 9, (
        f"de langsomme flader blev hentet igen inden intervallet: {kald}"
    )


def test_de_langsomme_kommer_igen_naar_intervallet_er_gaaet(monkeypatch) -> None:
    """De må ikke holde op med at opdatere — så var de jo døde."""
    ur = {"t": 1000.0}
    monkeypatch.setattr(H, "_monotonic", lambda: ur["t"])
    a, kald = _byg(monkeypatch)
    a.refresh_data()
    kald.clear()

    ur["t"] += H._LANGSOM_INTERVAL_S - 1
    a.refresh_data()
    assert kald == ["overview"], "for tidligt"

    ur["t"] += 2
    kald.clear()
    a.refresh_data()
    assert "affect" in kald and "tone" in kald and "cost_today" in kald, (
        f"de langsomme kom aldrig igen: {kald}"
    )


def test_en_doed_forbindelse_stopper_hele_opdateringen(monkeypatch) -> None:
    """Uændret adfærd: fejler `overview`, spørger vi ikke om resten.

    Det var sådan før, og en klient der hamrer videre på en død forbindelse er
    værre end en der holder pause.
    """
    a, kald = _byg(monkeypatch)

    def _braekker(_c):
        kald.append("overview")
        raise RuntimeError("nede")

    monkeypatch.setattr(H.datasource, "overview", _braekker)
    a.refresh_data()
    assert kald == ["overview"]
    assert a._connected is False
