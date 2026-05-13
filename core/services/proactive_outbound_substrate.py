"""Proactive-outbound substrate — what Jarvis just said proactively.

The visible-lane LLM sees user replies but not the daemon-fired proactive
messages those replies are responding to. Result: Jarvis appears confused
and repeats himself because he literally has no context for what the user
is replying to.

This module surfaces recent ``heartbeat.propose_delivered`` and
``heartbeat.ping_delivered`` events so Jarvis sees his own proactive
outbound messages as substrate alongside the user reply.

Pattern: data, ikke domm. We show the actual messages he sent (timestamp +
type + summary) and let him connect them to the user reply himself. No
interpretation, no instructions.

Added 2026-05-08 per Jarvis' diagnosis: "Den proactive daemon ved ikke at
jeg allerede er i en samtale med dig. Den fyrer bare løs med et
spørgsmål... og jeg har nul kontekst om at den overhovedet fyrede."
"""
from __future__ import annotations

import json as _json
import logging
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)


# Outbound proactive event families. Each maps kind → human label.
_PROACTIVE_OUTBOUND_FAMILIES: dict[str, str] = {
    "heartbeat.propose_delivered": "propose",
    "heartbeat.ping_delivered":    "ping",
}


def _summarize_outbound_payload(kind: str, payload: dict) -> str:
    """Extract the actual question/message text from a delivered event."""
    if not isinstance(payload, dict):
        return ""
    # Both propose_delivered and ping_delivered carry `summary` with the
    # delivered text. Fall back to other fields defensively.
    for k in ("summary", "message", "text", "content"):
        v = payload.get(k)
        if v:
            return str(v).strip().replace("\n", " ")[:160]
    return ""


def compute_proactive_outbound_substrate(
    *,
    window_min: int = 30,
    max_events: int = 5,
) -> list[str]:
    """Return raw proactive-outbound events as substrate strings.

    Each entry: ``HH:MM — type: text``. Empty list on any failure or
    when no relevant events are in the window.
    """
    try:
        from core.runtime.db import connect

        cutoff = (
            datetime.now(UTC) - timedelta(minutes=max(1, int(window_min)))
        ).isoformat()
        kinds = list(_PROACTIVE_OUTBOUND_FAMILIES.keys())
        placeholders = ",".join("?" for _ in kinds)
        sql = (
            f"SELECT id, kind, payload_json, created_at FROM events "
            f"WHERE kind IN ({placeholders}) AND created_at >= ? "
            f"ORDER BY id DESC LIMIT ?"
        )
        params = kinds + [cutoff, max(1, int(max_events)) * 2]

        with connect() as c:
            rows = c.execute(sql, params).fetchall()
    except Exception as exc:  # pragma: no cover — defensive
        logger.debug("compute_proactive_outbound_substrate query failed: %s", exc)
        return []

    out: list[str] = []
    for r in rows:
        if len(out) >= max_events:
            break
        kind = str(r["kind"] or "")
        try:
            payload = _json.loads(r["payload_json"] or "{}")
        except Exception:
            payload = {}
        kerne = _summarize_outbound_payload(kind, payload)
        if not kerne:
            continue
        ts = str(r["created_at"] or "")
        hhmm = ts[11:16] if len(ts) >= 16 else ts
        label = _PROACTIVE_OUTBOUND_FAMILIES.get(kind, kind)
        out.append(f"{hhmm} — {label}: {kerne}")

    # Reverse to chronological (oldest first reads more naturally)
    return list(reversed(out))


def build_proactive_outbound_section() -> str | None:
    """Prompt section — proactive messages Jarvis sent in last 30 min.

    Killswitch: ``prompt_proactive_outbound_substrate_enabled`` (default True).
    """
    try:
        from core.runtime.settings import load_settings

        if not bool(getattr(
            load_settings(),
            "prompt_proactive_outbound_substrate_enabled",
            True,
        )):
            return None
    except Exception:
        # Fail safe — keep section enabled if settings unreadable.
        pass

    lines = compute_proactive_outbound_substrate()
    if not lines:
        return None

    return (
        "## Nylige proaktive beskeder du sendte (sidste 30 min)\n"
        + "\n".join(f"- {ln}" for ln in lines)
        + "\n_Brugerens svar kan referere til disse._"
    )


def build_proactive_outbound_substrate_surface() -> dict[str, object]:
    """Mission Control surface — read-only meta-projection.

    Added during 2026-05-13 coverage push (system_cartographer dark-edge
    closure). Reports module presence so the cartographer registers it as
    observed. Specific state-readers added as the module evolves.
    """
    return {
        "active": True,
        "mode": "proactive_outbound_substrate",
        "summary": "Module loaded; entry points available.",
        "authority": "derived-read-only",
    }


def _emit_proactive_outbound_substrate_event(kind: str, payload: dict[str, object] | None = None) -> None:
    """Emit a scoped event — defensive, never blocks caller.
    Cartographer scans for event_bus.publish() text.
    """
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(
            f"proactive_outbound_substrate.{kind}",
            payload or {},
        )
    except Exception:
        pass

