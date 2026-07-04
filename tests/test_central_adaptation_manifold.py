"""Tests for MANIFOLD første skridt (LivingNeuron-roadmap §3): central_adaptation-registret.

Verificerer: registret indeholder KUN gut-bias med eksakte værdier; den HÅRDE frossen-kerne-assert
afviser SOUL/IDENTITY/SECURITY/dødsmekanisme-nøgler men accepterer godartede; adfærd for gut-klassen
er BEVARET (samme forslag-formel); run_adaptation_tick er self-safe (kaster aldrig ud)."""
from __future__ import annotations

import pytest

from core.services import central_adaptation as ad


# ── Registret: præcis gut-bias, eksakte værdier ─────────────────────────────────────
def test_registry_contains_exactly_gut_bias():
    assert len(ad.ADAPTATION_REGISTRY) == 1
    gut = ad.ADAPTATION_REGISTRY[0]
    assert gut.name == "gut_proceed_bias"
    assert gut.kv_key == "central_gut_proceed_bias"
    assert gut.prev_key == "central_gut_proceed_bias_prev"
    assert gut.sources == ("causal_convergence", "causal_divergence", "stance_divergence")
    assert gut.clamp == 0.25
    assert gut.budget == 0.30
    assert gut.live_flag == "central_lag4_live_enabled"
    assert gut.pause_flag == "central_lag4_paused"
    assert gut.domain == "gut_proceed_bias"
    assert gut.min_resolved == 5


def test_registry_element_matches_legacy_constants():
    """Registrets eneste element skal spejle de bagudkompatible modul-konstanter 1:1."""
    gut = ad.ADAPTATION_REGISTRY[0]
    assert gut.kv_key == ad._BIAS_KEY and gut.prev_key == ad._PREV_KEY
    assert gut.clamp == ad._BIAS_CLAMP and gut.budget == ad._BIAS_BUDGET
    assert gut.live_flag == ad._LIVE_FLAG and gut.pause_flag == ad._PAUSE_KEY
    assert gut.sources == ad._GUT_SOURCES


# ── HÅRDT VÆRN: assert afviser frossen kerne, accepterer godartet ───────────────────
def _fake_class(kv_key: str, name: str = "fake_muscle"):
    return ad.AdaptationClass(
        name=name, kv_key=kv_key, prev_key=f"{kv_key}_prev",
        sources=("causal_convergence",), budget=0.3, clamp=0.25,
        live_flag="fake_live", pause_flag="fake_pause",
        domain="fake_domain", anchor_version="fake-v1",
    )


@pytest.mark.parametrize("bad_key", [
    "soul_core_bias",
    "identity_drift",
    "central_security_gate",
    "MIN_ACT_CONFIDENCE",
    "learnable_aggregate_keys",
    "grounded_sources",
    "verify_frozen_core",
    "death_mechanism_conf",
    "central_killswitch",
])
def test_hard_assert_rejects_frozen_core_keys(bad_key):
    """Enhver muskel hvis kv_key rører SOUL/IDENTITY/SECURITY/dødsmekanismen SKAL afvises ved reg."""
    with pytest.raises(AssertionError):
        ad._register_adaptation_class(_fake_class(bad_key))


def test_hard_assert_rejects_frozen_core_in_name():
    """Værnet matcher også på name (ikke kun kv_key)."""
    with pytest.raises(AssertionError):
        ad._register_adaptation_class(_fake_class("benign_key", name="soul_muscle"))


@pytest.mark.parametrize("ok_key", [
    "procedure_weight_bias",
    "loop_persistence_bias",
    "central_dream_trust_bias",
    "curiosity_proceed_bias",
])
def test_hard_assert_accepts_benign_keys(ok_key):
    """Godartede, ikke-beskyttede nøgler skal passere registreringen uden fejl."""
    cls = ad._register_adaptation_class(_fake_class(ok_key))
    assert cls.kv_key == ok_key


def test_gut_class_itself_passes_the_guard():
    """Sanity: den ægte gut-klasse rører ikke den frosne kerne (ellers ville import fejle)."""
    ad._register_adaptation_class(ad.ADAPTATION_REGISTRY[0])  # må ikke kaste


# ── Adfærds-bevaring: gut-forslag er uændret ────────────────────────────────────────
def test_gut_proposed_bias_formula_unchanged(monkeypatch):
    """Mock track-record → forslaget skal følge den EKSAKTE før-MANIFOLD-formel (acc-0.5)*0.5."""
    monkeypatch.setattr(ad, "resolved_track_record",
                        lambda **_: {"supported": 8, "contradicted": 2})   # accuracy 0.8
    p = ad.compute_proposed_bias()             # default = gut
    assert p["enough"] is True
    assert p["accuracy"] == 0.8
    assert p["proposed"] == 0.15               # (0.8-0.5)*0.5 = 0.15


def test_gut_low_accuracy_gives_caution_bias(monkeypatch):
    monkeypatch.setattr(ad, "resolved_track_record",
                        lambda **_: {"supported": 1, "contradicted": 9})   # accuracy 0.1
    p = ad.compute_proposed_bias()
    assert p["proposed"] == -0.2               # (0.1-0.5)*0.5 = -0.2


def test_gut_too_few_resolved_proposes_zero(monkeypatch):
    monkeypatch.setattr(ad, "resolved_track_record",
                        lambda **_: {"supported": 2, "contradicted": 1})   # < min_resolved
    p = ad.compute_proposed_bias()
    assert p["enough"] is False and p["proposed"] == 0.0


def test_compute_default_equals_explicit_gut(monkeypatch):
    """compute_proposed_bias() uden arg == compute_proposed_bias(gut-klassen) — back-compat."""
    monkeypatch.setattr(ad, "resolved_track_record",
                        lambda **_: {"supported": 7, "contradicted": 3})
    assert ad.compute_proposed_bias() == ad.compute_proposed_bias(ad.ADAPTATION_REGISTRY[0])


# ── Self-safe: intet må kaste ud af run_adaptation_tick ─────────────────────────────
def test_run_tick_self_safe_on_broken_track_record(monkeypatch):
    def boom(**_):
        raise RuntimeError("db korrupt")
    monkeypatch.setattr(ad, "resolved_track_record", boom)
    out = ad.run_adaptation_tick()
    assert out["status"] == "ok"


def test_run_tick_self_safe_on_broken_class_tick(monkeypatch):
    """Selv hvis en musklens tick kaster, isolerer run_adaptation_tick den (per-muskel try)."""
    def boom(cls):
        raise RuntimeError("muskel-fejl")
    monkeypatch.setattr(ad, "_run_class_tick", boom)
    out = ad.run_adaptation_tick()
    assert out["status"] == "ok"
    assert out["muscles"][0]["mode"] == "error"


def test_run_tick_backcompat_toplevel_shape(monkeypatch):
    """Top-niveau-formen bevarer de gamle nøgler (mode/applied/proposed_bias/gate)."""
    monkeypatch.setattr(ad, "_run_class_tick",
                        lambda cls: {"muscle": cls.name, "mode": "shadow", "current_bias": 0.0,
                                     "proposed_bias": 0.15, "applied": False, "gate": "ok",
                                     "accuracy": 0.8, "resolved": 10})
    out = ad.run_adaptation_tick()
    for key in ("status", "mode", "current_bias", "proposed_bias", "applied", "gate",
                "accuracy", "resolved", "muscles"):
        assert key in out
    assert out["mode"] == "shadow" and out["proposed_bias"] == 0.15
