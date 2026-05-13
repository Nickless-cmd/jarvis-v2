"""Outbound nudge ledger — replaces direct daemon→user sends for Type A/C.

Background (2026-05-13): heartbeat ping + outreach composer + inner voice
+ boredom bridge all called send_discord_message() or
send_session_notification() directly. When the user replied, a fresh
session started with NO context of what the daemon had said — Jarvis
woke up holding a reply to a question he couldn't see. Bjørn coined
this the "spejlsal" problem.

This module is the gate. Type A (heartbeat pings) and Type C (longing/
inner voice/boredom) daemons now call push_nudge() instead of sending
directly. Jarvis sees pending nudges in his next visible-lane prompt and
decides whether to surface them himself — with full context.

Type B (scheduled tasks, wakeups, critical infra alerts) bypass this
gate and still send directly — they have external triggers the user
expects to land.

Schema-bootstrap lives in this module (Boy Scout — db.py untouched).
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.runtime.db import connect

logger = logging.getLogger(__name__)

# Valid values for kind + importance + status. Enforced at push time so the
# table stays clean and queries don't have to guard against typos.
_VALID_KINDS = {
    "heartbeat_ping",   # Path 1 + 2
    "outreach",         # Path 3
    "inner_voice",      # Path 5
    "boredom",          # Path 6
    "action_router",    # Path 4 (non-critical)
    "other",            # catch-all
}
_VALID_IMPORTANCE = {"low", "normal", "high", "critical"}
_VALID_STATUS = {"pending", "inspected", "sent", "dismissed"}

# Budget — when pending count exceeds this, dismiss oldest pending first.
# Prevents unbounded growth if Jarvis never inspects.
_MAX_PENDING = 50

_SCHEMA_INITIALIZED = False


def ensure_schema() -> None:
    """Idempotently create outbound_nudges table + indexes."""
    global _SCHEMA_INITIALIZED
    if _SCHEMA_INITIALIZED:
        return
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS outbound_nudges (
              nudge_id TEXT PRIMARY KEY,
              source TEXT NOT NULL,
              kind TEXT NOT NULL,
              message TEXT NOT NULL,
              parent_session_id TEXT,
              parent_message_id TEXT,
              importance TEXT NOT NULL,
              status TEXT NOT NULL,
              created_at TEXT NOT NULL,
              inspected_at TEXT,
              sent_at TEXT,
              dismissed_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_outbound_nudges_status
              ON outbound_nudges(status);
            CREATE INDEX IF NOT EXISTS idx_outbound_nudges_created
              ON outbound_nudges(created_at);
            CREATE INDEX IF NOT EXISTS idx_outbound_nudges_source
              ON outbound_nudges(source);
            """
        )
        conn.commit()
    _SCHEMA_INITIALIZED = True


def _enabled() -> bool:
    try:
        from core.runtime.settings import load_settings
        return bool(load_settings().nudge_system_enabled)
    except Exception:
        return True  # fail-open


def push_nudge(
    *,
    source: str,
    kind: str,
    message: str,
    importance: str = "normal",
    parent_session_id: str | None = None,
    parent_message_id: str | None = None,
) -> dict[str, Any]:
    """Daemons call this instead of sending directly.

    Returns {status, nudge_id, ...}. If the nudge system is disabled via
    killswitch, returns {status: 'disabled'} and daemons should fall back
    to their original direct-send path (each call site handles that).
    """
    if not _enabled():
        return {"status": "disabled"}

    if kind not in _VALID_KINDS:
        kind = "other"
    if importance not in _VALID_IMPORTANCE:
        importance = "normal"

    message = str(message or "").strip()
    if not message:
        return {"status": "error", "error": "empty message"}

    ensure_schema()
    nudge_id = f"nudge-{uuid4().hex[:12]}"
    now_iso = datetime.now(UTC).isoformat()
    with connect() as conn:
        conn.execute(
            "INSERT INTO outbound_nudges "
            "(nudge_id, source, kind, message, parent_session_id, "
            " parent_message_id, importance, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)",
            (
                nudge_id, source, kind, message[:2000],
                parent_session_id, parent_message_id,
                importance, now_iso,
            ),
        )
        # Budget — dismiss oldest pending if over cap
        rows = conn.execute(
            "SELECT nudge_id FROM outbound_nudges WHERE status='pending' "
            "ORDER BY created_at DESC"
        ).fetchall()
        if len(rows) > _MAX_PENDING:
            to_dismiss = [r["nudge_id"] for r in rows[_MAX_PENDING:]]
            conn.execute(
                f"UPDATE outbound_nudges SET status='dismissed', "
                f"dismissed_at=? WHERE nudge_id IN "
                f"({','.join('?' for _ in to_dismiss)})",
                [now_iso, *to_dismiss],
            )
        conn.commit()

    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("nudge.pushed", {
            "nudge_id": nudge_id, "source": source, "kind": kind,
            "importance": importance, "message_length": len(message),
        })
    except Exception:
        pass

    return {"status": "ok", "nudge_id": nudge_id}


