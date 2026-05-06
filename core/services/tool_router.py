"""Per-turn tool selection.

Returns a ToolSelection containing the names of tools to send with full
schema this turn. Falls back to the full registry when confidence is low,
when any subsystem fails, or when the killswitch is set.
"""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field

from core.eventbus.bus import event_bus
from core.runtime.db import connect
from core.runtime.settings import RuntimeSettings

logger = logging.getLogger(__name__)

_QUESTION_WORDS_DA_EN = {
    "hvor", "hvad", "hvem", "hvorfor", "hvordan", "hvornår",
    "what", "where", "why", "how", "who", "when",
}
_AFFIRMATIONS = {"ja", "nej", "ok", "okay", "godt", "go", "sure", "yes", "no"}

# Hardcoded fallback when call-log is empty and pinned set isn't loaded.
_BOOTSTRAP_FALLBACK_CORE = [
    "read_file", "write_file", "edit_file", "grep", "list_dir",
    "bash", "pause_and_ask", "remember_this", "recall_memories",
    "search_memory", "web_search", "decision_create",
    "todo_add", "load_more_tools",
    "git_status", "git_log", "git_diff",
    "discord_channel", "send_message",
    "scheduled_task_create", "goal_create",
    "search_sessions", "todo_complete", "web_fetch",
    "git_show",
]


@dataclass
class ToolSelection:
    selected_names: list[str]
    always_core: list[str] = field(default_factory=list)
    embedding_picks: list[str] = field(default_factory=list)
    confidence: float = 0.0
    threshold: float = 0.0
    fallback_used: bool = False
    fallback_reason: str = ""
    elapsed_ms: int = 0
    reason: str = ""


def _clarity_signal(msg: str) -> float:
    msg = (msg or "").strip()
    if not msg:
        return 0.0
    words = re.findall(r"\w+", msg.lower())
    if not words:
        return 0.0
    if len(words) == 1 and words[0] in _AFFIRMATIONS:
        return 0.15
    if len(words) < 3:
        return 0.30
    has_q = any(w in _QUESTION_WORDS_DA_EN for w in words) or "?" in msg
    base = 0.55 + (0.15 if has_q else 0.0) + min(0.15, len(words) * 0.01)
    return min(1.0, base)


def _score(user_message: str, *, top_sim: float, load_more_rate_7d: float) -> float:
    msg_clarity = _clarity_signal(user_message)
    similarity_strength = min(top_sim / 0.7, 1.0) if top_sim > 0 else 0.0
    adaptive_floor = max(0.30, 0.60 - load_more_rate_7d * 2.0)
    return (msg_clarity * 0.4 + similarity_strength * 0.6) * adaptive_floor


def _all_tool_names() -> list[str]:
    from core.tools.simple_tools import get_tool_definitions
    return [
        ((d.get("function") or {}).get("name") or d.get("name") or "")
        for d in (get_tool_definitions() or [])
    ]


def _always_core_set(limit: int) -> list[str]:
    """Top-N tools by 7-day call count ∪ pinned set, with fallback."""
    from core.services.tool_tagger import get_pinned_set
    try:
        pinned = get_pinned_set()
    except Exception:
        pinned = set()
    try:
        with connect() as c:
            rows = c.execute(
                "SELECT json_extract(payload_json, '$.tool') AS tool, COUNT(*) AS n "
                "FROM events WHERE kind = 'tool.invoked' "
                "AND created_at >= datetime('now', '-7 days') "
                "GROUP BY tool ORDER BY n DESC LIMIT ?",
                (max(limit, 200),),
            ).fetchall()
        used_top = [r[0] for r in rows if r[0]][:limit]
    except Exception as exc:
        logger.warning("tool_router._always_core_set query failed: %s", exc)
        used_top = []

    core = list(dict.fromkeys(list(pinned) + used_top))
    if not core:
        core = list(_BOOTSTRAP_FALLBACK_CORE)

    pinned_in_core = [n for n in core if n in pinned]
    rest = [n for n in core if n not in pinned]
    out = pinned_in_core + rest[: max(0, limit - len(pinned_in_core))]
    return out


def _load_more_rate_7d() -> float:
    try:
        with connect() as c:
            decisions = c.execute(
                "SELECT COUNT(*) FROM tool_router_decisions "
                "WHERE created_at >= datetime('now', '-7 days')"
            ).fetchone()[0]
            load_more = c.execute(
                "SELECT COUNT(*) FROM tool_router_load_more "
                "WHERE created_at >= datetime('now', '-7 days')"
            ).fetchone()[0]
        if not decisions:
            return 0.0
        return float(load_more) / float(decisions)
    except Exception:
        return 0.0


