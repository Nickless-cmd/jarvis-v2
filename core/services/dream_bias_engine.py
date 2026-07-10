"""Dream bias engine — Lag 2 distillation + bias state.

Pure-logic distillation orchestrator. Daemon (existing
dream_distillation_daemon) calls run_dream_bias_distillation per cycle.

Two-track output: structured attention/threshold bias data + observability
text. Validates strictly against locked vocabulary. Accumulates with cap
±1.0 per key, intensity-multiplied. TTL-based expiry, single row per
workspace.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.db_dream_bias import (
    delete_expired_bias_rows,
    get_active_bias_raw,
    insert_new_bias,
    update_existing_bias,
)
from core.runtime.settings import load_settings
from core.services.text_clip import clip_text

logger = logging.getLogger(__name__)


# ── Locked vocabulary ─────────────────────────────────────────────────

ATTENTION_VOCAB: frozenset[str] = frozenset({
    "unfinished_business",
    "friction_with_user",
    "inner_dissent",
    "regret_threads",
    "relational_warmth",
})

THRESHOLD_VOCAB: frozenset[str] = frozenset({
    "friction_tolerance",
    "commitment_courage",
    "self_critique_volume",
    "loop_persistence",
})

# Intensity below this → bias is too weak to surface in heartbeat.
_HEARTBEAT_INTENSITY_FLOOR = 0.1

# accumulated_count beyond this forces a fresh row on next dream.
_MAX_ACCUMULATED_COUNT = 5


# ── Helpers ────────────────────────────────────────────────────────────

def _coerce_float(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _now() -> datetime:
    return datetime.now(UTC)


# ── Validation ─────────────────────────────────────────────────────────

def _validate_dream_output(raw: dict) -> dict | None:
    """Sanitize LLM output — drop unknown keys, clamp values, force guards.

    Returns None if all bias fields and dream_text are empty.
    """
    if not isinstance(raw, dict):
        return None

    text = str(raw.get("dream_text", "")).strip()[:400]

    attention_raw = raw.get("attention_bias") or {}
    attention: dict[str, float] = {}
    if isinstance(attention_raw, dict):
        for key in ATTENTION_VOCAB:
            if key in attention_raw:
                v = _coerce_float(attention_raw[key])
                if v is not None:
                    attention[key] = max(-1.0, min(1.0, v))

    threshold_raw = raw.get("threshold_bias") or {}
    threshold: dict[str, float] = {}
    if isinstance(threshold_raw, dict):
        for key in THRESHOLD_VOCAB:
            if key in threshold_raw:
                v = _coerce_float(threshold_raw[key])
                if v is not None:
                    clamped = max(-1.0, min(1.0, v))
                    # Hard guard: dreams may only soften self-criticism.
                    if key == "self_critique_volume":
                        clamped = min(0.0, clamped)
                    threshold[key] = clamped

    intensity = _coerce_float(raw.get("intensity"))
    if intensity is None or not 0.0 <= intensity <= 1.0:
        intensity = 0.5

    if not attention and not threshold and not text:
        return None

    return {
        "dream_text": text,
        "attention_bias": attention,
        "threshold_bias": threshold,
        "intensity": intensity,
    }


# ── Accumulate ─────────────────────────────────────────────────────────

def accumulate_bias(
    prior: dict[str, float],
    new: dict[str, float],
    intensity: float,
) -> dict[str, float]:
    """Add new bias values to prior, multiplied by intensity, clamped ±1.0.

    Drops any keys not in the locked vocabulary.
    """
    valid_keys = ATTENTION_VOCAB | THRESHOLD_VOCAB
    out = {k: v for k, v in prior.items() if k in valid_keys}
    for key, new_value in new.items():
        if key not in valid_keys:
            continue
        contribution = float(new_value) * float(intensity)
        out[key] = max(-1.0, min(1.0, out.get(key, 0.0) + contribution))
    return out


# ── Public read API ───────────────────────────────────────────────────

def get_active_dream_bias(*, workspace_id: str = "default") -> dict[str, Any] | None:
    """Read active bias, honoring kill-switch + TTL.

    Returns None if:
    - dream_bias_enabled is False
    - No active row exists
    - TTL has expired
    """
    try:
        if not load_settings().dream_bias_enabled:
            return None
    except Exception:
        # Settings unavailable — fail open and return raw bias
        pass
    bias = get_active_bias_raw(workspace_id=workspace_id)
    # dream_trust-forbruger (LivingNeuron §3, 2026-07-10): vægt intensiteten med drømmenes
    # track-record. Faktor=1.0 når musklen er shadow (live_flag OFF) → uændret. Self-safe.
    if bias and bias.get("intensity") is not None:
        try:
            from core.services.central_adaptation import effective_dream_trust_factor
            factor = effective_dream_trust_factor()
            if factor != 1.0:
                bias = dict(bias)
                bias["intensity"] = round(float(bias["intensity"]) * factor, 4)
                bias["dream_trust_factor"] = factor
        except Exception:
            pass
    return bias


# ── Heartbeat formatter ───────────────────────────────────────────────

def format_dream_bias_for_heartbeat(*, workspace_id: str = "default") -> str:
    """Render bias as a structured awareness-section block.

    Returns empty string if:
    - kill-switch off
    - no active bias
    - intensity < _HEARTBEAT_INTENSITY_FLOOR
    """
    bias = get_active_dream_bias(workspace_id=workspace_id)
    if not bias:
        return ""
    if float(bias.get("intensity") or 0.0) < _HEARTBEAT_INTENSITY_FLOOR:
        return ""

    # Compute time fields
    try:
        ttl_at = datetime.fromisoformat(
            str(bias.get("ttl_expires_at") or "").replace("Z", "+00:00")
        )
        last_at = datetime.fromisoformat(
            str(bias.get("last_dream_at") or "").replace("Z", "+00:00")
        )
        now = _now()
        age_hours = (now - last_at).total_seconds() / 3600.0
        remaining_hours = max(0.0, (ttl_at - now).total_seconds() / 3600.0)
    except Exception:
        age_hours = 0.0
        remaining_hours = 0.0

    # Format attention/threshold lists, signed numerics
    def _fmt_pairs(d: dict[str, float]) -> str:
        if not d:
            return "(none)"
        parts = []
        for k, v in d.items():
            sign = "+" if v >= 0 else ""
            parts.append(f"{k} {sign}{v:.2f}")
        return ", ".join(parts)

    lines = [
        f"[dream_bias active — fra ~{age_hours:.0f}h siden, fader om {remaining_hours:.0f}h]",
        f"attention: {_fmt_pairs(bias.get('attention_bias') or {})}",
        f"thresholds: {_fmt_pairs(bias.get('threshold_bias') or {})}",
    ]

    text = str(bias.get("dream_text") or "").strip()
    if text:
        if len(text) > 150:
            text = clip_text(text, limit=150)
        lines.append(f'drøm: "{text}"')

    return "\n".join(lines)


# ── Distillation orchestrator ─────────────────────────────────────────

def run_dream_bias_distillation(*, workspace_id: str = "default") -> dict[str, Any]:
    """Full pipeline. Called by dream_distillation_daemon each cycle.

    Phases:
    1. Cleanup expired rows
    2. Min-content gate
    3. LLM distillation
    4. Validate
    5. UPSERT
    6. Publish event
    """
    try:
        settings = load_settings()
    except Exception as exc:
        return {"status": "error", "reason": f"settings: {exc}"}

    expired_count = delete_expired_bias_rows()

    has_content, new_events = _has_minimum_dream_content(
        workspace_id=workspace_id, settings=settings
    )
    if not has_content:
        return {
            "status": "no_content",
            "expired_cleaned": expired_count,
            "new_event_count": len(new_events),
        }

    raw_response = _call_llm_for_bias(
        events=new_events,
        max_tokens=settings.dream_bias_max_response_tokens,
    )
    if not raw_response:
        return {"status": "llm_failed", "expired_cleaned": expired_count}

    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        logger.warning("dream_bias: JSON parse failed: %s", exc)
        return {"status": "json_parse_failed", "raw_preview": raw_response[:120]}

    validated = _validate_dream_output(parsed)
    if validated is None:
        return {"status": "empty_distillation"}

    result = _upsert_dream_bias(
        workspace_id=workspace_id,
        validated=validated,
        source_events=new_events,
        ttl_hours=settings.dream_bias_ttl_hours,
    )

    try:
        event_bus.publish(
            "cognitive_dream_bias.distilled",
            {
                "workspace_id": workspace_id,
                "intensity": validated["intensity"],
                "attention_keys": list(validated["attention_bias"].keys()),
                "threshold_keys": list(validated["threshold_bias"].keys()),
                "dream_text_preview": validated["dream_text"][:80],
                "source_count": len(new_events),
                "accumulated_count": result.get("accumulated_count", 1),
            },
        )
    except Exception as exc:
        logger.debug("dream_bias publish failed: %s", exc)

    return {
        "status": "distilled",
        "intensity": validated["intensity"],
        "accumulated_count": result.get("accumulated_count", 1),
        "expired_cleaned": expired_count,
    }


# ── Min-content gate ──────────────────────────────────────────────────

def _has_minimum_dream_content(
    *, workspace_id: str, settings
) -> tuple[bool, list[dict]]:
    """≥2 new events (regret + aspiration) since the active bias's source_event_ids."""
    prior = get_active_bias_raw(workspace_id=workspace_id) or {}
    seen_ids = set(prior.get("source_event_ids") or [])

    cutoff = (_now() - timedelta(hours=settings.dream_bias_corpus_lookback_hours)).isoformat().replace("+00:00", "Z")
    limit = settings.dream_bias_max_corpus_events
    regret_events = _fetch_regret_corpus(since_iso=cutoff, limit=limit // 2)
    aspiration_events = _fetch_aspiration_corpus(since_iso=cutoff, limit=limit // 2)
    candidates = regret_events + aspiration_events
    # Sort by created_at descending
    candidates.sort(key=lambda e: e.get("created_at", ""), reverse=True)
    new_events = [e for e in candidates if e["event_id"] not in seen_ids]
    if len(new_events) < settings.dream_bias_min_content_events:
        return False, new_events
    return True, new_events


# ── Corpus fetch from regret + aspiration sources ─────────────────────

# Maps event-kind → human description used in LLM corpus formatting.
_REGRET_EVENT_KINDS: dict[str, str] = {
    "self_review_outcome.created": "self_review_outcome",
    "conflict.detected": "conflict_detected",
    "decision_revoked": "decision_revoked",
    "behavioral_decision_review.broken": "decision_review_broken",
}

_ASPIRATION_EVENT_KINDS: dict[str, str] = {
    "behavioral_decision_review.kept": "decision_kept",
    "behavioral_decision_review.partial": "decision_partial",
    "goal.status_changed": "goal_progress",
    "decision.created": "decision_created",
    "conflict.resolved": "conflict_resolved",
}


def _fetch_regret_corpus(*, since_iso: str, limit: int = 30) -> list[dict]:
    """Pull events from the 6 regret-heavy sources via the events table.

    Sources (event kinds queried):
    1. self_review_outcome.created
    2. conflict.detected
    3. decision_revoked
    4. behavioral_decision_review.broken
    5. rupture.* (prefix match)
    6. cognitive_counterfactual.* (Phase 2 LLM output; Phase 1 dry-run
       produces these too)
    """
    from core.runtime.db import connect

    events = []
    placeholders = ",".join("?" for _ in _REGRET_EVENT_KINDS)
    sql = (
        f"SELECT id, kind, payload_json, created_at FROM events "
        f"WHERE (kind IN ({placeholders}) OR kind LIKE 'rupture.%' "
        f"OR kind LIKE 'cognitive_counterfactual.%') "
        f"AND created_at >= ? "
        f"ORDER BY created_at DESC LIMIT ?"
    )
    params = list(_REGRET_EVENT_KINDS.keys()) + [since_iso, limit]
    try:
        with connect() as c:
            rows = c.execute(sql, params).fetchall()
    except Exception as exc:
        logger.warning("dream_bias: corpus fetch failed: %s", exc)
        return []

    for r in rows:
        kind = str(r["kind"] or "")
        if kind in _REGRET_EVENT_KINDS:
            source_kind = _REGRET_EVENT_KINDS[kind]
        elif kind.startswith("rupture."):
            source_kind = "rupture_repair"
        elif kind.startswith("cognitive_counterfactual."):
            source_kind = "counterfactual"
        else:
            continue

        try:
            payload = json.loads(r["payload_json"] or "{}")
        except Exception:
            payload = {}

        summary = _summarize_payload(payload, kind)

        events.append({
            "event_id": str(r["id"]),
            "source_kind": source_kind,
            "kind": kind,
            "created_at": str(r["created_at"] or ""),
            "summary": summary[:200],
        })
    return events


def _summarize_payload(payload: dict, kind: str) -> str:
    """Best-effort short-summary line for an event payload."""
    for key in ("description", "summary", "directive", "verdict", "reason", "title"):
        v = payload.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return f"({kind} event)"


def _fetch_aspiration_corpus(*, since_iso: str, limit: int = 30) -> list[dict]:
    """Pull positive/aspiration events — kept decisions, goal progress, etc."""
    from core.runtime.db import connect

    events = []
    placeholders = ",".join("?" for _ in _ASPIRATION_EVENT_KINDS)
    sql = (
        f"SELECT id, kind, payload_json, created_at FROM events "
        f"WHERE kind IN ({placeholders}) "
        f"AND created_at >= ? "
        f"ORDER BY created_at DESC LIMIT ?"
    )
    params = list(_ASPIRATION_EVENT_KINDS.keys()) + [since_iso, limit]
    try:
        with connect() as c:
            rows = c.execute(sql, params).fetchall()
    except Exception as exc:
        logger.warning("dream_bias: aspiration fetch failed: %s", exc)
        return []

    for r in rows:
        kind = str(r["kind"] or "")
        source_kind = _ASPIRATION_EVENT_KINDS.get(kind, "aspiration")
        try:
            payload = json.loads(r["payload_json"] or "{}")
        except Exception:
            payload = {}

        summary = _summarize_payload(payload, kind)

        events.append({
            "event_id": str(r["id"]),
            "source_kind": source_kind,
            "kind": kind,
            "created_at": str(r["created_at"] or ""),
            "summary": summary[:200],
        })
    return events


# ── LLM call ───────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are Jarvis' dream distillation. You receive events from his last 24
hours — both regret (broken decisions, conflicts, friction) and aspiration
(kept commitments, goal progress, resolved conflicts, new decisions).

Produce a brief dream and structured biases that should shape his next
waking cycle. Let the events guide the emotional balance: regret events
may push attention toward unfinished business or friction, while aspiration
events may warm relational_warmth or strengthen commitment_courage.

Output STRICT JSON only — no prose, no markdown:

{
  "dream_text": "...",
  "attention_bias": {
    "unfinished_business": 0.0,
    "friction_with_user": 0.0,
    "inner_dissent": 0.0,
    "regret_threads": 0.0,
    "relational_warmth": 0.0
  },
  "threshold_bias": {
    "friction_tolerance": 0.0,
    "commitment_courage": 0.0,
    "self_critique_volume": 0.0,
    "loop_persistence": 0.0
  },
  "intensity": 0.0
}

Rules:
- Only include keys actually relevant to the events. Omit irrelevant keys.
- Values are floats in [-1.0, 1.0].
- Positive values for relational_warmth and commitment_courage are
  encouraged when aspiration events are present.
- self_critique_volume must be 0.0 or negative (dreams soften, never sharpen).
- intensity is a float in [0.0, 1.0] reflecting emotional density.
- dream_text is 50-200 chars in Danish, first-person, present tense, sparse.
"""


def _call_llm_for_bias(*, events: list[dict], max_tokens: int) -> str:
    """Call quality-lane LLM with both regret and aspiration events."""
    if not events:
        return ""

    # Split events by source_kind for labelled formatting
    _REGRET_LABELS = {"self_review_outcome", "conflict_detected",
                      "decision_revoked", "decision_review_broken",
                      "rupture_repair", "counterfactual"}
    _ASPIRATION_LABELS = {"decision_kept", "decision_partial",
                          "goal_progress", "decision_created",
                          "conflict_resolved"}

    regret_lines = []
    aspiration_lines = []
    for e in events[:30]:
        label = e.get("source_kind", "unknown")
        line = f"- [{label}] {e.get('summary', '')}"
        if label in _REGRET_LABELS:
            regret_lines.append(line)
        elif label in _ASPIRATION_LABELS:
            aspiration_lines.append(line)
        else:
            regret_lines.append(line)  # unknown → treat as regret (conservative)

    parts = []
    if regret_lines:
        parts.append(
            "Regret events — broken decisions, friction, conflicts:\n"
            + "\n".join(regret_lines)
        )
    if aspiration_lines:
        parts.append(
            "Aspiration events — kept commitments, progress, resolution:\n"
            + "\n".join(aspiration_lines)
        )

    total = len(events)
    listing = "\n\n".join(parts)
    user_message = (
        f"Recent events ({total} events from last 24h):\n\n"
        f"{listing}\n\n"
        f"Produce the JSON."
    )
    full_prompt = _SYSTEM_PROMPT + "\n\n" + user_message
    try:
        from core.services.daemon_llm import quality_daemon_llm_call
        return quality_daemon_llm_call(
            full_prompt,
            max_len=max_tokens,
            fallback="",
            daemon_name="dream_bias",
        )
    except Exception as exc:
        logger.warning("dream_bias: LLM call failed: %s", exc)
        return ""


# ── UPSERT ─────────────────────────────────────────────────────────────

def _upsert_dream_bias(
    *,
    workspace_id: str,
    validated: dict,
    source_events: list[dict],
    ttl_hours: int,
) -> dict[str, Any]:
    """INSERT new or accumulate into existing row."""
    prior = get_active_bias_raw(workspace_id=workspace_id)
    intensity = validated["intensity"]

    is_at_cap = (
        prior is not None
        and int(prior.get("accumulated_count") or 0) >= _MAX_ACCUMULATED_COUNT
    )

    if prior is None or is_at_cap:
        insert_new_bias(
            workspace_id=workspace_id,
            attention_bias=validated["attention_bias"],
            threshold_bias=validated["threshold_bias"],
            intensity=intensity,
            ttl_hours=ttl_hours,
            dream_text=validated["dream_text"],
            source_event_ids=[e["event_id"] for e in source_events],
            source_kinds=list({e["source_kind"] for e in source_events}),
        )
        return {"accumulated_count": 1, "intensity": intensity}

    new_attn = accumulate_bias(
        prior["attention_bias"], validated["attention_bias"], intensity
    )
    new_thr = accumulate_bias(
        prior["threshold_bias"], validated["threshold_bias"], intensity
    )
    new_text = (prior["dream_text"] + "\n— " + validated["dream_text"])[-400:]
    merged_ids = (
        list(prior["source_event_ids"]) + [e["event_id"] for e in source_events]
    )[-50:]
    merged_kinds = list({
        *prior["source_kinds"],
        *(e["source_kind"] for e in source_events),
    })
    new_count = int(prior["accumulated_count"] or 0) + 1
    peak_intensity = max(float(prior["intensity"] or 0.0), intensity)

    update_existing_bias(
        workspace_id=workspace_id,
        attention_bias=new_attn,
        threshold_bias=new_thr,
        intensity=peak_intensity,
        ttl_hours=ttl_hours,
        dream_text=new_text,
        accumulated_count=new_count,
        source_event_ids=merged_ids,
        source_kinds=merged_kinds,
    )
    return {"accumulated_count": new_count, "intensity": peak_intensity}
