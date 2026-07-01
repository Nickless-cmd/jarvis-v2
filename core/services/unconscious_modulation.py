"""Unconscious modulation — sub-symbolic sampling-parameter shift.

Reads user_temperature_engine's active field and returns LLM API
parameters (temperature, top_p) shifted as a function of the user's
emotional state. Pure read, fail-silent.

Phase 1 (Lag 10, 2026-05-12): visible-chat LLM only. valens nudges
temperature (negative → lower / more cautious; positive → higher / more
creative). arousal nudges top_p (low → narrower / focused; high →
wider / associative). field_intensity scales the magnitude. All values
clamped to safe ranges from settings.

Jarvis sees zero tokens about the modulation. The model generates
differently because its API params shifted before the call. This is the
closest analogue in a transformer to Freud's Triebregulierung: a
pre-linguistic force that shifts flow without becoming a message.
"""
from __future__ import annotations

import logging

from core.runtime.settings import load_settings

logger = logging.getLogger(__name__)

# Implicit defaults when caller passes None for base values.
# Phase 1 assumption — matches industry-standard transformer defaults.
_DEFAULT_BASE_TEMPERATURE = 0.7
_DEFAULT_BASE_TOP_P = 1.0


def _modulation_enabled() -> bool:
    """Kill-switch check. True = modulate; False = pass base through."""
    try:
        return bool(load_settings().unconscious_modulation_enabled)
    except Exception:
        return True  # fail-open: if settings broken, modulation tries


def compute_unconscious_modulation(
    *,
    base_temperature: float | None,
    base_top_p: float | None,
    workspace_id: str = "default",
) -> tuple[float, float]:
    """Return (modulated_temperature, modulated_top_p).

    Reads user_temperature_field and applies intensity-scaled deltas:
        temp_delta  = max_temp_delta  × intensity × valens
        top_p_delta = max_top_p_delta × intensity × arousal

    Clamps to safe parameter ranges from settings. Returns base values
    unchanged if:
      - modulation disabled (kill-switch False)
      - no active field
      - any failure (fail-silent)

    When base is None, implicit defaults are used so the caller still
    gets concrete values to send to the API.
    """
    base_temp = (
        _DEFAULT_BASE_TEMPERATURE if base_temperature is None else float(base_temperature)
    )
    base_top_p_v = _DEFAULT_BASE_TOP_P if base_top_p is None else float(base_top_p)

    if not _modulation_enabled():
        return base_temp, base_top_p_v

    try:
        settings = load_settings()
        max_temp_delta = float(settings.unconscious_modulation_temp_delta)
        max_top_p_delta = float(settings.unconscious_modulation_top_p_delta)
        temp_floor = float(settings.unconscious_modulation_temp_floor)
        temp_ceiling = float(settings.unconscious_modulation_temp_ceiling)
        top_p_floor = float(settings.unconscious_modulation_top_p_floor)
        top_p_ceiling = float(settings.unconscious_modulation_top_p_ceiling)

        from core.services.user_temperature_engine import get_active_field
        field = get_active_field(workspace_id=workspace_id)
        if not field:
            return base_temp, base_top_p_v

        valens = float(field.get("field_valens") or 0.0)
        arousal = float(field.get("field_arousal") or 0.0)
        intensity = float(field.get("field_intensity") or 0.0)

        temp_delta = max_temp_delta * intensity * valens
        top_p_delta = max_top_p_delta * intensity * arousal

        mod_temp = max(temp_floor, min(temp_ceiling, base_temp + temp_delta))
        mod_top_p = max(top_p_floor, min(top_p_ceiling, base_top_p_v + top_p_delta))

        logger.debug(
            "unconscious_modulation: base=(%.3f,%.3f) → modulated=(%.3f,%.3f) "
            "[valens=%.2f arousal=%.2f intensity=%.2f]",
            base_temp, base_top_p_v, mod_temp, mod_top_p,
            valens, arousal, intensity,
        )
        # LivingNeuron felt-krop: Jarvis skifter sin EGEN temperatur/top_p ubevidst efter emotionel
        # tilstand — 100% usynligt før nu. Observer KUN ved reel skift (egress-frit, kun tal).
        if intensity > 0.05:
            try:
                from core.services.central_private_observe import observe_hub
                observe_hub("unconscious_modulation", meta={
                    "valens": round(valens, 2), "arousal": round(arousal, 2),
                    "intensity": round(intensity, 2), "temp_shift": round(mod_temp - base_temp, 3)})
            except Exception:
                pass
        return mod_temp, mod_top_p
    except Exception as exc:
        logger.debug("unconscious_modulation: fallback to base (%s)", exc)
        return base_temp, base_top_p_v
