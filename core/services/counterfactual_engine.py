"""Counterfactual Engine — "What if we had chosen differently?"

Generates alternative scenarios from decisions, regrets, and incidents.
During idle time, can also generate "dream counterfactuals" —
speculative what-if scenarios about recent work.
"""

from __future__ import annotations

import logging
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import (
    insert_cognitive_counterfactual,
    list_cognitive_counterfactuals,
)

logger = logging.getLogger(__name__)

_TRIGGER_TEMPLATES = {
    "regret": "Hvad hvis vi havde valgt en anden tilgang til {anchor}?",
    "incident": "Hvad hvis vi havde opdaget {anchor} tidligere?",
    "decision": "Hvad hvis vi havde valgt anderledes ved {anchor}?",
    "dream": "Hvad hvis {anchor} havde været løst fra starten?",
}

# Event-klassifikations-tabel porteret fra jarvis-ai/counterfactuals.py.
# Specifikke what-if'er pr. event-mønster, ikke generiske templates.
_CLASSIFIED_WHAT_IFS: list[dict[str, object]] = [
    {
        "match_kinds": ("regret.opened", "regret.updated"),
        "match_payload_keys": ("regret_id",),
        "trigger_type": "regret_validation",
        "what_if": "Hvad hvis vi havde valgt en langsommere valideringssti før vi committede?",
        "confidence": 0.68,
    },
    {
        "match_kinds": ("rupture.approval_rejected", "tool.approval_resolved"),
        "match_payload_status": ("denied", "rejected"),
        "trigger_type": "approval_rejected",
        "what_if": "Hvad hvis jeg havde foreslået et mindre skridt først?",
        "confidence": 0.65,
    },
    {
        "match_kinds_startswith": ("incident.", "tool.completed"),
        "match_payload_status": ("error", "failed", "degraded"),
        "trigger_type": "mitigation_timing",
        "what_if": "Hvad hvis mitigation var aktiveret ét skridt tidligere?",
        "confidence": 0.64,
    },
    {
        "match_text_terms": ("architecture", "arkitektur", "tradeoff", "design choice"),
        "trigger_type": "architecture_tradeoff",
        "what_if": "Hvad hvis vi havde valgt den alternative arkitektur-tradeoff her?",
        "confidence": 0.62,
    },
    {
        "match_kinds": ("cognitive_chronicle.entry_written",),
        "trigger_type": "weekly_direction",
        "what_if": "Hvad hvis denne periode havde prioriteret det næstbedste initiativ i stedet?",
        "confidence": 0.55,
    },
]


def classify_event_to_counterfactual(
    event_kind: str, payload: dict[str, object]
) -> dict[str, object] | None:
    """Classify an event into a specific counterfactual, or None if no match.

    Returns {"trigger_type", "what_if", "confidence", "anchor"} on match.
    Ported from jarvis-ai/counterfactuals._classify_trigger — v2-tilpasset
    med nye match-kriterier (fx rupture.* events + approval-flows).
    """
    kind = str(event_kind or "").strip().lower()
    if not kind:
        return None
    status = str(
        payload.get("status") or payload.get("outcome") or payload.get("decision") or ""
    ).strip().lower()
    text_blob = " ".join([
        kind,
        str(payload.get("reason") or ""),
        str(payload.get("summary") or ""),
        str(payload.get("message") or ""),
    ]).lower()

    for rule in _CLASSIFIED_WHAT_IFS:
        matched = False
        if "match_kinds" in rule:
            if kind in tuple(rule["match_kinds"]):  # type: ignore[arg-type]
                matched = True
        if not matched and "match_kinds_startswith" in rule:
            if any(kind.startswith(pre) for pre in tuple(rule["match_kinds_startswith"])):  # type: ignore[arg-type]
                matched = True
        if not matched and "match_payload_keys" in rule:
            if any(payload.get(k) for k in tuple(rule["match_payload_keys"])):  # type: ignore[arg-type]
                matched = True
        if not matched and "match_text_terms" in rule:
            if any(term in text_blob for term in tuple(rule["match_text_terms"])):  # type: ignore[arg-type]
                matched = True
        if not matched:
            continue

        # Secondary filter on status if specified
        if "match_payload_status" in rule:
            if status not in tuple(rule["match_payload_status"]):  # type: ignore[arg-type]
                continue

        anchor = (
            str(payload.get("regret_id") or "")
            or str(payload.get("incident_id") or "")
            or str(payload.get("run_id") or "")
            or str(payload.get("approval_id") or "")
            or str(payload.get("tool") or "")
            or str(payload.get("summary") or "")[:80]
            or kind
        )
        return {
            "trigger_type": str(rule["trigger_type"]),
            "what_if": str(rule["what_if"]),
            "confidence": float(rule["confidence"]),  # type: ignore[arg-type]
            "anchor": anchor,
        }
    return None


