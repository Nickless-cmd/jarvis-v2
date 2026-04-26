"""In-flight run tracker for resume-after-interrupt.

When a visible run starts, we drop a small record on disk. When it
completes (success OR fail OR cancel), we clear it. If a record
survives to the next visible turn for the same session, the prompt
assembler surfaces it as: "Du blev afbrudt midt i: <excerpt>" so the
model can ask the user whether to continue or restart.

Without this, a service restart, browser crash, or unhandled exception
silently drops whatever Jarvis was working on — the user has no signal
to follow up, and Jarvis has no memory of the dropped task. The whole
agentic-parity stack is undermined when interrupted work just vanishes.

Pattern follows phase 0's state_store (atomic JSON file).
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from core.runtime.state_store import load_json, save_json

logger = logging.getLogger(__name__)

_STATE_KEY = "in_flight_runs"
_EXCERPT_LIMIT = 240


def _load() -> dict[str, dict[str, Any]]:
    raw = load_json(_STATE_KEY, {})
    if not isinstance(raw, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for k, v in raw.items():
        if isinstance(v, dict):
            out[str(k)] = v
    return out


def _save(records: dict[str, dict[str, Any]]) -> None:
    save_json(_STATE_KEY, records)


def mark_started(*, run_id: str, session_id: str | None, user_message: str) -> None:
    """Record that a visible run is in flight. Keyed by run_id (unique)."""
    if not run_id:
        return
    records = _load()
    records[str(run_id)] = {
        "run_id": str(run_id),
        "session_id": str(session_id or ""),
        "excerpt": (user_message or "")[:_EXCERPT_LIMIT],
        "started_at": datetime.now(UTC).isoformat(),
        "last_tool": "",
    }
    _save(records)


def mark_tool(run_id: str, tool_name: str) -> None:
    """Update the last-tool-attempted hint for an in-flight run."""
    if not run_id or not tool_name:
        return
    records = _load()
    rec = records.get(str(run_id))
    if rec is None:
        return
    rec["last_tool"] = str(tool_name)[:80]
    _save(records)


def mark_completed(run_id: str) -> None:
    """Clear an in-flight record on success/fail/cancel — all the same to us;
    only *unresolved* records should reach the next prompt build."""
    if not run_id:
        return
    records = _load()
    if str(run_id) in records:
        records.pop(str(run_id), None)
        _save(records)


def interrupted_for_session(session_id: str | None) -> dict[str, Any] | None:
    """Return the most recent in-flight record for this session, or None.

    "Most recent" matters because a brief race during normal completion can
    leave a stale record momentarily; the freshest one is the most likely
    candidate for "this is what I was doing".
    """
    if not session_id:
        return None
    sid = str(session_id)
    records = _load()
    candidates = [r for r in records.values() if r.get("session_id") == sid]
    if not candidates:
        return None
    candidates.sort(key=lambda r: str(r.get("started_at", "")), reverse=True)
    return candidates[0]


def clear_session(session_id: str | None) -> int:
    """Drop all in-flight records for a session (used when user explicitly
    says 'restart' / 'forget that')."""
    if not session_id:
        return 0
    sid = str(session_id)
    records = _load()
    to_drop = [k for k, v in records.items() if v.get("session_id") == sid]
    for k in to_drop:
        records.pop(k, None)
    if to_drop:
        _save(records)
    return len(to_drop)


def interruption_prompt_section(session_id: str | None) -> str | None:
    """Format an interrupted record as a system-prompt block, or None."""
    rec = interrupted_for_session(session_id)
    if not rec:
        return None
    excerpt = str(rec.get("excerpt") or "(intet uddrag)")
    last_tool = str(rec.get("last_tool") or "")
    started_at = str(rec.get("started_at") or "")[11:19]
    tool_clause = f" — sidste tool var {last_tool}" if last_tool else ""
    return (
        "Du blev afbrudt midt i en opgave (startet "
        f"{started_at}{tool_clause}):\n"
        f"  \"{excerpt}\"\n"
        "Spørg brugeren om du skal fortsætte derfra eller starte forfra, "
        "FØR du gør noget. Brug ikke tool calls før der er afklaring."
    )
