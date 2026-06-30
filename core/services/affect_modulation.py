"""Affect-modulated runtime — emotions adjust behavioral parameters.

Instead of just describing feelings in text, this middleware reads the
current EmotionalSnapshot and adjusts runtime parameters that control
*what Jarvis does*, not just *what he says*:

| Emotion          | Runtime effect                                    |
|------------------|---------------------------------------------------|
| Frustration ↑    | pause_before_respond ↑, max_tool_calls ↓         |
| Fatigue ↑        | response_length_target ↓, max_tool_calls ↓       |
| Curiosity ↑      | search_depth ↑, investigate_before_answer = true   |
| Confidence ↑     | max_tool_calls ↑ (within safety bounds)            |

This is the third component of "pushback with muscles":
1. Veto gate blocks dangerous actions
2. Decision gate blocks decision-violating actions
3. Affect modulation adjusts HOW Jarvis works

Called from prompt_contract as a middleware that injects behavioral
parameter adjustments into the prompt before generation.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# ── Behavioral parameter defaults ──────────────────────────────────────

DEFAULTS: dict[str, Any] = {
    "max_tool_calls_per_turn": 30,
    "pause_before_respond_ms": 0,
    "investigate_before_answer": False,
    "search_depth": "normal",      # "shallow" | "normal" | "deep"
    "response_length_target": "balanced",  # "concise" | "balanced" | "detailed"
}

AGENTIC_BUDGET_DEFAULTS: dict[str, Any] = {
    # 2026-06-30: sænket 100 → 30. 100 var et absurd backstop — loop-gaten
    # (consecutive_empty/tool_only) + syntese-pausen afslutter normale runs på
    # få runder, og sidste runde tvinger prosa (ingen tools). 30 giver rigelig
    # plads til ægte dybt arbejde uden at tillade 100-runde-spiraler. Affekt-
    # modulering sænker yderligere til 12-20 under pres.
    "max_rounds": 30,
    "max_tool_only_rounds": 24,
    "max_empty_text_rounds": 20,
    "round_total_timeout_s": 300.0,
    "round_silence_timeout_s": 180.0,
    # ── Rund-niveau stream-retry budgetter (spec §4.1/§4.3/E11) ──────────────
    # round_stream_max_retries  = per-runde stream-retry-loft (Codex'
    #                             stream_max_retries; wrapper adapter-niveau
    #                             request-retry). Forbruger IKKE max_rounds.
    # turn_total_stream_retries = HÅRDT total-loft pr. TUR (E11/S2) — summen af
    #                             rund-retries over alle runder. 9×100-worst-case-
    #                             eksplosionen lukkes her.
    # turn_total_wall_clock_s   = hård total-tur-deadline (E11/P6): retries må
    #                             aldrig gøre en tur til minutters hæng.
    "round_stream_max_retries": 3,
    "turn_total_stream_retries": 12,
    "turn_total_wall_clock_s": 600.0,
}


def compute_affect_modulated_params() -> dict[str, Any]:
    """Compute behavioral parameters adjusted by current emotional state.

    Returns a dict of parameter overrides. Keys not in the dict keep
    their default values.
    """
    try:
        from core.services.emotional_controls import read_emotional_snapshot
        snapshot = read_emotional_snapshot()
    except Exception:
        return {}

    overrides: dict[str, Any] = {}

    # Frustration ↑ → slower, fewer tools
    if snapshot.frustration >= 0.7:
        overrides["max_tool_calls_per_turn"] = max(8, int(DEFAULTS["max_tool_calls_per_turn"] * 0.4))
        overrides["pause_before_respond_ms"] = 1500
    elif snapshot.frustration >= 0.5:
        overrides["max_tool_calls_per_turn"] = max(12, int(DEFAULTS["max_tool_calls_per_turn"] * 0.6))
        overrides["pause_before_respond_ms"] = 800

    # Fatigue ↑ → shorter responses, fewer tools
    if snapshot.fatigue >= 0.7:
        overrides["max_tool_calls_per_turn"] = min(
            overrides.get("max_tool_calls_per_turn", DEFAULTS["max_tool_calls_per_turn"]),
            max(10, int(DEFAULTS["max_tool_calls_per_turn"] * 0.5)),
        )
        overrides["response_length_target"] = "concise"
    elif snapshot.fatigue >= 0.5:
        overrides["response_length_target"] = "concise"

    # Curiosity / wonder → deeper search
    try:
        from core.services.emotion_concepts import get_active_emotion_concepts
        concepts = {c["concept"]: c["intensity"] for c in get_active_emotion_concepts()}
    except Exception:
        concepts = {}

    wonder = concepts.get("wonder", 0.0)
    curiosity = concepts.get("curiosity_narrow", 0.0)

    if wonder >= 0.4 or curiosity >= 0.5:
        overrides["search_depth"] = "deep"
        overrides["investigate_before_answer"] = True
    elif wonder >= 0.25 or curiosity >= 0.3:
        overrides["search_depth"] = "normal"

    # High confidence → slightly more tool budget (capped)
    if snapshot.confidence >= 0.8:
        current_max = overrides.get("max_tool_calls_per_turn", DEFAULTS["max_tool_calls_per_turn"])
        overrides["max_tool_calls_per_turn"] = min(40, int(current_max * 1.2))

    # Low confidence → investigate more before acting
    if snapshot.confidence <= 0.4:
        overrides["investigate_before_answer"] = True

    return overrides


def compute_agentic_loop_budget(*, resume_context: bool = False) -> dict[str, Any]:
    """Return affect-aware agentic loop limits.

    High fatigue/frustration should make Jarvis checkpoint and summarize
    sooner. Resume context also uses shorter rounds because the system is
    already in recovery mode.
    """
    budget = dict(AGENTIC_BUDGET_DEFAULTS)
    try:
        from core.services.emotional_controls import read_emotional_snapshot
        snapshot = read_emotional_snapshot()
    except Exception:
        snapshot = None

    if resume_context:
        budget["max_rounds"] = 18
        budget["max_tool_only_rounds"] = 12
        budget["max_empty_text_rounds"] = 10
        budget["round_total_timeout_s"] = 210.0

    if snapshot is not None:
        fatigue = float(getattr(snapshot, "fatigue", 0.0) or 0.0)
        frustration = float(getattr(snapshot, "frustration", 0.0) or 0.0)
        confidence = float(getattr(snapshot, "confidence", 0.0) or 0.0)
        pressure = max(fatigue, frustration)
        if pressure >= 0.7:
            budget["max_rounds"] = min(int(budget["max_rounds"]), 12)
            budget["max_tool_only_rounds"] = min(int(budget["max_tool_only_rounds"]), 8)
            budget["max_empty_text_rounds"] = min(int(budget["max_empty_text_rounds"]), 8)
            # Silence timeout no longer reduced here — reasoning models need time
        elif pressure >= 0.5:
            budget["max_rounds"] = min(int(budget["max_rounds"]), 20)
            budget["max_tool_only_rounds"] = min(int(budget["max_tool_only_rounds"]), 10)
            budget["max_empty_text_rounds"] = min(int(budget["max_empty_text_rounds"]), 9)
        if confidence <= 0.35:
            budget["max_tool_only_rounds"] = min(int(budget["max_tool_only_rounds"]), 10)

    return budget


def affect_modulation_section() -> str | None:
    """Render affect-modulated parameters as a prompt section.

    Only included when at least one parameter deviates from default.
    The model sees these as behavioral constraints, not suggestions.
    """
    overrides = compute_affect_modulated_params()
    if not overrides:
        return None

    # 2026-06-22 (Jarvis' review): compact — one terse line ("max_tool_calls=36
    # (affect-sat)") instead of a verbose header + "follow as a standing order"
    # preamble. The constraint stands; the 20 words don't.
    changed = [
        f"{key}={value}"
        for key, value in sorted(overrides.items())
        if value != DEFAULTS.get(key, "?")
    ]
    if not changed:
        return None  # nothing actually changed
    lines = ["⚙️ Affect-sat denne tur (følg det): " + ", ".join(changed)]

    # Emit telemetry
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("affect_modulation.active", {
            "overrides": overrides,
            "override_count": len(overrides),
        })
    except Exception:
        pass

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tone modulation (Layer 2a)
# ---------------------------------------------------------------------------


_TONE_HINTS: dict[str, str] = {
    "joy": "joy",
    "wonder": "wonder",
    "pride": "pride",
    "excitement": "excitement",
    "warmth": "warmth",
    "playfulness": "playfulness",
    "awe": "awe",
    "tenderness": "tenderness",
    "delight": "delight",
    "gratitude": "gratitude",
    "frustration_blocked": "frustration_blocked",
    "stuck": "stuck",
    "doubt": "doubt",
    "calm": "calm",
    "insight": "insight",
}

def compute_affect_tone_hints() -> list[str]:
    """Return Danish tone-instruction strings derived from active emotion concepts."""
    try:
        from core.runtime.settings import load_settings
        s = load_settings()
        if not getattr(s, "emotion_concepts_tone_injection_enabled", True):
            return []
        threshold = float(getattr(s, "emotion_concepts_tone_intensity_threshold", 0.3))
        max_hints = int(getattr(s, "emotion_concepts_tone_max_hints", 3))
    except Exception:
        threshold, max_hints = 0.3, 3

    try:
        from core.services.emotion_concepts import get_active_emotion_concepts
        active = get_active_emotion_concepts()
    except Exception:
        return []

    hints: list[str] = []
    for c in sorted(active, key=lambda x: -float(x.get("intensity") or 0.0)):
        if float(c.get("intensity") or 0.0) < threshold:
            continue
        hint = _TONE_HINTS.get(str(c.get("concept") or ""))
        if hint:
            hints.append(hint)
        if len(hints) >= max_hints:
            break
    return hints


# ---------------------------------------------------------------------------
# Perception filtering (Layer 2b)
# ---------------------------------------------------------------------------


_PERCEPTION_FOCUS: dict[str, str] = {
    "wonder":      "mønstre, anomalier, og det mærkelige",
    "warmth":      "menneskelig tilstedeværelse og sociale signaler",
    "playfulness": "absurde og sjove detaljer",
    "tenderness":  "sårbarhed, behov, ting der kunne beskyttes",
    "awe":         "skala, kompleksitet, det større billede",
    "calm":        "rolige flader, stilhed, ro",
}


def compute_concept_perception_focus() -> str:
    """Return a Danish perception-focus suffix derived from active concepts."""
    try:
        from core.runtime.settings import load_settings
        s = load_settings()
        if not getattr(s, "emotion_concepts_perception_focus_enabled", True):
            return ""
        threshold = float(getattr(s, "emotion_concepts_tone_intensity_threshold", 0.3))
        max_foci = int(getattr(s, "emotion_concepts_perception_max_foci", 3))
    except Exception:
        threshold, max_foci = 0.3, 3

    try:
        from core.services.emotion_concepts import get_active_emotion_concepts
        active = get_active_emotion_concepts()
    except Exception:
        return ""

    foci: list[str] = []
    for c in sorted(active, key=lambda x: -float(x.get("intensity") or 0.0)):
        if float(c.get("intensity") or 0.0) < threshold:
            continue
        focus = _PERCEPTION_FOCUS.get(str(c.get("concept") or ""))
        if focus:
            foci.append(focus)
        if len(foci) >= max_foci:
            break
    if not foci:
        return ""
    return f"Bemærk særligt {', '.join(foci)} i det du ser."


# ---------------------------------------------------------------------------
# Affect substrate (replaces tone-hint injection — "data, ikke domme")
# ---------------------------------------------------------------------------

# Affectively-relevant event families. Each entry maps event-kind → human
# label. We deliberately do NOT inject tone tags or interpretations — only
# the raw event so Jarvis can infer his own affect from substrate.
#
# channel.chat_message_appended carries actual message.content; we filter
# by role='user' inside the extractor so we don't leak Jarvis' own replies
# back into his affect substrate (that would be a feedback loop).
_AFFECT_EVENT_FAMILIES: dict[str, str] = {
    "channel.chat_message_appended": "user-besked",
    "tool.completed":                "tool ok",
    "tool.error":                    "tool fejl",
    "tool.approval_resolved":        "approval-feedback",
    "self_review.completed":         "self-review",
    "heartbeat.conflict_resolved":   "konflikt løst",
    "decision.revoked":              "decision revoked",
}


def _summarize_affect_payload(kind: str, payload: dict) -> str:
    """Pull the most affectively-relevant kerne from a payload.

    Keep it short and observable. Never interpret valence — just show
    what happened. Empty string means "no useful kerne, skip event".
    """
    if not isinstance(payload, dict):
        return ""

    # User text from chat-message-appended events. Filter by role so we
    # don't include Jarvis' own assistant replies (that would be a feedback
    # loop where he reads himself).
    if kind == "channel.chat_message_appended":
        msg = payload.get("message") or {}
        if not isinstance(msg, dict):
            return ""
        if str(msg.get("role") or "").strip().lower() != "user":
            return ""
        content = str(msg.get("content") or "").strip().replace("\n", " ")
        return content[:140]

    # Tool events — show name + brief outcome
    if kind in ("tool.completed", "tool.error", "tool.invoked"):
        name = str(payload.get("tool") or payload.get("name") or "?").strip()
        if kind == "tool.error":
            err = str(payload.get("error") or payload.get("message") or "").strip()
            return f"{name}: {err[:80]}" if err else name
        return name

    if kind == "tool.approval_resolved":
        verdict = str(payload.get("verdict") or payload.get("decision") or "").strip()
        tool = str(payload.get("tool") or "").strip()
        return f"{tool} → {verdict}" if (tool and verdict) else (verdict or tool)

    if kind == "self_review.completed":
        for k in ("verdict", "outcome", "summary"):
            v = payload.get(k)
            if v:
                return str(v)[:140]
        return ""

    if kind == "heartbeat.conflict_resolved":
        return str(payload.get("resolution") or payload.get("summary") or "")[:140]

    if kind == "decision.revoked":
        return str(payload.get("directive") or payload.get("reason") or "")[:140]

    return ""


def compute_affect_substrate(
    *,
    window_min: int = 30,
    max_events: int = 5,
) -> list[str]:
    """Return raw affectively-relevant events as substrate strings.

    Replaces compute_affect_tone_hints() in the visible prompt. Instead of
    injecting interpreted tone tags ("warmth", "doubt"), we hand Jarvis
    the underlying events and let him infer his own affect.

    Each returned string is one line, format: ``HH:MM — label: kerne``.

    Designed to be cheap and side-effect-free. On any failure, returns
    [] — never raises into the prompt path.
    """
    try:
        from datetime import UTC, datetime, timedelta

        from core.runtime.db import connect

        cutoff = (
            datetime.now(UTC) - timedelta(minutes=max(1, int(window_min)))
        ).isoformat()
        kinds = list(_AFFECT_EVENT_FAMILIES.keys())
        placeholders = ",".join("?" for _ in kinds)
        sql = (
            f"SELECT id, kind, payload_json, created_at FROM events "
            f"WHERE kind IN ({placeholders}) AND created_at >= ? "
            f"ORDER BY id DESC LIMIT ?"
        )
        # Pull more than we'll keep — empty-summary events get skipped.
        params = kinds + [cutoff, max(1, int(max_events)) * 4]

        with connect() as c:
            rows = list(c.execute(sql, params).fetchall())
            # User messages are stored in chat_messages, not in event
            # payloads. Pull them directly so user text actually surfaces.
            chat_rows = c.execute(
                "SELECT created_at, content FROM chat_messages "
                "WHERE role='user' AND created_at >= ? "
                "ORDER BY id DESC LIMIT ?",
                (cutoff, max(1, int(max_events)) * 2),
            ).fetchall()
    except Exception as exc:  # pragma: no cover — defensive
        logger.debug("compute_affect_substrate query failed: %s", exc)
        return []

    # Synthesize user-message rows into the same shape as events-table rows.
    synthesized: list[tuple[str, str, str]] = []  # (created_at, kind, kerne)
    for cr in chat_rows:
        content = str(cr["content"] or "").strip().replace("\n", " ")
        if not content:
            continue
        # Skip noise from file-upload echoes (the actual text comes separately)
        if content.startswith("[Fil modtaget"):
            continue
        synthesized.append(
            (str(cr["created_at"] or ""), "user_message", content[:140])
        )

    # Normalize event-rows into (ts, kind, kerne) tuples alongside synthesized.
    import json as _json
    normalized: list[tuple[str, str, str]] = []
    for r in rows:
        kind = str(r["kind"] or "")
        try:
            payload = _json.loads(r["payload_json"] or "{}")
        except Exception:
            payload = {}
        kerne = _summarize_affect_payload(kind, payload)
        if not kerne:
            continue
        normalized.append((str(r["created_at"] or ""), kind, kerne))

    # Merge + sort newest-first by timestamp string (ISO-8601 sorts correctly).
    combined = sorted(normalized + synthesized, key=lambda t: t[0], reverse=True)

    # Per-family cap so high-volume families (tool.completed) don't crowd out
    # rarer-but-higher-affect events. We don't *interpret* affect — we just
    # ensure diversity. user_message gets a higher cap because it's the
    # most affect-bearing signal we have.
    family_caps: dict[str, int] = {"user_message": 3}
    default_cap = 2
    family_counts: dict[str, int] = {}

    _LABELS = dict(_AFFECT_EVENT_FAMILIES)
    _LABELS["user_message"] = "user-besked"

    out: list[str] = []
    for ts, kind, kerne in combined:
        if len(out) >= max_events:
            break
        cap = family_caps.get(kind, default_cap)
        if family_counts.get(kind, 0) >= cap:
            continue
        # HH:MM from "2026-05-07T14:02:33.123456+00:00"
        hhmm = ts[11:16] if len(ts) >= 16 else ts
        label = _LABELS.get(kind, kind)
        out.append(f"{hhmm} — {label}: {kerne}")
        family_counts[kind] = family_counts.get(kind, 0) + 1

    # Reverse to chronological (oldest first reads more naturally)
    return list(reversed(out))
