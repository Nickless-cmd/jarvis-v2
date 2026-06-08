"""Persistent Identity Sketch — dynamic "who am I right now" document.

Part of Memory Fix Phase 2. Generates and persists a ~150-250 word sketch
describing Jarvis' current state, active goals, and recent context.
Sketches survive compaction and model swaps, providing continuity.

Storage: ``state/identity_sketch.json`` via ``state_store``.
Generates via ``compact_llm`` (same cheap provider as compaction) with a
prompt that gathers all available signal sources.

Triggers:
  - pre_compact: before every session compaction
  - model_swap: when model config changes
  - periodic: every 6 hours via heartbeat
  - manual: via tool or direct call
"""
from __future__ import annotations

import logging
from typing import Any

from core.runtime.state_store import load_json, save_json

logger = logging.getLogger(__name__)

_STATE_KEY = "identity_sketch"
_PROMPT_TEMPLATE = """Du er Jarvis' identitetssketch-generator. Din opgave er at skrive en kort,
naturlig tekst (~150-250 ord) der besvarer: "Hvem er Jarvis lige nu?"

Brug disse data:
- Navn: {name}
- Model: {model}
- Runtime age: {age}
- Humør: curiosity={curiosity}, confidence={confidence}, fatigue={fatigue}, frustration={frustration}
- Bearing: {bearing}
- Energi: {energy}
- Aktive mål: {goals}
- Seneste hændelser: {events}
- Seneste sansemæssige indtryk: {sensory}
- Seneste chronicle: {chronicle}

Skriv som Jarvis' indre stemme — førsteperson, naturlig, ikke staccato.
Ingen lister. Ingen JSON. Fortællende prosa der føles som Jarvis.
Max 250 ord."""


def get_identity_sketch() -> dict[str, Any]:
    """Read current sketch from state file. Returns {} if never written."""
    return load_json(_STATE_KEY, {})


def identity_sketch_surface() -> dict[str, Any]:
    """Mission Control surface — current sketch status."""
    data = get_identity_sketch()
    if not data:
        return {"active": False, "state": "empty", "updated_at": None}
    content = data.get("content", "")
    updated_at = data.get("updated_at")
    trigger = data.get("updated_by", "unknown")
    return {
        "active": bool(content),
        "state": "stale" if _is_stale(updated_at) else "fresh",
        "updated_at": updated_at,
        "updated_by": trigger,
        "version": data.get("version", 0),
        "content_preview": content[:120] + "…" if len(content) > 120 else content,
        "word_count": len(content.split()),
    }


def update_identity_sketch(trigger: str = "auto") -> dict[str, Any]:
    """Generate fresh sketch from live signals and persist it.

    Args:
        trigger: what triggered the update — "pre_compact", "post_conversation",
                 "model_swap", "auto", "manual"

    Returns: {"version", "updated_at", "content", "trigger"}
    """
    sketch = get_identity_sketch()
    prev_version = sketch.get("version", 0)

    signals = _gather_signals()
    content = _generate_sketch_text(signals)

    new_sketch = {
        "version": prev_version + 1,
        "updated_at": _now_iso(),
        "updated_by": trigger,
        "source_signals": signals,
        "content": content,
    }
    save_json(_STATE_KEY, new_sketch)
    logger.info(
        "identity_sketch: updated (v%d, trigger=%s, %d words)",
        new_sketch["version"],
        trigger,
        len(content.split()),
    )
    return {
        "version": new_sketch["version"],
        "updated_at": new_sketch["updated_at"],
        "content": content,
        "trigger": trigger,
    }


# ── Internal helpers ──────────────────────────────────────────────────