def select_tools(
    *, user_message: str, session_id: str | None, lane: str, run_id: str | None = None,
) -> ToolSelection:
    """Select a subset of tools for this turn. Always returns a ToolSelection."""
    started_at = time.monotonic()
    settings = RuntimeSettings()

    if not settings.tool_router_enabled:
        sel = ToolSelection(
            selected_names=_all_tool_names(),
            fallback_used=True,
            fallback_reason="killswitch-off",
            reason="tool_router_enabled=False",
            elapsed_ms=int((time.monotonic() - started_at) * 1000),
        )
        _persist(sel, user_message, session_id, lane, run_id)
        return sel

    try:
        return _select_inner(
            user_message=user_message,
            session_id=session_id,
            lane=lane,
            run_id=run_id,
            settings=settings,
            started_at=started_at,
        )
    except Exception as exc:
        logger.exception("tool_router.select_tools failed; falling back to full list")
        sel = ToolSelection(
            selected_names=_all_tool_names(),
            fallback_used=True,
            fallback_reason=f"router-error: {type(exc).__name__}",
            reason=str(exc)[:200],
            elapsed_ms=int((time.monotonic() - started_at) * 1000),
        )
        _persist(sel, user_message, session_id, lane, run_id)
        return sel


def _select_inner(
    *, user_message, session_id, lane, run_id, settings, started_at,
) -> ToolSelection:
    from core.services.tool_embeddings import top_k_similar

    always_core = _always_core_set(settings.tool_router_always_core_size)
    threshold = float(settings.tool_router_threshold)
    load_more_rate = _load_more_rate_7d()

    try:
        sim = top_k_similar(user_message or "", k=settings.tool_router_k_embeddings)
    except Exception as exc:
        logger.warning("tool_router: embedding lookup failed: %s", exc)
        sim = []

    top_sim = sim[0][1] if sim else 0.0
    confidence = _score(user_message or "", top_sim=top_sim, load_more_rate_7d=load_more_rate)

    if confidence < threshold:
        sel = ToolSelection(
            selected_names=_all_tool_names(),
            always_core=always_core,
            embedding_picks=[n for n, _ in sim],
            confidence=confidence,
            threshold=threshold,
            fallback_used=True,
            fallback_reason="confidence-below-threshold",
            elapsed_ms=int((time.monotonic() - started_at) * 1000),
            reason=f"confidence={confidence:.3f} < threshold={threshold:.3f}",
        )
        _persist(sel, user_message, session_id, lane, run_id)
        return sel

    embedding_picks = [n for n, _ in sim if n not in set(always_core)]
    selected = list(dict.fromkeys(always_core + embedding_picks))[:100]

    sel = ToolSelection(
        selected_names=selected,
        always_core=always_core,
        embedding_picks=embedding_picks,
        confidence=confidence,
        threshold=threshold,
        fallback_used=False,
        elapsed_ms=int((time.monotonic() - started_at) * 1000),
        reason=f"selected={len(selected)} core={len(always_core)} emb={len(embedding_picks)}",
    )
    _persist(sel, user_message, session_id, lane, run_id)
    return sel


def _persist(
    sel: ToolSelection, user_message: str, session_id: str | None, lane: str, run_id: str | None,
) -> None:
    preview = (user_message or "")[:200]
    full_count = len(_all_tool_names())
    tokens_saved = max(0, (full_count - len(sel.selected_names)) * 130)
    payload = {
        "run_id": run_id, "session_id": session_id, "lane": lane,
        "user_message_preview": preview,
        "selected_count": len(sel.selected_names),
        "fallback_used": bool(sel.fallback_used),
        "always_core_count": len(sel.always_core),
        "embedding_picks_count": len(sel.embedding_picks),
        "confidence": sel.confidence, "threshold": sel.threshold,
        "elapsed_ms": sel.elapsed_ms,
        "would_have_sent_full": full_count,
        "tokens_saved_estimate": tokens_saved,
    }
    try:
        event_bus.publish("tool_router.decision", payload)
    except Exception:
        pass
    try:
        with connect() as c:
            c.execute(
                "INSERT INTO tool_router_decisions("
                "run_id, session_id, lane, user_message_preview, "
                "selected_names_json, always_core_names_json, embedding_picks_json, "
                "confidence, threshold, fallback_used, fallback_reason, "
                "elapsed_ms, tokens_saved_estimate, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?, datetime('now'))",
                (
                    run_id, session_id, lane, preview,
                    json.dumps(sel.selected_names), json.dumps(sel.always_core),
                    json.dumps(sel.embedding_picks),
                    sel.confidence, sel.threshold,
                    1 if sel.fallback_used else 0, sel.fallback_reason,
                    sel.elapsed_ms, tokens_saved,
                ),
            )
            c.commit()
    except Exception as exc:
        logger.warning("tool_router._persist failed: %s", exc)
