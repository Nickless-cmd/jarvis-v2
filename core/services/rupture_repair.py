"""Rupture & Repair — relationel tension-tracking.

En "rupture" er et brud i samarbejdet: bruger overrider, beslutning afvises,
uenighed når uløst. En "repair" er et forsøg på (eller faktisk) at hele
bruddet: retry, mitigation, opfølgning, udtrykt forståelse.

Ikke alle ruptures skal repareres — men alle skal mærkes. De der ignoreres
akkumulerer og former relationen.

Porteret fra jarvis-ai/agent/cognition/rupture_repair.py (2026-04-21).

Eventsource: læser fra core.eventbus event_bus.recent() og klassificerer.
LLM-path: ingen — ren mønster-matchning på event-kind + payload-tekst.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.db import connect

logger = logging.getLogger(__name__)

# Event-kind/phrase-baseret klassifikation — tuned til v2 event-navngivning.
_RUPTURE_KIND_SIGNALS = (
    "override",
    "pushback",
    "disagree",
    "negotiation_failed",
    "rejected",
    "denied",
    "blocked",
)
_RUPTURE_DECISION_TERMS = {"deny", "denied", "blocked", "rejected", "degraded", "failed"}
# Tekst-terms kun som sidste resort — kræver stærk formulering.
# ("unresolved", "conflict", "crux" er droppet fordi de optræder hyppigt i
# inner-voice/dream summaries uden at være relationelle ruptures.)
_RUPTURE_TEXT_TERMS = (
    "manual override",
    "user rejected",
    "user denied",
    "rupture detected",
)

# Interne daemon-events som ikke er relationelle ruptures selv hvis de
# indeholder trigger-termer. Deres hensigt er selv-refleksion, ikke brud.
_EXCLUDED_KIND_PREFIXES = (
    "runtime.emergent_signal",
    "heartbeat.",
    "inner_voice.",
    "dream.",
    "dream_",
    "mood.",
    "mood_",
    "cognitive_compass.",
    "silence.",
    "self_model.",
    "chronicle.",
    "proprioception.",
    "regret.",
    "rupture.",  # vores egne events
)

_REPAIR_TERMS = ("retry", "repair", "mitigation", "follow-up", "followup", "forsøg igen")
_REPAIR_COMPLETE_DECISIONS = {
    "approved",
    "allow",
    "allowed",
    "resolved",
    "completed",
    "success",
}
_REPAIR_COMPLETE_TERMS = (
    "resolved",
    "repair completed",
    "tension closed",
    "reconciled",
    "løst",
)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _parse_iso(value: object) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    except Exception:
        return None


def _ensure_tables() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cognitive_ruptures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rupture_key TEXT NOT NULL UNIQUE,
                topic TEXT NOT NULL DEFAULT '',
                source_kind TEXT NOT NULL DEFAULT 'disagreement',
                reason TEXT NOT NULL DEFAULT '',
                evidence_json TEXT NOT NULL DEFAULT '{}',
                tension_level REAL NOT NULL DEFAULT 0.4,
                linked_run_id TEXT NOT NULL DEFAULT '',
                linked_session_id TEXT NOT NULL DEFAULT '',
                linked_incident_id TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'open',
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cognitive_ruptures_status "
            "ON cognitive_ruptures(status, id DESC)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cognitive_repairs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rupture_id INTEGER NOT NULL,
                repair_kind TEXT NOT NULL DEFAULT 'attempt',
                repair_note TEXT NOT NULL DEFAULT '',
                change_summary TEXT NOT NULL DEFAULT '',
                evidence_json TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'attempted',
                linked_run_id TEXT NOT NULL DEFAULT '',
                linked_session_id TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (rupture_id) REFERENCES cognitive_ruptures(id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cognitive_repairs_rupture "
            "ON cognitive_repairs(rupture_id, id DESC)"
        )
        conn.commit()


def _rupture_key(*, source_kind: str, topic: str) -> str:
    seed = f"{source_kind}:{topic.strip().lower()}".encode("utf-8", errors="ignore")
    return hashlib.sha256(seed).hexdigest()[:24]


def _normalize_topic(payload: dict[str, object], *, event_kind: str) -> str:
    for key in (
        "topic", "question", "goal", "run_id", "session_id",
        "target", "tool", "policy_key", "title",
    ):
        value = str(payload.get(key) or "").strip()
        if value:
            return value[:120]
    return event_kind.replace(".", " ").replace("_", " ")[:120]


def _classify_rupture(
    event_kind: str, payload: dict[str, object]
) -> tuple[bool, str, float]:
    """Returns (is_rupture, source_kind, tension_level ∈ [0,1])."""
    kind = str(event_kind or "").strip().lower()
    # Filter out internal cognitive daemon chatter — not relational ruptures.
    if any(kind.startswith(pre) for pre in _EXCLUDED_KIND_PREFIXES):
        return False, "", 0.0
    decision = (
        str(
            payload.get("decision")
            or payload.get("status")
            or payload.get("outcome")
            or ""
        ).strip().lower()
    )
    text_blob = " ".join([
        kind,
        str(payload.get("reason") or ""),
        str(payload.get("message") or ""),
        str(payload.get("summary") or ""),
    ]).lower()

    if any(sig in kind for sig in _RUPTURE_KIND_SIGNALS) or decision in _RUPTURE_DECISION_TERMS:
        return True, "disagreement", 0.62
    if "approval" in kind and decision in {"rejected", "deny", "denied", "blocked"}:
        return True, "approval_rejected", 0.7
    if any(term in text_blob for term in _RUPTURE_TEXT_TERMS):
        return True, "unresolved_tension", 0.56
    return False, "", 0.0


def _is_repair_attempt(event_kind: str, payload: dict[str, object]) -> bool:
    blob = " ".join([
        str(event_kind or "").lower(),
        str(payload.get("reason") or ""),
        str(payload.get("summary") or ""),
        str(payload.get("message") or ""),
    ]).lower()
    return any(term in blob for term in _REPAIR_TERMS)


def _is_repair_complete(event_kind: str, payload: dict[str, object]) -> bool:
    decision = (
        str(
            payload.get("decision")
            or payload.get("status")
            or payload.get("outcome")
            or ""
        ).strip().lower()
    )
    if decision in _REPAIR_COMPLETE_DECISIONS:
        return True
    blob = " ".join([
        str(event_kind or "").lower(),
        decision,
        str(payload.get("summary") or ""),
        str(payload.get("reason") or ""),
    ]).lower()
    return any(term in blob for term in _REPAIR_COMPLETE_TERMS)


def _row_to_rupture(row: Any) -> dict[str, object]:
    if row is None:
        return {}
    d = dict(row)
    try:
        d["evidence"] = json.loads(d.pop("evidence_json", "{}") or "{}")
    except Exception:
        d["evidence"] = {}
    return d


def _row_to_repair(row: Any) -> dict[str, object]:
    if row is None:
        return {}
    d = dict(row)
    try:
        d["evidence"] = json.loads(d.pop("evidence_json", "{}") or "{}")
    except Exception:
        d["evidence"] = {}
    return d


def _upsert_rupture(
    conn,
    *,
    rupture_key: str,
    topic: str,
    source_kind: str,
    reason: str,
    evidence: dict[str, object],
    tension_level: float,
    linked_run_id: str,
    linked_session_id: str,
    linked_incident_id: str,
    status: str,
    last_seen_at: str,
) -> tuple[dict[str, object], str]:
    """Insert or update a rupture by rupture_key. Returns (row_dict, mutation).

    mutation ∈ {"inserted", "updated", "reopened"}.
    """
    now = _now_iso()
    row = conn.execute(
        "SELECT * FROM cognitive_ruptures WHERE rupture_key = ?",
        (rupture_key,),
    ).fetchone()
    ev_json = json.dumps(evidence or {}, ensure_ascii=False)

    if row is None:
        cursor = conn.execute(
            """
            INSERT INTO cognitive_ruptures (
                rupture_key, topic, source_kind, reason, evidence_json,
                tension_level, linked_run_id, linked_session_id, linked_incident_id,
                status, first_seen_at, last_seen_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rupture_key, topic, source_kind, reason, ev_json,
                float(tension_level),
                linked_run_id, linked_session_id, linked_incident_id,
                status, last_seen_at or now, last_seen_at or now, now,
            ),
        )
        new_id = int(cursor.lastrowid)
        fresh = conn.execute(
            "SELECT * FROM cognitive_ruptures WHERE id = ?", (new_id,)
        ).fetchone()
        return _row_to_rupture(fresh), "inserted"

    rid = int(row["id"])
    prev_status = str(row["status"] or "")
    mutation = "reopened" if prev_status in {"repaired", "resolved"} else "updated"
    new_tension = max(float(row["tension_level"] or 0.0), float(tension_level))
    conn.execute(
        """
        UPDATE cognitive_ruptures
           SET topic = COALESCE(NULLIF(?, ''), topic),
               source_kind = ?,
               reason = ?,
               evidence_json = ?,
               tension_level = ?,
               linked_run_id = CASE WHEN ? != '' THEN ? ELSE linked_run_id END,
               linked_session_id = CASE WHEN ? != '' THEN ? ELSE linked_session_id END,
               linked_incident_id = CASE WHEN ? != '' THEN ? ELSE linked_incident_id END,
               status = ?,
               last_seen_at = ?,
               updated_at = ?
         WHERE id = ?
        """,
        (
            topic,
            source_kind, reason, ev_json, float(new_tension),
            linked_run_id, linked_run_id,
            linked_session_id, linked_session_id,
            linked_incident_id, linked_incident_id,
            "open",
            last_seen_at or now, now, rid,
        ),
    )
    fresh = conn.execute(
        "SELECT * FROM cognitive_ruptures WHERE id = ?", (rid,)
    ).fetchone()
    return _row_to_rupture(fresh), mutation


