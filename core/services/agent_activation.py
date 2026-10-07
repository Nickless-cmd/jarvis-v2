"""Aktivering af en persistent agent: ét assignment og én rute pr. aktivering (agent-contract-v1 G, spec 12.1).

En persistent agent har en varig identitet og et mål, men arbejder i afgraensede, planlagte runs. HVER aktivering
(planlagt vaekning, manuel besked/foerste koersel) opretter et nyt assignment med eget run, egen rutebeslutning
(``decide_route`` + ``agent_route_decisions``, saa rute-proveniens gaelder dem som alle andre) og slutter med
praecis én terminalbesked til den bundne parent-inbox. Samme identitet har hoejst ét aabent assignment: findes
der et (et retry efter en fejlet koersel, en lease-genstart), genbruges det som naeste forsoeg.

Ejeren er den autentificerede ejer der blev stemplet paa agenten ved spawn (``agent_contract_bridge``) - aldrig
tom, aldrig fra et argument. En planlagt aktivering respekterer kill switch, ``suspended``/``closing``/``closed``
og modelruten: kan ingen af dem opfyldes, koerer agenten IKKE, og aarsagen staar synligt (``last_error`` + en
lifecycle-besked) frem for en skjult loekke. En agent uden bundet ejer (``legacy_unscoped``) beroeres ikke.
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)

SCHEDULED_MODE = "scheduled-worker"


def _refuse(agent_id: str, code: str, detail: str, reasons: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Aktiveringen koerer ikke. Aarsagen gemmes synligt; agentens status roeres ikke."""
    from uuid import uuid4

    from core.runtime.db_agent_runtime import create_agent_message, update_agent_registry_entry
    note = f"aktivering afvist ({code}): {detail}"[:300]
    logger.info("agent %s: %s", agent_id, note)
    update_agent_registry_entry(agent_id, last_error=note)
    create_agent_message(message_id=f"agent-msg-{uuid4().hex}", thread_id=f"agent-thread-{agent_id}",
                         agent_id=agent_id, direction="runtime->agent", role="system",
                         kind="activation-refused", content=note)
    return {"status": "refused", "code": code, "detail": detail, "reasons": reasons or []}


def _slot(agent_id: str, execution_mode: str) -> str:
    """Idempotensnoegle: en planlagt aktivering er sit tidspunkt (saa samme slot aldrig koerer to gange);
    en manuel er altid ny."""
    if execution_mode == SCHEDULED_MODE:
        try:
            from core.runtime.db_agent_runtime import get_agent_schedule
            nxt = str((get_agent_schedule(f"agent-schedule-{agent_id}") or {}).get("next_fire_at") or "")
        except Exception:
            logger.warning("tidsplanen for %s kunne ikke laeses - aktiveringen behandles som manuel", agent_id,
                           exc_info=True)
            nxt = ""
        if nxt:
            return f"activation:{agent_id}:{nxt}"
    return f"activation:{agent_id}:manual-{uuid.uuid4().hex[:12]}"