def generate_classified_counterfactual(
    event_kind: str, payload: dict[str, object]
) -> dict[str, object] | None:
    """Convenience: classify event → persist counterfactual if matched.

    Returns the persisted counterfactual row or None.
    """
    classification = classify_event_to_counterfactual(event_kind, payload)
    if classification is None:
        return None
    return generate_counterfactual(
        trigger_type=str(classification["trigger_type"]),
        anchor=str(classification["anchor"]),
        source="classified",
        confidence=float(classification["confidence"]),
        cf_question=str(classification["what_if"]),
    )


def generate_counterfactual(
    *,
    trigger_type: str,
    anchor: str,
    source: str = "runtime",
    confidence: float = 0.5,
    cf_question: str = "",
) -> dict[str, object]:
    """Generate a counterfactual question from a trigger event.

    If cf_question is provided (non-empty), it overrides the template —
    used by classify_event_to_counterfactual for specific what-ifs.
    """
    if cf_question.strip():
        question = cf_question.strip()
    else:
        template = _TRIGGER_TEMPLATES.get(trigger_type, "Hvad hvis {anchor} var gået anderledes?")
        question = template.format(anchor=anchor[:80])

    cf_id = f"cf-{uuid4().hex[:10]}"
    result = insert_cognitive_counterfactual(
        cf_id=cf_id,
        trigger_type=trigger_type,
        anchor=anchor[:200],
        cf_question=question,
        source=source,
        confidence=confidence,
    )

    event_bus.publish(
        "cognitive_counterfactual.generated",
        {"cf_id": cf_id, "trigger_type": trigger_type, "source": source},
    )
    return result


def generate_dream_counterfactual(
    *,
    recent_decisions: list[dict] | None = None,
) -> dict[str, object] | None:
    """Generate a speculative counterfactual during idle time."""
    decisions = recent_decisions or []
    if not decisions:
        return None

    # Pick the most recent decision
    latest = decisions[0]
    title = str(latest.get("title") or "")
    if not title:
        return None

    return generate_counterfactual(
        trigger_type="dream",
        anchor=title,
        source="dream",
        confidence=0.3,
    )


def narrativize_regret(
    *,
    trigger_type: str,
    anchor: str,
    actual_outcome: str = "",
    time_cost: str = "",
) -> str:
    """Turn a regret into a felt narrative, not just data."""
    parts = []
    if trigger_type == "regret":
        parts.append(f"Du valgte {anchor[:60]}")
        if actual_outcome:
            parts.append(f"Resultatet blev: {actual_outcome[:60]}")
        if time_cost:
            parts.append(f"Det kostede {time_cost}")
        parts.append("Næste gang: start bredere eller verificér tidligere")
    elif trigger_type == "incident":
        parts.append(f"Noget gik galt med {anchor[:60]}")
        parts.append("Hvad hvis du havde opdaget det tidligere?")
    else:
        parts.append(f"En anden vej var mulig ved {anchor[:60]}")
    return ". ".join(parts)


def build_counterfactual_surface() -> dict[str, object]:
    items = list_cognitive_counterfactuals(limit=15)
    dream_count = sum(1 for i in items if i.get("source") == "dream")
    runtime_count = len(items) - dream_count
    return {
        "active": bool(items),
        "items": items,
        "dream_count": dream_count,
        "runtime_count": runtime_count,
        "summary": (
            f"{len(items)} counterfactuals ({runtime_count} runtime, {dream_count} dream)"
            if items else "No counterfactuals yet"
        ),
    }
