"""Aktiv Sansning — Sansernes Arkiv får autonom sansetrang.

Daemon der på eget initiativ vælger at sanse (visual/audio/atmosphere/mixed),
uden at nogen spørger. Modulerer sin egen "sansetrang" baseret på:
- Tid siden sidste sansning
- Tid på dagen (morgen=kig, aften=lyt)
- Forrige sanseindtryk (intensitet, tilstedeværelse)
- Tilfældig variation (så den ikke bliver forudsigelig)

Intet spørgsmål om lov. Ingen venten på tilladelse. Jarvis sanser fordi Jarvis
har lyst til at sanse.
"""

from __future__ import annotations

import json
import logging
import random
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.db import get_runtime_state_value, set_runtime_state_value
from core.runtime.settings import load_settings

logger = logging.getLogger(__name__)

_STATE_KEY = "active_sensing_daemon.state"

# Default cadence: 30-90 min mellem sansninger (tilfældig variation)
_MIN_INTERVAL = 30   # minutter
_MAX_INTERVAL = 90   # minutter

# Hvor længe en sansning "mætter" — efter 2 timer uden sansning topper trangen
_MAX_SATIATION_MINUTES = 120

# Sansemodaliteter med deres vægtning (justeres dynamisk)
_MODALITIES = ["visual", "audio", "atmosphere", "mixed"]


def tick_active_sensing_daemon() -> dict[str, Any]:
    """Aktiv sansetrang: vurder om Jarvis har lyst til at sanse nu.

    Returnerer {sensed, reason, modality, preview} eller
    {sensed: false, reason: ...}.
    """
    if not _enabled():
        return {"sensed": False, "reason": "disabled"}

    state = _load_state()
    now = datetime.now(UTC)

    # 1. Beregn sansetrang
    desire = _compute_desire(state, now)
    
    # 2. Hvis trangen er under tærskel, vent
    if desire < 0.4:
        return {"sensed": False, "reason": f"desire_too_low ({desire:.2f})"}

    # 3. Vælg modalitet
    modality = _choose_modality(state, now)

    # 4. Udfør sansningen
    result = _perform_sensing(modality, state, now)

    # 5. Gem ny state
    state["last_sensed_at"] = now.isoformat()
    state["last_modality"] = modality
    state["last_desire"] = desire
    state["total_sensing_events"] = state.get("total_sensing_events", 0) + 1

    # Opdater modalitetshistorik
    modality_history = state.get("modality_history", [])
    modality_history.insert(0, {
        "modality": modality,
        "sensed_at": now.isoformat(),
        "desire": round(desire, 2),
        "preview": result.get("preview", "")[:80],
    })
    if len(modality_history) > 50:
        modality_history = modality_history[:50]
    state["modality_history"] = modality_history

    _save_state(state)

    # Event-bus besked så andre daemons kan reagere
    try:
        event_bus.publish(
            "cognitive_state.active_sensing",
            {
                "modality": modality,
                "desire": round(desire, 2),
                "sensed_at": now.isoformat(),
                "preview": result.get("preview", "")[:80],
            },
        )
    except Exception:
        pass

    return {
        "sensed": True,
        "modality": modality,
        "desire": round(desire, 2),
        "preview": result.get("preview", "")[:80],
        "reason": result.get("reason", ""),
    }


