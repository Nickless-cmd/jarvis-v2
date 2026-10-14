"""Persist the visible run and its composer context for durable recovery."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def mark_visible_run_started(
    run, *, tool_scope: str = "", force_user_id: str | None = None,
    recovery_task_id: str = "",
) -> None:
    """Record the settings a resumed run needs to keep its original lane.

    ``recovery_task_id`` gives den INDRE koersel opgavens id, naar turen er en
    genoptagelse. Uden den skriver ``mark_started`` posten under runnets eget
    id, og afregningen kan ikke se at den hoerer til opgaven (maalt 14/10-2026).
    """
    try:
        from core.services.in_flight_runs import mark_started

        mark_started(
            run_id=run.run_id,
            session_id=run.session_id,
            user_message=run.user_message,
            kind="autonomous" if getattr(run, "autonomous", False) else "visible",
            provider=run.provider,
            model=run.model,
            approval_mode="trust" if run.trust_all else "ask",
            thinking_mode=run.thinking_mode,
            tool_scope=tool_scope,
            surface=run.surface,
            force_user_id=str(force_user_id or run.user_id or ""),
            local_tool_exec=bool(run.local_tool_exec),
            task_id=str(recovery_task_id or ""),
        )
    except Exception:
        logger.warning("visible-run %s: kunne ikke skrive in-flight-sporet",
                       run.run_id, exc_info=True)
