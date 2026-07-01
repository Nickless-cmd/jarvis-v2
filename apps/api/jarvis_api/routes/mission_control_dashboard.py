"""Mission Control dashboard-endpoints — de tre data-kilder som kontrolcenter-UI'et
(jarvis-desk cowork) mangler for at kunne HANDLE og ikke bare vise.

Bevidst et SELVSTÆNDIGT modul med egen router (inkluderes med prefix="/mc" i app.py,
samme mønster som system_health_router) — så den 4600-linjers mission_control.py IKKE
vokser (Boy Scout-reglen, CLAUDE.md). Kun læsning; genbruger eksisterende services.

  GET /mc/scheduled-tasks   planlagte/tilbagevendende opgaver (scheduled_tasks)
  GET /mc/runs/{run_id}      enkelt-run-detalje: run-række + dens hændelser (trin)
  GET /mc/costs/daily        pris/tokens pr. dag (ledger.daily_cost_summary)
"""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter

router = APIRouter(tags=["mission-control"])


@router.get("/scheduled-tasks")
def mc_scheduled_tasks(limit: int = 20) -> dict:
    """Afventende planlagte/tilbagevendende opgaver for nuværende bruger (owner uden
    kontekst-binding ser alle). Til MC's 'Planlagt'-panel. Self-safe."""
    try:
        from core.services.scheduled_tasks import list_pending_for_current_user
        items = list_pending_for_current_user()[: max(int(limit), 1)]
    except Exception as exc:  # pragma: no cover - defensivt
        return {"items": [], "error": str(exc), "summary": {"pending_count": 0}}
    return {"items": items, "summary": {"pending_count": len(items)}}


@router.get("/costs/daily")
def mc_costs_daily(days: int = 30) -> dict:
    """Pris/tokens pr. dag (op til 30 dage bagud) til MC's Cost-panel. Self-safe."""
    try:
        from core.costing.ledger import daily_cost_summary
        rows = list(daily_cost_summary())
    except Exception as exc:  # pragma: no cover - defensivt
        return {"days": [], "error": str(exc)}
    if days and days > 0:
        rows = rows[: int(days)]
    return {"days": rows, "meta": {"returned": len(rows)}}


def _event_to_step(row: Any) -> dict:
    """events-række → kompakt trin til run-detaljens tidslinje/træ."""
    try:
        payload = json.loads(row["payload_json"] or "{}")
    except Exception:
        payload = {}
    # Vælg et menneske-læsbart resumé fra de mest almindelige felter.
    summary = ""
    for key in ("reason", "text", "message", "tool", "status", "outcome", "detail"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            summary = val.strip()[:200]
            break
    return {
        "kind": row["kind"],
        "at": row["created_at"],
        "summary": summary,
        "tool": payload.get("tool") or payload.get("tool_name") or "",
    }


@router.get("/runs/{run_id}")
def mc_run_detail(run_id: str, event_limit: int = 60) -> dict:
    """Enkelt-run-detalje: selve run-rækken (visible_runs) + de hændelser der bærer dens
    run_id (drill-down-trin). Token/pris pr. run findes ikke i skemaet → udelades ærligt
    fremfor at fabrikere. Self-safe: tom detalje hvis run ikke findes."""
    from core.runtime.db import connect

    run: dict | None = None
    steps: list[dict] = []
    try:
        with connect() as conn:
            r = conn.execute(
                """
                SELECT run_id, lane, provider, model, status, started_at,
                       finished_at, text_preview, error, capability_id
                FROM visible_runs WHERE run_id = ? LIMIT 1
                """,
                (run_id,),
            ).fetchone()
            if r is not None:
                run = dict(r)
            # Hændelser hvis run_id optræder i payloaden (LIKE-probe — run_id er unikt nok).
            rows = conn.execute(
                """
                SELECT kind, payload_json, created_at FROM events
                WHERE payload_json LIKE ? ORDER BY id ASC LIMIT ?
                """,
                (f'%{run_id}%', max(int(event_limit), 1)),
            ).fetchall()
            steps = [_event_to_step(row) for row in rows]
    except Exception as exc:  # pragma: no cover - defensivt
        return {"run": run, "steps": steps, "error": str(exc)}

    return {
        "run": run,
        "found": run is not None,
        "steps": steps,
        "summary": {"step_count": len(steps)},
    }
