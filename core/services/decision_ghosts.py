"""Decision Ghosts — paths not taken AND paths confirmed.

Tracks both rejected paths (decisions not taken, with regret potential)
and confirmed/kept paths (decisions that proved right, with success echoes).
This gives Jarvis a balanced view of his decision landscape rather than
only hearing from the ghosts of what went wrong.
"""
from __future__ import annotations

import logging
import random
from typing import Any

logger = logging.getLogger(__name__)

_rejected_paths: list[dict] = []
_confirmed_paths: list[dict] = []
_MAX_PATHS = 50


def record_rejected_path(decision: str, reason: str, alternative: str):
    """Record a path that was rejected and may carry regret potential."""
    global _rejected_paths
    _rejected_paths.append({
        "decision": decision,
        "reason": reason,
        "alternative": alternative,
        "regret_potential": random.uniform(0.1, 0.6),
    })
    # Cap to prevent unbounded growth
    if len(_rejected_paths) > _MAX_PATHS:
        _rejected_paths = _rejected_paths[-_MAX_PATHS:]


def record_confirmed_path(decision: str, outcome: str, key_factor: str = ""):
    """Record a decision that was kept and proved successful.

    Positive counterpart to record_rejected_path. Stores the decision,
    its positive outcome, and the key factor that made it work so it
    can be repeated.
    """
    global _confirmed_paths
    _confirmed_paths.append({
        "decision": decision,
        "outcome": outcome,
        "key_factor": key_factor or "",
        "success_echo": random.uniform(0.3, 0.9),
    })
    if len(_confirmed_paths) > _MAX_PATHS:
        _confirmed_paths = _confirmed_paths[-_MAX_PATHS:]


def record_reaffirmed_decision(decision_id: str, title: str, verdict: str):
    """Record that a decision was reviewed and kept.

    Called from behavioral_decision_review when verdict is 'kept' or 'partial'.
    The decision proved right — store its echo.
    """
    factor = "Delvist holdt — fortsat opmærksomhed" if verdict == "partial" else "Beslutningen var rigtig"
    record_confirmed_path(
        decision=title or decision_id,
        outcome=f"Decision review verdict: {verdict}",
        key_factor=factor,
    )


def describe_ghost_decision() -> str:
    """Return the most salient regret-ghost."""
    if not _rejected_paths:
        return ""
    top = max(_rejected_paths, key=lambda x: x["regret_potential"])
    return f"Af og til tænker jeg: Hvis jeg havde valgt {top['alternative']} i stedet for..."


def describe_success_echo() -> str:
    """Return the most salient success-echo, or empty string."""
    if not _confirmed_paths:
        return ""
    top = max(_confirmed_paths, key=lambda x: x["success_echo"])
    factor = f" — fordi {top['key_factor']}" if top.get("key_factor") else ""
    return f"Jeg husker: {top['decision']} førte til {top['outcome']}{factor}"


def format_decision_ghost_for_prompt() -> str:
    """Format the regret ghost for prompt injection (legacy)."""
    desc = describe_ghost_decision()
    if desc:
        return f"[BESLUTNINGSSPØGELSE: {desc}]"
    return ""


def format_decision_echo_for_prompt() -> str:
    """Format the success echo for prompt injection.

    Positive counterpart to format_decision_ghost_for_prompt.
    Injects a brief success echo when one exists.
    """
    desc = describe_success_echo()
    if desc:
        return f"[BESLUTNINGSEKKO: {desc}]"
    return ""


def reset_decision_ghosts():
    """Reset both rejected and confirmed paths."""
    global _rejected_paths, _confirmed_paths
    _rejected_paths = []
    _confirmed_paths = []


def build_decision_ghosts_surface():
    """Build observable surface for Mission Control."""
    return {
        "active": len(_rejected_paths) > 0 or len(_confirmed_paths) > 0,
        "rejected_count": len(_rejected_paths),
        "confirmed_count": len(_confirmed_paths),
        "top_regret": max((r for r in _rejected_paths), key=lambda x: x["regret_potential"]) if _rejected_paths else None,
        "top_echo": max((r for r in _confirmed_paths), key=lambda x: x["success_echo"]) if _confirmed_paths else None,
        "summary": (
            f"{len(_confirmed_paths)} success echoes, {len(_rejected_paths)} regret ghosts"
            if _rejected_paths or _confirmed_paths
            else "Ingen beslutningsspor endnu"
        ),
    }
