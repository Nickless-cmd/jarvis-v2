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


def _run_synlig_for_kalder(conn, run_id: str) -> bool:
    """Maa den nuvaerende kalder se dette run?

    Samme regel som /mc/runs-listen (eb6886e03): owner ser sine egne plus
    systemets ejerloese; andre kun deres egne. Uden den kunne et kendt run_id
    aabne en ANDEN brugers run-detalje og alle dens haendelser — listen var
    lukket, men detaljen stod aaben ved siden af.
    """
    from core.identity.workspace_context import current_role, current_user_id
    from core.runtime.db_visible import _run_user_scope

    scope_sql, scope_params = _run_user_scope(
        current_user_id() or None,
        include_unassigned=current_role() in {"", "owner"},
    )
    row = conn.execute(
        f"SELECT 1 FROM visible_runs WHERE run_id = ? AND {scope_sql} LIMIT 1",
        (run_id, *scope_params),
    ).fetchone()
    return row is not None


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
            if not _run_synlig_for_kalder(conn, run_id):
                return {"run": None, "steps": []}
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


@router.get("/runs/{run_id}/prompt")
def mc_run_prompt(run_id: str) -> dict:
    """Hvad byggede han svaret paa? Sektionerne i prompten for netop dette run.

    Projektion af `prompt.section_answer_impact`, som baerer run_id — modsat
    `prompt.assembly_size`, der IKKE goer, og som derfor ikke kan bindes til
    et run uden tidsmatch. Vi udelader hellere `mode` end at gaette den.

    Daekning maalt 6/9-2026: 187 af de seneste 200 runs har posten, med ~68
    sektioner hver. Findes den ikke, siges det aabent i stedet for at vise
    en tom liste som om prompten var tom.
    """
    import json as _json

    from core.runtime.db import connect

    try:
        with connect() as conn:
            if not _run_synlig_for_kalder(conn, run_id):
                return {"run_id": run_id, "found": False, "sections": []}
            row = conn.execute(
                """
                SELECT payload_json FROM events
                WHERE kind = 'prompt.section_answer_impact'
                  AND json_extract(payload_json, '$.run_id') = ?
                ORDER BY id DESC LIMIT 1
                """,
                (run_id,),
            ).fetchone()
    except Exception as exc:  # pragma: no cover - defensivt
        return {"run_id": run_id, "found": False, "sections": [], "error": str(exc)}

    if row is None:
        return {"run_id": run_id, "found": False, "sections": []}

    try:
        payload = _json.loads(row["payload_json"] or "{}")
    except Exception:
        payload = {}

    raw = payload.get("sections")
    sections = [
        {"label": str(s.get("label") or ""), "chars": int(s.get("chars") or 0)}
        for s in (raw if isinstance(raw, list) else [])
        if isinstance(s, dict)
    ]
    sections.sort(key=lambda s: s["chars"], reverse=True)
    total = sum(s["chars"] for s in sections)
    for s in sections:
        s["pct"] = round(s["chars"] * 100.0 / total, 1) if total else 0.0

    return {
        "run_id": run_id,
        "found": True,
        "answer_chars": int(payload.get("answer_chars") or 0),
        "total_chars": total,
        "section_count": len(sections),
        "sections": sections,
    }
