from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from core.runtime.db import connect
from core.tools.claude_dispatch.spec import TaskSpec


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _sikr_ophav_kolonner(conn) -> None:
    """Doven migration — samme mønster som `kind` på chat_sessions.

    INTET tilbagefyld. En historisk dispatch kørte før kanten fandtes, og et
    gættet ophav ville være præcis den slags «sandhed» man ikke kan efterprøve.
    Tom streng betyder ærligt «ukendt».
    """
    for kolonne in ("origin_run_id", "origin_session_id", "work_ref"):
        try:
            conn.execute(
                f"ALTER TABLE claude_dispatch_audit ADD COLUMN {kolonne} "
                "TEXT NOT NULL DEFAULT ''"
            )
        except Exception:
            pass                      # findes allerede


def _ophav() -> tuple[str, str]:
    """Hvilken kørsel og session udløste denne dispatch?

    ## Hvorfor kanten er værd at gemme

    `claude_dispatch` præger sit eget `task_id` (`uuid4().hex[:12]`) der ikke
    deler noget med noget andet lager. Målt 13/9-2026: elleve forskellige
    stores repræsenterer «et stykke arbejde», og næsten ingen er koblet — så
    ingen flade kan vise «denne tur startede det arbejde».

    Forbindelsen fandtes hele tiden i koden. `aktivt_run_id()` blev bygget efter
    to hændelser der stod med tomt `run_id` og derfor ikke kunne efterforskes:
    feltet fandtes, kalderen sendte det bare ikke. Her var det samme — kanten
    blev kastet væk i det øjeblik dispatchen startede.

    Self-safe: kan ophavet ikke afgøres, gemmes tom streng. Et gæt ville være
    værre end et tomt felt, fordi det ville PEGE på en forkert kørsel.
    """
    try:
        from core.services.session_context_resolve import (
            aktiv_session_id,
            aktivt_run_id,
        )
        return str(aktivt_run_id("") or ""), str(aktiv_session_id("") or "")
    except Exception:
        return "", ""


def _work_ref(run_id: str, task_id: str) -> str:
    """RODEN for dette arbejde, som en præfikset reference.

    Er dispatchen født af en kørsel, er kørslen roden — alt arbejdet hører til
    den tur. Ellers er dispatchen sin egen rod.

    Det er forskellen på rod og ophav i praksis: `origin_run_id` siger *hvorfor*
    dispatchen findes, `work_ref` siger *hvilket* stykke arbejde den er en del
    af. For en dispatch født af en samtale er de to det samme — for en dispatch
    uden ophav er de ikke.
    """
    from core.runtime.work_ref import UgyldigReference, lav
    for art, id_ in (("run", run_id), ("dispatch", task_id)):
        try:
            return lav(art, id_)
        except UgyldigReference:
            continue
    return ""


def start_audit_row(task_id: str, spec: TaskSpec) -> None:
    rid, sid = _ophav()
    ref = _work_ref(rid, task_id)
    with connect() as conn:
        _sikr_ophav_kolonner(conn)
        conn.execute(
            """
            INSERT INTO claude_dispatch_audit
                (task_id, started_at, spec_json, status, tokens_used,
                 origin_run_id, origin_session_id, work_ref)
            VALUES (?, ?, ?, 'running', 0, ?, ?, ?)
            """,
            (task_id, _now_iso(), json.dumps(asdict(spec)), rid, sid, ref),
        )
        conn.commit()


def finalize_audit_row(
    task_id: str, *, status: str, tokens_used: int,
    exit_code: int | None, diff_summary: str | None, error: str | None,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            UPDATE claude_dispatch_audit
            SET ended_at=?, status=?, tokens_used=?, exit_code=?,
                diff_summary=?, error=?
            WHERE task_id=? AND status='running'
            """,
            (_now_iso(), status, int(tokens_used), exit_code,
             diff_summary, error, task_id),
        )
        conn.commit()


def read_audit_row(task_id: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM claude_dispatch_audit WHERE task_id=?",
            (task_id,),
        ).fetchone()
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}
