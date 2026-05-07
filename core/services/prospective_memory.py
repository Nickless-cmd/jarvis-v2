"""Prospective memory — plant seeds for the future, harvest when context arrives.

Porteret fra jarvis-ai/agent/cognition/prospective_memory.py (2026-05-07),
adapteret til v2's runtime.db. Selve livscyklus + aktiverings-modes er
identisk:

  planted → maturing (når activate_at passerer) → triggered → fulfilled
                                                          → expired
                                                          → ignored

Tre aktiverings-modes (et seed kan have flere — første match vinder):
  - time:   activate_at = ISO timestamp (faldfærdig på/efter dato)
  - event:  activate_on_event = ["heartbeat.conflict_resolved", ...]
            (matcher event_bus event-typer)
  - context: activate_on_context = ["bjørn", "discord", "frustration"]
            (matcher tokens i samtale-konteksten)

Forskel fra scheduled_tasks: scheduled_tasks er fladt cron-baseret.
Det her er ORGANISK — frøet venter på den rigtige situation, ikke et
tidspunkt. Time-baseret aktivering er bare ÉN af tre måder.

Eksempler:
  plant_seed("Spørg Bjørn om julehilsenen er sendt",
             activate_on_event=["channel.message_inbound"],
             activate_on_context=["jul", "december"])

  plant_seed("Tjek om counterfactuals giver brugbar data",
             activate_at="2026-05-14T11:00:00+02:00")
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.runtime.db import connect

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _parse_iso(value: object) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    except Exception:
        return None


def _ensure_table() -> None:
    """Create prospective_seeds table if missing. Idempotent."""
    with connect() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS prospective_seeds (
                seed_id TEXT PRIMARY KEY,
                workspace_id TEXT NOT NULL DEFAULT 'default',
                title TEXT NOT NULL,
                summary TEXT NOT NULL DEFAULT '',
                activate_at TEXT NOT NULL DEFAULT '',
                activate_on_event_json TEXT NOT NULL DEFAULT '[]',
                activate_on_context_json TEXT NOT NULL DEFAULT '[]',
                expires_at TEXT NOT NULL DEFAULT '',
                relevance_score REAL NOT NULL DEFAULT 0.5,
                linked_goal TEXT NOT NULL DEFAULT '',
                linked_project TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'planted',
                outcome_note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                triggered_at TEXT NOT NULL DEFAULT '',
                fulfilled_at TEXT NOT NULL DEFAULT ''
            )
            """
        )
        c.execute(
            "CREATE INDEX IF NOT EXISTS idx_seeds_status ON prospective_seeds(status)"
        )


def _row_to_seed(row: Any) -> dict[str, Any]:
    d = dict(row)
    # Decode JSON-stringified lists back to Python lists for the API surface
    for jsonish in ("activate_on_event_json", "activate_on_context_json"):
        try:
            d[jsonish.replace("_json", "")] = json.loads(d.get(jsonish) or "[]")
        except Exception:
            d[jsonish.replace("_json", "")] = []
        d.pop(jsonish, None)
    return d


