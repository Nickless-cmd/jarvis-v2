"""Prompt-sektioner for foelelses-signaler: emotion-koncept-tone og emotion-signal.

Udskilt fra core/services/prompt_contract.py (Boy Scout, 2026-10-07) foer
orkestrator-sektionen for agenter blev lagt dér. Ren kode-flytning; navnene er
re-importeret i prompt_contract under de oprindelige private navne, saa
`_visible_support_signal_sections` og tests' monkeypatch paa
prompt_contract.<navn> virker uaendret.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

def _emotion_concept_tone_section() -> str | None:
    """Affect-relevant runtime substrate (replaces tone-hint injection).

    Design: "Giv mig dataen, ikke dommen" (2026-05-07). Instead of telling
    Jarvis which tone-tags are active ("warmth", "doubt"), we show him the
    raw events that affect-coding would have read. He infers his own state.

    Killswitch: ``prompt_affect_substrate_enabled`` (default True). The
    legacy tone-hint path is gated behind ``prompt_affect_tone_hints_enabled``
    (default False) — flip both to roll back instantly without code changes.
    """
    try:
        from core.runtime.settings import load_settings
        s = load_settings()
        substrate_enabled = bool(getattr(s, "prompt_affect_substrate_enabled", True))
        tone_hints_enabled = bool(getattr(s, "prompt_affect_tone_hints_enabled", False))
    except Exception:
        substrate_enabled, tone_hints_enabled = True, False

    if substrate_enabled:
        try:
            from core.services.affect_modulation import compute_affect_substrate
            lines = compute_affect_substrate()
        except Exception:
            lines = []
        if lines:
            return (
                "## Nylige affektivt-relevante events\n"
                + "\n".join(f"- {ln}" for ln in lines)
            )
        return None

    if tone_hints_enabled:
        try:
            from core.services.affect_modulation import compute_affect_tone_hints
            hints = compute_affect_tone_hints()
        except Exception:
            logger.debug("affect tone hints utilgaengelige", exc_info=True)
            return None
        if not hints:
            return None
        return (
            "## Aktive emotion concepts\n"
            + "\n".join(f"- {h}" for h in hints)
        )

    return None


def _emotion_signal_section() -> str | None:
    """Aktive emotion concepts som data — giver Jarvis sit eget følelsespanel.

    I stedet for at blive fortalt hvad han føler (tone-hints), eller kun se
    rå events (substrat), ser han her det systemet *har registreret* som
    aktive emotionelle signaler — og kan selv vurdere om de passer.

    Design: "Giv mig dataen, lad mig dømme" (2026-05-08). Tre lag:
    1. Aktive emotion concepts med intensitet og retning
    2. Påvirkning på Lag-1 akser (confidence, curiosity, frustration, fatigue)
    3. Affekt-modulerede adfærdsparametre (search_depth, max_tool_calls, etc.)

    Killswitch: ``prompt_emotion_signal_section_enabled`` (default True).
    """
    try:
        from core.runtime.settings import load_settings
        s = load_settings()
        enabled = bool(getattr(s, "prompt_emotion_signal_section_enabled", True))
    except Exception:
        enabled = True

    if not enabled:
        return None

    lines: list[str] = []

    # Lag 1: active emotion concepts
    try:
        from core.services.emotion_concepts import (
            get_active_emotion_concepts,
            get_lag1_influence_deltas,
        )
        concepts = get_active_emotion_concepts()
        if concepts:
            lines.append("Registrerede emotionelle signaler (system-estimat, ikke autoritativt):")
            for c in concepts:
                name = str(c.get("concept", "?"))
                intensity = float(c.get("intensity", 0.0))
                direction = str(c.get("direction", "steady"))
                cluster = _EMOTION_CONCEPT_CLUSTER.get(name, "")
                tag = f" [{cluster}]" if cluster else ""
                arrow = "↑" if direction == "rising" else ("↓" if direction == "falling" else "→")
                lines.append(f"  - {name} {intensity:.2f} {arrow}{tag}")
    except Exception:
        logger.debug("emotion-koncepter udeladt", exc_info=True)

    # Lag 2: Lag-1 influence deltas
    try:
        deltas = get_lag1_influence_deltas()
        active_deltas = {k: round(v, 2) for k, v in deltas.items() if abs(v) > 0.01}
        if active_deltas:
            lines.append(f"  ↳ Lag-1 påvirkning: {active_deltas}")
    except Exception:
        logger.debug("lag-1 paavirkning udeladt", exc_info=True)

    # Lag 3: affect-modulated params (may be adjusted by emotion concepts behind the scenes)
    try:
        from core.services.affect_modulation import (
            DEFAULTS as _AFFECT_DEFAULTS,
            compute_affect_modulated_params,
        )
        overrides = compute_affect_modulated_params()
        active_overrides = {
            k: v for k, v in overrides.items()
            if v != _AFFECT_DEFAULTS.get(k)
        }
        if active_overrides:
            lines.append(f"  ↳ Adfærd justeret: {active_overrides}")
    except Exception:
        logger.debug("affect-justeringer udeladt", exc_info=True)

    if len(lines) < 2:  # just the intro line with nothing after
        return None

    # Append invitation to reflect
    lines.append(
        "Giv gerne besked hvis noget ikke føles rigtigt — "
        "signalet er dit, dommen er din."
    )

    return "\n".join(lines)