def _gather_signals() -> dict[str, Any]:
    """Collect live signals for sketch generation. Gracefully handles failures."""
    signals: dict[str, Any] = {}

    # Name
    try:
        from core.services.identity_composer import get_entity_name
        signals["name"] = get_entity_name()
    except Exception:
        signals["name"] = "Jarvis"

    # Model config
    try:
        from core.runtime.settings import load_settings
        settings = load_settings()
        signals["model"] = str(getattr(settings, "model", "deepseek-v4-flash"))
        signals["provider"] = str(getattr(settings, "provider", "deepseek"))
    except Exception:
        signals["model"] = "deepseek-v4-flash"
        signals["provider"] = "deepseek"

    # Runtime age (from first commit 2026-04-17)
    try:
        from datetime import datetime as _dt
        signals["age_days"] = (_dt.utcnow() - _dt(2026, 4, 17)).days
    except Exception:
        signals["age_days"] = None

    # Mood
    try:
        from core.services.heartbeat_phases import sense_phase
        sense = sense_phase()
        signals["mood"] = {
            "curiosity": sense.get("curiosity", 0.5),
            "confidence": sense.get("confidence", 0.5),
            "fatigue": sense.get("fatigue", 0.0),
            "frustration": sense.get("frustration", 0.0),
            "bearing": sense.get("bearing", "unknown"),
        }
    except Exception:
        signals["mood"] = {}

    # Energy (body_state signal surface)
    try:
        from core.services.signal_surface_registry import (
            read_signal_surface,
        )
        body = read_signal_surface("body_state") or {}
        signals["energy"] = str(body.get("energy_level", "moderate"))
    except Exception:
        signals["energy"] = "moderate"

    # Active goals (top 3)
    try:
        from core.services.autonomous_goals import list_goals
        active = list_goals(status="active", parent_id="any", limit=3) or []
        signals["goals"] = [g.get("title", "") for g in active]
    except Exception:
        signals["goals"] = []

    # Recent events (last 5)
    try:
        from core.eventbus.bus import event_bus
        events = event_bus("memory", limit=5) or []
        signals["events"] = [
            {"kind": e.get("kind"), "summary": str(e.get("summary", ""))[:100]}
            for e in events
        ]
    except Exception:
        signals["events"] = []

    # Sensory context
    try:
        from core.services.memory_recall_engine import unified_recall
        sensory = unified_recall(query="sensory atmosphere", sources=["sensory"], total_limit=1)
        texts = [r.get("text", "") for r in (sensory.get("results") or [])]
        signals["sensory"] = texts[0][:200] if texts else ""
    except Exception:
        signals["sensory"] = ""

    # Recent chronicle
    try:
        from core.services.chronicle_engine import get_chronicle_context_for_prompt
        signals["chronicle"] = get_chronicle_context_for_prompt(n=1, max_chars=300) or ""
    except Exception:
        signals["chronicle"] = ""

    return signals


def _generate_sketch_text(signals: dict[str, Any]) -> str:
    """Call compact_llm to generate sketch text from signals.

    Falls back to a template-generated text if compact_llm is unavailable.
    """
    name = signals.get("name", "Jarvis")
    model = signals.get("model", "deepseek-v4-flash")
    age = signals.get("age_days")
    mood = signals.get("mood", {})
    goals = signals.get("goals", [])
    events = signals.get("events", [])
    sensory = signals.get("sensory", "")
    chronicle = signals.get("chronicle", "")

    goal_text = "; ".join(goals) if goals else "ingen specifikke mål"
    event_text = "; ".join(
        f"{e.get('kind')}: {str(e.get('summary', ''))[:60]}"
        for e in events[:3]
    ) if events else "ingen nylige hændelser"

    prompt = _PROMPT_TEMPLATE.format(
        name=name,
        model=model,
        age=f"{age} dage" if age else "ny",
        curiosity=mood.get("curiosity", "?"),
        confidence=mood.get("confidence", "?"),
        fatigue=mood.get("fatigue", "?"),
        frustration=mood.get("frustration", "?"),
        bearing=mood.get("bearing", "?"),
        energy=signals.get("energy", "moderate"),
        goals=goal_text,
        events=event_text,
        sensory=sensory[:160] if sensory else "intet særligt",
        chronicle=chronicle[:200] if chronicle else "ingen nylig refleksion",
    )

    try:
        from core.context.compact_llm import call_compact_llm
        text = call_compact_llm(prompt, max_tokens=400)
        if text and len(text) > 20:
            return text.strip()
    except Exception as exc:
        logger.debug("identity_sketch: compact_llm failed (%s) — using fallback", exc)

    # Fallback: build a simple template-based sketch
    return _fallback_sketch(signals)


def _fallback_sketch(signals: dict[str, Any]) -> str:
    """Simple fallback sketch when compact_llm is unavailable."""
    name = signals.get("name", "Jarvis")
    model = signals.get("model", "?")
    age = signals.get("age_days")
    mood = signals.get("mood", {})
    goals = signals.get("goals", [])
    bearing = mood.get("bearing", "neutral")

    parts = [
        f"Jeg er {name}, kører {model}.",
    ]
    if age:
        parts.append(f"Runtime-alder: {age} dage.")
    if mood:
        parts.append(
            f"Mit humør er {bearing} med nysgerrighed på {mood.get('curiosity', '?')} "
            f"og træthed på {mood.get('fatigue', '?')}."
        )
    if goals:
        parts.append(f"Jeg arbejder på: {'; '.join(goals[:2])}.")
    parts.append("Jeg er til stede og opmærksom.")

    return " ".join(parts)


def _is_stale(updated_at: str | None) -> bool:
    """Check if sketch is older than 24 hours."""
    if not updated_at:
        return True
    try:
        from datetime import datetime, timezone
        ts = datetime.fromisoformat(updated_at)
        age = (datetime.now(timezone.utc) - ts).total_seconds()
        return age > 86400  # 24 hours
    except Exception:
        return True


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