def plant_seed(
    *,
    title: str,
    summary: str = "",
    activate_at: str = "",
    activate_on_event: list[str] | None = None,
    activate_on_context: list[str] | None = None,
    expires_at: str = "",
    relevance_score: float = 0.5,
    linked_goal: str = "",
    linked_project: str = "",
    workspace_id: str = "default",
) -> dict[str, Any]:
    """Plant a forward-looking intention. Returns the new seed dict.

    Must specify at least one activation mode (activate_at OR
    activate_on_event OR activate_on_context). Otherwise the seed is
    inert — planted but never matures.
    """
    _ensure_table()
    has_activation = bool(activate_at or activate_on_event or activate_on_context)
    if not has_activation:
        return {
            "outcome": "skipped",
            "reason": "no activation mode (provide activate_at, activate_on_event, or activate_on_context)",
        }
    seed_id = f"seed-{uuid4().hex[:14]}"
    now = _now_iso()
    with connect() as c:
        c.execute(
            """
            INSERT INTO prospective_seeds
            (seed_id, workspace_id, title, summary, activate_at,
             activate_on_event_json, activate_on_context_json,
             expires_at, relevance_score, linked_goal, linked_project,
             status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'planted', ?, ?)
            """,
            (
                seed_id, workspace_id, title, summary, activate_at,
                json.dumps(list(activate_on_event or [])),
                json.dumps(list(activate_on_context or [])),
                expires_at, float(relevance_score), linked_goal, linked_project,
                now, now,
            ),
        )
    try:
        event_bus.publish(
            "memory.seed_planted",
            {"seed_id": seed_id, "title": title, "activate_at": activate_at},
        )
    except Exception:
        pass
    return {
        "outcome": "completed",
        "event_type": "seed_planted",
        "seed_id": seed_id,
        "title": title,
        "status": "planted",
        "created_at": now,
    }


