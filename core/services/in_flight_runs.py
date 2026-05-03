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
# A run that's been "in flight" for less than this is probably just still
# streaming on another worker, NOT actually interrupted. Avoid the false
# positive where the next user message races the previous run's finally
# block.
_MIN_AGE_TO_SURFACE_SECONDS = 90
_RESUME_WORDS = (
    "fortsæt", "fortsaet", "prøv igen", "prov igen", "igen", "go on",
    "continue", "resume", "samle op", "kør videre", "kor videre",
)
_RESTART_WORDS = (
    "start forfra", "ny opgave", "glem den", "drop den", "restart",
    "start over", "ignore previous", "glem det",
)


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
    """Record that a visible run is in flight. Keyed by run_id (unique).

    Side effect: clears any prior in_flight records for the same session.
    A new turn implies the previous turn finished (or won't finish) — keep
    only the most recent so the digest never sees zombies left behind by
    crashes, killed runs, or finally-blocks that didn't complete.
    """
    if not run_id:
        return
    sid = str(session_id or "")
    records = _load()
    # Drop any earlier in_flight for the same session before adding the new one.
    if sid:
        stale_run_ids = [
            rid for rid, rec in records.items()
            if rec.get("session_id") == sid and rid != str(run_id)
        ]
    for rid in stale_run_ids:
        if str(records.get(rid, {}).get("status") or "running") != "interrupted":
            records.pop(rid, None)
    records[str(run_id)] = {
        "run_id": str(run_id),
        "session_id": sid,
        "status": "running",
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


def mark_interrupted(run_id: str, *, reason: str = "", summary: str = "") -> None:
    """Keep an in-flight record as a resumable interrupted run."""
    if not run_id:
        return
    records = _load()
    rec = records.get(str(run_id))
    if rec is None:
        return
    rec["status"] = "interrupted"
    rec["interruption_reason"] = str(reason or "")[:120]
    rec["interruption_summary"] = str(summary or "")[:240]
    rec["interrupted_at"] = datetime.now(UTC).isoformat()
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
    candidates = [
        r for r in records.values()
        if r.get("session_id") == sid
        and str(r.get("status") or "interrupted") == "interrupted"
    ]
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


def classify_resume_intent(user_message: str) -> str:
    """Classify whether a user message should resume an interrupted run."""
    normalized = " ".join(str(user_message or "").strip().lower().split())
    if not normalized:
        return "unclear"
    if any(word in normalized for word in _RESTART_WORDS):
        return "restart"
    if any(word in normalized for word in _RESUME_WORDS):
        return "resume"
    return "unclear"


def interruption_prompt_section(
    session_id: str | None,
    user_message: str = "",
) -> str | None:
    """Format an interrupted record as a system-prompt block, or None.

    Race-aware: only surfaces if the in_flight record is older than
    _MIN_AGE_TO_SURFACE_SECONDS. The previous run's finally-block (which
    calls mark_completed) runs *after* the [DONE] event reaches the
    client, so a fast follow-up message can race the cleanup. A genuine
    interruption (crash, restart) leaves the record older than the
    threshold and surfaces correctly.
    """
    rec = interrupted_for_session(session_id)
    if not rec:
        return None
    intent = classify_resume_intent(user_message)
    if intent == "restart":
        return None
    started_iso = str(rec.get("started_at") or "")
    if started_iso:
        try:
            started_dt = datetime.fromisoformat(started_iso)
            age = (datetime.now(UTC) - started_dt).total_seconds()
            if age < _MIN_AGE_TO_SURFACE_SECONDS:
                return None
        except Exception:
            pass
    excerpt = str(rec.get("excerpt") or "(intet uddrag)")
    last_tool = str(rec.get("last_tool") or "")
    reason = str(rec.get("interruption_reason") or "")
    started_at = started_iso[11:19] if started_iso else ""
    tool_clause = f" — sidste tool var {last_tool}" if last_tool else ""
    reason_clause = f" Årsag: {reason}." if reason else ""
    checkpoint = ""
    try:
        from core.services.agentic_checkpoints import checkpoint_prompt_section
        checkpoint = checkpoint_prompt_section(session_id) or ""
    except Exception:
        checkpoint = ""
    conclusion = ""
    try:
        from core.services.agentic_working_conclusions import working_conclusion_prompt_section
        conclusion = working_conclusion_prompt_section(session_id) or ""
    except Exception:
        conclusion = ""
    if intent == "resume":
        policy = (
            "AUTO-RESUME: Brugerens besked betyder fortsæt/prøv igen. "
            "Fortsæt fra checkpointet uden at spørge først, og undgå at gentage allerede udførte tools medmindre inputfilerne er ændret."
        )
    else:
        policy = (
            "Intent er ikke tydelig resume. Spørg kort om du skal fortsætte fra checkpointet eller starte forfra, før du bruger mere tool-budget."
        )
    return (
        "Du blev afbrudt midt i en opgave (startet "
        f"{started_at}{tool_clause}):\n"
        f"  \"{excerpt}\"\n"
        f"{reason_clause}\n"
        f"{checkpoint + chr(10) if checkpoint else ''}"
        f"{conclusion + chr(10) if conclusion else ''}"
        f"{policy}"
    )
