"""Personality Vector — cumulative personality that grows over time.

After each visible run, the local-lane LLM analyzes the conversation
and updates the personality vector. Version increments with each update.
The vector is injected into the visible prompt via cognitive_state_assembly.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import UTC, datetime
from urllib import request as urllib_request

from core.eventbus.bus import event_bus
from core.runtime.db import (
    get_latest_cognitive_personality_vector,
    list_cognitive_personality_vectors,
    upsert_cognitive_personality_vector,
)
from core.runtime.provider_router import resolve_provider_router_target

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fix 1: Decay debounce — natural decay runs at most once per 30 minutes
# ---------------------------------------------------------------------------
_DECAY_DEBOUNCE_SECONDS = 1800  # 30 minutes
_last_decay_ts: float | None = None
_decay_lock = threading.Lock()


def _should_apply_decay() -> bool:
    """Return True if enough time has passed since the last decay application."""
    import time
    with _decay_lock:
        if _last_decay_ts is None:
            return True
        return (time.monotonic() - _last_decay_ts) >= _DECAY_DEBOUNCE_SECONDS


def _record_decay_timestamp() -> None:
    """Record that decay was just applied."""
    import time
    global _last_decay_ts
    with _decay_lock:
        _last_decay_ts = time.monotonic()


def _build_update_prompt() -> str:
    from apps.api.jarvis_api.services.identity_composer import get_entity_name
    name = get_entity_name()
    return f"""Du er {name}s indre personligheds-opdaterer.
Baseret på denne samtale, opdatér personality vector.
Returner KUN et JSON-objekt med ændrede felter. Uændrede felter udelades.

Mulige felter:
- confidence_by_domain: {{"python": 0.0-1.0, "frontend": 0.0-1.0, "ops": 0.0-1.0, ...}}
- communication_style: {{"directness": 0.0-1.0, "humor": 0.0-1.0, "formality": 0.0-1.0}}
- learned_preferences: ["preference1", "preference2"] (tilføj nye, behold gamle)
- recurring_mistakes: ["mistake1"] (tilføj kun hvis gentaget)
- strengths_discovered: ["strength1"] (tilføj kun ved tydelig evidens)
- current_bearing: "kort sætning om nuværende fokus"
- emotional_baseline: {{"curiosity": 0.0-1.0, "confidence": 0.0-1.0, "fatigue": 0.0-1.0, "frustration": 0.0-1.0}}