def ensure_activation(agent_id: str, *, execution_mode: str = "solo-task") -> dict[str, Any]:
    """Sikr at aktiveringen har et aabent assignment + en rute. Returnerer ``{"status": ...}``:

    ``not_applicable`` (legacy / ikke-persistent), ``reused`` (der er allerede et aabent assignment),
    ``created`` (+ ``assignment_id``, ``run_id``, ``route``) eller ``refused`` (+ ``code``)."""
    from core.runtime import db_agent_contract as c
    from core.runtime.db_agent_runtime import get_agent_registry_entry

    agent = get_agent_registry_entry(agent_id)
    if agent is None or not agent.get("persistent"):
        return {"status": "not_applicable"}
    owner = str(agent.get("owner_user_id") or "").strip()
    session = str(agent.get("owner_session_id") or "").strip()
    if owner in ("", c.LEGACY_UNSCOPED) or not session:
        return {"status": "not_applicable"}
    if c.open_assignment_for_agent(agent_id) is not None:
        return {"status": "reused"}
    from core.services.agent_contract_service import capability_enabled
    if not capability_enabled():
        return _refuse(agent_id, "POLICY_DENIED", "agent-kontrakten er slukket - planlagte aktiveringer er stoppet")
    life_row = c._conn().execute("SELECT lifecycle_status FROM agent_registry WHERE agent_id=?",
                                 (agent_id,)).fetchone()          # registry-dicten bærer ikke kolonnen
    life = str(life_row["lifecycle_status"] if life_row else "available")
    if life in ("suspended", "closing", "closed"):
        return _refuse(agent_id, "POLICY_DENIED", f"agenten er {life}")
    budget = int(agent.get("budget_tokens") or 0)
    from core.services.agent_model_policy import ModelUnavailable, decide_route
    try:
        route = decide_route(owner_user_id=owner, role=str(agent.get("role") or "researcher"),
                             budget_tokens=budget)
    except ModelUnavailable as exc:
        logger.info("aktivering af %s: ingen tilladt model (%s)", agent_id, exc.detail)
        return _refuse(agent_id, "MODEL_UNAVAILABLE", exc.detail, exc.reasons)
    from core.services import agent_fork_policy as fork
    plan, route = fork.plan_context(owner_user_id=owner, session_id=session, parent_run_id="", route=route)
    route = dict(route, context_mode="fresh", context_path=plan["plan_path"], activation=True,
                 reasoning_effort=plan["reasoning_effort"], effort_source=plan["effort_source"],
                 parent_provider="", parent_model="", parent_effort="")
    try:
        result_keys = ",".join(sorted(json.loads(str(agent.get("result_contract_json") or "{}")).keys()))
    except ValueError:
        result_keys = ""
    key = _slot(agent_id, execution_mode)
    try:
        acc = c.accept_assignment(
            agent_id=agent_id, owner_user_id=owner, origin_session_id=session,
            goal=str(agent.get("goal") or ""), parent_agent_id=str(agent.get("parent_agent_id") or "") or "jarvis",
            expected_result=result_keys, budget={"tokens": budget, "max_turns": int(agent.get("max_turns") or 0)},
            created_by="scheduler" if execution_mode == SCHEDULED_MODE else "activation",
            operation="activation", idempotency_key=key, request_digest=key)
    except c.ContractError as exc:
        logger.info("aktivering af %s afvist af kontrakten: %s", agent_id, exc)
        return _refuse(agent_id, exc.code, exc.detail)
    if acc.get("replayed"):
        # samme planlagte tidspunkt er allerede aktiveret (og afsluttet): mistede/dobbelte slots samles
        return _refuse(agent_id, "DUPLICATE_ACTIVATION", f"tidspunktet {key} er allerede aktiveret")
    try:
        from core.runtime import db_agent_fork, db_agent_route
        db_agent_route.record_decision(assignment_id=acc["assignment_id"], agent_id=agent_id,
                                       owner_user_id=owner, decision=route, attempt=1)
        db_agent_fork.record_fork(assignment_id=acc["assignment_id"], agent_id=agent_id, owner_user_id=owner,
                                  origin_session_id=session, plan=plan)
        _use_route(agent_id, route)
    except Exception as exc:
        logger.warning("aktiveringens rute kunne ikke gemmes for %s", agent_id, exc_info=True)
        c.commit_terminal_outcome(assignment_id=acc["assignment_id"], status="failed", error_code="ROUTE_PERSIST",
                                  error_phase="persistence", summary=f"rute kunne ikke gemmes: {type(exc).__name__}")
        return {"status": "refused", "code": "ROUTE_PERSIST", "detail": type(exc).__name__, "reasons": []}
    return {"status": "created", "assignment_id": acc["assignment_id"], "run_id": acc["run_id"],
            "route": {"route_source": route["route_source"], "provider": route["provider"],
                      "model": route["model"]}}


def _use_route(agent_id: str, route: dict[str, Any]) -> None:
    from core.runtime.db_agent_contract import _conn
    conn = _conn()
    conn.execute("UPDATE agent_registry SET provider=?, model=? WHERE agent_id=?",
                 (route["provider"], route["model"], agent_id))
    conn.commit()
