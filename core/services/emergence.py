"""Emergence — evidence-based pattern detection across recent activity.

Porteret fra jarvis-ai/agent/cognition/emergence.py (2026-05-07).

I modsætning til counterfactuals (modkontrafaktiske hypotheser om hvad
der KUNNE være sket) er emergence EVIDENS-baseret: "der er nu nok data
til at sige noget om hvad der ER ved at ske". Pattern-candidaten passes
gennem apophenia_guard for at undgå overinterpretation.

Fire candidate-typer (samme som original):

  1. issue_cluster_incident — gentagne tool.error/incident events
  2. capability_growth_procedures — stigende cognitive_procedures
  3. direction_drift_decisions — flere recent behavioral_decisions
  4. unifying_problem_blocking — gentagne blocked/denied events

Hver candidate scores via apophenia_guard og persisteres i ny tabel
emergent_patterns. Status er én af: candidate, upgraded, downgraded,
rejected (apophenia bestemmer).

V2-tilpasning ift. jarvis-ai original:
- Kilder: events (kind/payload_json), cognitive_procedures,
  behavioral_decisions — alle eksisterende v2-tabeller
- Ingen mind_store-afhængighed — bygger eget patterns-table
- Publiserer pattern_candidate_* events
- Adapterer apophenia_guard.assess_pattern (returnerer dict, ikke dataclass)
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.db import connect
from core.services.apophenia_guard import assess_pattern

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmergenceCandidate:
    pattern_key: str
    title: str
    summary: str
    evidence_count: int
    base_confidence: float
    competing_explanations: list[str]
    confounders: list[str]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _ensure_table() -> None:
    """Create emergent_patterns table if missing. Idempotent."""
    with connect() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS emergent_patterns (
                pattern_key TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                summary TEXT NOT NULL,
                confidence REAL NOT NULL DEFAULT 0.0,
                evidence_count INTEGER NOT NULL DEFAULT 0,
                competing_explanations_json TEXT NOT NULL DEFAULT '[]',
                confounders_json TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'candidate',
                first_detected_at TEXT NOT NULL,
                last_updated_at TEXT NOT NULL,
                evaluation_count INTEGER NOT NULL DEFAULT 1
            )
            """
        )


