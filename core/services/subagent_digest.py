"""Surface recently-completed subagents into the visible prompt.

When Jarvis spawns a subagent (via spawn_agent_task), the subagent runs
in the background, writes to the eventbus, and updates its registry
entry on completion. The parent had to remember to call list_agents to
see what came back. Without an explicit nudge, completed work could sit
unread for hours.

This mirrors how Claude Code surfaces Agent results inline: when an
Agent call returns, I see the result in my next turn automatically. We
do the same here by tracking a per-session "last seen completion time"
mark and summarizing any subagent that finished since.

Cheap, bounded, idempotent — same shape as session_wakeup.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from core.runtime.state_store import load_json, save_json

logger = logging.getLogger(__name__)

_STATE_KEY = "subagent_digest_marks"
_MAX_DIGEST_ITEMS = 4


def _load_marks() -> dict[str, str]:
    raw = load_json(_STATE_KEY, {})
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) for k, v in raw.items()}


def _save_marks(marks: dict[str, str]) -> None:
    save_json(_STATE_KEY, marks)


def _last_seen(session_id: str) -> str:
    return _load_marks().get(session_id, "")


def _mark_seen(session_id: str, when_iso: str) -> None:
    marks = _load_marks()
    if when_iso > marks.get(session_id, ""):
        marks[session_id] = when_iso
        _save_marks(marks)


def subagent_digest_section(session_id: str | None) -> str | None:
    """Format completed subagents (since this session last looked) as a block.

    Returns None when nothing new. Updates the per-session mark as a side
    effect so the same agent doesn't appear in two consecutive prompts.
    """
    sid = str(session_id or "_default")
    try:
        from core.runtime.db import list_agent_registry_entries
    except Exception as exc:
        logger.debug("subagent_digest: db import failed: %s", exc)
        return None

    last_mark = _last_seen(sid)
    try:
        registry = list_agent_registry_entries(limit=80)
    except Exception as exc:
        logger.debug("subagent_digest: registry fetch failed: %s", exc)
        return None

    finished: list[dict[str, Any]] = []
    for ent in registry:
        if ent.get("status") not in {"completed", "failed", "expired", "cancelled"}:
            continue
        completed_at = str(ent.get("completed_at") or ent.get("expired_at") or "")
        if not completed_at:
            continue
        if last_mark and completed_at <= last_mark:
            continue
        finished.append(ent)

    if not finished:
        return None

    finished.sort(key=lambda e: str(e.get("completed_at") or e.get("expired_at") or ""), reverse=True)

    # Advance the mark to the newest completion seen so this digest doesn't
    # repeat next turn.
    newest = max(
        str(e.get("completed_at") or e.get("expired_at") or "") for e in finished
    )
    if newest:
        _mark_seen(sid, newest)

    bullets = []
    for ent in finished[:_MAX_DIGEST_ITEMS]:
        role = str(ent.get("role") or "?")
        status = str(ent.get("status") or "?")
        goal = str(ent.get("goal") or "")[:140]
        agent_id = str(ent.get("agent_id") or "?")[-10:]
        glyph = "✓" if status == "completed" else ("✗" if status == "failed" else "·")
        bullets.append(f"{glyph} {role}/{agent_id} ({status}): {goal}")

    return (
        "Subagenter der har afsluttet siden sidst (kald list_agents eller "
        "send_message_to_agent for fulde resultater hvis relevant):\n"
        + "\n".join(bullets)
    )
