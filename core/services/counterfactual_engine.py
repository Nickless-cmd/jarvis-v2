"""Counterfactual reflection orchestrator.

Phase 1 (dry-run): captures triggers, dedups, stores rows with placeholder
values. No LLM call. No apophenia modulation.

Phase 2-4 will progressively enable:
  - _generate_counterfactuals_via_llm (Phase 2)
  - _modulate_with_apophenia (Phase 3)
  - tool exposition via decisions_tools-style handlers (Phase 4)

Legacy API (classify_event_to_counterfactual, generate_counterfactual, etc.)
is preserved below for backward compatibility.
"""
from __future__ import annotations

import json
import logging
import time
from collections import Counter
from datetime import UTC, datetime
from typing import Any, Optional
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import connect
from core.runtime.settings import RuntimeSettings
from core.services.counterfactual_triggers import (
    TriggerEvent,
    cf_key,
    fetch_recent_triggers,
    fetch_recent_aspiration_triggers,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Phase 1+ pipeline — run() entry point
# ---------------------------------------------------------------------------

def run(*, workspace_id: str = "default", dry_run: bool = True) -> dict:
    """One full pipeline cycle. Always returns a summary dict, never raises.

    dry_run=True (Phase 1 default): skip LLM generation. All counterfactuals
    get what_if='TODO', llm_confidence=0.0, status='generated'.

    Phase 2+ will pass dry_run=False; Phase 1 always uses True.
    """
    started_at = time.monotonic()
    summary: dict[str, Any] = {
        "workspace_id": workspace_id,
        "triggers_fetched": 0,
        "triggers_unique": 0,
        "trigger_breakdown": {},
        "counterfactuals_generated": 0,
        "promoted": 0,
        "llm_generation_failures": 0,
        "elapsed_ms": 0,
        "skipped": False,
        "skipped_reason": "",
        "phase": "1",
    }

    try:
        settings = RuntimeSettings()
    except Exception as exc:
        logger.warning("counterfactual_engine: cannot load settings: %s", exc)
        summary["skipped"] = True
        summary["skipped_reason"] = "settings-load-error"
        summary["elapsed_ms"] = int((time.monotonic() - started_at) * 1000)
        return summary

    if not settings.counterfactual_engine_enabled:
        summary["skipped"] = True
        summary["skipped_reason"] = "killswitch-off"
        summary["elapsed_ms"] = int((time.monotonic() - started_at) * 1000)
        return summary

    # Step 1: fetch triggers (both regret and aspiration)
    try:
        regret_triggers = fetch_recent_triggers(
            workspace_id=workspace_id,
            lookback_minutes=settings.counterfactual_engine_lookback_minutes,
        )
    except Exception as exc:
        logger.warning("counterfactual_engine: regret fetch failed: %s", exc)
        regret_triggers = []

    try:
        aspiration_triggers = fetch_recent_aspiration_triggers(
            workspace_id=workspace_id,
            lookback_minutes=settings.counterfactual_engine_lookback_minutes,
        )
    except Exception as exc:
        logger.warning("counterfactual_engine: aspiration fetch failed: %s", exc)
        aspiration_triggers = []

    triggers = regret_triggers + aspiration_triggers
    if regret_triggers and aspiration_triggers:
        # Prefer positive when both are present — promotes balanced reflection
        triggers = aspiration_triggers + regret_triggers

    summary["triggers_fetched"] = len(triggers)
    summary["regret_count"] = len(regret_triggers)
    summary["aspiration_count"] = len(aspiration_triggers)
    summary["trigger_breakdown"] = dict(Counter(t.event_type for t in triggers))

    if not triggers:
        summary["elapsed_ms"] = int((time.monotonic() - started_at) * 1000)
        _publish_cycle_complete(summary)
        return summary

    # Step 2: dedup (first-pass via cf_key lookup)
    try:
        unique_triggers = _dedup_filter(triggers)
    except Exception as exc:
        logger.warning("counterfactual_engine: dedup failed: %s", exc)
        unique_triggers = triggers  # degrade gracefully — UNIQUE constraint catches dups
    summary["triggers_unique"] = len(unique_triggers)

    if not unique_triggers:
        summary["elapsed_ms"] = int((time.monotonic() - started_at) * 1000)
        _publish_cycle_complete(summary)
        return summary

    # Step 2.5: forward-query causal graph for downstream events that would
    # be prunet i hypotesen. Phase 1 returns empty list if graph hasn't
    # tracked edges for this trigger yet — Phase 2 LLM-generation will
    # use this context to populate the what_if field with concrete
    # downstream-event references instead of placeholders.
    downstream_context: list[dict] = []
    try:
        from core.services.causal_graph import query_causal_chain
        for trigger in unique_triggers:
            chain = query_causal_chain(
                event_id=trigger.source_event_id,
                direction="forward",
                max_depth=3,
                min_confidence=0.6,
            )
            if chain.get("chain"):
                downstream_context.append({
                    "trigger_id": trigger.source_event_id,
                    "downstream": [
                        {"id": s["event"]["id"], "kind": s["event"]["kind"]}
                        for s in chain["chain"]
                    ],
                })
    except Exception as exc:
        logger.debug("counterfactual_engine: causal forward-query failed: %s", exc)
    summary["downstream_events_seen"] = sum(
        len(d.get("downstream", [])) for d in downstream_context
    )

    # Step 3: generation (Phase 1: skip; placeholder per trigger)
    if dry_run:
        counterfactuals = [_dry_run_placeholder(t) for t in unique_triggers]
    else:
        # Phase 2 will fill this in; until then it's a no-op stub
        try:
            counterfactuals = _generate_counterfactuals_via_llm(unique_triggers)
        except Exception as exc:
            logger.warning("counterfactual_engine: LLM generation failed: %s", exc)
            summary["llm_generation_failures"] += 1
            counterfactuals = [_failed_generation_placeholder(t) for t in unique_triggers]

    # Step 4: apophenia modulation (Phase 3+; Phase 1 stub returns 1.0)
    counterfactuals = _modulate_with_apophenia(counterfactuals)

    # Step 5: store
    threshold = settings.counterfactual_engine_promotion_threshold
    for cf in counterfactuals:
        cf["status"] = (
            "promoted" if cf["final_confidence"] >= threshold else "generated"
        )
        try:
            _store_counterfactual(workspace_id=workspace_id, **cf)
        except Exception as exc:
            logger.warning("counterfactual_engine: store failed: %s", exc)
            continue
        summary["counterfactuals_generated"] += 1
        if cf["status"] == "promoted":
            summary["promoted"] += 1

        # Step 6: publish per-cf event with explicit caused_by trigger
        # (causal graph two-way integration — commit 894a214). Use first
        # trigger_event_id as the causal parent; if multiple triggers
        # contributed, downstream queries can still find them all via
        # trigger_event_ids_json on the counterfactual record.
        try:
            _trigger_ids = cf.get("trigger_event_ids") or []
            _first_trigger = int(_trigger_ids[0]) if _trigger_ids else None
            _publish_event(
                cf_id=cf["cf_id"],
                workspace_id=workspace_id,
                cluster_size=len(_trigger_ids),
                final_confidence=cf["final_confidence"],
                status=cf["status"],
                caused_by_trigger_id=_first_trigger,
            )
        except Exception:
            pass

        # Step 7: bind a real counterfactual (non-placeholder) to a
        # world-model prediction. Skips TODO placeholders since they
        # carry no semantic claim worth predicting on. trigger_types[0]
        # in the new pipeline IS the eventbus kind (e.g. "conflict.detected"),
        # so it doubles as event_kind for the Phase 2 frequency comparison.
        try:
            _what_if = str(cf.get("what_if") or "").strip()
            if _what_if and _what_if != "TODO" and _what_if != "[generation failed]":
                from core.services.counterfactual_predictions import (
                    bind_counterfactual_to_prediction,
                )
                _trigger_types = cf.get("trigger_types") or []
                _primary_type = str(_trigger_types[0]) if _trigger_types else "unknown"
                bind_counterfactual_to_prediction(
                    cf_id=cf["cf_id"],
                    trigger_type=_primary_type,
                    anchor=_what_if[:200],
                    confidence=float(cf.get("final_confidence", 0.0)),
                    source="counterfactual",
                    event_kind=_primary_type,
                )
        except Exception as exc:
            logger.debug("counterfactual_engine: pipeline binding failed: %s", exc)

    summary["elapsed_ms"] = int((time.monotonic() - started_at) * 1000)
    _publish_cycle_complete(summary)
    return summary


def _dry_run_placeholder(trigger: TriggerEvent) -> dict:
    """Phase 1: every unique trigger becomes a TODO counterfactual."""
    return {
        "cf_id": f"cf-{uuid4().hex[:16]}",
        "cf_key": cf_key(trigger.workspace_id, trigger.event_type, trigger.primary_key),
        "cluster_id": f"cluster-{trigger.source_event_id}",
        "trigger_event_ids": [trigger.source_event_id],
        "trigger_types": [trigger.event_type],
        "what_if": "TODO",
        "likely_difference": None,
        "reasoning": None,
        "llm_confidence": 0.0,
        "apophenia_score": 1.0,
        "final_confidence": 0.0,
    }


def _failed_generation_placeholder(trigger: TriggerEvent) -> dict:
    """Phase 2+: when LLM call fails, store with a marker so we can see frequency."""
    return {
        "cf_id": f"cf-{uuid4().hex[:16]}",
        "cf_key": cf_key(trigger.workspace_id, trigger.event_type, trigger.primary_key),
        "cluster_id": f"cluster-{trigger.source_event_id}",
        "trigger_event_ids": [trigger.source_event_id],
        "trigger_types": [trigger.event_type],
        "what_if": "[generation failed]",
        "likely_difference": None,
        "reasoning": None,
        "llm_confidence": 0.0,
        "apophenia_score": 1.0,
        "final_confidence": 0.0,
    }


def _dedup_filter(triggers: list[TriggerEvent]) -> list[TriggerEvent]:
    """Remove triggers whose cf_key is already stored in the DB."""
    if not triggers:
        return []
    keys = [
        cf_key(t.workspace_id, t.event_type, t.primary_key) for t in triggers
    ]
    placeholders = ",".join("?" for _ in keys)
    with connect() as c:
        rows = c.execute(
            f"SELECT cf_key FROM counterfactuals WHERE cf_key IN ({placeholders})",
            keys,
        ).fetchall()
    existing = {str(r["cf_key"]) for r in rows}
    return [
        t for t, k in zip(triggers, keys) if k not in existing
    ]


def _generate_counterfactuals_via_llm(triggers: list[TriggerEvent]) -> list[dict]:
    """Phase 2 stub. Returns empty list in Phase 1.

    Will be implemented in Phase 2 plan as a single cheap-lane LLM call.
    """
    return []


def _modulate_with_apophenia(counterfactuals: list[dict]) -> list[dict]:
    """Phase 3 stub. Returns counterfactuals unchanged with apophenia_score=1.0.

    Will be implemented in Phase 3 plan as per-cf apophenia_guard.rate_hypothesis()
    call. final_confidence = min(llm_confidence, apophenia_score).
    """
    for cf in counterfactuals:
        cf.setdefault("apophenia_score", 1.0)
        cf["final_confidence"] = min(
            float(cf.get("llm_confidence", 0.0)),
            float(cf["apophenia_score"]),
        )
    return counterfactuals


def _store_counterfactual(*, workspace_id: str, **cf) -> None:
    """INSERT OR IGNORE — UNIQUE(cf_key) makes this idempotent."""
    now = datetime.now(UTC).isoformat()
    with connect() as c:
        c.execute(
            "INSERT OR IGNORE INTO counterfactuals("
            "cf_id, cf_key, workspace_id, cluster_id, "
            "trigger_event_ids_json, trigger_types_json, "
            "what_if, likely_difference, reasoning, "
            "llm_confidence, apophenia_score, final_confidence, "
            "status, created_at, updated_at"
            ") VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                cf["cf_id"], cf["cf_key"], workspace_id, cf["cluster_id"],
                json.dumps(cf["trigger_event_ids"]),
                json.dumps(cf["trigger_types"]),
                cf["what_if"], cf.get("likely_difference"), cf.get("reasoning"),
                float(cf["llm_confidence"]),
                float(cf["apophenia_score"]),
                float(cf["final_confidence"]),
                cf["status"], now, now,
            ),
        )
        c.commit()


