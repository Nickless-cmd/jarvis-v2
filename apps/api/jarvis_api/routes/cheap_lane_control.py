"""Owner-only read surface for the Cheap Lane control center."""
from __future__ import annotations

import asyncio
import csv
import hashlib
import io
import json
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse

from core.runtime.db_cheap_lane_control import (
    get_cheap_lane_invocation_detail,
    list_cheap_lane_audit,
    list_cheap_lane_invocations,
)
from core.services.cheap_lane_dashboard import build_cheap_lane_dashboard
from core.services.cheap_lane_diagnostics import diagnose_cheap_lane
from core.services.cheap_lane_quotas import capacity_snapshot

router = APIRouter(prefix="/mc/cheap-lane", tags=["mc-cheap-lane"])

_EXPORT_MAX_ROWS = 5_000
_EXPORT_FIELDS = (
    "invocation_id", "correlation_id", "created_at", "provider", "model",
    "auth_profile", "daemon", "task_kind", "egress", "status", "error_code",
    "error_class", "latency_ms", "input_tokens", "output_tokens", "cost_usd",
    "cache_hit_tokens", "cache_miss_tokens", "attempt", "retry_parent_id",
    "fallback_parent_id", "route_decision_id", "payload_status",
)


def _require_owner() -> None:
    from apps.api.jarvis_api.routes.central_auth import require_central_owner

    require_central_owner()


def _since(hours: int) -> str:
    return (datetime.now(UTC) - timedelta(hours=hours)).isoformat()


def _safe_row(row: dict[str, object]) -> dict[str, object]:
    safe = dict(row)
    if safe.get("error_message"):
        from core.services.secret_redaction import redact

        safe["error_message"] = redact(str(safe["error_message"]))
    return safe


def _filtered_logs(
    *,
    hours: int,
    provider: str = "",
    model: str = "",
    auth_profile: str = "",
    daemon: str = "",
    status: str = "",
    error_class: str = "",
    correlation_id: str = "",
    query: str = "",
    cursor: str = "",
    limit: int = 100,
) -> dict[str, object]:
    page = list_cheap_lane_invocations(
        since=_since(hours), provider=provider, model=model,
        auth_profile=auth_profile, daemon=daemon, status=status,
        error_class=error_class, correlation_id=correlation_id,
        query=query, cursor=cursor, limit=limit,
    )
    page["items"] = [_safe_row(row) for row in page["items"]]
    return page


def _export_rows(*, hours: int) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    cursor = ""
    while len(rows) < _EXPORT_MAX_ROWS:
        page = _filtered_logs(
            hours=hours, cursor=cursor,
            limit=min(500, _EXPORT_MAX_ROWS - len(rows)),
        )
        rows.extend(page["items"])  # type: ignore[arg-type]
        cursor = str(page.get("next_cursor") or "")
        if not cursor:
            break
    return [{field: row.get(field) for field in _EXPORT_FIELDS} for row in rows]


def _config_fingerprints() -> dict[str, str]:
    from core.services.provider_registry_admin import fuld_registrering

    registry = fuld_registrering()
    stable = json.dumps(registry, sort_keys=True, separators=(",", ":"), default=str)
    return {"provider_registry_sha256": hashlib.sha256(stable.encode("utf-8")).hexdigest()}


@router.get("/dashboard")
async def dashboard(hours: int = Query(24, ge=1, le=1440)) -> dict:
    _require_owner()
    return await asyncio.to_thread(build_cheap_lane_dashboard, window_hours=hours)


@router.get("/capacity")
async def capacity() -> dict:
    _require_owner()
    return await asyncio.to_thread(capacity_snapshot)


@router.get("/logs")
async def logs(
    hours: int = Query(24, ge=1, le=1440),
    provider: str = "",
    model: str = "",
    auth_profile: str = "",
    daemon: str = "",
    status: str = "",
    error_class: str = "",
    correlation_id: str = "",
    query: str = "",
    cursor: str = "",
    limit: int = Query(100, ge=1, le=500),
) -> dict:
    _require_owner()
    try:
        return await asyncio.to_thread(
            _filtered_logs, hours=hours, provider=provider, model=model,
            auth_profile=auth_profile, daemon=daemon, status=status,
            error_class=error_class, correlation_id=correlation_id,
            query=query, cursor=cursor, limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/logs/export")
async def export_logs(
    format: Literal["json", "csv"] = "json",
    hours: int = Query(24, ge=1, le=1440),
):
    _require_owner()
    rows = await asyncio.to_thread(_export_rows, hours=hours)
    if format == "json":
        return JSONResponse({
            "items": rows, "count": len(rows),
            "truncated": len(rows) >= _EXPORT_MAX_ROWS,
        })
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(_EXPORT_FIELDS), extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return StreamingResponse(
        iter([output.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=cheap-lane-logs.csv"},
    )


@router.get("/logs/{invocation_id}")
async def log_detail(invocation_id: str) -> dict:
    _require_owner()
    detail = await asyncio.to_thread(get_cheap_lane_invocation_detail, invocation_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Cheap Lane invocation not found")
    return _safe_row(detail)


@router.get("/diagnostics")
async def diagnostics() -> dict:
    _require_owner()
    return await asyncio.to_thread(diagnose_cheap_lane)


@router.get("/audit")
async def audit(limit: int = Query(100, ge=1, le=500)) -> dict:
    _require_owner()
    return await asyncio.to_thread(list_cheap_lane_audit, limit=limit)


@router.get("/diagnostics/export")
async def export_diagnostics(hours: int = Query(24, ge=1, le=1440)) -> dict:
    _require_owner()
    snapshot, diagnosis, rows, fingerprints = await asyncio.gather(
        asyncio.to_thread(build_cheap_lane_dashboard, window_hours=hours),
        asyncio.to_thread(diagnose_cheap_lane),
        asyncio.to_thread(_export_rows, hours=hours),
        asyncio.to_thread(_config_fingerprints),
    )
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "window_hours": hours,
        "snapshot": snapshot,
        "findings": diagnosis.get("findings", []),
        "logs": rows,
        "config_fingerprints": fingerprints,
        "schema_versions": {"cheap_lane_dashboard": 1, "diagnostic_package": 1},
    }
