"""Tests for den samlede indre tilstands-flade (7/11-2026).

Måler KOBLINGEN, ikke implementeringen: at aggregatoren kalder hver producent,
at en kastende producent isoleres uden at skjule de øvrige, og at routen faktisk
eksponerer den.

Baggrund: 31 ``build_*_surface`` i core/services havde nul reference uden for
deres egen fil — målt både som tekst-søgning og ved at kalde hver enkelt. Det er
de lag der beskriver hvad Jarvis ER og hvordan han beslutter. En flade ingen
indgang har, er stadig mørk.
"""

from __future__ import annotations

import importlib

import pytest

from core.services import inner_state_surface as agg

EXPECTED_GROUPS = ["indre", "beslutning", "verden"]

# De 31, maalt 7/11-2026: nul påkrævede argumenter, dict-svar, nul fejl.
EXPECTED_COUNT = 31


def test_grupperne_er_de_tre_ejer_relationer():
    assert agg.group_names() == EXPECTED_GROUPS


def test_alle_31_producenter_er_registreret():
    navne = agg.producer_names()
    assert len(navne) == EXPECTED_COUNT, (
        f"registret har {len(navne)} producenter, ikke {EXPECTED_COUNT} — "
        f"en flade er faldet ud af koblingen"
    )
    assert len(set(navne)) == len(navne), "en producent er registreret to gange"


def test_aggregatoren_svarer_og_grupperer():
    r = agg.build_inner_state_surface()
    assert r["mode"] == "inner-state-v1"
    assert set(r["groups"]) == set(EXPECTED_GROUPS)
    assert sum(d["count"] for d in r["groups"].values()) == EXPECTED_COUNT
    # Alle 31 svarede da de blev målt — en tavs her betyder en brudt producent.
    assert r["taxse"] == [], f"producenter svigtede: {r['taxse']}"


def test_kastende_producent_isoleres(monkeypatch):
    """En defekt producent må ikke skjule de øvrige 30."""

    def spræng():
        raise RuntimeError("bevidst fejl i test")

    monkeypatch.setitem(
        agg._GROUPS,
        "indre",
        [("sprængt", "core.services.inner_state_surface", "_findes_ikke")],
    )
    r = agg.build_inner_state_surface()
    assert "sprængt" in r["groups"]["indre"]["surfaces"]
    assert r["groups"]["indre"]["surfaces"]["sprængt"]["active"] is False
    assert "reason" in r["groups"]["indre"]["surfaces"]["sprængt"]
    # De to andre grupper er urørte.
    assert r["groups"]["beslutning"]["count"] == 6
    assert r["groups"]["verden"]["count"] == 7


def test_active_false_med_grund_taelles_ikke_som_tavs(monkeypatch):
    """En flade der ærligt melder «intet lige nu» er ikke død.

    Det var fejlen i `_is_live` i infra_state_surface: `active=None` blev talt
    som tavs selv når fladen svarede med ni felter. Her må en `active=False`
    med indhold ikke havne i `taxse`.
    """
    monkeypatch.setitem(
        agg._GROUPS,
        "indre",
        [("tom_men_aerlig", "core.services.inner_state_surface", "_findes_ikke")],
    )
    monkeypatch.setattr(
        agg,
        "_call",
        lambda name, mod, fn: {"active": False, "count": 0, "summary": "intet laast"},
    )
    r = agg.build_inner_state_surface()
    assert r["taxse"] == [], "en ærlig active=False blev talt som tavs"
    assert "tom_men_aerlig" in r["svarer"]


def test_ruten_eksponerer_fladen():
    """Routen skal være monteret — ellers er fladen stadig uden indgang."""
    import apps.api.jarvis_api.routes.central as central

    stier = {r.path for r in central.router.routes}
    assert "/central/inner-state" in stier, (
        "ruten mangler — aggregatoren er bygget men ingen kan kalde den"
    )
