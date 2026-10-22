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


def test_tail_relevance_drops_default_low_value_context():
    assert pc.should_include_tail("samtale", "causal patterns") is False
    assert pc.should_include_tail("spørgsmål", "pattern counterfactuals") is False
    assert pc.should_include_tail("kode", "causal patterns") is True
    assert pc.should_include_tail("opgave", "TOOLS.md guidance") is True
    assert pc.should_include_tail("samtale", "ukendt tail") is True


def test_tail_relevance_never_gates_frozen_sections():
    pc._kv_set(pc._WEIGHTS_KEY, {"samtale|identity tail": 0.0})
    assert pc.should_include_tail("samtale", "identity tail") is True


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


def test_frequency_substrate_and_candidates(isolated_runtime):
    # observér 25 kode-ture hvor 'somatik' altid var med → høj-frekvens kandidat
    for _ in range(25):
        pc.observe_composition("kode", sections_total=10, sections_included=2,
                               included_labels=["somatik", "markdown formatting"])
    cands = pc.build_relevance_candidates(min_count=20)
    keys = {(c["turn_type"], c["section"]) for c in cands}
    assert ("kode", "somatik") in keys
    # kandidat bærer interlanguage-notation (sektion ⊂ kald)
    som = next(c for c in cands if c["section"] == "somatik")
    assert som["notation"] == "kode ⊂ kald" and som["count"] >= 20


def test_frozen_sections_not_candidates(isolated_runtime):
    for _ in range(30):
        pc.observe_composition("kode", sections_total=5, sections_included=1,
                               included_labels=["pinned identity context"])
    cands = pc.build_relevance_candidates(min_count=20)
    # identitet må ALDRIG blive en udeladelses-kandidat
    assert not any("identity" in c["section"].lower() for c in cands)


# ── Mode-forskel: samtalen skal ikke bære maskinrummet ──────────────────────
# Målt 22/10-2026. Bjørn 20/10: chat-svar endte som mødenotater fordi
# decision-adherence-gaten, forward-chaining-konklusionerne og de kausale
# diagnostik-blokke fyldte konteksten i en samtale hvor de ikke hører hjemme.
#
# `get_weight` læste KUN runtime-kv'en, så uden en indbagt tabel faldt hver
# sektion til 1.0 og gaten — som ellers ER live — kunne aldrig skære noget.
#
# MUTATION: fjern `_DEFAULT_WEIGHTS`-opslaget i `get_weight` → test 1 og 3 fejler.

_TUNGE_AWARENESS = (
    "decision adherence gate",
    "rule engine conclusions",
    "causal alerts",
    "causal narrative",
)


def _live(monkeypatch):
    """Gaten skal måles LIVE — i test-DB'en er flaget ikke sat, og så kører den
    i shadow og inkluderer alt. Produktionen har det tændt (målt 22/10-2026)."""
    from core.services import central_prompt_composer as c

    monkeypatch.setattr(c, "is_live_enabled", lambda: True)
    monkeypatch.setattr(c, "is_tail_live_enabled", lambda: True)
    return c


def test_samtalen_skærer_de_tunge_diagnostik_sektioner(monkeypatch):
    c = _live(monkeypatch)

    for label in _TUNGE_AWARENESS:
        assert c.should_include("samtale", label) is False, (
            f"'{label}' hører i maskinrummet, ikke i en samtale")


def test_spoergsmaalet_skærer_dem_også(monkeypatch):
    c = _live(monkeypatch)

    for label in _TUNGE_AWARENESS:
        assert c.should_include("spørgsmål", label) is False


def test_kode_beholder_alt_uaendret(monkeypatch):
    """Maskinrummet ER pointen i kode-mode. Ingen af de tunge sektioner må skæres."""
    c = _live(monkeypatch)

    for label in _TUNGE_AWARENESS:
        assert c.should_include("kode", label) is True, (
            f"'{label}' må ikke skæres i kode-mode")
    for label in ("model pools", "causal patterns", "pattern counterfactuals"):
        assert c.should_include_tail("kode", label) is True


def test_opgave_beholder_alt_uaendret(monkeypatch):
    c = _live(monkeypatch)

    for label in _TUNGE_AWARENESS:
        assert c.should_include("opgave", label) is True


def test_samtalen_skærer_model_pools(monkeypatch):
    """Model-pools var den ENESTE tunge hale-sektion der stadig kom med i samtale."""
    c = _live(monkeypatch)

    assert c.should_include_tail("samtale", "model pools") is False
    assert c.should_include_tail("kode", "model pools") is True


def test_frosne_sektioner_skæres_aldrig(monkeypatch):
    """Identitet og sikkerhed er frossen kerne — gaten må ikke røre dem."""
    from core.services import central_prompt_composer as c

    for label in ("soul", "identity", "pinned identity context", "security"):
        assert c.should_include("samtale", label) is True
        assert c.should_include_tail("samtale", label) is True


def test_runtime_kv_vinder_over_den_indbagte_tabel(monkeypatch):
    """En målt kalibrering skal kunne justere uden en deploy."""
    from core.services import central_prompt_composer as c

    monkeypatch.setattr(c, "_kv_get", lambda k, d: {"samtale|decision adherence gate": 0.9})
    assert c.get_weight("samtale", "decision adherence gate") == 0.9


def test_shadow_mode_inkluderer_alt(monkeypatch):
    """Er flaget slået fra, må gaten ikke skære noget — det er dens sikkerhedsnet."""
    from core.services import central_prompt_composer as c

    monkeypatch.setattr(c, "is_live_enabled", lambda: False)
    monkeypatch.setattr(c, "is_tail_live_enabled", lambda: False)
    for label in _TUNGE_AWARENESS:
        assert c.should_include("samtale", label) is True
    assert c.should_include_tail("samtale", "model pools") is True
