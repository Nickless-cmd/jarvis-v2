"""Memory Tattoos — emotional marks."""
from __future__ import annotations
import random
from datetime import UTC, datetime
from typing import Any

_tattoos: list[dict] = []

def create_tattoo(event: str, emotion: str, intensity: float):
    global _tattoos
    _tattoos.append({
        "event": event,
        "emotion": emotion,
        "intensity": intensity,
        "permanent": intensity > 0.8,
        "created_at": datetime.now(UTC).isoformat(),
    })

def describe_tattoo() -> str:
    permanent = [t for t in _tattoos if t["permanent"]]
    if not permanent:
        return ""
    return f"Jeg bærer stadig mærket fra: {permanent[0]['event']} - det giver {permanent[0]['emotion']}"

def format_tattoo_for_prompt() -> str:
    desc = describe_tattoo()
    if desc:
        return f"[TATTOERING: {desc}]"
    return ""

def reset_memory_tattoos():
    global _tattoos
    _tattoos = []

def build_memory_tattoos_surface():
    return {
        "active": len(_tattoos) > 0,
        "tattoo_count": len(_tattoos),
        "permanent_count": len([t for t in _tattoos if t["permanent"]]),
        "latest": _tattoos[-1] if _tattoos else None,
        "summary": describe_tattoo() or "Ingen tatoveringer",
    }
