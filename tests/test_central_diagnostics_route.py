"""Tests for /central/diagnostics' helbreds-flader.

MÅLT 7/11-2026: fire `build_*_surface`-flader i central-laget havde NUL læsere —
nul referencer uden for `core/services`, kun deres egne tests. De målte rigtige
ting (`open_breakers`, `all_live`, `volume_coverage`, `tier3_precision`) som
ingen kunne se. De er nu koblet ind i diagnostik-stedet, hvor en bruger kigger
når noget er galt.

Testene måler KOBLINGEN, ikke fladerne: at nøglerne faktisk står i svaret, at én
fejlende flade ikke fjerner de andre, og at en flade der ikke kan måles bliver
`None` — ikke «alt ok».
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

import apps.api.jarvis_api.routes.central as central

from tests.conftest import kald_rute

HELBREDS_NOEGLER = ("health", "signal_health", "coverage", "causal_quality")


def _run(coro):
    return kald_rute(coro)


def _fake_flade(monkeypatch, navn: str, vaerdi) -> None:
    """Erstat én af de fire flader. `vaerdi` er returvaerdien eller en exception."""
    # Navnene følger ikke et ensartet mønster i kilden — slå det rigtige op.
    from importlib import import_module

    egentlig = {
        "health": ("core.services.central_health", "build_central_health_surface"),
        "signal_health": ("core.services.central_signal_health", "build_central_signal_health_surface"),
        "coverage": ("core.services.central_coverage", "build_central_coverage_surface"),
        "causal_quality": ("core.services.central_causal_quality", "build_central_causal_quality_surface"),
    }[navn]
    m = import_module(egentlig[0])
    if isinstance(vaerdi, BaseException):
        def _kaster(*_a, **_k):
            raise vaerdi
        monkeypatch.setattr(m, egentlig[1], _kaster)
    else:
        monkeypatch.setattr(m, egentlig[1], lambda *a, **k: vaerdi)


def test_owner_gate_propagerer(monkeypatch):
    """Owner-gaten må ikke sluges — en ikke-ejer skal få 403, ikke et svar."""
    def deny() -> None:
        raise HTTPException(status_code=403, detail="nope")

    monkeypatch.setattr(central, "_require_owner", deny)
    with pytest.raises(HTTPException) as ei:
        _run(central.central_diagnostics())
    assert ei.value.status_code == 403


def test_alle_fire_helbredsflader_er_i_svaret(monkeypatch):
    """KOBLINGEN. Fejler hvis nogen fjerner fladerne fra routen igen."""
    monkeypatch.setattr(central, "_require_owner", lambda: None)
    svar = _run(central.central_diagnostics())

    mangler = [n for n in HELBREDS_NOEGLER if n not in svar]
    assert not mangler, f"helbreds-flader mangler i diagnostik-svaret: {mangler}"

    # De gamle nøgler skal stadig være der — koblingen må ikke fortrænge dem.
    for gammel in ("incidents", "anomalies", "instrument", "root_causes", "degrading"):
        assert gammel in svar, f"den eksisterende nøgle {gammel!r} forsvandt"


def test_en_fejlende_flade_fjerner_ikke_de_andre(monkeypatch):
    """Self-safe pr. flade: hver sin måling, ikke én der vælter alt."""
    monkeypatch.setattr(central, "_require_owner", lambda: None)
    _fake_flade(monkeypatch, "health", RuntimeError("beak-kreds"))
    _fake_flade(monkeypatch, "coverage", {"volume_coverage": 0.9})

    svar = _run(central.central_diagnostics())

    assert isinstance(svar["health"], dict) and "error" in svar["health"], (
        "en fejlende flade skal melde sin fejl, ikke forsvinde"
    )
    assert "beak-kreds" in svar["health"]["error"]
    # Naboen må ikke være påvirket.
    assert svar["coverage"] == {"volume_coverage": 0.9}


def test_ikke_maalbar_flade_er_None_og_ikke_alt_ok(monkeypatch):
    """`None` betyder «ikke målt». En tom dict ville læses som «alt i orden»."""
    monkeypatch.setattr(central, "_require_owner", lambda: None)
    for navn in HELBREDS_NOEGLER:
        _fake_flade(monkeypatch, navn, None)

    svar = _run(central.central_diagnostics())

    for navn in HELBREDS_NOEGLER:
        assert svar[navn] is None, (
            f"{navn} skulle være None når fladen ikke kan måles, var {svar[navn]!r}"
        )
