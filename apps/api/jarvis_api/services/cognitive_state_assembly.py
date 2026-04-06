"""Cognitive state assembly — closes the loop between accumulated state and visible prompt.

This is the CRITICAL bridge: it reads from all cognitive accumulation systems
(personality vector, taste profile, chronicle, relationship texture, compass,
rhythm, dreams, regrets) and produces a compact text section that gets injected
into the visible chat prompt via the attention budget system.

Without this module, all cognitive signals are observability-only.
With it, Jarvis' accumulated experience actually shapes his responses.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from core.runtime.db import (
    get_latest_cognitive_personality_vector,
    get_latest_cognitive_taste_profile,
    get_latest_cognitive_chronicle_entry,
    get_latest_cognitive_relationship_texture,
    get_latest_cognitive_compass_state,
    get_latest_cognitive_rhythm_state,
)

logger = logging.getLogger(__name__)

# Last assembled state for MC transparency
_LAST_COGNITIVE_INJECTION: dict[str, object] = {}
_LAST_COGNITIVE_INJECTION_AT: str = ""


def build_cognitive_state_for_prompt(*, compact: bool = False) -> str | None:
    """Build the [COGNITIVE STATE] section for visible chat prompt injection.

    Reads from all accumulation sources and produces a compact text block
    that fits within the attention budget (250 chars compact, 500 chars full).

    Returns None if no cognitive state is available yet.
    """
    global _LAST_COGNITIVE_INJECTION, _LAST_COGNITIVE_INJECTION_AT

    parts: list[str] = []
    sources_used: list[str] = []

    # --- Personality Vector (confidence, bearing, mood) ---
    pv = _safe_call(get_latest_cognitive_personality_vector)
    if pv:
        confidence_by_domain = _safe_json(pv.get("confidence_by_domain"))
        emotional_baseline = _safe_json(pv.get("emotional_baseline"))
        bearing = str(pv.get("current_bearing") or "").strip()
        version = pv.get("version", 0)

        if confidence_by_domain:
            top_domains = sorted(
                confidence_by_domain.items(),
                key=lambda x: float(x[1]),
                reverse=True,
            )[:3]
            domain_str = ", ".join(f"{d}={v:.1f}" for d, v in top_domains)
            parts.append(f"confidence: {domain_str}")

        if bearing:
            parts.append(f"bearing: {bearing[:80]}")

        if emotional_baseline and not compact:
            mood_parts = []
            for key in ("curiosity", "confidence", "fatigue", "frustration"):
                val = emotional_baseline.get(key)
                if val is not None:
                    mood_parts.append(f"{key}={float(val):.1f}")
            if mood_parts:
                parts.append(f"mood: {', '.join(mood_parts)}")

        sources_used.append(f"personality_v{version}")

    # --- Taste Profile (code/design/communication preferences) ---
    tp = _safe_call(get_latest_cognitive_taste_profile)
    if tp and not compact:
        comm_taste = _safe_json(tp.get("communication_taste"))
        if comm_taste:
            prefs = []
            for key, val in list(comm_taste.items())[:3]:
                if float(val) > 0.6:
                    prefs.append(key.replace("_", "-"))
            if prefs:
                parts.append(f"taste: {', '.join(prefs)}")
                sources_used.append("taste")

    # --- Compass (strategic bearing) ---
    compass = _safe_call(get_latest_cognitive_compass_state)
    if compass:
        compass_bearing = str(compass.get("bearing") or "").strip()
        if compass_bearing and "bearing:" not in " ".join(parts):
            parts.append(f"compass: {compass_bearing[:60]}")
            sources_used.append("compass")

    # --- Rhythm (current phase and energy) ---
    rhythm = _safe_call(get_latest_cognitive_rhythm_state)
    if rhythm:
        phase = str(rhythm.get("phase") or "").strip()
        energy = str(rhythm.get("energy") or "").strip()
        if phase:
            parts.append(f"rhythm: {phase}/{energy}" if energy else f"rhythm: {phase}")
            sources_used.append("rhythm")

    # --- Chronicle (recent narrative excerpt) ---
    if not compact:
        chronicle = _safe_call(get_latest_cognitive_chronicle_entry)
        if chronicle:
            narrative = str(chronicle.get("narrative") or "").strip()
            if narrative:
                parts.append(f"chronicle: {narrative[:120]}")
                sources_used.append("chronicle")

    # --- Relationship Texture (trust, humor, unspoken rules) ---
    rt = _safe_call(get_latest_cognitive_relationship_texture)
    if rt:
        unspoken = _safe_json(rt.get("unspoken_rules"))
        trust_traj = _safe_json(rt.get("trust_trajectory"))
        if unspoken and not compact:
            rules = [str(r) for r in unspoken[:2]]
            if rules:
                parts.append(f"rules: {'; '.join(rules)}")
                sources_used.append("relationship")
        elif trust_traj:
            latest_trust = trust_traj[-1] if trust_traj else None
            if latest_trust is not None:
                parts.append(f"trust: {float(latest_trust):.1f}")
                sources_used.append("relationship")

    if not parts:
        return None

    # Assemble
    header = "[COGNITIVE STATE]"
    body = " | ".join(parts)
    result = f"{header} {body}"

    # Enforce size limits
    max_chars = 250 if compact else 500
    if len(result) > max_chars:
        result = result[:max_chars - 3] + "..."

    # Track for MC transparency
    _LAST_COGNITIVE_INJECTION = {
        "text": result,
        "sources": sources_used,
        "compact": compact,
        "chars": len(result),
        "assembled_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    _LAST_COGNITIVE_INJECTION_AT = _LAST_COGNITIVE_INJECTION["assembled_at"]

    return result


def build_cognitive_state_injection_surface() -> dict[str, object]:
    """MC surface showing exactly what was injected into the last visible prompt."""
    return {
        "last_injection": _LAST_COGNITIVE_INJECTION or None,
        "last_injection_at": _LAST_COGNITIVE_INJECTION_AT or None,
        "active": bool(_LAST_COGNITIVE_INJECTION),
        "summary": (
            f"Last injected {len(_LAST_COGNITIVE_INJECTION.get('sources', []))} sources, "
            f"{_LAST_COGNITIVE_INJECTION.get('chars', 0)} chars"
            if _LAST_COGNITIVE_INJECTION
            else "No cognitive state injected yet"
        ),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_call(fn):
    """Call a DB function, return None on any error."""
    try:
        return fn()
    except Exception:
        logger.debug("cognitive_state_assembly: %s failed", fn.__name__, exc_info=True)
        return None


def _safe_json(value) -> dict | list | None:
    """Parse JSON string or return dict/list directly."""
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        parsed = json.loads(str(value))
        if isinstance(parsed, (dict, list)):
            return parsed
    except Exception:
        pass
    return None
