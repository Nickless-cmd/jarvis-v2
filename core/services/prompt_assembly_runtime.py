"""Turn-cache orchestration for visible prompt assembly.

Extracted from ``prompt_contract`` so the large contract module only describes
prompt content. The cache remains strictly keyed by the newest persisted user
message id; it can reuse post-tool rounds but never a later user turn.
"""
from __future__ import annotations

import time
from typing import Any, Callable

from core.services import prompt_assembly_turn_cache as turn_cache


def _query_latest_user_msg_id(session_id: str) -> int:
    from core.services.chat_sessions import connect
    with connect() as conn:
        row = conn.execute(
            "SELECT MAX(id) AS m FROM chat_messages "
            "WHERE session_id = ? AND role = 'user'",
            (session_id,),
        ).fetchone()
    return int(row["m"]) if row and row["m"] is not None else 0


def latest_user_msg_id(session_id: str | None) -> int:
    sid = (session_id or "").strip()
    if not sid:
        return 0
    try:
        return _query_latest_user_msg_id(sid)
    except Exception:  # Cache-sikkerhed: en DB-fejl skal bygge frisk, aldrig servere stale.
        return 0


def build_with_turn_cache(
    *,
    builder: Callable[..., Any],
    latest_message_id: int,
    provider: str,
    model: str,
    user_message: str,
    session_id: str | None,
    name: str,
    runtime_self_report_context: dict[str, object] | None,
    caller_phase: str,
) -> Any:
    from core.services.prompt_assembly_telemetri import rapporter_cache_lookup

    # Scope hoerer i noeglen: samme besked bygget i chat og i code er to
    # forskellige prompts. Maalt 22/10-2026 stod scope uden for noeglen, saa en
    # genbygning efter et rums-skift kunne servere den anden modes assembly —
    # inkl. den forkerte vaerktoejsoverblik og den forkerte orientering.
    from core.tools.tool_scoping import current_tool_scope

    key = (
        (
            str(session_id or ""),
            latest_message_id,
            provider,
            model,
            name,
            current_tool_scope(),
        )
        if latest_message_id > 0 else None
    )
    now = time.monotonic()
    lookup_started = time.monotonic()
    lookup = turn_cache.lookup(key, now=now)
    lookup_ms = (time.monotonic() - lookup_started) * 1000
    if lookup.outcome == "hit":
        rapporter_cache_lookup(
            key=key, outcome=lookup.outcome, cache_age_ms=lookup.age_ms,
            lookup_ms=lookup_ms, build_ms=None, caller_phase=caller_phase,
        )
        return lookup.value

    build_started = time.monotonic()
    try:
        result = builder(
            provider=provider, model=model, user_message=user_message,
            session_id=session_id, name=name,
            runtime_self_report_context=runtime_self_report_context,
        )
    finally:
        rapporter_cache_lookup(
            key=key, outcome=lookup.outcome, cache_age_ms=lookup.age_ms,
            lookup_ms=lookup_ms,
            build_ms=(time.monotonic() - build_started) * 1000,
            caller_phase=caller_phase,
        )
    if key is not None:
        turn_cache.store(key, result, now=now)
    return result
