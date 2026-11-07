"""Tests for Centralens samlede tilstands-flade (7/11-2026).

Måler KOBLINGEN: at aggregatoren kalder hver producent i listen, at en
kastende producent isoleres uden at skjule de øvrige, og at routen faktisk
eksponerer den.

Baggrund: `central_hub._SURFACE_GROUPS` peger på navne i
`cognitive_architecture_surface`, som IKKE kalder `build_*_surface`. De 72
flader var derfor uden indgang — de så synlige ud i én måling og mørke i
den næste.
"""
from __future__ import annotations

import importlib

import pytest

from core.services import central_state_surface as agg

EXPECTED = [
    "affect", "valence", "tone", "mood_regulator", "existence_feel", "soul_feel",
    "stance", "self_state", "body_map", "body_mood_feel", "inner_salience",
    "trinity", "adaptation",
    "analyst", "belief_gap", "causal_quality", "hypothesis_generator", "construct",
    "dissent", "rca", "sequence", "lexicon", "notation", "dejavu", "ghost",
    "self_model", "inner_life_ablation",
    "cadence_tempo", "loop_lag", "membrane_watch", "output_conservation",
    "signal_health", "health", "coverage", "coverage_action", "sentinel", "continuity",
    "oneiric_loop", "oneiric_sampler", "morpheus", "dream_action", "mourning",
    "exile", "persephone", "red_dress", "redpill", "white_rabbit", "seraph",
    "merovingian", "trainman", "keymaker", "twins",
    "agents", "council", "profiles", "moltbook", "agent_smith", "relational",
    "agenda", "todo",
    "cost", "llm_egress", "model_meta", "router_adapt", "router_explore",
    "prompt_composer", "prompt_explore", "machines", "surgery", "tool_infra",
    "excess", "brain_link",
]


def test_alle_72_producenter_er_registreret() -> None:
    """Listen må ikke stille miste en flade."""
    navne = [n for n, _, _ in agg._producenter()]
    assert len(navne) == 72, f"forventede 72, fandt {len(navne)}"
    assert navne == EXPECTED


def test_aggregatoren_svarer_og_grupperer() -> None:
    flade = agg.build_central_state_surface()
    assert flade["mode"] == "central-state-v1"
    assert flade["producenter"] == 72
    assert flade["svarer"] == 72
    assert flade["taxse"] == [], f"flader uden svar: {flade['taxse']}"
    assert set(flade["grupper"]) == {
        "tilstand", "kognition", "rytme", "drom", "relation", "maskinrum"
    }
    antal = sum(len(g) for g in flade["grupper"].values())
    assert antal == 72


def test_uden_active_flag_taelles_ikke_som_taxse() -> None:
    """En flade med data men uden `active`-felt er ikke død.

    Målt 7/11-2026: 34 af de 72 hører her. Slog man dem sammen med de
    taxse, ville 34 levende flader blive meldt døde.
    """
    flade = agg.build_central_state_surface()
    assert len(flade["uden_active_flag"]) > 0, (
        "ingen flader uden active-flag — så måler testen ikke den forskel"
    )
    assert not set(flade["taxse"]) & set(flade["uden_active_flag"])


def test_kastende_producent_isoleres(monkeypatch) -> None:
    """Én defekt må ikke skjule de 71 andre."""
    import core.services.central_valence as mod

    def boom() -> dict:
        raise RuntimeError("bevidst fejl i test")

    monkeypatch.setattr(mod, "build_valence_surface", boom)
    flade = agg.build_central_state_surface()
    assert flade["svarer"] == 72, "aggregatoren stoppede ved den kastende producent"
    assert "valence" in flade["taxse"], "den kastende flade blev ikke rapporteret"
    # de øvrige i samme gruppe skal stadig have ægte indhold
    assert flade["grupper"]["tilstand"]["affect"]


def test_ruten_er_mountet() -> None:
    """Uden ruten er fladen stadig mørk for operatøren."""
    from apps.api.jarvis_api.routes import central

    ruter = {r.path for r in central.router.routes}
    assert "/central/central-state" in ruter