def _create_repair(
    conn,
    *,
    rupture_id: int,
    repair_kind: str,
    repair_note: str,
    change_summary: str,
    evidence: dict[str, object],
    status: str,
    linked_run_id: str,
    linked_session_id: str,
) -> dict[str, object]:
    now = _now_iso()
    ev_json = json.dumps(evidence or {}, ensure_ascii=False)
    cursor = conn.execute(
        """
        INSERT INTO cognitive_repairs (
            rupture_id, repair_kind, repair_note, change_summary,
            evidence_json, status, linked_run_id, linked_session_id,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(rupture_id), repair_kind, repair_note, change_summary,
            ev_json, status, linked_run_id, linked_session_id, now, now,
        ),
    )
    rid = int(cursor.lastrowid)
    fresh = conn.execute(
        "SELECT * FROM cognitive_repairs WHERE id = ?", (rid,)
    ).fetchone()
    return _row_to_repair(fresh)


def evaluate_ruptures(*, lookback_hours: int = 72, event_limit: int = 300) -> list[dict[str, object]]:
    """Scan recent events and detect/update ruptures and repairs.

    Returns list of {"event_type": str, "rupture": dict, "repair"?: dict,
    "source_event_kind": str}.

    event_type ∈ {"rupture_detected", "tension_reopened",
                   "repair_attempted", "repair_completed"}.
    """
    _ensure_tables()
    now = datetime.now(UTC)
    min_ts = now - timedelta(hours=max(1, int(lookback_hours)))
    events = event_bus.recent(limit=int(event_limit))
    events_chrono = list(reversed(events))  # oldest first
    results: list[dict[str, object]] = []

    with connect() as conn:
        # Load current open ruptures by topic for cross-ref
        open_rows = conn.execute(
            "SELECT * FROM cognitive_ruptures WHERE status = 'open' "
            "ORDER BY id DESC LIMIT 300"
        ).fetchall()
        open_by_topic: dict[str, dict[str, object]] = {}
        for r in open_rows:
            topic = str(r["topic"] or "").strip().lower()
            if topic:
                open_by_topic[topic] = _row_to_rupture(r)

        for ev in events_chrono:
            kind = str(ev.get("kind") or "").strip().lower()
            if not kind:
                continue
            payload = ev.get("payload") if isinstance(ev.get("payload"), dict) else {}
            ev_ts = _parse_iso(ev.get("created_at"))
            if ev_ts is not None and ev_ts < min_ts:
                continue
            topic = _normalize_topic(payload, event_kind=kind)
            topic_key = topic.strip().lower()
            run_id = str(payload.get("run_id") or "").strip()
            session_id = str(payload.get("session_id") or "").strip()
            incident_id = str(payload.get("incident_id") or "").strip()
            last_seen = str(ev.get("created_at") or _now_iso())

            is_rupture, source_kind, tension = _classify_rupture(kind, payload)
            if is_rupture:
                rkey = _rupture_key(source_kind=source_kind, topic=topic)
                rupture, mutation = _upsert_rupture(
                    conn,
                    rupture_key=rkey,
                    topic=topic,
                    source_kind=source_kind,
                    reason=str(payload.get("reason") or payload.get("summary") or kind),
                    evidence={"event_kind": kind, "payload": payload},
                    tension_level=tension,
                    linked_run_id=run_id,
                    linked_session_id=session_id,
                    linked_incident_id=incident_id,
                    status="open",
                    last_seen_at=last_seen,
                )
                open_by_topic[topic_key] = rupture
                results.append({
                    "event_type": "tension_reopened" if mutation == "reopened" else "rupture_detected",
                    "rupture": rupture,
                    "source_event_kind": kind,
                })
                continue

            open_row = open_by_topic.get(topic_key)
            if not open_row:
                continue
            rupture_id = int(open_row.get("id") or 0)
            if rupture_id <= 0:
                continue

            if _is_repair_complete(kind, payload):
                repair = _create_repair(
                    conn,
                    rupture_id=rupture_id,
                    repair_kind="resolution",
                    repair_note=str(payload.get("reason") or payload.get("summary") or "resolved"),
                    change_summary=str(payload.get("summary") or payload.get("status") or "resolved"),
                    evidence={"event_kind": kind, "payload": payload},
                    status="completed",
                    linked_run_id=run_id,
                    linked_session_id=session_id,
                )
                conn.execute(
                    "UPDATE cognitive_ruptures SET status = 'repaired', "
                    "last_seen_at = ?, updated_at = ? WHERE id = ?",
                    (last_seen, _now_iso(), rupture_id),
                )
                row = conn.execute(
                    "SELECT * FROM cognitive_ruptures WHERE id = ?", (rupture_id,)
                ).fetchone()
                updated = _row_to_rupture(row)
                open_by_topic.pop(topic_key, None)
                results.append({
                    "event_type": "repair_completed",
                    "rupture": updated,
                    "repair": repair,
                    "source_event_kind": kind,
                })
                continue

            if _is_repair_attempt(kind, payload):
                repair = _create_repair(
                    conn,
                    rupture_id=rupture_id,
                    repair_kind="attempt",
                    repair_note=str(
                        payload.get("reason") or payload.get("summary") or "repair_attempt"
                    ),
                    change_summary=str(
                        payload.get("message") or payload.get("summary") or "attempted"
                    ),
                    evidence={"event_kind": kind, "payload": payload},
                    status="attempted",
                    linked_run_id=run_id,
                    linked_session_id=session_id,
                )
                results.append({
                    "event_type": "repair_attempted",
                    "rupture": open_row,
                    "repair": repair,
                    "source_event_kind": kind,
                })

        conn.commit()

    # Publish events on the bus for downstream listeners
    for item in results:
        try:
            ev_type = str(item.get("event_type") or "")
            rupture = item.get("rupture") or {}
            event_bus.publish(f"rupture.{ev_type}", {
                "rupture_id": int(rupture.get("id") or 0) if isinstance(rupture, dict) else 0,
                "topic": str(rupture.get("topic") or "") if isinstance(rupture, dict) else "",
                "source_event_kind": item.get("source_event_kind"),
            })
        except Exception:
            pass
    return results


def list_ruptures(
    *,
    status: str = "",
    limit: int = 120,
) -> list[dict[str, object]]:
    _ensure_tables()
    status = str(status or "").strip().lower()
    lim = max(1, min(int(limit or 120), 500))
    with connect() as conn:
        if status in {"open", "repaired", "resolved"}:
            rows = conn.execute(
                "SELECT * FROM cognitive_ruptures WHERE status = ? "
                "ORDER BY id DESC LIMIT ?",
                (status, lim),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM cognitive_ruptures ORDER BY id DESC LIMIT ?",
                (lim,),
            ).fetchall()
    return [_row_to_rupture(r) for r in rows]


def list_repairs(
    *,
    rupture_id: int | None = None,
    status: str = "",
    limit: int = 120,
) -> list[dict[str, object]]:
    _ensure_tables()
    status = str(status or "").strip().lower()
    lim = max(1, min(int(limit or 120), 500))
    with connect() as conn:
        if rupture_id is not None:
            rows = conn.execute(
                "SELECT * FROM cognitive_repairs WHERE rupture_id = ? "
                "ORDER BY id DESC LIMIT ?",
                (int(rupture_id), lim),
            ).fetchall()
        elif status in {"attempted", "completed"}:
            rows = conn.execute(
                "SELECT * FROM cognitive_repairs WHERE status = ? "
                "ORDER BY id DESC LIMIT ?",
                (status, lim),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM cognitive_repairs ORDER BY id DESC LIMIT ?",
                (lim,),
            ).fetchall()
    return [_row_to_repair(r) for r in rows]


def summarize_ruptures() -> dict[str, object]:
    _ensure_tables()
    with connect() as conn:
        open_count = int(
            conn.execute(
                "SELECT COUNT(*) FROM cognitive_ruptures WHERE status = 'open'"
            ).fetchone()[0] or 0
        )
        repaired_count = int(
            conn.execute(
                "SELECT COUNT(*) FROM cognitive_ruptures WHERE status = 'repaired'"
            ).fetchone()[0] or 0
        )
        repairs_attempted = int(
            conn.execute(
                "SELECT COUNT(*) FROM cognitive_repairs WHERE status = 'attempted'"
            ).fetchone()[0] or 0
        )
        repairs_completed = int(
            conn.execute(
                "SELECT COUNT(*) FROM cognitive_repairs WHERE status = 'completed'"
            ).fetchone()[0] or 0
        )
        top_row = conn.execute(
            "SELECT * FROM cognitive_ruptures WHERE status = 'open' "
            "ORDER BY tension_level DESC, id DESC LIMIT 1"
        ).fetchone()
        top = _row_to_rupture(top_row) if top_row else None
    return {
        "open_ruptures": open_count,
        "repaired_ruptures": repaired_count,
        "repair_attempts": repairs_attempted,
        "repairs_completed": repairs_completed,
        "top_open": top,
    }


def build_rupture_repair_surface() -> dict[str, object]:
    """MC surface for Rupture & Repair."""
    _ensure_tables()
    summary = summarize_ruptures()
    recent_open = list_ruptures(status="open", limit=5)
    recent_repairs = list_repairs(limit=5)
    active = int(summary.get("open_ruptures") or 0) > 0 or bool(recent_repairs)
    top = summary.get("top_open") or {}
    summary_line = (
        f"{summary.get('open_ruptures', 0)} åbne / "
        f"{summary.get('repaired_ruptures', 0)} helede — "
        f"{summary.get('repair_attempts', 0)} forsøg"
    )
    if isinstance(top, dict) and top.get("topic"):
        summary_line += f" — top: {str(top.get('topic'))[:60]}"
    return {
        "active": active,
        "summary": summary_line,
        "stats": summary,
        "recent_open": recent_open,
        "recent_repairs": recent_repairs,
    }
