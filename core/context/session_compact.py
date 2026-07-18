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
    keep_recent_tokens: int | None = None,
    summarise_fn: Callable[[list[dict]], str],
    git_sha: str = "",
) -> CompactResult | None:
    """Compact old session history for session_id.

    Fetches all messages, splits into (old, kept_tail), summarises the old slice via
    summarise_fn, stores a compact_marker in DB, and returns a CompactResult. Returns
    None if there is nothing worth compacting.

    Split strategy:
      - `keep_recent_tokens` given → ROUND-ATOMIC selection (never splits a
        tool_use/tool_result pair, always keeps the live/last round), keeping recent whole
        rounds up to that token budget (2026-07-18 live-compaction spec).
      - else → legacy count-split at (total - keep_recent). Kept for backward compat.

    If git_sha is provided, it's stored with the marker for freshness checks
    (Lag B — ground-truth grounding).

    Lag D: On entry, attempts to resolve any stale/unresolved compact markers
    for this session. This is the boot-time self-healing hook.
    """
    # Lag D: self-heal stale markers before compacting
    try:
        from core.context.compact_ground_truth import resolve_stale_markers_on_load
        healed = resolve_stale_markers_on_load(session_id)
        if healed:
            logger.info(
                "session_compact: self-healed session=%s → new marker=%s",
                session_id, healed,
            )
    except Exception as exc:
        logger.debug("session_compact: self-heal skipped (%s)", exc)

    messages = _get_all_session_messages(session_id)

    _kept: list[dict] = []
    if keep_recent_tokens is not None:
        # Round-atomic, token-budgeted (never splits a tool pair, keeps the live round).
        from core.context.compaction_policy import select_for_compaction
        old_messages, _kept = select_for_compaction(
            messages, keep_recent_tokens=int(keep_recent_tokens)
        )
        if not old_messages:
            return None
    else:
        if len(messages) <= keep_recent:
            return None
        old_messages = messages[: len(messages) - keep_recent]
    freed_chars = sum(len(m.get("content") or "") for m in old_messages)
    freed_tokens = estimate_tokens("x" * freed_chars)

    # Memory Fix Phase 2: pre-compaction identity sketch update
    try:
        from core.services.identity_sketch import update_identity_sketch
        update_identity_sketch(trigger="pre_compact")
    except Exception as exc:
        logger.debug("session_compact: identity_sketch update skipped (%s)", exc)

    summary_text = summarise_fn(old_messages)

    # Tail-preservation (2026-07-18): the compact_marker is appended at the END of the
    # session, so messages BEFORE it (incl. the kept recent rounds) are no longer sent.
    # To keep the recent exchange VERBATIM after compaction (Codex/Cline "summary + recent
    # tail" model — avoids post-compaction thread loss), the kept rounds are embedded in the
    # marker blob itself, right after the summary. The prepended marker then carries both.
    marker_content = summary_text
    if _kept:
        try:
            from core.context.compaction_policy import render_transcript_for_summary
            tail = render_transcript_for_summary(_kept)
            if tail.strip():
                marker_content = (
                    summary_text
                    + "\n\n## Seneste udveksling (ordret bevaret siden compaction):\n"
                    + tail
                )
        except Exception as exc:
            logger.debug("session_compact: tail-embed skipped (%s)", exc)

    marker_id = _store_marker(session_id, marker_content, git_sha=git_sha)

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
