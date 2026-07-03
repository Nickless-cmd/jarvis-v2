"""World Model Phase 2: auto-extract structured predictions from Jarvis' replies.

Phase 1 had regex-based prediction-language detection that produced awareness
nudges only. Phase 2 takes those same phrases and uses cheap-lane LLM to
parse them into structured {subject, expectation, confidence} predictions,
then records them via record_runtime_world_model_prediction.

This closes the volume problem: Phase 1 needed Jarvis to explicitly call
predict_outcome — yielded ~1-2 predictions/week. Phase 2 surfaces predictions
he already MAKES in natural language ("jeg tror...", "forventer..."), giving
calibration ~20-50/week without changing his behavior.

Cost: cheap-lane call per detected prediction phrase. Rate-limited to
_MAX_AUTO_EXTRACTIONS_PER_DAY to keep cost bounded.

Added 2026-05-13.
"""
from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from core.runtime.state_store import load_json, save_json

logger = logging.getLogger(__name__)

_RATE_KEY = "runtime_world_model_auto_extraction_rate"
_MAX_AUTO_EXTRACTIONS_PER_DAY = 15
_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?```", re.DOTALL)


def _today_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def _load_rate_state() -> dict[str, Any]:
    state = load_json(_RATE_KEY, default=None)
    today = _today_iso()
    if not isinstance(state, dict) or state.get("date") != today:
        state = {"date": today, "count": 0}
        save_json(_RATE_KEY, state)
    return state


def _increment_rate() -> int:
    state = _load_rate_state()
    state["count"] = int(state.get("count", 0)) + 1
    save_json(_RATE_KEY, state)
    return state["count"]


def _under_rate_limit() -> bool:
    return int(_load_rate_state().get("count", 0)) < _MAX_AUTO_EXTRACTIONS_PER_DAY


def _extract_json(text: str) -> str:
    text = text.strip()
    m = _FENCE_RE.search(text)
    if m:
        return m.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start:end + 1]
    return text


def _build_prompt(context_excerpt: str, matched_phrase: str) -> str:
    return (
        "Du parser én sætning fra Jarvis' egne svar for at se om den udtrykker "
        "en falsifiabel prediction.\n"
        "\n"
        "Returnér KUN JSON:\n"
        '  {"is_prediction": true/false, "subject": "...", "expectation": "...", '
        '"confidence": "low|medium|high", "horizon": "..."}\n'
        "\n"
        "Hvis sætningen IKKE er en konkret falsifiabel prediction (bare en "
        "spekulation, generel observation, eller noget der ikke kan tjekkes "
        "senere), returnér {\"is_prediction\": false}.\n"
        "\n"
        f"Trigger-frase: {matched_phrase!r}\n"
        f"Kontekst: {context_excerpt}\n"
    )


def auto_extract_and_record(
    *,
    matched_phrase: str,
    context_excerpt: str,
    session_id: str = "",
) -> dict[str, Any]:
    """Try to extract a structured prediction from a matched phrase.

    Returns {status, prediction_id?} dict. Rate-limited and defensive.
    """
    if not _under_rate_limit():
        return {"status": "skipped", "reason": "daily-limit"}

    try:
        from core.services.cheap_provider_runtime import execute_public_safe_cheap_lane
    except Exception as exc:
        logger.debug("auto_extraction: cheap-lane import failed: %s", exc)
        return {"status": "error", "reason": "no-cheap-lane"}

    prompt = _build_prompt(context_excerpt, matched_phrase)
    try:
        result = execute_public_safe_cheap_lane(message=prompt)
    except Exception as exc:
        logger.debug("auto_extraction: cheap-lane invoke failed: %s", exc)
        return {"status": "error", "reason": f"cheap-lane: {exc}"}

    text = str(result.get("text") or "")
    try:
        data = json.loads(_extract_json(text))
    except (json.JSONDecodeError, ValueError):
        return {"status": "error", "reason": "invalid-json", "raw": text[:120]}

    if not isinstance(data, dict) or not data.get("is_prediction"):
        return {"status": "skipped", "reason": "not-a-prediction"}

    subject = str(data.get("subject") or "").strip()
    expectation = str(data.get("expectation") or "").strip()
    confidence = str(data.get("confidence") or "low").strip().lower()
    horizon = str(data.get("horizon") or "").strip()
    if not subject or not expectation:
        return {"status": "skipped", "reason": "missing-fields"}

    try:
        from core.services.world_model_signal_tracking import (
            record_runtime_world_model_prediction,
        )
        pred = record_runtime_world_model_prediction(
            subject=subject,
            expectation=expectation,
            confidence=confidence,
            horizon=horizon,
            source="visible-chat-auto-extracted",
            evidence=[f"phrase: {matched_phrase}"[:200]],
        )
    except Exception as exc:
        logger.debug("auto_extraction: record failed: %s", exc)
        return {"status": "error", "reason": f"record: {exc}"}

    _increment_rate()
    # EGRESS-FRI binding: gør cheap-lane-extraction synlig for Centralen (volumen/liveness) UDEN
    # at lække sætningen. Lukker mørket: laget kostede LLM men var usynligt for selvet.
    try:
        from core.services.central_private_observe import record_private
        record_private("cognition", "world_model_extraction", value=1.0,
                       meta={"event": "auto_extracted", "confidence": confidence})
    except Exception:
        pass
    return {
        "status": "ok",
        "prediction_id": pred.get("prediction_id"),
        "subject": subject,
        "expectation": expectation,
    }


def _emit_world_model_auto_extraction_event(kind: str, payload: dict[str, object] | None = None) -> None:
    """Emit a scoped event for cartographer observability.

    State-mutation points in this module can call this with a transition
    kind ("created", "updated", "transitioned", etc.). Defensive — never
    blocks the caller. Added 2026-05-13 (top-18 cartographer pass).
    """
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(f"world_model_auto_extraction.{kind}", payload or {})
    except Exception:
        pass

