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

    # ── PreCompact-hook ──────────────────────────────────────────────────
    # Foer historikken klippes: `block` betyder lad vaere. Det er den eneste
    # dom der giver mening — bagefter er beskederne vaek, og en hook der
    # «blokerede» ville have blokeret ingenting.
    try:
        from core.services import lifecycle_hooks as _lh
        if "PreCompact" in _lh.WIRED_EVENTS and _lh.hooks_for("PreCompact"):
            _d = _lh.fire("PreCompact", {"session_id": str(session_id or ""),
                                         "keep_recent": int(keep_recent or 0)})
            if _d.get("action") == "block":
                _log_pc = __import__("logging").getLogger(__name__)
                _log_pc.info("PreCompact blokeret af hook: %s",
                             str(_d.get("message") or "")[:120])
                return None
    except Exception:
        pass
    # INGEN self-heal foer komprimeringen (fjernet 16/9-2026).
    #
    # Her stod «Lag D»: skriv den gamle markoer om, FOER den nye komprimering.
    # Maalt i journalen: hver gang skrev den en ny kort markoer (~1.700 tegn,
    # ofte ubrugelig — «We need answer user asks rewrite compact summary…»),
    # og 10-17 s senere lagde komprimeringen den store oven paa. Bjoern saa
    # parrene paa 12/9, 14/9 og 15/9 og koblede dem til sine stille cutoffs.
    #
    # Omskrivningen var spildt — markoeren blev afloest med det samme — og
    # farlig i mellemtiden: markoeren laegges sidst i sessionen, og kun beskeder
    # EFTER den sendes med. I hullet saa en ny prompt-bygning (prompt-cachen
    # holder 45 s, og hans ture varer minutter) et resume paa 300 ord og
    # INGENTING efter det — heller ikke den besked han var ved at faa svar paa.
    #
    # De gamle fejl markeres i stedet som afloest, naar den nye markoer staar.

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

    # Den nye markoer afloeser de gamle. Uden dette ville vagten (hvert 30.
    # min) og prompt-stien senere «hele» en markoer der ikke laengere bruges —
    # og laegge en ny oven paa alt der er skrevet siden.
    try:
        from core.context.compact_ground_truth import mark_failures_superseded
        mark_failures_superseded(session_id, new_marker_id=marker_id)
    except Exception as exc:
        logger.debug("session_compact: afloesning ikke markeret (%s)", exc)

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
