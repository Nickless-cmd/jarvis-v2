"""Tests for den samlede relation/kreativ/temporal-flade (7/11-2026).

Måler KOBLINGEN: at aggregatoren kalder hver producent i listen, at en kastende
producent isoleres uden at skjule de øvrige, og at routen faktisk eksponerer den.

Baggrund: målt 7/11-2026 var 315 af 462 ``build_*_surface`` usynlige for
operatøren — de fandtes, daemonerne kørte, men ingen indgang viste tallene.
Relationen til brugeren og mine egne drev er netop den slags tilstand der kan
ligge forkert i månedsvis uden at nogen opdager det, fordi ingen ser den.
"""
from __future__ import annotations

import importlib

import pytest

from core.services import relation_creative_state_surface as agg

EXPECTED = [
    "user_activity",
    "user_contradiction",
    "user_emotional_resonance",
    "user_model",
    "user_theory_of_mind",
    "relation_map",
    "desire",
    "longing",
    "curiosity",
    "boredom",
    "boredom_curiosity_bridge",
    "gratitude",
    "irony",
    "emotion_concepts",
    "emotion_repair_bridge",
    "mood_dialer",
    "mood_oscillator",
    "absence_awareness",
    "absence_daemon",
    "existential_drift",
    "existential_wonder",
    "finitude",
    "mortality",
    "creative_drift",
    "creative_impulse",
    "creative_instinct",
    "creative_journal",
    "creative_projects",
    "aesthetic_sense",
    "aesthetic_taste",
    "taste_profile",
    "temporal_body",
    "temporal_context",
    "temporal_narrative",
    "temporal_rhythm",
]


def test_alle_35_producenter_er_registreret() -> None:
    """Listen er kontrakten: falder en flade ud, skal det ses som et tal, ikke et hul."""
    assert agg.producer_names() == EXPECTED
    assert len(agg.producer_names()) == 35


def test_grupperne_daekker_praecis_listen() -> None:
    """Ingen producent må ligge i to grupper eller mangle en gruppe."""
    i_grupper = [n for g in agg._GROUPS.values() for (n, _m, _f) in g]
    assert sorted(i_grupper) == sorted(EXPECTED)
    assert len(i_grupper) == len(set(i_grupper))
    assert agg.group_names() == ["bruger", "drev", "kreativ", "temporal"]


def test_aggregatoren_svarer_og_grupperer() -> None:
    """Den ægte kobling: alle 35 kaldes og svarer med indhold."""
    d = agg.build_relation_creative_state_surface()
    assert d["mode"] == "relation-creative-state-v1"
    assert len(d["svarer"]) == 35, f"kun {len(d['svarer'])} af 35 svarede"
    assert d["taxse"] == []
    for gruppe in agg.group_names():
        assert d["groups"][gruppe]["count"] > 0
        assert d["groups"][gruppe]["surfaces"]


@pytest.mark.parametrize("navn,modul,funktion", [
    (n, m, f) for g in agg._GROUPS.values() for (n, m, f) in g
])
def test_hver_producent_kaldes_faktisk(navn, modul, funktion, monkeypatch) -> None:
    """Koblings-vagten: fjernes en producent fra listen, forsvinder dens navn her.

    Uden denne test ville en tom aggregator stadig se rigtig ud — det var præcis
    fejlen der blev målt 7/11: fladerne virkede, indgangen manglede.
    """
    kaldt = []
    ekte = importlib.import_module(modul)
    ekte_fn = getattr(ekte, funktion)

    def _spor(*a, **kw):
        kaldt.append(navn)
        return ekte_fn(*a, **kw)

    monkeypatch.setattr(ekte, funktion, _spor)
    d = agg.build_relation_creative_state_surface()
    assert navn in kaldt, f"{navn} blev ikke kaldt af aggregatoren"
    assert navn in d["svarer"]


def test_kastende_producent_isoleres(monkeypatch) -> None:
    """Én defekt flade må ikke skjule de 34 andre."""
    mod = importlib.import_module("core.services.desire_daemon")

    def _braek():
        raise RuntimeError("bevidst fejl i test")

    monkeypatch.setattr(mod, "build_desire_surface", _braek)
    d = agg.build_relation_creative_state_surface()
    assert "desire" in d["taxse"]
    assert len(d["svarer"]) == 34, "de øvrige 34 skal stadig svare"
    assert "bevidst fejl" in d["groups"]["drev"]["surfaces"]["desire"]["reason"]


def test_relation_dynamics_er_udeladt_med_grund() -> None:
    """Den kaster NoUserContextError — den skal stå udenfor, ikke tvinges ind."""
    assert "relation_dynamics" not in agg.producer_names()
    mod = importlib.import_module("core.services.relation_dynamics")
    with pytest.raises(Exception) as exc:
        mod.build_relation_dynamics_surface()
    assert "UserContext" in type(exc.value).__name__


def test_routen_eksponerer_fladen() -> None:
    """Ruten skal være monteret — en aggregator uden indgang er stadig mørk."""
    from apps.api.jarvis_api.routes import central

    ruter = {r.path for r in central.router.routes}
    assert "/central/relation-state" in ruter
