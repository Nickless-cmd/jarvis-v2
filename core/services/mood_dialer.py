"""Mood Dialer — humør til gradueret initiativ-parametre.

Konverterer mood_level (0-4) til konkrete adfærds-parametre:
- initiative_multiplier — hvor meget Jarvis "pusher" på egne tanker
- confidence_threshold — hvor sikker skal han være før handling
- max_steps / max_tool_calls — hvor dybt kører han selvstændigt
- auto_execute_small_tasks — må han handle uden approval på små ting
- style_preset — passive / balanced / agentic

Komplementerer emotional_controls (binære gates) med gradueret tuning.

Porteret fra jarvis-ai/agent/mood_dialer.py (2026-04-22).

v2-tilpasning: mapper v2's mood (euphoric/content/neutral/melancholic/
distressed) til level 0-4 i stedet for direkte level-int.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MoodDialerParams:
    mood_level: int
    initiative_multiplier: float
    confidence_threshold: float
    max_steps: int
    max_tool_calls: int
    tick_interval_sec: int
    cooldown_sec: int
    auto_execute_small_tasks: bool
    requires_confirmation: bool
    style_preset: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "mood_level": int(self.mood_level),
            "initiative_multiplier": float(self.initiative_multiplier),
            "confidence_threshold": float(self.confidence_threshold),
            "max_steps": int(self.max_steps),
            "max_tool_calls": int(self.max_tool_calls),
            "tick_interval_sec": int(self.tick_interval_sec),
            "cooldown_sec": int(self.cooldown_sec),
            "auto_execute_small_tasks": bool(self.auto_execute_small_tasks),
            "requires_confirmation": bool(self.requires_confirmation),
            "style_preset": str(self.style_preset),
        }


def clamp_mood_level(value: Any) -> int:
    if isinstance(value, bool):
        return 2
    if isinstance(value, (int, float)):
        return max(0, min(4, int(value)))
    return 2


# v2-mapping: mood name → level
_MOOD_NAME_TO_LEVEL = {
    "distressed": 0,
    "melancholic": 1,
    "neutral": 2,
    "content": 3,
    "euphoric": 4,
}


def mood_name_to_level(mood_name: str, intensity: float = 0.5) -> int:
    """Convert v2 mood oscillator name + intensity to 0-4 level.

    Intensity boosts/dampens: if mood=content and intensity=0.9,
    we nudge toward euphoric (level 4).
    """
    base = _MOOD_NAME_TO_LEVEL.get(str(mood_name or "").strip().lower(), 2)
    try:
        i = float(intensity or 0.0)
    except Exception:
        i = 0.5
    # intensity > 0.8 nudges toward extremes
    if i > 0.8:
        if base >= 3:
            return min(4, base + 1)
        if base <= 1:
            return max(0, base - 1)
    return base


_PRESETS: dict[int, MoodDialerParams] = {
    0: MoodDialerParams(
        mood_level=0, initiative_multiplier=0.0, confidence_threshold=0.95,
        max_steps=1, max_tool_calls=1,
        tick_interval_sec=180, cooldown_sec=10_800,
        auto_execute_small_tasks=False, requires_confirmation=True,
        style_preset="passive",
    ),
    1: MoodDialerParams(
        mood_level=1, initiative_multiplier=0.55, confidence_threshold=0.82,
        max_steps=2, max_tool_calls=2,
        tick_interval_sec=120, cooldown_sec=5_400,
        auto_execute_small_tasks=False, requires_confirmation=True,
        style_preset="passive",
    ),
    2: MoodDialerParams(
        mood_level=2, initiative_multiplier=1.0, confidence_threshold=0.72,
        max_steps=4, max_tool_calls=4,
        tick_interval_sec=60, cooldown_sec=2_700,
        auto_execute_small_tasks=False, requires_confirmation=True,
        style_preset="balanced",
    ),
    3: MoodDialerParams(
        mood_level=3, initiative_multiplier=1.28, confidence_threshold=0.64,
        max_steps=6, max_tool_calls=6,
        tick_interval_sec=45, cooldown_sec=1_800,
        auto_execute_small_tasks=True, requires_confirmation=False,
        style_preset="agentic",
    ),
    4: MoodDialerParams(
        mood_level=4, initiative_multiplier=1.55, confidence_threshold=0.58,
        max_steps=8, max_tool_calls=8,
        tick_interval_sec=30, cooldown_sec=900,
        auto_execute_small_tasks=True, requires_confirmation=False,
        style_preset="agentic",
    ),
}


def derive_mood_dialer_params(mood_level: Any) -> MoodDialerParams:
    """Derive concrete params from a 0-4 mood level."""
    level = clamp_mood_level(mood_level)
    return _PRESETS[level]


def derive_from_v2_mood() -> MoodDialerParams:
    """Pull current mood from mood_oscillator and derive params.

    Single-call integration for callers who just want current-state params.
    """
    try:
        from core.services.mood_oscillator import get_current_mood, get_mood_intensity
        name = str(get_current_mood() or "neutral")
        intensity = float(get_mood_intensity() or 0.0)
    except Exception:
        name = "neutral"
        intensity = 0.0
    level = mood_name_to_level(name, intensity=intensity)
    return derive_mood_dialer_params(level)


def build_mood_dialer_surface() -> dict[str, Any]:
    """MC surface — current dialed params."""
    params = derive_from_v2_mood()
    return {
        "active": True,
        "summary": (
            f"level={params.mood_level} / style={params.style_preset} / "
            f"initiative×{params.initiative_multiplier:.2f} / "
            f"confidence≥{params.confidence_threshold:.2f} / "
            f"max_steps={params.max_steps}"
        ),
        "params": params.as_dict(),
        "interpretation": _interpret_dialer(params),
    }


def _interpret_dialer(params: MoodDialerParams) -> str:
    """Natural-language explanation of what these params mean right now."""
    if params.style_preset == "agentic":
        return (
            "Jarvis er i agentic mode — tager selv initiativ, kører flere "
            f"skridt ({params.max_steps}) uden at spørge om små ting."
        )
    if params.style_preset == "passive":
        return (
            "Jarvis er i passive mode — venter på dig, tager minimal "
            f"initiativ, kræver bekræftelse. Max {params.max_steps} skridt."
        )
    return (
        "Jarvis er balanced — moderat initiativ, bekræftelse på større skridt. "
        f"Op til {params.max_steps} skridt per opgave."
    )
