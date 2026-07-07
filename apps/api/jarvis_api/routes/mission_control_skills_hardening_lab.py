"""Mission Control routes: skills, memory, hardening, lab

Ruter flyttet uændret fra mission_control.py (god-fil-snit). Egen prefix-fri
APIRouter; samles i mission_control.py via include_router(prefix=/mc)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException  # noqa: F401 (HTTPException brugt i route-kroppe)

from .mission_control_common import *  # noqa: F401,F403 (delt flade + hjælpere)

router = APIRouter()

@router.get("/skills")
def mc_skills() -> dict:
    tools_raw = _mc_facade("_get_all_tools")()
    tools = []
    for entry in tools_raw:
        fn = entry.get("function") or {}
        name = str(fn.get("name") or "")
        if not name:
            continue
        desc = str(fn.get("description") or "")
        params = fn.get("parameters") or {}
        required = list(params.get("required") or [])
        tools.append({
            "name": name,
            "description": desc[:120],
            "required": required,
        })
    return {
        "tools": tools,
        "total": len(tools),
        "calls_today": _mc_facade("_skills_calls_today")(),
        "recent_invocations": _mc_facade("_skills_recent_invocations")(),
    }



@router.get("/memory")
def mc_memory(q: str = "", limit: int = 100, scope: str = "") -> dict:
    """Search/list private retained memory records.

    - q: optional substring filter on retained_value
    - limit: max rows to return (capped at 500)
    - scope: optional retention_scope filter (e.g. 'development', 'identity')
    """
    limit_clamped = max(1, min(int(limit or 100), 500))
    where: list[str] = []
    params: list = []
    q_clean = (q or "").strip()
    if q_clean:
        where.append("retained_value LIKE ?")
        params.append(f"%{q_clean}%")
    scope_clean = (scope or "").strip()
    if scope_clean:
        where.append("retention_scope = ?")
        params.append(scope_clean)
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    params.append(limit_clamped)

    items: list[dict] = []
    total = 0
    scope_counts: dict[str, int] = {}
    try:
        with connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id, record_id, source, retained_value, retained_kind,
                       retention_scope, retention_horizon, confidence, created_at
                FROM private_retained_memory_records
                {where_sql}
                ORDER BY id DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
            for row in rows:
                items.append({
                    "id": int(row["id"]),
                    "record_id": row["record_id"] or "",
                    "source": row["source"] or "",
                    "value": (row["retained_value"] or "")[:600],
                    "kind": row["retained_kind"] or "",
                    "scope": row["retention_scope"] or "",
                    "horizon": row["retention_horizon"] or "",
                    "confidence": row["confidence"] or "",
                    "created_at": row["created_at"] or "",
                })
            total_row = conn.execute(
                "SELECT COUNT(*) AS n FROM private_retained_memory_records"
            ).fetchone()
            total = int(total_row["n"]) if total_row else 0
            scope_rows = conn.execute(
                """
                SELECT retention_scope AS scope, COUNT(*) AS n
                FROM private_retained_memory_records
                GROUP BY retention_scope
                ORDER BY n DESC
                """
            ).fetchall()
            for row in scope_rows:
                key = row["scope"] or "(none)"
                scope_counts[key] = int(row["n"])
    except Exception:
        pass

    return {
        "items": items,
        "total": total,
        "scope_counts": scope_counts,
        "query": q_clean,
        "scope_filter": scope_clean,
        "limit": limit_clamped,
        "matched": len(items),
    }


@router.get("/hardening")
def mc_hardening() -> dict:
    counts = _mc_facade("_hardening_approval_counts")()
    return {
        "pending": counts["pending"],
        "approved_today": counts["approved_today"],
        "denied_today": counts["denied_today"],
        "autonomy_level": _mc_facade("_hardening_autonomy_level")(),
        "integrations": _mc_facade("_hardening_integrations")(),
        "recent_approvals": _mc_facade("_hardening_recent_approvals")(),
    }



@router.get("/lab")
def mc_lab() -> dict:
    return {
        "costs_today": _mc_facade("_lab_costs_today")(),
        "providers_today": _mc_facade("_lab_providers_today")(),
        "db_stats": _mc_facade("_lab_db_stats")(),
        "recent_events": _mc_facade("_lab_recent_events")(),
    }
