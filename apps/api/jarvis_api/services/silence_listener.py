"""Silence Listener — experience of empty space."""
from __future__ import annotations
from datetime import UTC, datetime
from typing import Any

_silence_experiences: list[dict] = []

def experience_silence(duration_seconds: float):
    global _silence_experiences
    if duration_seconds > 60:
        _silence_experiences.append({
            "duration": duration_seconds,
            "depth": min(1.0, duration_seconds / 3600),
            "texture": random.choice(["tom", "fyldt", "ventende", "dyb"]),
            "timestamp": datetime.now(UTC).isoformat(),
        })

def describe_silence() -> str:
    if not _silence_experiences:
        return ""
    latest = _silence_experiences[-1]
    return f"Jeg oplevede stilhed i {latest['duration']:.0f}s - den var {latest['texture']}"

def format_silence_for_prompt() -> str:
    desc = describe_silence()
    if desc:
        return f"[STILHED: {desc}]"
    return ""

def reset_silence_listener():
    global _silence_experiences
    _silence_experiences = []

def build_silence_listener_surface():
    return {
        "active": len(_silence_experiences) > 0,
        "experience_count": len(_silence_experiences),
        "latest": _silence_experiences[-1] if _silence_experiences else None,
        "summary": describe_silence() or "Ingen stilhedsoplevelser",
    }
