"""Identity Composer — entity name lookup and signal-driven preamble.

get_entity_name(): reads Name: from workspace/default/IDENTITY.md, lazy cached.
build_identity_preamble(): returns "{name}. {bearing}. {energy}." from live signals.
"""
from __future__ import annotations

import re
from pathlib import Path

from core.runtime.config import WORKSPACES_DIR

_IDENTITY_FILE = WORKSPACES_DIR / "default" / "IDENTITY.md"
_FALLBACK_NAME = "the entity"

_name_cache: str | None = None


def get_entity_name() -> str:
    """Return the entity name from IDENTITY.md. Cached after first read."""
    global _name_cache
    if _name_cache is None:
        _name_cache = _parse_name_from_identity()
    return _name_cache


def _parse_name_from_identity() -> str:
    try:
        text = _IDENTITY_FILE.read_text(encoding="utf-8")
        for line in text.splitlines():
            m = re.match(r"^Name:\s*(.+)", line.strip())
            if m:
                return m.group(1).strip()
    except Exception:
        pass
    return _FALLBACK_NAME


def _read_bearing() -> str:
    """Read current_bearing from personality vector. Returns '' on failure."""
    try:
        from core.runtime.db import get_latest_cognitive_personality_vector
        pv = get_latest_cognitive_personality_vector()
        return str((pv or {}).get("current_bearing") or "").strip()
    except Exception:
        return ""


def _read_energy() -> str:
    """Read energy_level from body_state surface. Returns '' on failure."""
    try:
        from apps.api.jarvis_api.services.signal_surface_router import read_surface
        body = read_surface("body_state")
        return str(body.get("energy_level") or "").strip()
    except Exception:
        return ""


def build_identity_preamble() -> str:
    """Return signal-driven identity string: '{name}. {bearing}. {energy}.'

    Falls back gracefully if signals are unavailable — always returns at least '{name}.'.
    Uses tick_cache when active to avoid rebuilding 12+ times per heartbeat tick.
    """
    try:
        from apps.api.jarvis_api.services import tick_cache
        cached = tick_cache.get("identity_preamble")
        if cached is not None:
            return cached
    except Exception:
        pass

    name = get_entity_name()
    parts = [name]
    bearing = _read_bearing()
    if bearing:
        parts.append(bearing)
    energy = _read_energy()
    if energy:
        parts.append(f"Energi: {energy}")
    result = ". ".join(parts) + "."

    try:
        from apps.api.jarvis_api.services import tick_cache
        tick_cache.set("identity_preamble", result)
    except Exception:
        pass

    return result