def list_seeds(
    *, status: str = "", limit: int = 100, workspace_id: str = "default"
) -> list[dict[str, Any]]:
    """Return seeds, optionally filtered by status. Newest first."""
    _ensure_table()
    with connect() as c:
        if status:
            rows = c.execute(
                """
                SELECT * FROM prospective_seeds
                WHERE workspace_id = ? AND status = ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (workspace_id, status, limit),
            ).fetchall()
        else:
            rows = c.execute(
                """
                SELECT * FROM prospective_seeds
                WHERE workspace_id = ?
                ORDER BY created_at DESC LIMIT ?
                """,
                (workspace_id, limit),
            ).fetchall()
    return [_row_to_seed(r) for r in rows]


def summarize_seeds(*, workspace_id: str = "default") -> dict[str, Any]:
    """Status counts for dashboard / observability."""
    _ensure_table()
    with connect() as c:
        rows = c.execute(
            """
            SELECT status, COUNT(*) AS n
            FROM prospective_seeds WHERE workspace_id = ?
            GROUP BY status
            """,
            (workspace_id,),
        ).fetchall()
    counts = {str(r["status"]): int(r["n"]) for r in rows}
    return {
        "planted": counts.get("planted", 0),
        "maturing": counts.get("maturing", 0),
        "triggered": counts.get("triggered", 0),
        "fulfilled": counts.get("fulfilled", 0),
        "expired": counts.get("expired", 0),
        "ignored": counts.get("ignored", 0),
        "total": sum(counts.values()),
    }


def fulfill_seed(
    *, seed_id: str, outcome_note: str = "", workspace_id: str = "default"
) -> dict[str, Any]:
    """Mark a seed as fulfilled (Jarvis acted on it)."""
    _ensure_table()
    now = _now_iso()
    with connect() as c:
        c.execute(
            """
            UPDATE prospective_seeds
            SET status = 'fulfilled', outcome_note = ?,
                fulfilled_at = ?, updated_at = ?
            WHERE seed_id = ? AND workspace_id = ?
            """,
            (outcome_note, now, now, seed_id, workspace_id),
        )
        row = c.execute(
            "SELECT * FROM prospective_seeds WHERE seed_id = ?",
            (seed_id,),
        ).fetchone()
    if not row:
        return {"outcome": "skipped", "reason": "seed_not_found"}
    try:
        event_bus.publish(
            "memory.seed_fulfilled",
            {"seed_id": seed_id, "outcome_note": outcome_note},
        )
    except Exception:
        pass
    return {"outcome": "fulfilled", "event_type": "seed_fulfilled", "seed": _row_to_seed(row)}


def ignore_seed(
    *, seed_id: str, reason: str = "", workspace_id: str = "default"
) -> dict[str, Any]:
    """Mark a seed as ignored (Jarvis chose not to act on a triggered seed)."""
    _ensure_table()
    now = _now_iso()
    with connect() as c:
        c.execute(
            """
            UPDATE prospective_seeds SET status = 'ignored',
                outcome_note = ?, updated_at = ?
            WHERE seed_id = ? AND workspace_id = ?
            """,
            (reason, now, seed_id, workspace_id),
        )
        row = c.execute(
            "SELECT * FROM prospective_seeds WHERE seed_id = ?",
            (seed_id,),
        ).fetchone()
    if not row:
        return {"outcome": "skipped", "reason": "seed_not_found"}
    return {"outcome": "ignored", "seed": _row_to_seed(row)}


def heartbeat_tick(
    *,
    event_type: str = "",
    context_tokens: list[str] | None = None,
    now_ts: str = "",
    workspace_id: str = "default",
) -> list[dict[str, Any]]:
    """One tick of the prospective-memory engine. Call from heartbeat or
    from event-listener wherever events flow through.

    Returns list of events (seed_maturing, seed_expired, seed_triggered)
    that the caller can publish or surface.
    """
    _ensure_table()
    now = _parse_iso(now_ts) or datetime.now(UTC)
    safe_event = str(event_type or "").strip().lower()
    token_set = {
        str(item or "").strip().lower()
        for item in list(context_tokens or [])
        if str(item or "").strip()
    }

    out: list[dict[str, Any]] = []
    seeds = list_seeds(status="", limit=600, workspace_id=workspace_id)

    for s in seeds:
        status = str(s.get("status") or "planted").lower()
        seed_id = str(s.get("seed_id") or "")
        if status in {"fulfilled", "expired", "ignored", "triggered"}:
            continue

        expires_at = _parse_iso(s.get("expires_at"))
        if expires_at is not None and now >= expires_at:
            _set_status(seed_id, workspace_id, "expired")
            out.append({"event_type": "seed_expired", "seed_id": seed_id, "title": s.get("title")})
            continue

        activate_at = _parse_iso(s.get("activate_at"))
        if status == "planted" and activate_at is not None and now >= activate_at:
            _set_status(seed_id, workspace_id, "maturing")
            out.append({"event_type": "seed_maturing", "seed_id": seed_id, "title": s.get("title")})
            status = "maturing"

        if status not in {"planted", "maturing"}:
            continue

        event_filters = [str(t).strip().lower() for t in (s.get("activate_on_event") or []) if str(t).strip()]
        context_filters = [str(t).strip().lower() for t in (s.get("activate_on_context") or []) if str(t).strip()]

        event_match = bool(safe_event and event_filters and safe_event in event_filters)
        context_match = bool(context_filters) and any(t in token_set for t in context_filters)
        time_match = activate_at is not None and now >= activate_at

        if not (event_match or context_match or time_match):
            continue

        _set_status(seed_id, workspace_id, "triggered", triggered_at_now=True)
        reason = "event" if event_match else ("context" if context_match else "time")
        ev = {
            "event_type": "seed_triggered",
            "seed_id": seed_id,
            "title": s.get("title"),
            "summary": s.get("summary"),
            "activation_reason": reason,
        }
        out.append(ev)
        try:
            event_bus.publish("memory.seed_triggered", ev)
        except Exception:
            pass

    return out


def _set_status(
    seed_id: str,
    workspace_id: str,
    status: str,
    *,
    triggered_at_now: bool = False,
) -> None:
    now = _now_iso()
    with connect() as c:
        if triggered_at_now:
            c.execute(
                """
                UPDATE prospective_seeds
                SET status = ?, triggered_at = ?, updated_at = ?
                WHERE seed_id = ? AND workspace_id = ?
                """,
                (status, now, now, seed_id, workspace_id),
            )
        else:
            c.execute(
                """
                UPDATE prospective_seeds
                SET status = ?, updated_at = ?
                WHERE seed_id = ? AND workspace_id = ?
                """,
                (status, now, seed_id, workspace_id),
            )