def _publish_event(
    *, cf_id: str, workspace_id: str, cluster_size: int,
    final_confidence: float, status: str,
    caused_by_trigger_id: int | None = None,
) -> None:
    """Publish counterfactual event. If caused_by_trigger_id is given,
    a causal edge is written linking this counterfactual to its trigger
    (Phase 1 backward integration with causal graph — commit 894a214)."""
    if caused_by_trigger_id is not None:
        event_bus.publish(
            "cognitive_counterfactual.generated",
            {
                "cf_id": cf_id,
                "workspace_id": workspace_id,
                "cluster_size": cluster_size,
                "final_confidence": float(final_confidence),
                "status": status,
            },
            caused_by=int(caused_by_trigger_id),
            edge_kind="caused",
        )
    else:
        event_bus.publish("cognitive_counterfactual.generated", {
            "cf_id": cf_id,
            "workspace_id": workspace_id,
            "cluster_size": cluster_size,
            "final_confidence": float(final_confidence),
            "status": status,
        })


def _publish_cycle_complete(summary: dict) -> None:
    try:
        event_bus.publish("cognitive_counterfactual.cycle_complete", dict(summary))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Legacy API — preserved for backward compatibility
# ---------------------------------------------------------------------------

try:
    from core.runtime.db import (
        insert_cognitive_counterfactual,
        list_cognitive_counterfactuals,
    )
    _LEGACY_DB_AVAILABLE = True
