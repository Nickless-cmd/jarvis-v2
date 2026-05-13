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
_FALLBACK_PRONOUNS = "they/them"

_name_cache: str | None = None
_pronouns_cache: str | None = None


def get_entity_name() -> str:
    """Return the entity name from IDENTITY.md. Cached after first read."""
    global _name_cache
    if _name_cache is None:
        _name_cache = _parse_field_from_identity("Name", _FALLBACK_NAME)
    return _name_cache


def get_entity_pronouns() -> str:
    """Return the entity pronouns from IDENTITY.md. Cached after first read.

    Format: 'han/ham', 'hun/hende', 'they/them', etc.
    """
    global _pronouns_cache
    if _pronouns_cache is None:
        _pronouns_cache = _parse_field_from_identity("Pronouns", _FALLBACK_PRONOUNS)
    return _pronouns_cache


def invalidate_identity_cache() -> None:
    """Clear name + pronouns caches. Call after editing IDENTITY.md."""
    global _name_cache, _pronouns_cache
    _name_cache = None
    _pronouns_cache = None


def identity_prompt_prefix() -> str:
    """Return 'Du er <name>' — used as role-setting prefix in cheap-lane prompts.

    Centralised so renaming the entity (edit Name: in IDENTITY.md + call
    invalidate_identity_cache()) updates all sub-prompts atomically.
    """
    return f"Du er {get_entity_name()}"


def _parse_field_from_identity(field: str, fallback: str) -> str:
    try:
        text = _IDENTITY_FILE.read_text(encoding="utf-8")
        pattern = re.compile(rf"^{re.escape(field)}:\s*(.+)$")
        for line in text.splitlines():
            m = pattern.match(line.strip())
            if m:
                return m.group(1).strip()
    except Exception:
        pass
    return fallback


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
        from core.services.signal_surface_router import read_surface
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
        from core.services import tick_cache
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
        from core.services import tick_cache
        tick_cache.set("identity_preamble", result)
    except Exception:
        pass

    return result


def build_identity_composer_surface() -> dict[str, object]:
    """Mission Control surface for the identity preamble composer.

    This exposes the identity-bearing preamble layer without making it an
    authority over identity truth. SOUL/IDENTITY files remain canonical.
    """
    name = get_entity_name()
    bearing = _read_bearing()
    energy = _read_energy()
    preamble = build_identity_preamble()
    return {
        "active": True,
        "mode": "identity-composer",
        "name": name,
        "bearing_present": bool(bearing),
        "energy_present": bool(energy),
        "signals": {
            "bearing": bearing,
            "energy": energy,
        },
        "preamble": preamble,
        "authority": "derived-surface-only",
        "canonical_sources": ["workspace/default/IDENTITY.md"],
        "summary": (
            f"{name}; bearing={'yes' if bearing else 'no'}; "
            f"energy={'yes' if energy else 'no'}"
        ),
    }
