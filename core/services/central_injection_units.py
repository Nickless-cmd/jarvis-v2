"""Deklarative injektions-enheds-definitioner (adskilt fra mekanismen).

Pilot (Fase 1): de to tungeste ikke-besked-afhængige sektioner. compose_fn GENBRUGER
de eksisterende buildere uændret — vi flytter dem bare til baggrunds-refresh.
"""
from __future__ import annotations

from core.services.central_injection_registry import InjectionUnit, register

_REGISTERED = False


def _compose_rule_conclusions() -> str:
    try:
        from core.services.prompt_sections.rule_conclusions import rule_conclusions_section
        return rule_conclusions_section() or ""
    except Exception:
        return ""


def _compose_cognitive_state() -> str:
    # force=True: omgå builderens interne cache — vi VIL have en frisk genberegning i
    # baggrunden (de kolde 6s betales OFF hot-path).
    try:
        from core.services.cognitive_state_assembly import build_cognitive_state_for_prompt
        return build_cognitive_state_for_prompt(compact=False, force=True) or ""
    except Exception:
        return ""


def _compose_tone_guidance() -> str:
    """Centralens sproglige stil-hint (rådets #5): én kort linje der kan injiceres
    som tone-styring. J.A.R.V.I.S-kernen moduleret af tilstanden. Self-safe → "".
    """
    try:
        from core.services.central_tone import build_tone_profile
        prof = build_tone_profile() or {}
        guidance = str(prof.get("guidance") or "")
        return f"[STIL] {guidance}" if guidance else ""
    except Exception:
        return ""


def register_default_units() -> None:
    global _REGISTERED
    if _REGISTERED:
        return
    register(InjectionUnit(
        key="rule_conclusions", source_nerves=(), threshold=1.0,
        max_age_s=120.0, compose_fn=_compose_rule_conclusions, priority=28))
    register(InjectionUnit(
        key="cognitive_state",
        source_nerves=("cognition:affect", "cognition:agenda", "cognition:affective_meta"),
        threshold=0.5, max_age_s=180.0, compose_fn=_compose_cognitive_state, priority=20))
    # Tone-stil-hint (rådets #5): baggrunds-komponeret, off hot-path. Gated bag
    # injection_live("tone") (default False = no-op) OG kræver et read-site i
    # prompt-assembly for at nå prompten — det read-site er BEVIDST IKKE tilføjet
    # (ville røre hot-path). Enheden gør stil-hintet komponerbart+observerbart nu.
    register(InjectionUnit(
        key="tone",
        source_nerves=("cognition:valence_integrated",),
        threshold=0.5, max_age_s=180.0, compose_fn=_compose_tone_guidance, priority=30))
    _REGISTERED = True
