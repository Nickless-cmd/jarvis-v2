"""Tests for Prompt-cluster Phase 1 (prompt_observer).

Verificerer paritet (blacklistede sektioner default OFF, resten ON), at en override vinder
(live on/off), at default-tilfældet ikke koster opslag, og at observe_build er self-safe.
"""
from __future__ import annotations

from core.services import prompt_observer as po


# ── section_enabled: paritet + override ──────────────────────────────────
def test_blacklisted_default_off():
    assert po.section_enabled("R2 gate telemetry", blacklisted=True, overrides={}) is False


def test_non_blacklisted_default_on():
    assert po.section_enabled("brain facts", blacklisted=False, overrides={}) is True


def test_override_reenables_blacklisted():
    ov = {"R2 gate telemetry": True}
    assert po.section_enabled("R2 gate telemetry", blacklisted=True, overrides=ov) is True


def test_override_disables_active_section():
    ov = {"brain facts": False}
    assert po.section_enabled("brain facts", blacklisted=False, overrides=ov) is False


def test_override_wins_over_default_both_directions():
    # eksplicit True på en ikke-blacklistet (no-op men eksplicit) og False på blacklistet
    assert po.section_enabled("x", blacklisted=False, overrides={"x": True}) is True
    assert po.section_enabled("y", blacklisted=True, overrides={"y": False}) is False


# ── load_overrides: round-trip via central_switches ──────────────────────
def test_set_section_then_load_roundtrip():
    label = "test-section-roundtrip-xyz"
    try:
        po.set_section(label, False)
        ov = po.load_overrides()
        assert ov.get(label) is False
        po.set_section(label, True)
        ov2 = po.load_overrides()
        assert ov2.get(label) is True
    finally:
        from core.services import shared_cache
        shared_cache.delete("flag:central.switch.prompt_section." + label)


def test_load_overrides_returns_dict():
    assert isinstance(po.load_overrides(), dict)


# ── observe_build: self-safe ─────────────────────────────────────────────
def test_observe_build_never_raises():
    # må aldrig kaste uanset input
    po.observe_build(lane="visible", included=12,
                     dropped_disabled=["a", "b"], dropped_budget=["c"])
    po.observe_build(lane="", included=0, dropped_disabled=[], dropped_budget=[])


# ── katalog ──────────────────────────────────────────────────────────────
def test_catalog_validates_with_prompt():
    from core.services import central_catalog as cc
    assert cc.validate() == []
    assert "prompt" in cc.clusters()