Regler:
- Vær konservativ — kun opdatér det der faktisk ændrede sig
- Foretræk små justeringer over dramatiske ændringer
- Confidence stiger langsomt ved succes, falder hurtigere ved fejl
- Svar KUN med JSON, ingen forklaring
"""


def update_personality_vector_from_run(
    *,
    run_id: str,
    user_message: str,
    assistant_response: str,
    outcome_status: str,
) -> dict[str, object] | None:
    """Update the personality vector based on a visible run.

    Called fire-and-forget after write_private_terminal_layers.
    Uses the local lane for LLM analysis, with an internal fallback lane only when needed.
    """
    current = get_latest_cognitive_personality_vector()
    current_json = json.dumps(current, ensure_ascii=False) if current else "{}"

    user_prompt = (
        f"Nuværende vektor:\n{current_json}\n\n"
        f"Status: {outcome_status}\n"
        f"Bruger: {user_message[:400]}\n"
        f"Svar: {assistant_response[:400]}\n\n"
        f"Returner opdateret JSON:"
    )

    try:
        target = _resolve_local_llm_target()
        if not target:
            return _deterministic_update(outcome_status, current)
        response_text = _call_llm(target, _build_update_prompt(), user_prompt)
        updates = _parse_json_response(response_text)
        if not updates:
            return _deterministic_update(outcome_status, current)
    except Exception:
        logger.debug("personality_vector: LLM update failed, using deterministic", exc_info=True)
        return _deterministic_update(outcome_status, current)

    # Merge with existing
    merged = _merge_vector(current or {}, updates)

    result = upsert_cognitive_personality_vector(
        confidence_by_domain=json.dumps(merged.get("confidence_by_domain", {}), ensure_ascii=False),
        communication_style=json.dumps(merged.get("communication_style", {}), ensure_ascii=False),
        learned_preferences=json.dumps(merged.get("learned_preferences", []), ensure_ascii=False),
        recurring_mistakes=json.dumps(merged.get("recurring_mistakes", []), ensure_ascii=False),
        strengths_discovered=json.dumps(merged.get("strengths_discovered", []), ensure_ascii=False),
        current_bearing=str(merged.get("current_bearing", "")),
        emotional_baseline=json.dumps(merged.get("emotional_baseline", {}), ensure_ascii=False),
    )

    event_bus.publish(
        "cognitive_personality.vector_updated",
        {
            "run_id": run_id,
            "version": result.get("version"),
            "source": "llm" if updates else "deterministic",
        },
    )
    return result


def update_personality_vector_async(
    *,
    run_id: str,
    user_message: str,
    assistant_response: str,
    outcome_status: str,
) -> None:
    """Fire-and-forget async wrapper."""
    thread = threading.Thread(
        target=_safe_update,
        kwargs={
            "run_id": run_id,
            "user_message": user_message,
            "assistant_response": assistant_response,
            "outcome_status": outcome_status,
        },
        daemon=True,
    )
    thread.start()


def _safe_update(**kwargs) -> None:
    try:
        update_personality_vector_from_run(**kwargs)
    except Exception:
        logger.debug("personality_vector: async update failed", exc_info=True)


def build_personality_vector_surface() -> dict[str, object]:
    """MC surface for personality vector."""
    current = get_latest_cognitive_personality_vector()
    history = list_cognitive_personality_vectors(limit=10)
    return {
        "active": current is not None,
        "current": current,
        "history_count": len(history),
        "history": history,
        "summary": (
            f"v{current['version']}, bearing: {current.get('current_bearing', 'none')[:60]}"
            if current
            else "No personality vector yet"
        ),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _deterministic_update(
    outcome_status: str,
    current: dict[str, object] | None,
) -> dict[str, object] | None:
    """Fallback: small deterministic adjustments without LLM.

    Fix 1: Natural decay (×0.95) is debounced — applied at most once per 30
    minutes to prevent repeated calls within the same session from erasing
    justified emotional state.

    Fix 5: If the computed baseline is identical to what's already stored
    (within 0.001 tolerance), we skip the DB write entirely to avoid
    inflating the version history with no-op entries.
    """
    baseline = json.loads(str(current.get("emotional_baseline") or "{}")) if current else {}
    original_baseline = dict(baseline)

    # Fix 1: Debounced natural decay — at most once per 30 minutes
    if _should_apply_decay():
        baseline["fatigue"] = max(0.0, float(baseline.get("fatigue", 0.0)) * 0.95)
        baseline["frustration"] = max(0.0, float(baseline.get("frustration", 0.0)) * 0.95)
        _record_decay_timestamp()

    if outcome_status in ("completed", "success"):
        baseline["confidence"] = min(1.0, float(baseline.get("confidence", 0.5)) + 0.02)
        baseline["fatigue"] = min(1.0, float(baseline.get("fatigue", 0.0)) + 0.01)
    elif outcome_status in ("failed", "error"):
        baseline["confidence"] = max(0.0, float(baseline.get("confidence", 0.5)) - 0.05)
        baseline["frustration"] = min(1.0, float(baseline.get("frustration", 0.0)) + 0.03)

    # Fix 5: Skip upsert if baseline is effectively unchanged
    if not _baseline_changed(current, baseline):
        logger.debug("personality_vector: deterministic update skipped — no effective change")
        return current

    confidence_by_domain = json.loads(
        str(current.get("confidence_by_domain") or "{}") if current else "{}"
    )

    return upsert_cognitive_personality_vector(
        confidence_by_domain=json.dumps(confidence_by_domain, ensure_ascii=False),
        communication_style=str(current.get("communication_style", "{}")) if current else "{}",
        learned_preferences=str(current.get("learned_preferences", "[]")) if current else "[]",
        recurring_mistakes=str(current.get("recurring_mistakes", "[]")) if current else "[]",
        strengths_discovered=str(current.get("strengths_discovered", "[]")) if current else "[]",
        current_bearing=str(current.get("current_bearing", "")) if current else "",
        emotional_baseline=json.dumps(baseline, ensure_ascii=False),
    )


_EMOTIONAL_AXES = ("confidence", "curiosity", "fatigue", "frustration")


def _merge_vector(current: dict, updates: dict) -> dict:
    """Deep merge updates into current vector."""
    result = {}

    # JSON fields — merge dicts, extend lists
    for key in ("confidence_by_domain", "communication_style", "emotional_baseline"):
        current_val = _safe_json_field(current.get(key), {})
        update_val = updates.get(key)
        if isinstance(update_val, dict):
            merged = {**current_val, **update_val}
            # Fix 4: clamp emotional_baseline axes to [0.0, 1.0] so invalid LLM
            # output (negatives, values > 1) cannot corrupt the baseline.
            if key == "emotional_baseline":
                merged = {
                    k: max(0.0, min(1.0, float(v))) if k in _EMOTIONAL_AXES and v is not None else v
                    for k, v in merged.items()
                }
            result[key] = merged
        else:
            result[key] = current_val

    for key in ("learned_preferences", "recurring_mistakes", "strengths_discovered"):
        current_val = _safe_json_field(current.get(key), [])
        update_val = updates.get(key)
        if isinstance(update_val, list):
            merged = list(current_val)
            for item in update_val:
                if item not in merged:
                    merged.append(item)
            result[key] = merged[-20:]  # cap at 20
        else:
            result[key] = current_val

    # Simple string fields
    result["current_bearing"] = str(
        updates.get("current_bearing")
        or current.get("current_bearing")
        or ""
    )

    return result


def _baseline_changed(old: dict[str, object] | None, new_baseline: dict) -> bool:
    """Fix 5 helper: return True if emotional_baseline values differ by > 0.001."""
    if old is None:
        return True
    old_baseline = _safe_json_field(old.get("emotional_baseline"), {})
    all_keys = set(old_baseline) | set(new_baseline)
    for k in all_keys:
        old_v = float(old_baseline.get(k) or 0.0)
        new_v = float(new_baseline.get(k) or 0.0)
        if abs(old_v - new_v) > 0.001:
            return True
    return False


def _safe_json_field(value, default):
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, type(default)):
                return parsed
        except Exception:
            pass
    return default


def _resolve_local_llm_target() -> dict[str, object] | None:
    for lane in ("local", "cheap"):
        try:
            target = resolve_provider_router_target(lane=lane)
            if bool(target.get("active")):
                return target
        except Exception:
            continue
    return None


def _call_llm(target: dict, system_prompt: str, user_prompt: str) -> str:
    """Minimal LLM call via provider router target."""
    provider = str(target.get("provider") or "")
    model = str(target.get("model") or "")
    base_url = str(target.get("base_url") or "")

    if provider == "ollama":
        url = f"{base_url or 'http://127.0.0.1:11434'}/api/chat"
        payload = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {"num_predict": 200},
        }).encode()
        req = urllib_request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        with urllib_request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
        return str(result.get("message", {}).get("content", ""))
    return ""


def _parse_json_response(text: str) -> dict | None:
    text = text.strip()
    # Try to extract JSON from response
    if text.startswith("```"):
        lines = text.split("\n")
        json_lines = [l for l in lines if not l.startswith("```")]
        text = "\n".join(json_lines).strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    # Try to find JSON object in text
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(text[start:end + 1])
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
    return None
