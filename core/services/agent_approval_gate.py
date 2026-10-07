"""Gate i agentens vaerktoejsdispatch: en handling der kraever godkendelse STOPPER foer den udfoeres
(agent-contract-v1 F4b, spec 8.2).

Kun for kontrakt-bundne agenter (et aabent assignment); legacy-agenter er uaendrede. Hvilke vaerktoejer
kraever godkendelse afgoeres af runtime-politikken (``tool_definition_v2``: ``approval_requirement == ask``
plus en fast liste), aldrig af modeltekst. Gaten afgoer tre ting:

* ``None``           - udfoer kaldet (ikke godkendelseskraevende, eller en approval er netop BRUGT til det);
* en tekst           - giv denne tekst til modellen i stedet (afslag/udloeb/aendrede argumenter): barnet
                       faar et eksplicit afvist udfald og kan ikke proeve samme handling igen;
* ``ApprovalPending``- loekken parkeres; en varig approval er oprettet.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from core.runtime import db_agent_approvals as appr
from core.runtime.db_agent_contract import ContractError, open_assignment_for_agent
from core.services.agent_loop_core import ApprovalPending

logger = logging.getLogger(__name__)

#: Altid godkendelseskraevende for en agent, selv hvis metadata skulle mangle.
ALWAYS_APPROVE = frozenset({
    "bash", "write_file", "edit_file", "multi_edit", "operator_bash", "operator_write_file",
    "operator_edit_file", "operator_kill_process", "operator_launch_app", "operator_open_url",
    "gmail_send", "calendar_create_event", "docs_append", "sheets_write", "stripe_create_issuing_card",
})


def requires_approval(tool_name: str) -> tuple[bool, str]:
    """(kraever, risikoklasse). Fail-CLOSED for de faste navne; ukendt metadata -> ingen krav for resten."""
    name = str(tool_name or "")
    if name in ALWAYS_APPROVE:
        return True, "write"
    try:
        from core.tools.tool_definition_v2 import APPROVAL_ASK, NON_IDEMPOTENT_WRITE, describe
        d = describe(name)
    except Exception:
        logger.warning("kunne ikke laese approval-metadata for %s", name, exc_info=True)
        return False, ""
    if d is not None and d.approval_requirement == APPROVAL_ASK:
        return True, "write" if d.effect_class == NON_IDEMPOTENT_WRITE else "unknown"
    return False, ""


def _denied(reason: str, approval_id: str = "") -> str:
    return json.dumps({"status": "denied", "code": "APPROVAL_DENIED", "approval_id": approval_id,
                       "error": f"Handlingen blev IKKE udfoert: {reason}. Proev ikke samme handling igen "
                                f"(hverken her eller via et andet vaerktoej); forklar hvad du ikke kunne goere."},
                      ensure_ascii=False)


def _parse(tc: dict) -> tuple[str, dict[str, Any]]:
    fn = tc.get("function") if isinstance(tc.get("function"), dict) else {}
    name = str(fn.get("name") or tc.get("name") or "")
    raw = fn.get("arguments")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw) if raw.strip() else {}
        except ValueError:
            raw = {}
    return name, (raw if isinstance(raw, dict) else {})


def gate(*, agent: dict[str, Any], run_id: str, tc: dict[str, Any], resume_approval_id: str = "") -> str | None:
    """Se modulbeskrivelsen. ``resume_approval_id`` er den approval det parkerede kald venter paa."""
    name, args = _parse(tc)
    needed, risk = requires_approval(name)
    if not needed:
        return None
    agent_id = str(agent.get("agent_id") or "")
    a = open_assignment_for_agent(agent_id)
    if a is None:
        if str(agent.get("owner_user_id") or "") not in ("", "legacy_unscoped"):
            # En BUNDET agent hvis assignment er afsluttet (f.eks. annulleret mens tråden stadig koerer) maa
            # ALDRIG udfoere en godkendelseskraevende handling uden vagt.
            return _denied("assignmentet er afsluttet")
        return None                                         # legacy-agent: uaendret adfaerd
    digest = appr.invocation_digest(tool_name=name, arguments=args, target=a["target"],
                                    assignment_id=a["assignment_id"])
    tc_id = str(tc.get("id") or "")
    if resume_approval_id:
        r = appr.get(approval_id=resume_approval_id)
        if r is None or r["assignment_id"] != a["assignment_id"]:
            return _denied("approvalen findes ikke for dette assignment", resume_approval_id)
        if r["status"] == appr.APPROVED:
            if r["args_digest"] != digest:
                return _denied("argumenterne er aendret siden godkendelsen", r["approval_id"])
            if appr.consume(approval_id=r["approval_id"], digest=digest):
                return None
            return _denied("approvalen er allerede brugt eller udloebet", r["approval_id"])
        reason = {"denied": "afvist af brugeren", "expired": "godkendelsen udloeb uden svar",
                  "cancelled": "godkendelsen blev annulleret",
                  "consumed": "approvalen er allerede brugt"}.get(r["status"], f"approvalen er {r['status']}")
        return _denied(reason, r["approval_id"])
    try:
        r = appr.request(owner_user_id=a["owner_user_id"], origin_session_id=a["origin_session_id"],
                         assignment_id=a["assignment_id"], tool_name=name, arguments=args, run_id=run_id,
                         risk_class=risk or "write", requested_by="agent")
    except ContractError as exc:
        logger.info("approval kunne ikke oprettes for %s: %s", name, exc)
        return _denied("samme handling er allerede afvist" if exc.code == "POLICY_DENIED"
                       else f"kunne ikke anmode om godkendelse ({exc.code})")
    if r["status"] == appr.APPROVED and appr.consume(approval_id=r["approval_id"], digest=digest):
        return None
    try:
        from core.services.agent_approval_notify import on_requested
        on_requested(r)
    except Exception:
        logger.warning("kunne ikke notificere om approval %s", r["approval_id"], exc_info=True)
    raise ApprovalPending(r["approval_id"], tc_id)
