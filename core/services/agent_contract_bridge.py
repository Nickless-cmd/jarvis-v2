"""Binder spawn_agent_task til agent-contract-v1 (leverance A2).

Ejer og oprindelsessession tages fra den autentificerede anmodningskontekst
(eller den eksplicitte `context`), aldrig fra et tomt felt. Mangler en af dem,
bindes agenten IKKE: den forbliver `legacy_unscoped` og kører som hidtil, så
det er en synlig mangel i stedet for en opdigtet ejer (§4, §12.2).
Persistente agenter får ejer og session ved spawn (når motoren er tændt), men
ét assignment pr. aktivering (§12.1, `agent_activation`).
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
                   max_turns: int = 0, result_contract: dict[str, Any] | None = None,
                   idempotency_key: str = "", request_digest: str = "",
                   target: str = "runtime-container", operation: str = "dispatch",
                   expected_result: str = "") -> dict[str, Any]:
    """Opret agentens første assignment. Kaster aldrig: dispatch må ikke dø af bindingen."""
    owner, session = resolve_owner_and_session(context)
    if persistent:
        return _bind_persistent(agent_id, owner, session)
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
            expected_result=expected_result or ",".join(sorted((result_contract or {}).keys())),
            budget={"tokens": budget_tokens, "max_turns": max_turns}, target=target,
            created_by=parent_agent_id, operation=operation,
            idempotency_key=idempotency_key or agent_id, request_digest=request_digest,
        )
        _write_assignment_artifact(agent_id, owner, acc, goal, parent_agent_id, context, target)
        return {"bound": True, **acc}
    except Exception as exc:
        logger.warning("kunne ikke binde agent %s til kontrakten: %s", agent_id, exc, exc_info=True)
        return {"bound": False, "reason": "error", "error": str(exc)}


def _bind_persistent(agent_id: str, owner: str, session: str) -> dict[str, Any]:
    """En persistent agent faar sin autentificerede ejer og oprindelsessession, men INTET assignment: de
    oprettes pr. aktivering (``agent_activation``, §12.1). Kun naar motoren er taendt - slukket forbliver
    den som hidtil (``legacy_unscoped``), saa dark launch ikke aendrer en eksisterende vagts adfaerd."""
    if not owner or not session:
        logger.warning("persistent agent %s bundet uden ejer/session - forbliver legacy_unscoped", agent_id)
        return {"bound": False, "reason": "no_owner_or_session"}
    try:
        from core.services.agent_contract_service import capability_enabled
        if not capability_enabled():
            return {"bound": False, "reason": "engine_off"}
        from core.runtime import db_agent_contract as c
        c.bind_agent_owner(agent_id=agent_id, owner_user_id=owner, owner_session_id=session)
        return {"bound": True, "persistent": True, "owner_user_id": owner}
    except Exception as exc:
        logger.warning("kunne ikke binde persistent agent %s: %s", agent_id, exc, exc_info=True)
        return {"bound": False, "reason": "error", "error": str(exc)}


def _write_assignment_artifact(agent_id: str, owner: str, acc: dict[str, Any], goal: str,
                               parent_agent_id: str, context: dict[str, Any] | None,
                               target: str) -> None:
    """``assignment.json`` for foerste run (§9). Bedste-indsats: et manglende artefakt
    maa aldrig vaelte et dispatch - den vises senere som en synlig mangel."""
    import json

    try:
        from core.runtime import db_agent_artifacts as art
        art.write_artifact(
            agent_id=agent_id, run_id=acc["run_id"], name="assignment.json",
            assignment_id=acc["assignment_id"], owner_user_id=owner,
            data=json.dumps({"assignment_id": acc["assignment_id"], "agent_id": agent_id,
                             "goal": goal, "parent_agent_id": parent_agent_id,
                             "parent_run_id": str((context or {}).get("parent_run_id") or ""),
                             "target": target, "contract_version": acc.get("contract_version", "")},
                            ensure_ascii=False, indent=2))
    except Exception:
        logger.warning("assignment.json kunne ikke gemmes for %s", agent_id, exc_info=True)