except ImportError:
    _LEGACY_DB_AVAILABLE = False

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
        event_kind=event_kind,
    )


def generate_counterfactual(
    *,
    trigger_type: str,
    anchor: str,
    source: str = "runtime",
    confidence: float = 0.5,
    cf_question: str = "",
    event_kind: str = "",
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

    if not _LEGACY_DB_AVAILABLE:
        logger.warning("counterfactual_engine: legacy DB functions unavailable")
        result: dict[str, object] = {
            "cf_id": cf_id,
            "trigger_type": trigger_type,
            "anchor": anchor[:200],
            "cf_question": question,
            "source": source,
            "confidence": confidence,
        }
    else:
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

    # Bind to a world-model prediction so the calibration loop has
    # something to chew on. Best-effort — never blocks counterfactual
    # creation (2026-05-14 fix: previously 0/1019 generated counterfactuals
    # were bound to predictions).
    try:
        from core.services.counterfactual_predictions import (
            bind_counterfactual_to_prediction,
        )
        bind_counterfactual_to_prediction(
            cf_id=cf_id,
            trigger_type=trigger_type,
            anchor=anchor,
            confidence=float(confidence),
            source="counterfactual",
            event_kind=event_kind,
        )
    except Exception as exc:
        logger.debug("counterfactual_engine: prediction binding failed: %s", exc)
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


def narrativize_aspiration(
    *,
    trigger_type: str,
    anchor: str,
    actual_outcome: str = "",
    positive_effect: str = "",
) -> str:
    """Turn a success/kept-decision into an aspiration narrative.

    Positive counterpart to narrativize_regret — captures what went
    right so it can be repeated and built upon.
    """
    parts = []
    if trigger_type == "kept":
        parts.append(f"Du holdt fast i {anchor[:60]}")
        if actual_outcome:
            parts.append(f"Det førte til: {actual_outcome[:60]}")
        if positive_effect:
            parts.append(f"Virkning: {positive_effect[:60]}")
        parts.append("Hvordan kan du gøre det igen?")
    elif trigger_type == "goal_completed":
        parts.append(f"Målet {anchor[:60]} blev nået")
        if positive_effect:
            parts.append(f"Det betød: {positive_effect[:60]}")
        parts.append("Hvad kan du lære af den vej?")
    elif trigger_type == "conflict_resolved":
        parts.append(f"Konflikten omkring {anchor[:60]} blev løst")
        parts.append("Hvad gjorde forskellen?")
    else:
        parts.append(f"En vej viste sig at være rigtig ved {anchor[:60]}")
    return ". ".join(parts)


def build_counterfactual_surface() -> dict[str, object]:
    if not _LEGACY_DB_AVAILABLE:
        return {"active": False, "items": [], "dream_count": 0, "runtime_count": 0,
                "summary": "Legacy DB unavailable"}
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
