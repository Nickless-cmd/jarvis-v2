"""Session-level context compaction.

Summarises old chat history into a compact_marker stored in the DB.
The newest `keep_recent` messages are never compacted.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

from core.context.token_estimate import estimate_tokens

logger = logging.getLogger(__name__)


@dataclass
class CompactResult:
    freed_tokens: int
    summary_text: str
    marker_id: str
    validation: dict | None = None  # Lag C: post-compact validation report


def compact_session_history(
    session_id: str,
    *,
    keep_recent: int = 20,
    summarise_fn: Callable[[list[dict]], str],
    git_sha: str = "",
) -> CompactResult | None:
    """Compact old session history for session_id.

    Fetches all messages, splits at (total - keep_recent), summarises the
    old slice via summarise_fn, stores a compact_marker in DB, and returns
    a CompactResult. Returns None if there are not enough messages to compact
    (i.e. total <= keep_recent).

    If git_sha is provided, it's stored with the marker for freshness checks
    (Lag B — ground-truth grounding).
    """
    messages = _get_all_session_messages(session_id)
    if len(messages) <= keep_recent:
        return None

    old_messages = messages[: len(messages) - keep_recent]
    freed_chars = sum(len(m.get("content") or "") for m in old_messages)
    freed_tokens = estimate_tokens("x" * freed_chars)

    summary_text = summarise_fn(old_messages)

    marker_id = _store_marker(session_id, summary_text, git_sha=git_sha)

    # Lag C: post-compact validation — check for hallucinated claims
    validation: dict | None = None
    try:
        from core.context.compact_ground_truth import validate_compact_marker
        validation = validate_compact_marker(
            session_id,
            summary_text,
            marker_id=marker_id,
        )
        if validation.get("verified_false", 0) > 0:
            logger.warning(
                "session_compact: session=%s marker=%s has %d verified-false claims",
                session_id,
                marker_id,
                validation["verified_false"],
            )
    except Exception as exc:
        logger.debug("session_compact: validation skipped (%s)", exc)

    logger.info(
        "session_compact: session=%s compacted %d messages → %d tokens freed",
        session_id,
        len(old_messages),
        freed_tokens,
    )
    return CompactResult(
        freed_tokens=freed_tokens,
        summary_text=summary_text,
        marker_id=marker_id,
        validation=validation,
    )


# ── Internal helpers (monkeypatched in tests) ──────────────────────────────

def _get_all_session_messages(session_id: str) -> list[dict]:
    from core.services.chat_sessions import recent_chat_session_messages
    return recent_chat_session_messages(session_id, limit=500)


def _store_marker(session_id: str, summary_text: str, git_sha: str = "") -> str:
    from core.services.chat_sessions import store_compact_marker
    return store_compact_marker(session_id, summary_text, git_sha=git_sha)
