"""Tests for central_dark_products_digest — dark-LLM-programmet, §24.4.

Verificerer at digestet KUN bærer liveness+count pr. signal (aldrig rå
produkt-tekst), at reduktionen er self-safe, og at en kastende producent
isoleres.
"""
from __future__ import annotations

import core.services.central_dark_products_digest as d


def test_digest_shape_and_total():
    out = d.build_dark_products_digest()
    assert isinstance(out, dict)
    assert "signals" in out and "live_count" in out and "total" in out
    assert isinstance(out["signals"], dict)
    assert out["total"] == len(out["signals"]) == 6


def test_no_text_keys_leak():
    out = d.build_dark_products_digest()
    for name, sec in out["signals"].items():
        # INGEN tekst-nøgler må lække — kun liveness/count
        assert set(sec.keys()) <= {"liveness", "count"}, f"{name} lækkede {sec.keys()}"
        assert isinstance(sec.get("liveness"), bool)
        assert isinstance(sec.get("count"), int)


def test_live_count_matches_liveness():
    out = d.build_dark_products_digest()
    expected = sum(1 for s in out["signals"].values() if s.get("liveness"))
    assert out["live_count"] == expected


def test_self_safe_when_producer_raises(monkeypatch):
    import importlib

    real_import = importlib.import_module

    def boom(mod):
        if mod == "core.services.apophenia_guard":
            raise RuntimeError("boom")
        return real_import(mod)

    monkeypatch.setattr(importlib, "import_module", boom)
    out = d.build_dark_products_digest()
    # den kastende producent isoleres — resten overlever
    assert out["signals"]["apophenia"] == {"liveness": False, "count": 0}
    assert out["total"] == 6


def test_no_raw_content_leaks_from_verbose_producer(monkeypatch):
    """En producent der returnerer rå tekst/lister må KUN reduceres til
    liveness+count — intet råt indhold slipper igennem digestet."""
    import importlib
    import types

    real_import = importlib.import_module

    def fake(mod):
        if mod == "core.services.dream_consolidation_daemon":
            m = types.ModuleType(mod)
            m.build_dream_consolidation_surface = lambda: {  # type: ignore[attr-defined]
                "active": True,
                "summary": "RÅ DRØM-TEKST",
                "recent": [{"theme": "HEMMELIG"}, {"theme": "TEKST"}],
            }
            return m
        return real_import(mod)

    monkeypatch.setattr(importlib, "import_module", fake)
    out = d.build_dark_products_digest()
    sec = out["signals"]["dream_consolidation"]
    assert sec == {"liveness": True, "count": 2}
    flat = str(out)
    assert "RÅ DRØM-TEKST" not in flat
    assert "HEMMELIG" not in flat


def test_reduce_empty():
    assert d._reduce({}) == {"liveness": False, "count": 0}
    assert d._reduce(None) == {"liveness": False, "count": 0}


def test_reduce_list_and_active():
    assert d._reduce({"items": [1, 2, 3], "active": True}) == {"liveness": True, "count": 3}


def test_reduce_active_false():
    assert d._reduce({"active": False, "items": [1]}) == {"liveness": False, "count": 1}


def test_first_count_int_when_no_list():
    assert d._first_count({"n": 7}) == 7
    assert d._first_count({"active": True, "n": 4}) == 4
