"""Binder spawn_agent_task til agent-contract-v1 (leverance A2).

Ejer og oprindelsessession tages fra den autentificerede anmodningskontekst
(eller den eksplicitte `context`), aldrig fra et tomt felt. Mangler en af dem,
bindes agenten IKKE: den forbliver `legacy_unscoped` og kører som hidtil, så
det er en synlig mangel i stedet for en opdigtet ejer (§4, §12.2).
Persistente agenter bindes ikke endnu: de får ét assignment pr. aktivering
(§12.1), som hører til en senere leverance.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def resolve_owner_and_session(context: dict[str, Any] | None) -> tuple[str, str]:
    ctx = context or {}
    owner = str(ctx.get("user_id") or "").strip()
    session = str(ctx.get("parent_session_id") or "").strip()
    if not owner or not session:
        try:
            from core.identity.workspace_context import current_session_id, current_user_id
            owner = owner or str(current_user_id() or "").strip()
            session = session or str(current_session_id() or "").strip()
        except Exception:
            logger.debug("kontekst ikke tilgængelig ved agentbinding", exc_info=True)
    return owner, session


def bind_new_agent(*, agent_id: str, parent_agent_id: str, goal: str, persistent: bool,
                   context: dict[str, Any] | None, budget_tokens: int = 0,
                   max_turns: int = 0, result_contract: dict[str, Any] | None = None) -> dict[str, Any]:
    """Opret agentens første assignment. Kaster aldrig: dispatch må ikke dø af bindingen."""
    if persistent:
        return {"bound": False, "reason": "persistent"}
    owner, session = resolve_owner_and_session(context)
    if not owner or not session:
        logger.warning("agent %s bundet uden ejer/session — forbliver legacy_unscoped", agent_id)
        return {"bound": False, "reason": "no_owner_or_session"}
    try:
        from core.runtime import db_agent_contract as c
        c.bind_agent_owner(agent_id=agent_id, owner_user_id=owner, owner_session_id=session)
        acc = c.accept_assignment(
            agent_id=agent_id, owner_user_id=owner, origin_session_id=session, goal=goal,
            parent_agent_id=parent_agent_id,
            parent_run_id=str((context or {}).get("parent_run_id") or ""),
            expected_result=",".join(sorted((result_contract or {}).keys())),
            budget={"tokens": budget_tokens, "max_turns": max_turns},
            created_by=parent_agent_id, idempotency_key=agent_id,
        )
        return {"bound": True, **acc}
    except Exception as exc:
        logger.warning("kunne ikke binde agent %s til kontrakten: %s", agent_id, exc, exc_info=True)
        return {"bound": False, "reason": "error", "error": str(exc)}
