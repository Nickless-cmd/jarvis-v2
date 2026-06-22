"""API-endpoint forbrugs-statistik (parallel til tool_usage_store). Centralen holder styr på
hvilke af de ~412 API-endpoints der bruges mest/sjældent/ALDRIG → flag døde/ubrugte endpoints
+ grundlag for at rydde op / finde smartere endpoints. ÉT sted, begge veje.

DB-backed (cross-proces): middleware i api-processen tæller; cadence-observe i runtime-
processen læser. Self-safe; UPSERT pr. request er sub-ms (request-håndteringen dominerer).
Registrerede ruter snapshottes til shared_cache ved api-start, så dead-detektion (registreret-
men-aldrig-kaldt) kan ske cross-proces. Read-only statistik — ALDRIG destruktiv.
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Any

_REGISTERED_KEY = "endpoint_registered_routes"
_REGISTERED_TTL = 30 * 24 * 3600.0

_BUCKETS = (("most", 5000), ("often", 500), ("sometimes", 50), ("rare", 1))


def _ensure(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS endpoint_usage (
            endpoint TEXT PRIMARY KEY,
            method TEXT,
            path TEXT,
            call_count INTEGER NOT NULL DEFAULT 0,
            error_count INTEGER NOT NULL DEFAULT 0,
            last_used_at TEXT
        )"""
    )


def record_request(method: str, path: str, status_code: int = 200) -> None:
    """UPSERT-increment for ét request. Best-effort, hot-path-sikker. path = rute-TEMPLATE
    (fx /attachments/{id}) så alle kald til samme endpoint aggregeres."""
    m = str(method or "").upper().strip()
    p = str(path or "").strip()
    if not m or not p:
        return
    endpoint = f"{m} {p}"
    err = 1 if int(status_code or 0) >= 400 else 0
    now = datetime.now(UTC).isoformat()
    try:
        from core.runtime.db import connect
        with connect() as conn:
            _ensure(conn)
            conn.execute(
                """INSERT INTO endpoint_usage(endpoint, method, path, call_count, error_count, last_used_at)
                   VALUES (?, ?, ?, 1, ?, ?)
                   ON CONFLICT(endpoint) DO UPDATE SET
                       call_count = call_count + 1,
                       error_count = error_count + ?,
                       last_used_at = ?""",
                (endpoint, m, p, err, now, err, now),
            )
            conn.commit()
    except Exception:
        pass


def store_registered_routes(routes: list[tuple[str, str]]) -> None:
    """Snapshot af registrerede (method, path)-ruter ved api-start → shared_cache, så dead-
    detektion kan ske cross-proces. Best-effort."""
    try:
        from core.services import shared_cache
        norm = sorted({f"{str(m).upper()} {str(p)}" for m, p in routes if m and p})
        shared_cache.set(_REGISTERED_KEY, norm, ttl_seconds=_REGISTERED_TTL)
    except Exception:
        pass


def _registered() -> list[str]:
    try:
        from core.services import shared_cache
        v = shared_cache.get(_REGISTERED_KEY)
        return list(v) if isinstance(v, list) else []
    except Exception:
        return []


def usage_stats() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    try:
        from core.runtime.db import connect
        with connect() as conn:
            _ensure(conn)
            rows = conn.execute(
                "SELECT endpoint, method, path, call_count, error_count, last_used_at FROM endpoint_usage"
            ).fetchall()
        for r in rows:
            out[str(r[0])] = {"method": str(r[1] or ""), "path": str(r[2] or ""),
                              "count": int(r[3] or 0), "errors": int(r[4] or 0),
                              "last_used": r[5]}
    except Exception:
        pass
    return out


def _bucket_for(count: int) -> str:
    for label, threshold in _BUCKETS:
        if count >= threshold:
            return label
    return "never"


def usage_buckets() -> dict[str, list[str]]:
    """Klassificér endpoints most/often/sometimes/rare/never. Registrerede-men-aldrig-kaldte
    (fra shared_cache-snapshot) indgår som 'never' — dem skal vi kigge på / rydde op."""
    stats = usage_stats()
    names = set(_registered()) | set(stats.keys())
    buckets: dict[str, list[str]] = {"most": [], "often": [], "sometimes": [], "rare": [], "never": []}
    for name in names:
        buckets[_bucket_for(int(stats.get(name, {}).get("count") or 0))].append(name)
    for k in buckets:
        buckets[k].sort()
    return buckets


def dead_endpoints() -> list[str]:
    """Registrerede endpoints der ALDRIG er kaldt. Kandidater til oprydning / smartere design.
    KUN en liste — Centralen flagger, mennesket beslutter (aldrig auto-fjernet)."""
    stats = usage_stats()
    used = {k for k, v in stats.items() if int(v.get("count") or 0) > 0}
    return sorted(r for r in _registered() if r not in used)


def observe_stats() -> dict[str, Any]:
    """Periodisk (cadence): central.observe forbrugs-summary + flag antal døde endpoints.
    Self-safe, aldrig destruktiv."""
    stats = usage_stats()
    buckets = usage_buckets()
    dead = dead_endpoints()
    summary = {
        "tracked": len(stats), "registered": len(_registered()),
        "most": len(buckets["most"]), "often": len(buckets["often"]),
        "sometimes": len(buckets["sometimes"]), "rare": len(buckets["rare"]),
        "never": len(buckets["never"]), "dead": len(dead),
    }
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "tools", "nerve": "endpoint_usage_stats",
            "tracked": summary["tracked"], "registered": summary["registered"],
            "dead": summary["dead"], "dead_sample": dead[:30],
            "top": sorted(({"endpoint": k, "count": v["count"]} for k, v in stats.items()),
                          key=lambda d: -d["count"])[:10],
        })
    except Exception:
        pass
    return summary