def _fetch_recent_events(*, window_days: int = 21, limit: int = 2400) -> list[dict[str, Any]]:
    """Pull recent events from the eventbus events table."""
    cutoff = (datetime.now(UTC) - timedelta(days=max(1, window_days))).isoformat()
    try:
        with connect() as c:
            rows = c.execute(
                """
                SELECT kind, payload_json, created_at
                FROM events
                WHERE created_at >= ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (cutoff, limit),
            ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            try:
                d["payload"] = json.loads(d.get("payload_json") or "{}")
            except Exception:
                d["payload"] = {}
            out.append(d)
        return out
    except Exception as exc:
        logger.debug("emergence: fetch events failed: %s", exc)
        return []


def _count_by_kind_prefix(events: list[dict[str, Any]], prefix: str) -> int:
    safe = str(prefix or "").strip().lower()
    if not safe:
        return 0
    return sum(
        1 for e in events
        if str(e.get("kind") or "").strip().lower().startswith(safe)
    )


def _count_blocked(events: list[dict[str, Any]]) -> int:
    """Count events that look like blocked/denied signals."""
    n = 0
    for e in events:
        kind = str(e.get("kind") or "").lower()
        if "blocked" in kind or "denied" in kind or "rejected" in kind:
            n += 1
            continue
        payload = e.get("payload") or {}
        if not isinstance(payload, dict):
            continue
        decision = str(payload.get("decision") or "").strip().lower()
        if decision in {"blocked", "deny", "denied", "reject"}:
            n += 1
    return n


def _fetch_procedures_count() -> int:
    try:
        with connect() as c:
            row = c.execute(
                "SELECT COUNT(*) AS n FROM cognitive_procedures WHERE deleted = 0"
            ).fetchone()
        return int(row["n"]) if row else 0
    except Exception:
        return 0


def _fetch_decisions_count(*, window_days: int = 21) -> int:
    cutoff = (datetime.now(UTC) - timedelta(days=window_days)).isoformat()
    try:
        with connect() as c:
            row = c.execute(
                "SELECT COUNT(*) AS n FROM behavioral_decisions WHERE created_at >= ?",
                (cutoff,),
            ).fetchone()
        return int(row["n"]) if row else 0
    except Exception:
        return 0


def _detect_candidates(*, window_days: int = 21) -> list[EmergenceCandidate]:
    events = _fetch_recent_events(window_days=window_days)
    candidates: list[EmergenceCandidate] = []

    # 1. Incident clusters — events starting with tool.error or incident
    incidentish = (
        _count_by_kind_prefix(events, "tool.error")
        + _count_by_kind_prefix(events, "incident")
    )
    if incidentish >= 3:
        candidates.append(
            EmergenceCandidate(
                pattern_key="issue_cluster_incident",
                title="Repeated Incident Cluster",
                summary=f"{incidentish} incident-like events in the recent window.",
                evidence_count=incidentish,
                base_confidence=min(0.95, 0.34 + (incidentish / 18.0)),
                competing_explanations=["normal_noise", "one-off_provider_outage"],
                confounders=[],
            )
        )

    # 2. Capability growth — count of cognitive_procedures
    proc_count = _fetch_procedures_count()
    if proc_count >= 5:
        candidates.append(
            EmergenceCandidate(
                pattern_key="capability_growth_procedures",
                title="Capability Growth",
                summary=f"{proc_count} procedures indicate expanding stable capability.",
                evidence_count=proc_count,
                base_confidence=min(0.9, 0.3 + (proc_count / 24.0)),
                competing_explanations=["duplicate_procedures"],
                confounders=[],
            )
        )

    # 3. Direction drift — recent behavioral_decisions count
    decision_count = _fetch_decisions_count(window_days=window_days)
    if decision_count >= 4:
        candidates.append(
            EmergenceCandidate(
                pattern_key="direction_drift_decisions",
                title="Direction Drift",
                summary=f"{decision_count} recent decisions suggest evolving direction.",
                evidence_count=decision_count,
                base_confidence=min(0.88, 0.28 + (decision_count / 20.0)),
                competing_explanations=["short_term_task_spike"],
                confounders=[],
            )
        )

    # 4. Unifying blocked problem
    blocked = _count_blocked(events)
    if blocked >= 4:
        candidates.append(
            EmergenceCandidate(
                pattern_key="unifying_problem_blocking",
                title="Hidden Unifying Problem",
                summary=f"{blocked} blocked/rejected signals suggest a shared root issue.",
                evidence_count=blocked,
                base_confidence=min(0.9, 0.32 + (blocked / 22.0)),
                competing_explanations=["temporary_policy_strictness"],
                confounders=[],
            )
        )

    return candidates


def _create_or_update_pattern(
    *,
    pattern_key: str,
    title: str,
    summary: str,
    confidence: float,
    evidence_count: int,
    competing_explanations: list[str],
    confounders: list[str],
    status: str,
) -> dict[str, Any]:
    """Insert or update a pattern row. Returns the persisted row."""
    _ensure_table()
    now = _now_iso()
    with connect() as c:
        existing = c.execute(
            "SELECT * FROM emergent_patterns WHERE pattern_key = ?",
            (pattern_key,),
        ).fetchone()
        if existing:
            c.execute(
                """
                UPDATE emergent_patterns SET
                    title = ?, summary = ?, confidence = ?,
                    evidence_count = ?, competing_explanations_json = ?,
                    confounders_json = ?, status = ?,
                    last_updated_at = ?, evaluation_count = evaluation_count + 1
                WHERE pattern_key = ?
                """,
                (
                    title, summary, float(confidence), int(evidence_count),
                    json.dumps(competing_explanations or []),
                    json.dumps(confounders or []),
                    status, now, pattern_key,
                ),
            )
        else:
            c.execute(
                """
                INSERT INTO emergent_patterns
                (pattern_key, title, summary, confidence, evidence_count,
                 competing_explanations_json, confounders_json, status,
                 first_detected_at, last_updated_at, evaluation_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    pattern_key, title, summary, float(confidence),
                    int(evidence_count),
                    json.dumps(competing_explanations or []),
                    json.dumps(confounders or []),
                    status, now, now,
                ),
            )
        row = c.execute(
            "SELECT * FROM emergent_patterns WHERE pattern_key = ?",
            (pattern_key,),
        ).fetchone()
    return dict(row) if row else {}


