"""Tests for core/services/central_route_headroom.py — proaktiv kvote-rotation."""
from __future__ import annotations
import core.services.central_route_headroom as hr


def test_headroom_deweights_at_80_and_skips_at_95(monkeypatch):
    monkeypatch.setattr(hr, "_usage_fraction", lambda provider: 0.5)  # 50%
    assert hr.headroom_ok("groq") is True
    assert hr.headroom_weight("groq") == 1.0
    monkeypatch.setattr(hr, "_usage_fraction", lambda provider: 0.85)  # 85%
    assert hr.headroom_ok("groq") is True
    assert hr.headroom_weight("groq") < 1.0        # de-vægtet
    monkeypatch.setattr(hr, "_usage_fraction", lambda provider: 0.97)  # 97%
    assert hr.headroom_ok("groq") is False         # skip proaktivt


def _fake_count(monkeypatch, calls, *, used=25):
    """Erstat DB-tællingen, så vi kan SE hvor mange gange den bliver kaldt."""
    import core.runtime.db_cheap_provider as dcp

    def fake(**_kw):
        calls["n"] += 1
        return used

    monkeypatch.setattr(dcp, "count_cheap_provider_invocations", fake)


def _fake_defaults(monkeypatch, *, daily=100):
    import core.services.cheap_provider_runtime_adapters as adapters

    monkeypatch.setattr(
        adapters, "CHEAP_PROVIDER_DEFAULTS", {"testprov": {"daily_limit": daily}}
    )


def test_usage_fraction_cachet_indtil_ttl_udloeber(monkeypatch):
    """Målt 12/10-2026: ét route()-kald kaldte _usage_fraction 361 gange, og hver
    beregning kørte sin egen COUNT(*). Uden cachen falder denne test på antallet."""
    calls = {"n": 0}
    _fake_count(monkeypatch, calls)
    _fake_defaults(monkeypatch)
    monkeypatch.setattr(hr, "_USAGE_CACHE", {})

    assert hr._usage_fraction("testprov") == 0.25
    assert hr._usage_fraction("testprov") == 0.25
    assert calls["n"] == 1, f"andet kald gik til DB'en ({calls['n']} beregninger)"


def test_udloebet_ttl_beregner_forfra(monkeypatch):
    """Cachen må ikke fryse en brøk for evigt — udløb skal give et frisk tal."""
    calls = {"n": 0}
    _fake_count(monkeypatch, calls)
    _fake_defaults(monkeypatch)
    monkeypatch.setattr(hr, "_USAGE_CACHE", {})
    monkeypatch.setattr(hr, "_USAGE_TTL_SECONDS", -1.0)  # alt er udløbet med det samme

    hr._usage_fraction("testprov")
    hr._usage_fraction("testprov")
    assert calls["n"] == 2, "en udløbet cache-post skal genberegnes"


def test_fejl_caches_ikke(monkeypatch):
    """En transient DB-fejl må ikke fryse provideren som «fuld headroom»."""
    import core.runtime.db_cheap_provider as dcp

    calls = {"n": 0}

    def boom(**_kw):
        calls["n"] += 1
        raise RuntimeError("db nede")

    monkeypatch.setattr(dcp, "count_cheap_provider_invocations", boom)
    _fake_defaults(monkeypatch)
    monkeypatch.setattr(hr, "_USAGE_CACHE", {})

    assert hr._usage_fraction("testprov") == 0.0
    assert hr._usage_fraction("testprov") == 0.0
    assert calls["n"] == 2, "fejlstien skal forsøge igen, ikke cache 0.0"
