"""Auto-inject of relevant brain fakta into prompt awareness.

Embedding-search brain_index for top-K fakta matching the current user
message. Privacy-gated by session-derived visibility ceiling.

Spec: docs/superpowers/specs/2026-05-02-jarvis-brain-design.md sektion 5.2.
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone

logger = logging.getLogger("prompt_sections.jarvis_brain_facts")


def _ceiling_from_session_id(session_id: str | None) -> str:
    """Map session_id → visibility ceiling.

    Conservative mapping based on session title channel-parsing:
    - jarvisx_native / webchat (single-user, owner) → intimate
    - discord_dm / telegram_dm (1:1 with owner) → intimate
    - discord_channel (multi-user) → public_safe
    - unknown / autonomous / no session → public_safe (default deny)

    For full participant-based visibility logic, callers can construct
    a richer Session-like object and call session_visibility_ceiling
    directly. This helper is the practical default for prompt assembly.
    """
    if not session_id:
        return "public_safe"

    try:
        from core.services.chat_sessions import (
            get_chat_session,
            parse_channel_from_session_title,
        )
        sess = get_chat_session(session_id)
        if not sess:
            return "public_safe"
        title = str(sess.get("title") or "")
        channel_type, _detail = parse_channel_from_session_title(title)
    except Exception:
        return "public_safe"

    # Owner-only single-user channels → intimate
    if channel_type in {"webchat", "jarvisx_native"}:
        return "intimate"
    # 1:1 DMs → intimate (we only know if it's a DM, not who's on the
    # other side — DMs are addressed by definition to one party so if
    # title says "DM" we assume owner)
    if channel_type in {"discord_dm", "telegram_dm"}:
        return "intimate"
    # Multi-user channels → public_safe (least-privileged-wins)
    if channel_type in {"discord_channel", "telegram_channel"}:
        return "public_safe"
    return "public_safe"


def build_brain_facts_section(
    *,
    user_message: str,
    session_id: str | None,
    top_k: int = 3,
    threshold: float = 0.55,
) -> str:
    """Return markdown section with top-K relevant fakta, or "" if none.

    Bumper salience for hver returneret entry (use-it-or-lose-it).
    Fail-soft: any exception → return "" (recall must never block prompt).
    """
    try:
        from core.services import jarvis_brain
    except Exception:
        return ""

    ceiling = _ceiling_from_session_id(session_id)

    try:
        results = jarvis_brain.search_brain(
            query_text=user_message,
            kinds=["fakta"],
            visibility_ceiling=ceiling,
            limit=max(1, top_k),
        )
    except Exception as exc:
        logger.warning("brain auto-inject search failed: %s", exc)
        return ""

    if not results:
        return ""

    # Filter by threshold using a re-score (search_brain doesn't expose scores;
    # we approximate by re-computing via embedding match). Simpler: trust
    # search_brain's ordering and just take top_k. Apply threshold filter via
    # cosine on the front-runner (approximate).
    # For v1 we trust search_brain's ranking. Threshold becomes an effective
    # min_results gate — if even top entry is irrelevant, search returns it
    # but we drop everything if user_message has no embedding overlap.
    # TODO v2: expose scores from search_brain for proper thresholding.
    _ = threshold  # currently unused; v1 trusts search_brain ordering

    # Bump salience (use-it-or-lose-it)
    now = datetime.now(timezone.utc)
    for e in results:
        try:
            jarvis_brain.bump_salience(e.id, now=now)
        except Exception:
            pass

    lines = ["## Relevante fakta fra min hjerne", ""]
    for e in results:
        snippet = e.content if len(e.content) <= 200 else e.content[:200] + "…"
        lines.append(f"- **{e.title}** [{e.id[-8:]}]: {snippet}")
    return "\n".join(lines)
