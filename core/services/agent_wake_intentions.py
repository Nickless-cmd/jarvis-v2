"""Varig fortsaettelsesintention for en parent der venter paa agenter (B2, §6).

Ventekontrakten er en BETINGELSE paa den eksisterende synlige dispatch-sti, ikke
en ny dispatcher: opfyldes den, skrives en `recovering`-post i `in_flight_runs`
for den oprindelige session, og KUN API-processens
`visible_run_recovery_dispatcher` omsaetter den til et run via
`claim_due_recovery` (generation + lease + single-flight). Her skrives posten og
her aflyses den; her startes intet.

Posten er markeret `wake_kind`, saa den ikke vises som en afbrudt opgave
(`recovery_snapshot`) og ikke faar et «du blev afbrudt»-varsel.
"""
from __future__ import annotations

import logging
from typing import Any

from core.services import in_flight_runs as ifr

logger = logging.getLogger(__name__)

WAKE_KIND = "agent_wait"
_FRAME = "[SYSTEM — agentvækning, ikke en besked fra brugeren]\n"


def wake_message(*, condition: str, assignment_ids: list[str]) -> str:
    """Teksten der starter det vaagnede run. Maerket som fra systemet (staaende
    regel: alt der ikke er skrevet fra composeren skal vaere kendeligt)."""
    hvornaar = ("mindst én af" if condition == "first_terminal" else "alle")
    return (
        _FRAME
        + f"Du ventede paa dine agenter; {hvornaar} dem er nu naaet et terminalt udfald: "
        + ", ".join(assignment_ids) + ". Resultaterne ligger i din agent-inbox og "
        "kommer med i dette modeltrin. Kontroller status og evidens, og fortsaet "
        "det arbejde du ventede paa."
    )


def stage_wake(*, task_id: str, session_id: str, owner_user_id: str, message: str,
               parent_run_id: str = "", wake_kind: str = WAKE_KIND) -> dict[str, Any]:
    """Skriv intentionen. Idempotent paa `task_id`. Findes der allerede en anden
    afventende fortsaettelse i samme session, SAMLES de til én (§6): returnerer
    da den eksisterendes task_id med `merged=True` og skriver intet nyt."""
    def change(records):
        if task_id in records:
            return {"task_id": task_id, "merged": False, "created": False}
        for key, rec in records.items():
            if (str(rec.get("session_id") or "") == session_id
                    and str(rec.get("status") or "") == "recovering"
                    and str(rec.get("kind") or "visible") == "visible"):
                return {"task_id": str(rec.get("task_id") or key), "merged": True,
                        "created": False}
        now = ifr._iso()
        records[task_id] = {
            "task_id": task_id, "run_id": task_id, "session_id": session_id,
            "status": "recovering", "kind": "visible", "wake_kind": wake_kind,
            "approval_mode": "ask", "thinking_mode": "think", "tool_scope": "",
            "surface": "", "force_user_id": owner_user_id, "local_tool_exec": False,
            "excerpt": message[:240], "original_request": message,
            "parent_run_id": parent_run_id,
            "started_at": now, "last_progress_at": now, "settled_at": now,
            "interrupted_at": now, "first_interrupted_at": now,
            "exit_reason": "agent-wake", "interruption_reason": "agent-wake",
            "recovery_generation": 0, "recovery_attempt": 0, "recovery_limit": 1,
            "recovery_owner": "", "recovery_lease_until": "", "next_attempt_at": "",
            "notice_pending": False, "final_synthesis_pending": False,
            "recovery_deferrals": 0,
        }
        return {"task_id": task_id, "merged": False, "created": True}
    out = ifr._mutate(change)
    try:
        from core.services.visible_run_recovery_dispatcher import signal_recovery_dispatcher
        signal_recovery_dispatcher()
    except Exception:
        logger.debug("kunne ikke vække dispatcheren", exc_info=True)
    return out


def cancel_pending_wake(task_id: str, *, reason: str) -> bool:
    """Aflys en vaekning der endnu IKKE er startet. En allerede claimet (`running`)
    post roeres ikke: den er i gang, og brugerstoppet gaelder en tidligere generation."""
    def change(records):
        rec = records.get(task_id)
        if rec is None or str(rec.get("status") or "") != "recovering":
            return False
        rec["status"] = "cancelled"
        rec["exit_reason"] = str(reason)[:160]
        rec["settled_at"] = ifr._iso()
        rec["notice_pending"] = False
        rec["next_attempt_at"] = ""
        return True
    return bool(ifr._mutate(change))