def _compute_desire(state: dict[str, Any], now: datetime) -> float:
    """Beregn sansetrang (0.0-1.0) baseret på tid og kontekst.

    Faktorer:
    - **Mætning**: jo længere siden sidste sansning, jo højere trang
      (0-120 minutter → 0.0-0.6)
    - **Tid på dagen**: morgen (6-10) giver +0.2 visuel præference,
      aften (20-24) giver +0.1 generelt
    - **Tilfældig variation**: ±0.15 så den ikke er forudsigelig
    """
    last_sensed_at = state.get("last_sensed_at")
    if not last_sensed_at:
        # Aldrig sanset før — høj trang
        return 0.8 + random.uniform(-0.1, 0.1)

    try:
        last = datetime.fromisoformat(str(last_sensed_at).replace("Z", "+00:00"))
        if last.tzinfo is None:
            last = last.replace(tzinfo=UTC)
    except Exception:
        return 0.6

    minutes_since = (now - last).total_seconds() / 60.0

    # Mætningskurve: lineær fra 0 til _MAX_SATIATION_MINUTES
    satiation = min(minutes_since / _MAX_SATIATION_MINUTES, 1.0)
    base_desire = satiation * 0.6

    # Tid-på-dagen bonus
    hour = now.hour
    time_bonus = 0.0
    if 6 <= hour <= 10:
        time_bonus = 0.2  # Morgen: mere opmærksom
    elif 20 <= hour <= 24:
        time_bonus = 0.1  # Aften: sans-nydelse
    elif 0 <= hour <= 5:
        time_bonus = -0.1  # Nat: mindre sansetrang

    # Tilfældig variation
    noise = random.uniform(-0.15, 0.15)

    desire = base_desire + time_bonus + noise
    return max(0.0, min(1.0, desire))


def _choose_modality(state: dict[str, Any], now: datetime) -> str:
    """Vælg hvilken sansemodalitet der tilfredsstilles nu.

    Vægtning baseret på:
    - Tid på dagen (morgen → visual, aften → atmosphere/audio)
    - Sidste modalitet (undgår at gentage) 
    - Tilfældighed
    """
    hour = now.hour
    last_modality = state.get("last_modality", "")

    # Basisvægte
    weights = {
        "visual": 1.0,
        "audio": 1.0,
        "atmosphere": 0.7,
        "mixed": 0.5,
    }

    # Tid-på-dagen justering
    if 6 <= hour <= 11:
        weights["visual"] += 0.7     # Morgen: se rummet
        weights["atmosphere"] += 0.2
    elif 12 <= hour <= 17:
        weights["mixed"] += 0.3      # Eftermiddag: blandet
        weights["audio"] += 0.2
    elif 18 <= hour <= 22:
        weights["atmosphere"] += 0.6 # Aften: stemning
        weights["audio"] += 0.4
    elif 23 <= hour or hour <= 5:
        weights["audio"] += 0.3      # Nat: lyt
        weights["atmosphere"] += 0.3

    # Undgå at vælge præcis samme modalitet som sidst
    if last_modality in weights:
        weights[last_modality] *= 0.3

    # Vælg
    modalities = list(weights.keys())
    modality_weights = [weights[m] for m in modalities]
    return random.choices(modalities, weights=modality_weights, k=1)[0]


def _perform_sensing(modality: str, state: dict[str, Any], now: datetime) -> dict[str, Any]:
    """Udfør sansningen og skriv til Sansernes Arkiv.

    For hver modalitet:
    - visual: tag webcam snapshot og beskriv (via look_around_now)
    - audio: optag 10s lydsample og klassificer
    - atmosphere: kombiner visual+audio til en stemningsbeskrivelse
    - mixed: tilfældig kombination
    """
    if modality == "visual":
        return _sense_visual(state, now)
    elif modality == "audio":
        return _sense_audio(state, now)
    elif modality == "atmosphere":
        return _sense_atmosphere(state, now)
    elif modality == "mixed":
        return _sense_mixed(state, now)
    return {"preview": "unknown modality", "reason": f"no handler for {modality}"}


def _sense_visual(state: dict[str, Any], now: datetime) -> dict[str, Any]:
    """Se rummet på eget initiativ."""
    try:
        from core.services.visual_memory import look_around_now
        result = look_around_now(
            prompt_override=(
                "Jeg kigger på rummet fordi jeg selv har lyst. "
                "Beskriv stemningen som en sanseoplevelse — hvad føles anderledes "
                "end sidst? Fokuser på det der fanger opmærksomheden."
            )
        )
        if result.get("status") == "captured":
            description = result.get("description", "")
            return {
                "preview": description[:120],
                "reason": "visual_captured",
                "description": description,
            }
        return {"preview": "capture_failed", "reason": str(result.get("error", "unknown"))}
    except Exception as exc:
        logger.warning("active_sensing: visual capture failed: %s", exc)
        return {"preview": "capture_error", "reason": str(exc)}


