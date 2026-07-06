"""Trigger detection for counterfactual reflection.

Reads recent regret-events from the events table and normalizes them
into TriggerEvent records. Each event-family has a primary-key extractor
that picks the most stable identifier from the payload.
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Callable

from core.runtime.db import connect

logger = logging.getLogger(__name__)


@dataclass
class TriggerEvent:
    """A regret-worthy event normalized for counterfactual processing."""
    source_event_id: int
    workspace_id: str
    event_type: str
    primary_key: str
    summary: str
    payload: dict
    created_at: str


def _key_self_review(payload: dict) -> str:
    return str(payload.get("review_id") or payload.get("run_id") or "").strip()


def _key_conflict(payload: dict) -> str:
    """Primary key for conflict.detected events.

    Tries stable identifiers first (conflict_id, run_id). Falls back to
    a composite of conflict_type + phrase-hash when neither is present —
    which is the actual schema currently emitted by the conflict
    detector (2026-05-14 fix: 138/138 events on 7-day window had only
    conflict_type+phrase, no conflict_id, so the whole family was being
    silently dropped).
    """
    explicit = str(payload.get("conflict_id") or payload.get("run_id") or "").strip()
    if explicit:
        return explicit
    conflict_type = str(payload.get("conflict_type") or "").strip()
    phrase = str(payload.get("phrase") or "").strip()
    if conflict_type and phrase:
        phrase_hash = hashlib.sha1(phrase.encode("utf-8", errors="ignore")).hexdigest()[:16]
        return f"{conflict_type}:{phrase_hash}"
    if conflict_type:
        return conflict_type
    return ""


def _key_decision(payload: dict) -> str:
    return str(payload.get("decision_id") or "").strip()


def _key_review(payload: dict) -> str:
    return str(payload.get("review_id") or "").strip()


def _key_goal(payload: dict) -> str:
    return str(payload.get("goal_id") or "").strip()


def _key_decision_kept(payload: dict) -> str:
    return str(payload.get("decision_id") or payload.get("review_id") or "").strip()


def _key_conflict_resolved(payload: dict) -> str:
    return str(payload.get("conflict_id") or payload.get("run_id") or "").strip()


# Positive event families — aspiration triggers for counterfactual reflection.
# Mirrors the regret families using the same TriggerEvent/cf_key/dedup pipeline.
_ASPIRATION_TRIGGER_FAMILIES: dict[str, Callable[[dict], str]] = {
    "behavioral_decision_review.kept": _key_decision_kept,
    "behavioral_decision_review.partial": _key_decision_kept,
    "goal.completed": _key_goal,
    "goal.updated": _key_goal,
    "conflict.resolved": _key_conflict_resolved,
}

# event_type → primary_key extractor
_TRIGGER_FAMILIES: dict[str, Callable[[dict], str]] = {
    "self_review_outcome.created": _key_self_review,
    "conflict.detected": _key_conflict,
    "decision_revoked": _key_decision,
    "behavioral_decision_review.broken": _key_review,
}


def cf_key(workspace_id: str, event_type: str, primary_key: str) -> str:
    """First-pass dedup hash. Same workspace+type+key = same hash = skip."""
    raw = f"{workspace_id}:{event_type}:{primary_key}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:24]


def _extract_summary(payload: dict) -> str:
    for k in ("summary", "reason", "message", "directive", "note"):
        v = payload.get(k)
        if v:
            return str(v)[:300]
    return ""


def fetch_recent_aspiration_triggers(
    *, workspace_id: str, lookback_minutes: int = 60
) -> list[TriggerEvent]:
    """Query events table for recent aspiration-worthy (positive) events.

    Returns TriggerEvents for the 5 positive trigger families:
    kept/partial decisions, completed/updated goals, resolved conflicts.
    Uses the same TriggerEvent/cf_key/dedup pipeline as regret triggers.
    """
    cutoff = (datetime.now(UTC) - timedelta(minutes=max(1, int(lookback_minutes)))).isoformat()
    families = _ASPIRATION_TRIGGER_FAMILIES
    placeholders = ",".join("?" for _ in families)
    sql = (
        f"SELECT id, kind, payload_json, created_at FROM events "
        f"WHERE kind IN ({placeholders}) AND created_at >= ? "
        f"ORDER BY id ASC"
    )
    params = list(families.keys()) + [cutoff]

    out: list[TriggerEvent] = []
    try:
        with connect() as c:
            rows = c.execute(sql, params).fetchall()
    except Exception as exc:
        logger.warning("counterfactual_triggers: aspiration query failed: %s", exc)
        return []

    for r in rows:
        try:
            payload = json.loads(r["payload_json"] or "{}")
        except Exception:
            payload = {}
        event_type = str(r["kind"] or "")
        extractor = families.get(event_type)
        if extractor is None:
            continue
        primary_key = extractor(payload)
        if not primary_key:
            continue
        out.append(TriggerEvent(
            source_event_id=int(r["id"]),
            workspace_id=str(workspace_id),
            event_type=event_type,
            primary_key=primary_key,
            summary=_extract_summary(payload),
            payload=payload,
            created_at=str(r["created_at"] or ""),
        ))
    return out


def fetch_recent_triggers(
    *, workspace_id: str, lookback_minutes: int = 60
) -> list[TriggerEvent]:
    """Query events table for recent regret-worthy events.

    Returns TriggerEvents for the 4 trigger families. Events whose
    primary-key extractor returns empty string are skipped (we need a
    stable identifier for cf_key dedup).
    """
    cutoff = (datetime.now(UTC) - timedelta(minutes=max(1, int(lookback_minutes)))).isoformat()
    placeholders = ",".join("?" for _ in _TRIGGER_FAMILIES)
    sql = (
        f"SELECT id, kind, payload_json, created_at FROM events "
        f"WHERE kind IN ({placeholders}) AND created_at >= ? "
        f"ORDER BY id ASC"
    )
    params = list(_TRIGGER_FAMILIES.keys()) + [cutoff]

    out: list[TriggerEvent] = []
    try:
        with connect() as c:
            rows = c.execute(sql, params).fetchall()
    except Exception as exc:
        logger.warning("counterfactual_triggers: events query failed: %s", exc)
        return []

    for r in rows:
        try:
            payload = json.loads(r["payload_json"] or "{}")
        except Exception:
            payload = {}
        event_type = str(r["kind"] or "")
        extractor = _TRIGGER_FAMILIES.get(event_type)
        if extractor is None:
            continue
        primary_key = extractor(payload)
        if not primary_key:
            # Skip events without stable identifier — can't dedup safely
            continue
        out.append(TriggerEvent(
            source_event_id=int(r["id"]),
            workspace_id=str(workspace_id),
            event_type=event_type,
            primary_key=primary_key,
            summary=_extract_summary(payload),
            payload=payload,
            created_at=str(r["created_at"] or ""),
        ))
    return out


