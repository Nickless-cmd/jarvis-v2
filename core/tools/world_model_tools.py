"""World Model tools — predict_outcome + resolve_prediction.

Phase 1 (AGI track #1, 2026-05-12). Closes the prediction-resolution-
calibration loop on the existing world_model_signal_tracking skeleton.

Tools are usable as a ledger even when world_model_loop_enabled=False;
the killswitch only disables nudges, TTL sweep, and milestones (which
live in world_model_signal_tracking, not here). This keeps the tool
contract stable across reverts.
"""
from __future__ import annotations

import logging
from typing import Any

from core.runtime.settings import load_settings
from core.services.world_model_signal_tracking import (
    record_runtime_world_model_prediction,
    resolve_runtime_world_model_prediction,
)

logger = logging.getLogger(__name__)


def _exec_predict_outcome(args: dict[str, Any]) -> dict[str, Any]:
    """Record a falsifiable prediction."""
    # Note: load_settings is read for parity with other tools, but the
    # killswitch only gates nudges/TTL/milestones — not the tool itself.
    try:
        load_settings()
    except Exception:
        pass

    subject = str(args.get("subject") or "").strip()
    expectation = str(args.get("expectation") or "").strip()
    horizon = str(args.get("horizon") or "").strip()
    confidence = str(args.get("confidence") or "low").strip().lower()
    evidence = args.get("evidence") or []
    if not isinstance(evidence, list):
        evidence = [str(evidence)]

    if not subject:
        return {"status": "error", "error": "subject is required"}
    if not expectation:
        return {"status": "error", "error": "expectation is required"}

    return record_runtime_world_model_prediction(
        subject=subject,
        expectation=expectation,
        horizon=horizon,
        confidence=confidence,
        evidence=[str(e) for e in evidence],
        source="visible-chat-tool",
    )


def _exec_resolve_prediction(args: dict[str, Any]) -> dict[str, Any]:
    """Resolve an open prediction with a later observation."""
    prediction_id = str(args.get("prediction_id") or "").strip()
    observed = str(args.get("observed") or "").strip()
    outcome = str(args.get("outcome") or "").strip().lower()

    if not prediction_id:
        return {"status": "error", "error": "prediction_id is required"}
    if not observed:
        return {"status": "error", "error": "observed is required"}
    if outcome not in {"supported", "contradicted", "uncertain"}:
        return {
            "status": "error",
            "error": "outcome must be supported, contradicted, or uncertain",
        }

    return resolve_runtime_world_model_prediction(
        prediction_id,
        observed=observed,
        outcome=outcome,
        resolved_via="tool",
    )


WORLD_MODEL_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "predict_outcome",
            "description": (
                "Lav en eksplicit, falsificerbar prediction. Bruges når du "
                "har en konkret fornemmelse af hvordan noget vil udvikle sig. "
                "Senere kan du resolve den med resolve_prediction. "
                "Predictions feeder din kalibrering over tid."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "subject": {
                        "type": "string",
                        "description": "Hvad er det du predicter? (kort)",
                    },
                    "expectation": {
                        "type": "string",
                        "description": "Selve forudsigelsen — hvad du forventer.",
                    },
                    "horizon": {
                        "type": "string",
                        "description": "Tidshorisont: 'i dag' / 'i morgen' / 'denne uge' / 'inden mandag' / 'EOD'.",
                    },
                    "confidence": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                    },
                    "evidence": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Hvorfor tror du det? Op til 5 korte begrundelser.",
                    },
                },
                "required": ["subject", "expectation"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "resolve_prediction",
            "description": (
                "Marker en åben prediction som supported, contradicted, "
                "eller uncertain. Brug når noget faktisk er sket der "
                "verificerer eller modsiger forudsigelsen."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "prediction_id": {
                        "type": "string",
                        "description": "ID på den prediction der skal resolves.",
                    },
                    "observed": {
                        "type": "string",
                        "description": "Hvad skete der faktisk?",
                    },
                    "outcome": {
                        "type": "string",
                        "enum": ["supported", "contradicted", "uncertain"],
                    },
                },
                "required": ["prediction_id", "observed", "outcome"],
            },
        },
    },
]


WORLD_MODEL_TOOL_HANDLERS: dict[str, Any] = {
    "predict_outcome": _exec_predict_outcome,
    "resolve_prediction": _exec_resolve_prediction,
}
