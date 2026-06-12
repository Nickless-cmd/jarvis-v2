"""User temperature field engine — Lag 10 two-stream pipeline.

Pure-logic. No threading. The runtime daemon
(user_temperature_runtime.py) wraps this with locks + cadence loop.
The structural stream is invoked synchronously per user message from
chat_sessions.append_chat_message().

Two streams:
  - structural: per-message, 6 z-scored signals → valens/arousal/texture
  - LLM: 4h cadence + on-trigger, deepseek-v4-flash via quality_daemon_llm_call

Combination: agreement averages valens/arousal; conflict (>0.6 distance
or texture mismatch) → structural primary, LLM exposed as secondary.

Backwards compat: legacy build_unconscious_temperature_hint() in
unconscious_temperature_field.py delegates here.
"""
from __future__ import annotations

import json
import logging
import re
import statistics
from datetime import UTC, datetime, timedelta
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.db import connect
from core.runtime.db_user_temperature import (
    consume_llm_trigger_pending,
    get_active_field_raw,
    set_llm_trigger_pending,
    upsert_active_field,
)
from core.runtime.settings import load_settings

logger = logging.getLogger(__name__)


# ── Locked vocabulary ─────────────────────────────────────────────────

TEXTURE_VOCAB: frozenset[str] = frozenset({
    "warm", "cool", "restless", "tender", "frustrated", "playful",
    "withdrawn", "alert",
})

# Site 1 (heartbeat) intensity floor.
_HEARTBEAT_INTENSITY_FLOOR = 0.15
# Site 4 (response-style) intensity floor.
_RESPONSE_STYLE_INTENSITY_FLOOR = 0.2

# Conflict thresholds.
_CONFLICT_VALENS_DISTANCE = 0.6
_CONFLICT_AROUSAL_DISTANCE = 0.6


# ── Helpers ────────────────────────────────────────────────────────────