def list_pending(*, limit: int = 10) -> list[dict[str, Any]]:
    """Return pending nudges, newest first. Used by awareness-injection."""
    ensure_schema()
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM outbound_nudges WHERE status='pending' "
            "ORDER BY "
            "  CASE importance "
            "    WHEN 'critical' THEN 1 "
            "    WHEN 'high' THEN 2 "
            "    WHEN 'normal' THEN 3 "
            "    WHEN 'low' THEN 4 "
            "    ELSE 5 END, "
            "  created_at DESC LIMIT ?",
            (int(limit),),
        ).fetchall()
    return [dict(r) for r in rows]


def mark_inspected(nudge_ids: list[str]) -> int:
    """Mark nudges as seen by Jarvis (he saw them in prompt). Returns count."""
    if not nudge_ids:
        return 0
    ensure_schema()
    now_iso = datetime.now(UTC).isoformat()
    placeholders = ",".join("?" for _ in nudge_ids)
    with connect() as conn:
        cur = conn.execute(
            f"UPDATE outbound_nudges SET status='inspected', inspected_at=? "
            f"WHERE nudge_id IN ({placeholders}) AND status='pending'",
            [now_iso, *nudge_ids],
        )
        conn.commit()
        return cur.rowcount


def mark_sent(nudge_id: str) -> bool:
    """Mark a nudge as actually surfaced to the user by Jarvis."""
    ensure_schema()
    now_iso = datetime.now(UTC).isoformat()
    with connect() as conn:
        cur = conn.execute(
            "UPDATE outbound_nudges SET status='sent', sent_at=? "
            "WHERE nudge_id = ? AND status IN ('pending', 'inspected')",
            (now_iso, nudge_id),
        )
        conn.commit()
    return cur.rowcount > 0


def mark_dismissed(nudge_id: str) -> bool:
    """Mark a nudge as explicitly skipped by Jarvis (won't reappear)."""
    ensure_schema()
    now_iso = datetime.now(UTC).isoformat()
    with connect() as conn:
        cur = conn.execute(
            "UPDATE outbound_nudges SET status='dismissed', dismissed_at=? "
            "WHERE nudge_id = ? AND status IN ('pending', 'inspected')",
            (now_iso, nudge_id),
        )
        conn.commit()
    return cur.rowcount > 0


def format_pending_for_awareness() -> str:
    """Render pending nudges as awareness section.

    Returns "" when none pending or killswitch off. Marks all surfaced
    nudges as 'inspected' so they don't keep reappearing as fresh.
    """
    if not _enabled():
        return ""
    try:
        pending = list_pending(limit=10)
    except Exception:
        return ""
    if not pending:
        return ""

    lines = [
        "Pending nudges (daemons fra dit indre — du afgør om de skal surface):",
    ]
    ids_seen = []
    for n in pending:
        ts = str(n.get("created_at") or "")[11:16]  # HH:MM
        src = n.get("source") or n.get("kind") or "?"
        imp = n.get("importance") or "normal"
        msg = str(n.get("message") or "")[:160]
        nid = n.get("nudge_id") or ""
        lines.append(f"  [{nid}] {ts} {src}/{imp}: {msg}")
        ids_seen.append(nid)
    lines.append(
        "Mekanisme: mark_sent(nudge_id) hvis du vil surface, "
        "mark_dismissed(nudge_id) hvis ikke. Inspekteret automatisk når læst."
    )

    # Mark as inspected (best-effort, never blocks awareness rendering)
    try:
        mark_inspected(ids_seen)
    except Exception:
        pass

    return "\n".join(lines)
