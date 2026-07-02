"""Tests for core/services/central_prompt_composer.py — Tråd 2 kontekst-komponist (substrat + switch)."""
from __future__ import annotations

import pytest

from core.services import central_prompt_composer as pc


@pytest.fixture(autouse=True)
def _reset(isolated_runtime):
    pc._kv_set(pc._LIVE_FLAG, False)
    pc._kv_set(pc._WEIGHTS_KEY, {})
    yield


def test_classify_turn_type():
    assert pc.classify_turn_type("kan du fikse denne python bug?") == "kode"
    assert pc.classify_turn_type("husk hvad vi talte om sidste gang") == "hukommelse"
    assert pc.classify_turn_type("lav en indkøbsliste til mig") == "opgave"
    assert pc.classify_turn_type("hvorfor virker det ikke?") == "spørgsmål"
    assert pc.classify_turn_type("hej, hvordan går det") == "spørgsmål"  # 'hvordan'
    assert pc.classify_turn_type("godmorgen") == "samtale"
    assert pc.classify_turn_type("") == "samtale"


def test_shadow_includes_everything():
    # default (shadow, live OFF): should_include ALTID True — intet skæres
    assert pc.should_include("kode", "somatik") is True
    assert pc.should_include("samtale", "mood") is True


def test_frozen_sections_never_gated():
    # selv live + vægt 0 må ikke skjule identitet/sikkerhed
    pc._kv_set(pc._LIVE_FLAG, True)
    pc._kv_set(pc._WEIGHTS_KEY, {"kode|soul": 0.0, "kode|security": 0.0})
    assert pc.should_include("kode", "soul") is True
    assert pc.should_include("kode", "security") is True


def test_live_gating_drops_low_weight():
    pc._kv_set(pc._LIVE_FLAG, True)
    pc._kv_set(pc._WEIGHTS_KEY, {"kode|somatik": 0.1, "kode|hukommelse": 0.9})
    assert pc.should_include("kode", "somatik") is False    # under tærskel → udelad
    assert pc.should_include("kode", "hukommelse") is True   # over tærskel → med
    # ukendt (turn_type, section) defaulter til 1.0 → med
    assert pc.should_include("kode", "ukendt") is True


def test_observe_composition_egress_free(isolated_runtime, monkeypatch):
    import core.services.central_private_observe as cpo
    recs = []
    monkeypatch.setattr(cpo, "record_private", lambda *a, **k: recs.append((a, k)))
    pc.observe_composition("kode", sections_total=20, sections_included=12, outcome="ok")
    assert recs and recs[0][0][0] == "cognition"


def test_surface_shows_would_drop():
    pc._kv_set(pc._WEIGHTS_KEY, {"kode|somatik": 0.1, "kode|mood": 0.9})
    surf = pc.build_central_prompt_composer_surface()
    assert "kode|somatik" in surf["would_drop"] and "kode|mood" not in surf["would_drop"]