def detect_and_score_patterns(*, window_days: int = 21) -> list[dict[str, Any]]:
    """Main entry — detect candidates, score via apophenia, persist, emit events.

    Returns list of result dicts with pattern + assessment + event_type.
    """
    candidates = _detect_candidates(window_days=window_days)
    out: list[dict[str, Any]] = []
    for c_ in candidates:
        assessed = assess_pattern(
            observation_count=c_.evidence_count,
            base_confidence=c_.base_confidence,
            competing_explanations=list(c_.competing_explanations),
            confounders=list(c_.confounders),
        )
        confidence = float(assessed.get("confidence") or 0.0)
        status = str(assessed.get("status") or "candidate")
        # apophenia_guard may return adjusted confounders/alternatives;
        # surface them if present, fall back to the input.
        confounders_out = list(assessed.get("confounders") or c_.confounders)
        alternatives_out = list(
            assessed.get("alternatives")
            or assessed.get("competing_explanations")
            or c_.competing_explanations
        )
        row = _create_or_update_pattern(
            pattern_key=c_.pattern_key,
            title=c_.title,
            summary=c_.summary,
            confidence=confidence,
            evidence_count=c_.evidence_count,
            competing_explanations=alternatives_out,
            confounders=confounders_out,
            status=status,
        )
        # Event names use family.name format per eventbus contract.
        # Family "emergence" added to ALLOWED_EVENT_FAMILIES alongside this port.
        event_type = {
            "candidate": "emergence.pattern_candidate_detected",
            "upgraded": "emergence.pattern_candidate_upgraded",
            "downgraded": "emergence.pattern_candidate_downgraded",
            "rejected": "emergence.pattern_candidate_rejected",
        }.get(status, "emergence.pattern_candidate_detected")
        try:
            event_bus.publish(
                event_type,
                {
                    "pattern_key": c_.pattern_key,
                    "title": c_.title,
                    "confidence": confidence,
                    "evidence_count": c_.evidence_count,
                    "status": status,
                },
            )
        except Exception:
            pass
        out.append(
            {
                "event_type": event_type,
                "pattern": row,
                "assessment": dict(assessed),
            }
        )
    return out


def list_patterns(*, status: str = "", limit: int = 120) -> list[dict[str, Any]]:
    """Return persisted patterns, optionally filtered by status."""
    _ensure_table()
    try:
        with connect() as c:
            if status:
                rows = c.execute(
                    """SELECT * FROM emergent_patterns
                       WHERE status = ? ORDER BY last_updated_at DESC LIMIT ?""",
                    (status, limit),
                ).fetchall()
            else:
                rows = c.execute(
                    """SELECT * FROM emergent_patterns
                       ORDER BY last_updated_at DESC LIMIT ?""",
                    (limit,),
                ).fetchall()
        return [dict(r) for r in rows]
    except Exception as exc:
        logger.debug("emergence: list_patterns failed: %s", exc)
        return []


def summarize_patterns() -> dict[str, Any]:
    _ensure_table()
    try:
        with connect() as c:
            rows = c.execute(
                "SELECT status, COUNT(*) AS n FROM emergent_patterns GROUP BY status"
            ).fetchall()
        counts = {str(r["status"]): int(r["n"]) for r in rows}
    except Exception:
        counts = {}
    return {
        "candidate": counts.get("candidate", 0),
        "upgraded": counts.get("upgraded", 0),
        "downgraded": counts.get("downgraded", 0),
        "rejected": counts.get("rejected", 0),
        "total": sum(counts.values()),
    }


def _decode_json_list(value: object) -> list[str]:
    try:
        loaded = json.loads(str(value or "[]"))
    except Exception:
        loaded = []
    if not isinstance(loaded, list):
        return []
    return [str(item) for item in loaded if str(item).strip()]


def build_emergence_surface(*, limit: int = 8) -> dict[str, Any]:
    """Surface persisted emergence candidates without running detection."""
    patterns = list_patterns(limit=max(1, int(limit or 8)))
    items: list[dict[str, Any]] = []
    for pattern in patterns:
        items.append({
            "pattern_key": str(pattern.get("pattern_key") or ""),
            "title": str(pattern.get("title") or ""),
            "summary": str(pattern.get("summary") or ""),
            "status": str(pattern.get("status") or ""),
            "confidence": float(pattern.get("confidence") or 0.0),
            "evidence_count": int(pattern.get("evidence_count") or 0),
            "competing_explanations": _decode_json_list(
                pattern.get("competing_explanations_json")
            ),
            "confounders": _decode_json_list(pattern.get("confounders_json")),
            "last_updated_at": str(pattern.get("last_updated_at") or ""),
        })
    summary = summarize_patterns()
    active = bool(summary.get("candidate") or summary.get("upgraded"))
    return {
        "active": active,
        "mode": "evidence-based-emergence-patterns",
        "summary": {
            **summary,
            "current_pattern": (
                items[0]["title"] if items else "No persisted emergence pattern"
            ),
        },
        "items": items,
        "allowed_effects": [
            "prompt_attention",
            "request_more_evidence",
            "do_not_treat_candidate_as_identity_truth",
        ],
    }