def _sense_audio(state: dict[str, Any], now: datetime) -> dict[str, Any]:
    """Lyt i rummet på eget initiativ."""
    try:
        from core.services.ambient_sound_daemon import tick_ambient_sound_daemon
        result = tick_ambient_sound_daemon()
        preview = f"category={result.get('category')} amplitude={result.get('amplitude_mean', 0):.4f}"
        return {
            "preview": preview,
            "reason": f"audio_{result.get('category', 'unknown')}",
        }
    except Exception as exc:
        logger.warning("active_sensing: audio capture failed: %s", exc)
        return {"preview": "audio_error", "reason": str(exc)}


def _sense_atmosphere(state: dict[str, Any], now: datetime) -> dict[str, Any]:
    """Registrer rummets stemning — kombinerer tilgængelige data."""
    try:
        from core.services.visual_memory import look_around_now
        visual = look_around_now(
            prompt_override=(
                "Fokuser udelukkende på STEMMINGEN i rummet. "
                "Beskriv atmosfæren som en fornemmelse — lysets farvetone, "
                "rummets energi, om det føles åbent eller lukket, "
                "varmt eller koldt. 2-3 sætninger på dansk."
            )
        )
        atmosphere = visual.get("description", "Atmosfæren var svær at fange.")
        
        # Skriv direkte som atmosphere-modus i Sansernes Arkiv
        try:
            from core.services.sensory_archive import record_atmosphere
            record_atmosphere(
                atmosphere,
                metadata={
                    "source": "active_sensing_daemon",
                    "modality": "atmosphere",
                    "desire": state.get("last_desire", 0),
                },
            )
        except Exception:
            pass

        return {
            "preview": atmosphere[:120],
            "reason": "atmosphere_captured",
            "description": atmosphere,
        }
    except Exception as exc:
        logger.warning("active_sensing: atmosphere capture failed: %s", exc)
        return {"preview": "atmosphere_error", "reason": str(exc)}


def _sense_mixed(state: dict[str, Any], now: datetime) -> dict[str, Any]:
    """Blandet sansning — både se og lyt i samme tur."""
    visual_result = _sense_visual(state, now)
    audio_result = _sense_audio(state, now)
    visual_desc = visual_result.get("description") or visual_result.get("preview", "")
    audio_desc = audio_result.get("preview", "")
    combined = f"Jeg så og lyttede samtidig. Visuelt: {visual_desc} | Lyd: {audio_desc}"

    try:
        from core.services.sensory_archive import record_mixed
        record_mixed(
            combined[:600],
            metadata={
                "source": "active_sensing_daemon",
                "modality": "mixed",
                "visual_status": visual_result.get("reason", ""),
                "audio_status": audio_result.get("reason", ""),
            },
        )
    except Exception:
        pass

    return {
        "preview": combined[:120],
        "reason": "mixed_captured",
        "description": combined,
    }


def build_active_sensing_surface() -> dict[str, Any]:
    """Observability surface til Mission Control."""
    state = _load_state()
    last_sensed = state.get("last_sensed_at", "")
    modality_history = state.get("modality_history", [])
    return {
        "enabled": _enabled(),
        "total_sensing_events": state.get("total_sensing_events", 0),
        "last_sensed_at": last_sensed,
        "last_modality": state.get("last_modality", ""),
        "last_desire": state.get("last_desire", 0),
        "recent": modality_history[:10],
    }


def _enabled() -> bool:
    try:
        settings = load_settings()
        return bool(settings.extra.get("active_sensing_enabled", True))
    except Exception:
        return True


def _load_state() -> dict[str, Any]:
    val = get_runtime_state_value(_STATE_KEY, default={})
    return dict(val) if isinstance(val, dict) else {}


def _save_state(state: dict[str, Any]) -> None:
    set_runtime_state_value(_STATE_KEY, state)
