"""Én doer ind og ud af en godkendelse — Fase 4's sidste stykke.

Spec'en: «move policy resolution, request/decision persistence, answerer
dispatch, expiry, and the Phase 3 atomic claim bridge behind
`ApprovalRuntime`.»

## Hvad der faktisk var spredt — maalt, ikke antaget

BESLUTNINGEN var allerede samlet: tre svarere (chat /approve, /deny, cowork)
gaar alle gennem `resolve_pending_approval`, hvor udloeb, ejerskab, digest og
den atomiske overtagelse ligger. Den doer skal ikke bygges om; den virker.

KORTET var derimod bygget i haanden FIRE steder. Det er ikke teoretisk: hver
gang Fase 4 tilfoejede et felt — ejer, tidsstempel, digest — skulle det
tilfoejes fire gange, og en glemt kopi ville have vaeret et stille hul. Tre
gange paa én dag har det moenster kostet en ekstra runde.

Derfor er dette moduls kerne `build_request()`: ét sted der ved hvordan et
gyldigt kort ser ud, saa et nyt kald-sted ikke KAN glemme et felt.

UDLOEBET blev kun tjekket to steder — ved svar og ved opstart. Et udloebet kort
blev altsaa liggende i filen til nogen roerte det. Ikke et sikkerhedshul (svar
afvises), men tilstanden loej om hvad der var i vente. `sweep_expired()` er
fejningen der manglede.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

# Felter ethvert kort SKAL have. Fase 4 tilfoejede de tre sidste én ad gangen,
# hver gang fire steder. Listen er her saa en test kan haevde den.
PAAKRAEVEDE = ("tool_name", "arguments", "run_id", "session_id",
               "created_at", "owner_user_id", "invocation_digest")


def new_id() -> str:
    return f"approval-{uuid4().hex[:12]}"


def build_request(*, tool_name: str, arguments: dict[str, Any],
                  result: Any, run: Any,
                  created_at: str | None = None) -> dict[str, Any]:
    """Byg et gyldigt godkendelses-kort. Det ENE sted formen bor.

    `run` giver ejer og herkomst; resten kommer fra kaldet. Ejeren og digesten
    udledes gennem `visible_runs`' egne hjaelpere, saa der ikke opstaar en
    anden definition af «hvem» og «samme kald».
    """
    import core.services.visible_runs as _vr

    return {
        "tool_name": tool_name,
        "arguments": arguments,
        "result": result,
        "run_id": getattr(run, "run_id", "") or "",
        "session_id": getattr(run, "session_id", "") or "",
        "created_at": created_at or datetime.now(UTC).isoformat(),
        "owner_user_id": _vr._godkendelses_ejer(run),
        "invocation_digest": _vr._kald_digest(tool_name, arguments),
    }


def decide(approval_id: str, *, approved: bool,
           answered_by: str | None = None) -> dict[str, Any]:
    """Svar paa en godkendelse. Den ENE vej ind for enhver svarer.

    Delegerer med vilje til `resolve_pending_approval`: dér ligger udloebet,
    ejerskabet, digesten og den atomiske overtagelse allerede, og at flytte
    dem ville vaere at bygge den mest konsekvenstunge sti om uden en fejl at
    rette.
    """
    from core.services.visible_runs_approvals import resolve_pending_approval
    return resolve_pending_approval(approval_id, approved=approved,
                                    answered_by=answered_by)


def state(approval_id: str) -> dict[str, Any] | None:
    """Hvad ved vi om dette kort? None hvis det ikke findes."""
    import core.services.visible_runs as _vr
    kort = _vr._PENDING_APPROVALS.get(approval_id)
    if kort is not None:
        return dict(kort)
    try:
        delt = _vr._get_visible_approval_state(approval_id)
    except Exception:
        return None
    return dict(delt) if delt else None


def sweep_expired() -> dict[str, int]:
    """Fjern udloebne kort. Returnerer hvad der blev fejet.

    Fejningen der manglede: udloeb blev kun tjekket ved svar og ved opstart, saa
    et doedt kort blev liggende og fik tilstanden til at loeve om hvad der var
    i vente. Kaster aldrig.
    """
    ud = {"fejet": 0, "tilbage": 0}
    try:
        import core.services.visible_runs as _vr
        from core.services.visible_runs_approvals import _er_udloebet

        doede = [k for k, v in list(_vr._PENDING_APPROVALS.items())
                 if isinstance(v, dict) and _er_udloebet(v)]
        for k in doede:
            _vr._PENDING_APPROVALS.pop(k, None)
        if doede:
            _vr._persist_pending_approvals()
            logger.info("approval_runtime: fejede %d udloebne kort", len(doede))
        ud["fejet"] = len(doede)
        ud["tilbage"] = len(_vr._PENDING_APPROVALS)
    except Exception:
        logger.warning("approval_runtime: fejningen fejlede", exc_info=True)
    return ud
