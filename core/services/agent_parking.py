"""Parkering og genoptagelse af et barn der venter paa en approval (agent-contract-v1 F4b, spec 8.2).

Parkering: loekken er stoppet FOER det godkendelseskraevende kald. Her gemmes checkpointen, runnet faar
status ``waiting_for_approval``, assignmentet ``waiting`` og agenten ``waiting_for_approval`` - INGEN worker,
lease eller tråd holdes imens (en ventende approval bruger ikke en workerplads).

Genoptagelse: naar approvalen er afgjort (godkendt, afvist, udloebet eller annulleret) tager
``resume_decided`` checkpointen atomisk (HOEJST EN gang) og starter agenten igen som et nyt run (nyt
forsoeg paa samme assignment), der fortsaetter praecis dér: det parkerede kald afgoeres af beslutningen.
Kaldes af beslutnings-API'et og af supervisor-tikket (saa en beslutning ikke gaar tabt ved en genstart).
"""
from __future__ import annotations

import logging
from typing import Any

from core.runtime import db_agent_approvals as appr
from core.runtime.db_agent_contract import _conn, _now_iso, open_assignment_for_agent

logger = logging.getLogger(__name__)

DECIDED = ("approved", "denied", "expired", "cancelled")
WAITING_STATUS = "waiting_for_approval"


def set_assignment_status(*, assignment_id: str, status: str, only_from: tuple[str, ...]) -> bool:
    """Atomisk statusskifte inden for de aabne tilstande. ``False`` hvis den ikke stod i ``only_from``."""
    conn = _conn()
    marks = ",".join("?" * len(only_from))
    cur = conn.execute(f"UPDATE agent_assignments SET status=?, updated_at=? WHERE assignment_id=? "
                       f"AND status IN ({marks})", (status, _now_iso(), assignment_id, *only_from))
    conn.commit()
    return cur.rowcount == 1


def park_run(*, agent: dict[str, Any], run_id: str, result: dict[str, Any], thread_id: str = "") -> dict[str, Any]:
    """Gem checkpointen og sæt tilstandene. Returnerer agentens detaljeflade (som en almindelig tur)."""
    from core.runtime.db_agent_runtime import update_agent_registry_entry, update_agent_run
    from core.services.agent_runtime_spawn import build_agent_detail_surface

    agent_id = str(agent.get("agent_id") or "")
    a = open_assignment_for_agent(agent_id)
    p = result["parked"]
    if a is None:
        raise RuntimeError("en parkeret agent skal have et aabent assignment")
    appr.save_checkpoint(assignment_id=a["assignment_id"], run_id=run_id, approval_id=p["approval_id"],
                         payload=p["checkpoint"])
    update_agent_run(run_id, status=WAITING_STATUS, finished_at=_now_iso(), provider_status="parked",
                     output_summary=f"venter paa approval {p['approval_id']}"[:400],
                     input_tokens=int(result.get("input_tokens") or 0),
                     output_tokens=int(result.get("output_tokens") or 0),
                     cost_usd=float(result.get("cost_usd") or 0.0))
    set_assignment_status(assignment_id=a["assignment_id"], status="waiting", only_from=("queued", "active"))
    update_agent_registry_entry(agent_id, status=WAITING_STATUS,
                                tokens_burned_delta=int(result.get("input_tokens") or 0)
                                + int(result.get("output_tokens") or 0))
    try:
        from core.services.agent_transcript import write_lifecycle
        write_lifecycle(agent_id, "parked", note=f"approval={p['approval_id']} run_id={run_id}")
    except Exception:
        logger.warning("transcript-linje for parkering kunne ikke skrives", exc_info=True)
    return build_agent_detail_surface(agent_id) or {"agent_id": agent_id, "status": WAITING_STATUS}


def take_resume(agent_id: str) -> dict[str, Any] | None:
    """Er agenten parkeret og afgjort? Tag checkpointen (atomisk) og returnér loekkens ``resume``-dict, eller
    ``None`` for en almindelig tur. En parkeret agent hvis approval IKKE er afgjort maa ikke koeres."""
    a = open_assignment_for_agent(agent_id)
    if a is None:
        return None
    cp = appr.parked_checkpoint(assignment_id=a["assignment_id"])
    if cp is None:
        return None
    ap = appr.get(approval_id=cp["approval_id"])
    if ap is None or ap["status"] not in DECIDED:
        raise RuntimeError(f"agenten venter paa approval {cp['approval_id']}")
    taken = appr.take_checkpoint(assignment_id=a["assignment_id"])
    if taken is None:
        raise RuntimeError("checkpointen er allerede taget af en anden genoptagelse")
    try:
        from core.runtime.db_agent_runtime import update_agent_run
        update_agent_run(taken["run_id"], status="resumed", finished_at=_now_iso())
    except Exception:
        logger.warning("forrige run kunne ikke markeres resumed", exc_info=True)
    return {**taken["payload"], "approval_id": taken["approval_id"]}


def resume_decided(start) -> list[dict[str, str]]:
    """Genoptag alle parkerede agenter hvis approval er afgjort. ``start(agent_id)`` starter udfoerelsen
    (service'ens baggrundsstarter). Et assignment der imens er afsluttet genoptages IKKE - dets checkpoint
    kasseres. Idempotent: ``waiting -> queued`` er en CAS, saa to kaldere ikke starter to gange."""
    from core.runtime.db_agent_runtime import update_agent_registry_entry

    done: list[dict[str, str]] = []
    conn = _conn()
    for row in appr.decided_parked():
        st = conn.execute("SELECT status FROM agent_assignments WHERE assignment_id=?",
                          (row["assignment_id"],)).fetchone()
        if st is None or st["status"] in ("completed", "failed", "cancelled", "timed_out"):
            conn.execute("UPDATE agent_checkpoints SET status='discarded' WHERE assignment_id=? AND status='parked'",
                         (row["assignment_id"],))
            # Run-raekken maa ikke blive staaende i waiting_for_approval naar assignmentet
            # er terminalt. Maalt 8/10-2026: run-d20c48dac022473d stod som
            # 'waiting_for_approval' laenge efter at baade agenten og approvalen var
            # 'cancelled' - en zombie-raekke. Projektionen klassificerer paa den SENESTE
            # run-status (``classify``), saa raekken holdt kortet i «venter» og talte med
            # i opmaerksomheden selv om der ikke ventede noget. Et parkeret run der ikke
            # genoptages blev afbrudt; det er hvad 'cancelled' siger.
            conn.execute("UPDATE agent_runs SET status='cancelled', finished_at=? "
                         "WHERE assignment_id=? AND status=?",
                         (_now_iso(), row["assignment_id"], WAITING_STATUS))
            conn.commit()
            continue
        if st["status"] != "waiting":
            continue            # genoptagelsen er allerede i gang (queued/active): checkpointen maa IKKE roeres
        if not set_assignment_status(assignment_id=row["assignment_id"], status="queued", only_from=("waiting",)):
            continue
        update_agent_registry_entry(row["agent_id"], status="queued", last_error="")
        start(row["agent_id"])
        done.append({"agent_id": row["agent_id"], "approval_id": row["approval_id"],
                     "approval_status": row["approval_status"]})
    return done