def _coerce_float(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _now() -> datetime:
    return datetime.now(UTC)


def _now_iso() -> str:
    return _now().isoformat().replace("+00:00", "Z")


# ── Raw signal computation ────────────────────────────────────────────


def _punct_density(message: str) -> float:
    if not message:
        return 0.0
    punct = sum(1 for c in message if c in "!?…")
    return min(1.0, punct / max(1, len(message)))


def _caps_density(message: str) -> float:
    letters = [c for c in message if c.isalpha()]
    if not letters:
        return 0.0
    upper = sum(1 for c in letters if c.isupper())
    return upper / len(letters)


def _burst_density(message_at: str) -> float:
    """User msgs in last 5 min, normalized: 0 → 0.0, 5+ → 1.0."""
    try:
        at = datetime.fromisoformat(str(message_at).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return 0.0
    cutoff = (at - timedelta(seconds=300)).isoformat().replace("+00:00", "Z")
    cutoff_end = at.isoformat().replace("+00:00", "Z")
    try:
        with connect() as c:
            n = c.execute(
                "SELECT COUNT(*) FROM chat_messages "
                "WHERE role='user' AND created_at >= ? AND created_at <= ?",
                (cutoff, cutoff_end),
            ).fetchone()[0]
        return min(1.0, int(n) / 5.0)
    except Exception:
        return 0.0


def _delay_since_last_jarvis(message_at: str) -> float | None:
    """Seconds since the prior assistant message. None if no prior or > 60min."""
    try:
        at = datetime.fromisoformat(str(message_at).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    try:
        with connect() as c:
            row = c.execute(
                "SELECT created_at FROM chat_messages "
                "WHERE role='assistant' AND created_at < ? "
                "ORDER BY created_at DESC LIMIT 1",
                (message_at,),
            ).fetchone()
    except Exception:
        return None
    if row is None:
        return None
    try:
        prior = datetime.fromisoformat(str(row[0]).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    delta_seconds = (at - prior).total_seconds()
    if delta_seconds < 0 or delta_seconds > 3600:
        return None
    return delta_seconds


def _parse_hour(message_at: str) -> int:
    try:
        at = datetime.fromisoformat(str(message_at).replace("Z", "+00:00"))
        return at.hour
    except (ValueError, TypeError):
        return 12


def _compute_raw_signals(*, message: str, message_at: str, baseline: dict) -> dict:
    """Map a single message + baseline to 6 normalized signals."""
    if not baseline.get("ready"):
        return {
            "length_z_score": 0.0,
            "response_delay_z_score": 0.0,
            "punctuation_density": _punct_density(message),
            "caps_density": _caps_density(message),
            "hour_of_day_offset": 0.0,
            "burst_density": _burst_density(message_at),
        }

    char_count = len(message)
    length_z = (char_count - baseline["char_count_mean"]) / max(baseline["char_count_stdev"], 1)
    length_z = max(-3.0, min(3.0, length_z)) / 3.0

    delay = _delay_since_last_jarvis(message_at)
    if delay is None:
        response_z = 0.0
    else:
        response_z = (delay - baseline["response_delay_mean"]) / max(baseline["response_delay_stdev"], 1)
        response_z = max(-3.0, min(3.0, response_z)) / 3.0

    hour = _parse_hour(message_at)
    typical_hours = set(baseline.get("typical_hours") or [])
    if hour in typical_hours:
        hour_offset = 0.0
    elif typical_hours:
        nearest = min(abs(hour - h) for h in typical_hours)
        hour_offset = min(1.0, nearest / 6.0)
    else:
        hour_offset = 0.0

    return {
        "length_z_score": length_z,
        "response_delay_z_score": response_z,
        "punctuation_density": _punct_density(message),
        "caps_density": _caps_density(message),
        "hour_of_day_offset": hour_offset,
        "burst_density": _burst_density(message_at),
    }


# ── Field mapping ──────────────────────────────────────────────────────


def map_signals_to_field(signals: dict) -> dict:
    """Pure function: 6 raw signals → valens/arousal/texture/confidence."""
    arousal = (
        signals.get("punctuation_density", 0.0) * 0.3
        + signals.get("caps_density", 0.0) * 0.2
        + signals.get("burst_density", 0.0) * 0.3
        - signals.get("response_delay_z_score", 0.0) * 0.2
    )
    valens = (
        signals.get("length_z_score", 0.0) * 0.4
        - signals.get("response_delay_z_score", 0.0) * 0.3
        - max(0.0, signals.get("hour_of_day_offset", 0.0)) * 0.3
    )
    arousal = max(-1.0, min(1.0, arousal))
    valens = max(-1.0, min(1.0, valens))
    texture = _texture_from_circumplex(valens, arousal)
    confidence = min(1.0, abs(valens) + abs(arousal))
    return {
        "valens": valens, "arousal": arousal,
        "texture": texture, "confidence": confidence,
    }


def _texture_from_circumplex(valens: float, arousal: float) -> str:
    """Pure function: (valens, arousal) → texture key."""
    if arousal > 0.4:
        if valens > 0.3:
            return "playful"
        if valens < -0.3:
            return "frustrated"
        return "alert"
    if arousal > -0.2:
        if valens > 0.3:
            return "warm"
        if valens < -0.3:
            return "tender"
        return "restless" if abs(valens) < 0.3 and arousal > 0.0 else "cool"
    if valens > 0.0:
        return "warm"
    if valens < -0.5:
        return "withdrawn"
    return "cool"


# ── LLM validation ─────────────────────────────────────────────────────


def _validate_llm_output(raw: dict) -> dict | None:
    if not isinstance(raw, dict):
        return None
    valens = _coerce_float(raw.get("valens"))
    arousal = _coerce_float(raw.get("arousal"))
    if valens is None or arousal is None:
        return None
    valens = max(-1.0, min(1.0, valens))
    arousal = max(-1.0, min(1.0, arousal))
    texture = str(raw.get("texture") or "").strip().lower()
    if texture not in TEXTURE_VOCAB:
        return None
    confidence = _coerce_float(raw.get("confidence"))
    if confidence is None or not 0.0 <= confidence <= 1.0:
        confidence = 0.5
    rationale = str(raw.get("rationale") or "").strip()[:200]
    return {
        "valens": valens, "arousal": arousal, "texture": texture,
        "confidence": confidence, "rationale": rationale,
    }


# ── Combine ────────────────────────────────────────────────────────────


def combine_streams(*, struct: dict, llm: dict | None) -> dict:
    """Deterministic merge of structural + LLM streams.

    Rules (2026-06-11 — LLM confidence override added):
    - If no LLM or LLM confidence < 0.3 → structural wins (unchanged).
    - If LLM confidence > 0.7 AND structural confidence < 0.3 → LLM wins
      (structural is too uncertain to veto the more perceptive LLM).
    - If conflict (valens/arousal distance > threshold or texture mismatch):
      weighted average favouring whichever has higher confidence.
    - If no conflict → simple average (unchanged).
    """
    llm_conf = float(llm.get("confidence", 0.0)) if llm else 0.0
    struct_conf = float(struct.get("confidence", 0.0))

    if llm is None or llm_conf < 0.3:
        return {
            "field_valens": struct["valens"],
            "field_arousal": struct["arousal"],
            "field_texture": struct["texture"],
            "field_intensity": min(1.0, abs(struct["valens"]) + abs(struct["arousal"])),
            "field_conflict": False,
        }

    # LLM override: structural too uncertain to veto
    if llm_conf > 0.7 and struct_conf < 0.3:
        return {
            "field_valens": llm["valens"],
            "field_arousal": llm["arousal"],
            "field_texture": llm["texture"],
            "field_intensity": min(1.0, abs(llm["valens"]) + abs(llm["arousal"])),
            "field_conflict": True,  # marked as conflict so downstream knows
        }

    valens_dist = abs(struct["valens"] - llm["valens"])
    arousal_dist = abs(struct["arousal"] - llm["arousal"])
    conflict = (
        valens_dist > _CONFLICT_VALENS_DISTANCE
        or arousal_dist > _CONFLICT_AROUSAL_DISTANCE
        or struct["texture"] != llm["texture"]
    )
    if conflict:
        # Weighted average — favour higher confidence
        total_conf = struct_conf + llm_conf
        w_s = struct_conf / total_conf if total_conf > 0 else 0.5
        w_l = llm_conf / total_conf if total_conf > 0 else 0.5
        fv = struct["valens"] * w_s + llm["valens"] * w_l
        fa = struct["arousal"] * w_s + llm["arousal"] * w_l
        return {
            "field_valens": fv,
            "field_arousal": fa,
            "field_texture": llm["texture"] if w_l > w_s else struct["texture"],
            "field_intensity": min(1.0, abs(fv) + abs(fa)),
            "field_conflict": True,
        }
    fv = (struct["valens"] + llm["valens"]) / 2
    fa = (struct["arousal"] + llm["arousal"]) / 2
    return {
        "field_valens": fv,
        "field_arousal": fa,
        "field_texture": struct["texture"],
        "field_intensity": min(1.0, abs(fv) + abs(fa)),
        "field_conflict": False,
    }


# ── Shift detection ────────────────────────────────────────────────────


def _is_significant_shift(prior: dict | None, new: dict) -> bool:
    """Did valens/arousal shift > threshold or texture change?"""
    if prior is None:
        return False
    threshold = 0.4
    valens_shift = abs(new["valens"] - float(prior.get("struct_valens", 0.0)))
    arousal_shift = abs(new["arousal"] - float(prior.get("struct_arousal", 0.0)))
    texture_changed = new["texture"] != prior.get("struct_texture")
    return valens_shift > threshold or arousal_shift > threshold or texture_changed


# ── Baseline computation ──────────────────────────────────────────────


def _compute_baseline(*, days: int = 30) -> dict:
    """Compute rolling baseline from last N days of user messages."""
    cutoff = (_now() - timedelta(days=days)).isoformat().replace("+00:00", "Z")
    try:
        with connect() as c:
            rows = c.execute(
                "SELECT content, created_at FROM chat_messages "
                "WHERE role='user' AND created_at > ? "
                "ORDER BY created_at ASC",
                (cutoff,),
            ).fetchall()
    except Exception as exc:
        logger.warning("temperature: baseline query failed: %s", exc)
        return {"ready": False, "message_count": 0, "built_at": _now_iso()}

    n = len(rows)
    if n < 30:
        return {
            "ready": False, "message_count": n,
            "built_at": _now_iso(),
        }

    char_counts = [len(str(r["content"] or "")) for r in rows]
    delays = []
    for r in rows:
        d = _delay_since_last_jarvis(str(r["created_at"]))
        if d is not None:
            delays.append(d)
    hours = []
    for r in rows:
        try:
            hours.append(_parse_hour(str(r["created_at"])))
        except Exception:
            pass

    char_mean = statistics.mean(char_counts) if char_counts else 0.0
    char_stdev = statistics.stdev(char_counts) if len(char_counts) > 1 else 1.0
    delay_mean = statistics.mean(delays) if delays else 0.0
    delay_stdev = statistics.stdev(delays) if len(delays) > 1 else 1.0

    hour_counts: dict[int, int] = {}
    for h in hours:
        hour_counts[h] = hour_counts.get(h, 0) + 1
    if hour_counts:
        sorted_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)
        top_n = max(1, len(sorted_hours) // 4)
        typical_hours = [h for h, _ in sorted_hours[:top_n]]
    else:
        typical_hours = []

    return {
        "ready": True,
        "message_count": n,
        "char_count_mean": char_mean,
        "char_count_stdev": char_stdev or 1.0,
        "response_delay_mean": delay_mean,
        "response_delay_stdev": delay_stdev or 1.0,
        "typical_hours": typical_hours,
        "built_at": _now_iso(),
    }


# ── Public read API ───────────────────────────────────────────────────


def get_active_field(*, workspace_id: str = "default") -> dict[str, Any] | None:
    """Read active field, honoring kill-switch."""
    try:
        if not load_settings().user_temperature_enabled:
            return None
    except Exception:
        pass
    return get_active_field_raw(workspace_id=workspace_id)


# ── Heartbeat formatter (Site 1) ──────────────────────────────────────


_DEFAULT_HINTS: dict[str, str] = {
    "warm":       "Brug rolig samarbejdende tone; varme bærer feltet.",
    "cool":       "Hold tonen nøgtern og klar; lav varme, høj præcision.",
    "restless":   "Kort momentum, få skridt; feltet virker rastløst.",
    "tender":     "Svar blidt og uden hård kant; feltet er sart.",
    "frustrated": "Vær verificerende, undgå gæt; tydelig irritation.",
    "playful":    "Tillad lidt leg og lethed, uden at miste retning.",
    "withdrawn":  "Hold afstand, vær til rådighed uden at presse.",
    "alert":      "Vær præcis og hurtig; brugeren er skarp og fokuseret.",
}


def format_temperature_field_for_heartbeat(*, workspace_id: str = "default") -> str:
    """Render the field as a heartbeat awareness-section block."""
    field = get_active_field(workspace_id=workspace_id)
    if not field:
        return ""
    if float(field.get("field_intensity") or 0.0) < _HEARTBEAT_INTENSITY_FLOOR:
        return ""

    valens = field["field_valens"]
    arousal = field["field_arousal"]
    texture = field["field_texture"]
    intensity = field["field_intensity"]
    conflict = field.get("field_conflict", False)

    lines = [
        "[user_temperature_field]",
        f"valens: {valens:+.2f} | arousal: {arousal:+.2f} | "
        f"texture: {texture} | intensity: {intensity:.2f}",
    ]

    if conflict:
        llm_t = field.get("llm_texture") or "?"
        struct_t = field.get("struct_texture") or "?"
        lines.append(
            f"field_conflict: true (struct: {struct_t}, llm: {llm_t}) — "
            "ambivalent felt"
        )

    rationale = str(field.get("llm_rationale") or "").strip()
    if rationale:
        lines.append(f"hint: {rationale[:160]}")
    else:
        lines.append(f"hint: {_DEFAULT_HINTS.get(texture, '')}")

    return "\n".join(lines)


# ── Response-style modifiers (Site 4) ─────────────────────────────────


def get_response_style_modifiers(*, workspace_id: str = "default") -> dict[str, str]:
    """Return response-style hints based on active temperature field."""
    default = {
        "preferred_length": "normal",
        "warmth": "neutral",
        "pace": "normal",
    }
    try:
        field = get_active_field(workspace_id=workspace_id)
        if not field:
            return default
        if float(field.get("field_intensity") or 0.0) < _RESPONSE_STYLE_INTENSITY_FLOOR:
            return default

        valens = float(field["field_valens"])
        arousal = float(field["field_arousal"])
        texture = str(field["field_texture"])

        if texture in ("withdrawn", "tender"):
            length = "short"
        elif arousal > 0.5 and valens < 0:
            length = "short"
        elif valens > 0.4 and arousal > 0.3:
            length = "long"
        else:
            length = "normal"

        if texture in ("tender", "withdrawn"):
            warmth = "gentle"
        elif texture in ("warm", "playful"):
            warmth = "warm"
        else:
            warmth = "neutral"

        if arousal > 0.5:
            pace = "quick"
        elif arousal < -0.3 or texture == "tender":
            pace = "patient"
        else:
            pace = "normal"

        return {
            "preferred_length": length,
            "warmth": warmth,
            "pace": pace,
        }
    except Exception:
        return default


# ── Surface for Mission Control (backwards compat) ────────────────────


def get_active_field_surface(
    *, workspace_id: str = "default", force_refresh: bool = False
) -> dict[str, Any]:
    """Return MC-friendly surface dict. force_refresh ignored in Phase 1."""
    field = get_active_field(workspace_id=workspace_id)
    if not field:
        return {
            "active": False,
            "enabled": True,
            "summary": "No active temperature field",
        }
    return {
        "active": True,
        "enabled": True,
        "current_field": field["field_texture"],
        "valens": field["field_valens"],
        "arousal": field["field_arousal"],
        "intensity": field["field_intensity"],
        "conflict": field["field_conflict"],
        "rationale": field.get("llm_rationale", ""),
        "summary": (
            f"{field['field_texture']} field "
            f"(valens={field['field_valens']:+.2f}, "
            f"arousal={field['field_arousal']:+.2f})"
        ),
    }


# ── Structural stream (per user message) ──────────────────────────────


def run_structural_stream(
    *, workspace_id: str, message: str, message_at: str
) -> dict[str, Any]:
    """Per-message structural pipeline. Updates struct_* + recomputes field_*."""
    try:
        settings = load_settings()
    except Exception as exc:
        return {"status": "error", "reason": f"settings: {exc}"}

    prior = get_active_field_raw(workspace_id=workspace_id)
    baseline = _get_or_build_baseline(prior=prior, settings=settings)

    signals = _compute_raw_signals(
        message=message, message_at=message_at, baseline=baseline,
    )

    struct_result = map_signals_to_field(signals)

    shift = _is_significant_shift(prior, struct_result)

    cached_llm = None
    if prior and prior.get("llm_texture"):
        cached_llm = {
            "valens": prior["llm_valens"],
            "arousal": prior["llm_arousal"],
            "texture": prior["llm_texture"],
            "confidence": prior["llm_confidence"] or 0.0,
            "rationale": prior.get("llm_rationale", ""),
        }

    combined = combine_streams(struct=struct_result, llm=cached_llm)

    upsert_active_field(
        workspace_id=workspace_id,
        struct=struct_result,
        struct_signals=signals,
        llm=cached_llm,
        combined=combined,
        baseline=baseline,
    )

    if shift:
        set_llm_trigger_pending(workspace_id=workspace_id)

    try:
        event_bus.publish(
            "cognitive_temperature.field_updated",
            {
                "workspace_id": workspace_id,
                "field_valens": combined["field_valens"],
                "field_arousal": combined["field_arousal"],
                "field_texture": combined["field_texture"],
                "field_conflict": combined["field_conflict"],
                "stream_source": "structural",
                "shift_detected": shift,
            },
        )
    except Exception as exc:
        logger.debug("temperature: publish failed: %s", exc)

    return {
        "status": "ok",
        "shift_detected": shift,
        "struct_valens": struct_result["valens"],
        "struct_arousal": struct_result["arousal"],
        "struct_texture": struct_result["texture"],
        "field_conflict": combined["field_conflict"],
    }


def _get_or_build_baseline(*, prior: dict | None, settings) -> dict:
    """Return cached baseline if fresh, else rebuild."""
    if prior and prior.get("baseline_stats"):
        cached = prior["baseline_stats"]
        built_at_str = prior.get("baseline_built_at") or ""
        try:
            built_at = datetime.fromisoformat(built_at_str.replace("Z", "+00:00"))
            age_hours = (_now() - built_at).total_seconds() / 3600.0
            if age_hours < settings.user_temperature_baseline_refresh_hours:
                cached["message_count"] = prior.get("baseline_message_count", 0)
                cached["built_at"] = built_at_str
                return cached
        except Exception:
            pass
    return _compute_baseline(days=settings.user_temperature_baseline_days)


# ── LLM stream (4h cadence + on-trigger) ──────────────────────────────


_LLM_SYSTEM_PROMPT = """\
You are reading the user's emotional temperature field — the un-articulated
state behind their words. NOT what they say, but how they feel beneath it.

You receive their last messages (24h window). Output STRICT JSON only:

{
  "valens": -1.0..+1.0,
  "arousal": -1.0..+1.0,
  "texture": "warm"|"cool"|"restless"|"tender"|"frustrated"|"playful"|"withdrawn"|"alert",
  "confidence": 0.0..1.0,
  "rationale": "..."
}

Texture guide:
- warm: positive, present, engaged
- cool: neutral, distance, transactional
- restless: mixed, agitated, can't settle
- tender: vulnerable, soft, careful
- frustrated: negative + activated, irritation
- playful: positive + activated, ease and energy
- withdrawn: negative + low energy, closed off
- alert: neutral + activated, sharp focus

Rules:
- Read texture beneath the words. Sarcasm, omissions, abruptness.
- If you can't tell, set confidence < 0.3.
- rationale is for Bjorn to read — explanation, not diagnosis.
- rationale ≤200 chars Danish.
"""


def _has_pending_trigger(*, workspace_id: str) -> bool:
    """Read trigger flag without consuming."""
    raw = get_active_field_raw(workspace_id=workspace_id)
    return bool(raw and raw.get("llm_trigger_pending"))


def run_llm_stream(*, workspace_id: str = "default", force: bool = False) -> dict[str, Any]:
    """Run LLM-based pipeline (4h cadence or on trigger)."""
    try:
        settings = load_settings()
    except Exception as exc:
        return {"status": "error", "reason": f"settings: {exc}"}

    if not force:
        if not consume_llm_trigger_pending(workspace_id=workspace_id):
            return {"status": "no_trigger"}

    n_messages = settings.user_temperature_llm_corpus_messages
    cutoff = (_now() - timedelta(hours=24)).isoformat().replace("+00:00", "Z")
    try:
        with connect() as c:
            rows = c.execute(
                "SELECT content, created_at FROM chat_messages "
                "WHERE role='user' AND created_at > ? "
                "ORDER BY created_at DESC LIMIT ?",
                (cutoff, n_messages),
            ).fetchall()
    except Exception as exc:
        return {"status": "error", "reason": f"corpus fetch: {exc}"}
    if not rows:
        return {"status": "no_corpus"}

    listing_lines = []
    for r in reversed(rows):
        ts = str(r["created_at"] or "")
        try:
            t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            time_str = t.strftime("%H:%M")
        except Exception:
            time_str = "??:??"
        content = str(r["content"] or "")[:200]
        listing_lines.append(f"[{time_str}] \"{content}\"")
    listing = "\n".join(listing_lines)
    user_msg = (
        f"Bjørns sidste {len(rows)} beskeder (sidste 24 timer):\n\n"
        f"{listing}\n\n"
        f"Produce the JSON."
    )

    full_prompt = _LLM_SYSTEM_PROMPT + "\n\n" + user_msg
    try:
        from core.services.daemon_llm import quality_daemon_llm_call
        raw_response = quality_daemon_llm_call(
            full_prompt,
            max_len=settings.user_temperature_llm_max_response_tokens,
            fallback="",
            daemon_name="user_temperature",
        )
    except Exception as exc:
        return {"status": "llm_failed", "reason": str(exc)[:120]}
    if not raw_response:
        return {"status": "llm_failed", "reason": "empty"}

    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw_response, re.DOTALL)
        if not m:
            return {"status": "json_parse_failed", "raw": raw_response[:120]}
        try:
            parsed = json.loads(m.group(0))
        except json.JSONDecodeError:
            return {"status": "json_parse_failed", "raw": raw_response[:120]}

    validated = _validate_llm_output(parsed)
    if validated is None:
        return {"status": "validation_failed"}

    prior = get_active_field_raw(workspace_id=workspace_id)
    if prior:
        struct = {
            "valens": prior["struct_valens"],
            "arousal": prior["struct_arousal"],
            "texture": prior["struct_texture"],
            "confidence": prior["struct_confidence"],
        }
        struct_signals = prior.get("struct_signals", {})
        baseline = {
            "ready": True,
            "message_count": prior.get("baseline_message_count", 0),
            "built_at": prior.get("baseline_built_at", ""),
            **prior.get("baseline_stats", {}),
        }
    else:
        struct = {"valens": 0.0, "arousal": 0.0, "texture": "cool", "confidence": 0.0}
        struct_signals = {}
        baseline = {"ready": False, "message_count": 0, "built_at": ""}

    combined = combine_streams(struct=struct, llm=validated)
    upsert_active_field(
        workspace_id=workspace_id,
        struct=struct,
        struct_signals=struct_signals,
        llm=validated,
        combined=combined,
        baseline=baseline,
    )

    try:
        event_bus.publish(
            "cognitive_temperature.field_updated",
            {
                "workspace_id": workspace_id,
                "field_valens": combined["field_valens"],
                "field_arousal": combined["field_arousal"],
                "field_texture": combined["field_texture"],
                "field_conflict": combined["field_conflict"],
                "stream_source": "llm",
                "shift_detected": False,
            },
        )
    except Exception:
        pass

    return {
        "status": "ok",
        "field_texture": combined["field_texture"],
        "field_intensity": combined["field_intensity"],
        "field_conflict": combined["field_conflict"],
    }
