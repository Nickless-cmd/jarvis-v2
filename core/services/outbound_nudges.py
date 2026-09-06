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
        # shown_count tilføjet 19. aug 2026 (idempotent — eksisterende DB'er mangler den).
        # Bærer hvor mange gange en nudge er renderet, så pensionering kan kræve flere
        # visninger i stedet for én.
        cols = {r[1] for r in conn.execute("PRAGMA table_info(outbound_nudges)").fetchall()}
        if "shown_count" not in cols:
            conn.execute("ALTER TABLE outbound_nudges ADD COLUMN shown_count INTEGER DEFAULT 0")
        conn.commit()
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

    # ── Router (redesign 4. sep 2026) ────────────────────────────────────
    # Brønden er ikke længere en beslutningsflade Jarvis skal polle.
    #  • telemetri ("Autonom run ✓ færdig") → event, aldrig en besked
    #  • mid-run-brugerbeskeder → gemmes her og vises som egen sektion
    #  • alt andet → proactive_candidates → proactivity_bridge leverer
    route = route_for(source=source, kind=kind)
    if route == "telemetry":
        _publish_routed(source, kind, importance, "telemetry")
        return {"status": "telemetry", "route": "telemetry"}
    if route == "bridge":
        try:
            from core.services.proactive_candidates import add_candidate
            res = add_candidate(source=source, kind=kind, text=message,
                                priority=_bridge_priority(importance))
        except Exception as exc:
            logger.debug("outbound_nudges: bridge route failed: %s", exc)
            res = {"status": "error", "error": str(exc)[:120]}
        _publish_routed(source, kind, importance, "bridge")
        return {"status": "ok" if res.get("status") in {"added", "duplicate"} else "error",
                "route": "bridge", "nudge_id": str(res.get("candidate_id") or ""),
                "candidate": res}

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


MIDWAY_SOURCE = "user_midway_followup"
_TELEMETRY_SOURCES = frozenset({"autonomous_run"})
_TELEMETRY_KINDS = frozenset({"autonomous_run"})


def route_for(*, source: str, kind: str) -> str:
    """'midway' | 'telemetry' | 'bridge' — pure."""
    src = str(source or "")
    knd = str(kind or "")
    if src == MIDWAY_SOURCE:
        return "midway"
    if src in _TELEMETRY_SOURCES or knd in _TELEMETRY_KINDS:
        return "telemetry"
    return "bridge"


def _bridge_priority(importance: str) -> str:
    v = str(importance or "").lower()
    if v in {"critical", "high"}:
        return "high"
    if v == "low":
        return "low"
    return "medium"


def _publish_routed(source: str, kind: str, importance: str, route: str) -> None:
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("nudge.routed", {"source": source, "kind": kind,
                                           "importance": importance, "route": route})
    except Exception:
        pass


def format_midway_for_prompt(*, limit: int = 5) -> str:
    """Bjørns beskeder sendt MENS et run kørte — de er hans ord, ikke daemon-støj.

    Rendered as its own operational section (never inside the diagnostics
    block). Consumed via note_shown like before (prewarm never consumes).
    """
    if not _enabled():
        return ""
    try:
        pending = [n for n in list_pending(limit=30) if str(n.get("source") or "") == MIDWAY_SOURCE][:limit]
    except Exception:
        return ""
    if not pending:
        return ""
    lines = ["Beskeder fra Bjørn undervejs (sendt mens du arbejdede — svar på dem nu):"]
    ids = []
    for n in pending:
        ts = str(n.get("created_at") or "")[11:16]
        lines.append(f"  - [{ts}] {str(n.get('message') or '')[:300]}")
        ids.append(str(n.get("nudge_id") or ""))
    try:
        from core.services.assembly_prewarm import is_prewarm_active
        if is_prewarm_active():
            return "\n".join(lines)
    except Exception:
        pass
    try:
        note_shown(ids)
    except Exception:
        pass
    return "\n".join(lines)


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


# Hvor mange gange en nudge må vises FØR den pensioneres. Var implicit 1: den blev
# markeret `inspected` i samme åndedrag som den blev renderet, og `list_pending` henter
# kun `pending` — så hver nudge fik ÉN prompt-optræden og forsvandt. Målt 19. aug 2026:
# 1.752 nudges, median-levetid **26 sekunder**, 997 opslugt på under et minut, og
# `mark_sent` kaldt NUL gange. Alle 78 matrix-beskeder — hans egne indre stemmer —
# endte som `inspected` uden at nogen havde læst dem.
_SHOW_LIMIT = 3


def note_shown(nudge_ids: list[str]) -> int:
    """Tæl én visning. Pensionerer først ved `_SHOW_LIMIT`, ikke ved første render.

    "Renderet ind i en prompt" er ikke det samme som "set og overvejet" — det var
    præcis den sammenblanding der tømte brønden. En nudge overlever nu til den enten
    er vist nok gange, eller er eksplicit sendt/afvist.
    """
    if not nudge_ids:
        return 0
    ensure_schema()
    now_iso = datetime.now(UTC).isoformat()
    ph = ",".join("?" for _ in nudge_ids)
    with connect() as conn:
        conn.execute(
            f"UPDATE outbound_nudges SET shown_count = COALESCE(shown_count, 0) + 1 "
            f"WHERE nudge_id IN ({ph}) AND status = 'pending'",
            list(nudge_ids),
        )
        cur = conn.execute(
            f"UPDATE outbound_nudges SET status='inspected', inspected_at=? "
            f"WHERE nudge_id IN ({ph}) AND status='pending' "
            f"AND COALESCE(shown_count, 0) >= ?",
            [now_iso, *nudge_ids, int(_SHOW_LIMIT)],
        )
        conn.commit()
        return cur.rowcount


def mark_inspected(nudge_ids: list[str]) -> int:
    """Bagudkompatibelt alias for `note_shown`."""
    return note_shown(nudge_ids)


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

    # En SPEKULATIV build må aldrig forbruge en nudge. `assembly_prewarm` bygger en
    # throwaway-assembly for at varme sektions-cachen — ingen læser resultatet. Uden
    # dette tjek pensionerede cache-opvarmningen hans indre stemmer i baggrunden.
    # Signalet fandtes allerede (`is_prewarm_active`); brønden spurgte bare aldrig.
    try:
        from core.services.assembly_prewarm import is_prewarm_active
        if is_prewarm_active():
            return "\n".join(lines)
    except Exception:
        pass

    # Tæl visningen. Pensionerer først efter _SHOW_LIMIT — se note_shown.
    try:
        note_shown(ids_seen)
    except Exception:
        pass

    return "\n".join(lines)
