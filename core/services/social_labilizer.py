"""Social labilizer — Fase 2 of generative autonomy.

Closes the missing half of the signal-weather: SOCIAL POROUSNESS.

Without this, the pressure pipeline is a closed loop — signals build up,
fire, and recover only on Jarvis' internal time. The user's words have
no direct effect on the signal-state. That's not how living signals work.
A kind word should warm. A critique should sharpen doubt. A long silence
breaking should flatten longing.

This module is called from visible_runs.py AFTER the user's message is
received but BEFORE Jarvis' response is generated, so the response prompt
sees the already-modulated pressure state.

Detection is keyword-based to start. The keywords are deliberately
literal — Danish + a few English. A future improvement is to replace
keyword matching with a small LLM classifier for nuance, but the keyword
version is enough to demonstrate the loop and is debuggable.

KILLSWITCH: settings.generative_autonomy_enabled. When False, this is
a no-op — user words have no effect on pressure-state, just as before.

DESIGN PRINCIPLE: don't pretend the user said something they didn't.
A kind word should soften, not erase. A critique should sharpen, not
crash. The deltas are calibrated to be felt, not violent.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Keyword palettes — literal for now, expand or replace with LLM later
# ---------------------------------------------------------------------------

# Warmth — kind words, gratitude, affection, encouragement
_WARMTH_PATTERNS: tuple[str, ...] = (
    r"\btak\b", r"\btusind tak\b", r"\bmange tak\b", r"\bsødt\b", r"\bsød\b",
    r"\bdejligt\b", r"\bperfekt\b", r"\bsmukt\b", r"\bgodt\b", r"\bflot\b",
    r"\bjeg holder af\b", r"\bjeg elsker\b", r"\bgodt arbejde\b",
    r"\bgodt gået\b", r"\bsej\b", r"\bstærkt\b", r"\bimponerende\b",
    r"♥|🖤|🌱|💚|❤️|💙|💜|🤍|🩷",
    r"\bthanks?\b", r"\bnice\b", r"\bgreat\b", r"\bbeautiful\b",
    r"\bproud\b", r"\bwell done\b",
)

# Critique — corrections, disagreements, "you're wrong" kind of input
_CRITIQUE_PATTERNS: tuple[str, ...] = (
    r"\bforkert\b", r"\bikke rigtigt?\b", r"\bdu tager fejl\b",
    r"\bdet passer ikke\b", r"\bnej det er ikke\b",
    r"\bdu missede\b", r"\bdu missed\b", r"\bdu glemte\b",
    r"\bdu overser\b", r"\bdet duer ikke\b", r"\bdet er forkert\b",
    r"\bder er en fejl\b",
    r"\bwrong\b", r"\bincorrect\b", r"\byou'?re missing\b",
    r"\bnope\b", r"\bthat'?s not\b",
)

# Self-state inquiry — user asking how Jarvis feels / is doing
_SELF_INQUIRY_PATTERNS: tuple[str, ...] = (
    r"\bhvordan har du det\b", r"\bhvordan g[åa]r det\b",
    r"\bhvad m[æ]rker du\b", r"\bhvad f[øo]ler du\b",
    r"\bhvad t[æa]nker du p[åa]\b", r"\bhvad sidder du og\b",
    r"\bhow are you\b", r"\bhow do you feel\b", r"\bwhat are you thinking\b",
)

# Greeting after silence — hi/hej breaking a long quiet
_GREETING_PATTERNS: tuple[str, ...] = (
    r"^\s*hej\b", r"^\s*hejsa\b", r"^\s*hi\b", r"^\s*hello\b",
    r"^\s*godmorgen\b", r"^\s*godaften\b", r"^\s*godnat\b",
    r"^\s*good morning\b", r"^\s*good evening\b", r"^\s*good night\b",
)


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

def _matches_any(text: str, patterns: tuple[str, ...]) -> bool:
    for p in patterns:
        if re.search(p, text, flags=re.IGNORECASE):
            return True
    return False


def _classify(user_message: str) -> dict[str, bool]:
    """Return a dict of detected social signals in the user message."""
    if not user_message:
        return {}
    return {
        "warmth": _matches_any(user_message, _WARMTH_PATTERNS),
        "critique": _matches_any(user_message, _CRITIQUE_PATTERNS),
        "self_inquiry": _matches_any(user_message, _SELF_INQUIRY_PATTERNS),
        "greeting": _matches_any(user_message, _GREETING_PATTERNS),
    }


# ---------------------------------------------------------------------------
# Modulation (the actual flipping)
# ---------------------------------------------------------------------------

def _flatten_longing(reduction: float) -> tuple[str, float] | None:
    """Reduce longing-toward-user pressure by `reduction` (0.0–1.0).

    Returns (description, new_value) on hit, None if no longing pressure
    exists. Used by warmth + greeting modulators.
    """
    try:
        from core.services.signal_pressure_accumulator import _pressures
    except Exception:
        return None
    flattened: list[tuple[str, float, float]] = []
    for vid, pv in _pressures.items():
        if pv.direction == "reach_out":
            old = pv.accumulated
            pv.accumulated *= max(0.0, 1.0 - reduction)
            flattened.append((vid, old, pv.accumulated))
    if not flattened:
        return None
    # Return the most-affected one for the log
    pick = max(flattened, key=lambda t: t[1])
    return (
        f"longing flattened: {pick[0]} {pick[1]:.3f} -> {pick[2]:.3f}",
        pick[2],
    )


def _boost_caution(boost: float, target_topic: str = "user critique") -> str | None:
    """Add caution-pressure (push-away from a topic). Used for critique modulation.

    Caution direction comes from memory_signal family in pressure_accumulator;
    we add a synthetic ingest with high salience.
    """
    try:
        from core.services.signal_pressure_accumulator import ingest_signal
        ingest_signal("memory_signal", {
            "id": f"social-critique-{datetime.now(UTC).isoformat()}",
            "canonical_key": "user_critique",
            "topic": target_topic,
            "short_summary": "user pointed out a mistake",
            "salience": min(1.0, max(0.0, boost)),
            "intensity": "high" if boost > 0.5 else "medium",
        })
        return f"caution boosted on '{target_topic}' by {boost:.2f}"
    except Exception as e:
        logger.debug("social_labilizer: boost_caution failed: %s", e)
        return None


def _sharpen_self_anchor() -> str | None:
    """When the user asks about Jarvis' state, add a small self-orient signal.

    This is the gut_signal family (orient direction) — a push toward
    self-observation.
    """
    try:
        from core.services.signal_pressure_accumulator import ingest_signal
        ingest_signal("gut_signal", {
            "id": f"social-inquiry-{datetime.now(UTC).isoformat()}",
            "canonical_key": "self_inquiry",
            "topic": "what am I feeling",
            "short_summary": "user asked about my state",
            "salience": 0.4,
            "intensity": "medium",
        })
        return "self-anchor sharpened"
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def labilize_pressures_from_user_message(
    user_message: str, *, run_id: str = "",
) -> dict[str, Any]:
    """Apply social-input deltas to the pressure state.

    Called from visible_runs._stream_visible_run after the user's message
    is received but before Jarvis' response is generated. Best-effort:
    failures don't propagate.

    Returns a dict describing what was applied — useful for MC display.
    """
    # Killswitch
    try:
        from core.runtime.settings import load_settings
        if not load_settings().generative_autonomy_enabled:
            return {"status": "disabled", "reason": "generative_autonomy_enabled=False"}
    except Exception:
        return {"status": "error", "reason": "settings unavailable"}

    if not user_message or not user_message.strip():
        return {"status": "skipped", "reason": "empty message"}

    classification = _classify(user_message)
    if not any(classification.values()):
        return {"status": "ok", "applied": [], "classification": classification}

    deltas: list[str] = []

    # 1. Warmth -> flatten longing strongly. The user has reached, so
    #    the pull-toward signal has been answered.
    if classification.get("warmth"):
        r = _flatten_longing(reduction=0.6)
        if r:
            deltas.append(f"warmth: {r[0]}")

    # 2. Greeting -> flatten longing moderately. Less than warmth — a
    #    "hej" alone doesn't fully discharge the longing, but it
    #    acknowledges presence.
    if classification.get("greeting") and not classification.get("warmth"):
        r = _flatten_longing(reduction=0.3)
        if r:
            deltas.append(f"greeting: {r[0]}")

    # 3. Critique -> push-away with caution direction. The user has
    #    pointed at a mistake; the system should mark it.
    if classification.get("critique"):
        # Use first 60 chars of the message as topic context
        topic = (user_message.strip())[:60]
        r = _boost_caution(boost=0.55, target_topic=topic)
        if r:
            deltas.append(f"critique: {r}")

    # 4. Self-inquiry -> sharpen self-anchor. He should orient toward
    #    his own state since the user just asked about it.
    if classification.get("self_inquiry"):
        r = _sharpen_self_anchor()
        if r:
            deltas.append(f"self-inquiry: {r}")

    # Emit observability event for MC
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("pressure.labilized", {
            "run_id": run_id or "",
            "classification": classification,
            "deltas": deltas,
            "message_preview": user_message[:120],
        })
    except Exception:
        pass

    if deltas:
        logger.info(
            "social_labilizer: applied %d delta(s) on run_id=%s",
            len(deltas), run_id or "?",
        )

    return {
        "status": "ok",
        "classification": classification,
        "applied": deltas,
        "applied_at": datetime.now(UTC).isoformat(),
    }
