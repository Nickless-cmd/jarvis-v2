"""Reflection → Plan: skrive-hagen.

Målt 29/9-2026: 603 planer i cognitive_reflective_plans, alle 'proposed', ældste
fra 14. maj. Tre daemons skrev dem; intet læste dem (accept_reflective_plan og
build_reflection_to_plan_surface kaldes ikke uden for deres egen fil). Hagen
lukkes nu som default via reflection_to_plan_enabled=False.
"""
from __future__ import annotations

from types import SimpleNamespace

from core.runtime import settings as settings_mod
from core.services import reflection_to_plan as rtp


def _settings(enabled: bool) -> SimpleNamespace:
    return SimpleNamespace(reflection_to_plan_enabled=enabled)


def test_hagen_er_lukket_som_default(monkeypatch):
    monkeypatch.setattr(settings_mod, "load_settings", lambda: _settings(False))
    ud = rtp.create_reflective_plan(reflection_text="x" * 60, source_kind="inner_voice")
    assert ud["outcome"] == "skipped"
    assert ud["reason"] == "disabled"


def test_hagen_kan_aabnes(monkeypatch, isolated_runtime):
    """Med enabled fortsætter den forbi gaten — uden LLM bliver det et LLM-svar,
    aldrig 'disabled'."""
    from core.services import daemon_llm

    monkeypatch.setattr(settings_mod, "load_settings", lambda: _settings(True))
    monkeypatch.setattr(daemon_llm, "daemon_llm_call", lambda *a, **k: "")
    ud = rtp.create_reflective_plan(reflection_text="x" * 60, source_kind="inner_voice")
    assert ud.get("reason") != "disabled"


def test_for_kort_refleksion_springes_over(monkeypatch):
    """Gaten skal ikke sløre det eksisterende min_length-filter."""
    monkeypatch.setattr(settings_mod, "load_settings", lambda: _settings(True))
    ud = rtp.create_reflective_plan(reflection_text="kort", source_kind="inner_voice",
                                    min_length=40)
    assert ud["outcome"] == "skipped"
    assert ud["reason"] == "reflection_too_short"
