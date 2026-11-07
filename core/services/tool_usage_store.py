"""Tools-cluster Phase 2 — persistent forbrugs-statistik (DB-backed, cross-proces).

Centralen holder styr på hvilke tools Jarvis bruger MEST / mindre / nogle gange / SLET IKKE,
så vi kan (a) ordne tool-kataloget — mest-brugte først, døde sidst — og (b) flagge døde tools.
Begge veje fra ÉT sted: observe (tæl forbrug) → beslut (rækkefølge + flag), så vi aldrig skal
rode rundt for at finde ud af hvad der skal ud af prompten.

DB-backed (ikke in-memory): jarvis-api (--workers 1) OG jarvis-runtime er SEPARATE processer
— tool-kald sker i begge, så tælleren skal være cross-proces (samme jarvis.db). UPSERT pr.
kald er sub-ms på en PK-indekseret række; tool-eksekveringen selv dominerer → ingen reel
hot-path-omkostning. Self-safe: kaster aldrig.
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Any

# Forbrugs-buckets (kald-count → kategori). Bevidst simple tærskler; kan kalibreres på data.
_BUCKETS = (
    ("most", 500),       # >500
    ("often", 50),       # 51–500
    ("sometimes", 6),    # 6–50
    ("rare", 1),         # 1–5
    # 0 / fraværende → "never"
)


def _ensure(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS tool_usage (
            tool TEXT PRIMARY KEY,
            kind TEXT,
            call_count INTEGER NOT NULL DEFAULT 0,
            error_count INTEGER NOT NULL DEFAULT 0,
            last_used_at TEXT
        )"""
    )


def record_use(tool: str, *, kind: str = "native", ok: bool = True) -> None:
    """UPSERT-increment forbrugs-tæller for ét tool-kald. Best-effort, hot-path-sikker."""
    name = str(tool or "").strip()
    if not name:
        return
    err = 0 if ok else 1
    now = datetime.now(UTC).isoformat()
    try:
        from core.runtime.db import connect
        with connect() as conn:
            _ensure(conn)
            conn.execute(
                """INSERT INTO tool_usage(tool, kind, call_count, error_count, last_used_at)
                   VALUES (?, ?, 1, ?, ?)
                   ON CONFLICT(tool) DO UPDATE SET
                       call_count = call_count + 1,
                       error_count = error_count + ?,
                       last_used_at = ?,
                       kind = ?""",
                (name, kind, err, now, err, now, kind),
            )
            conn.commit()
    except Exception:
        pass


def usage_stats() -> dict[str, dict[str, Any]]:
    """{tool: {count, errors, kind, last_used}} for alle tools der ER blevet kaldt."""
    out: dict[str, dict[str, Any]] = {}
    try:
        from core.runtime.db import connect
        with connect() as conn:
            _ensure(conn)
            rows = conn.execute(
                "SELECT tool, kind, call_count, error_count, last_used_at FROM tool_usage"
            ).fetchall()
        for r in rows:
            out[str(r[0])] = {"count": int(r[2] or 0), "errors": int(r[3] or 0),
                              "kind": str(r[1] or ""), "last_used": r[4]}
    except Exception:
        pass
    return out


def _bucket_for(count: int) -> str:
    for label, threshold in _BUCKETS:
        if count >= threshold:
            return label
    return "never"


def usage_buckets(registered: list[str] | None = None) -> dict[str, list[str]]:
    """Klassificér tools i most/often/sometimes/rare/never. Hvis `registered` gives, indgår
    også tools der ALDRIG er kaldt (count 0) som 'never' — det er dem der skal vises sidst."""
    stats = usage_stats()
    names = set(registered or []) | set(stats.keys())
    buckets: dict[str, list[str]] = {"most": [], "often": [], "sometimes": [], "rare": [], "never": []}
    for name in names:
        count = int(stats.get(name, {}).get("count") or 0)
        buckets[_bucket_for(count)].append(name)
    for k in buckets:
        buckets[k].sort()
    return buckets


def tool_order(registered: list[str]) -> list[str]:
    """Ordn registrerede tools efter forbrug: mest-brugte FØRST, aldrig-brugte SIDST.
    Ties brydes alfabetisk. Bruges af katalog-assembly så døde tools lander nederst."""
    stats = usage_stats()
    return sorted(
        registered,
        key=lambda n: (-int(stats.get(n, {}).get("count") or 0), n),
    )


def dead_tools(registered: list[str]) -> list[str]:
    """Registrerede tools der ALDRIG er kaldt (count 0). Vises sidst / kandidater til at
    fjerne fra kataloget. KUN en liste — Centralen flagger, mennesket beslutter."""
    stats = usage_stats()
    return sorted(n for n in registered if int(stats.get(n, {}).get("count") or 0) == 0)


def observe_stats(registered: list[str] | None = None) -> dict[str, Any]:
    """Periodisk (cadence): central.observe forbrugs-summary + flag antal døde tools.
    Self-safe, aldrig destruktiv."""
    stats = usage_stats()
    buckets = usage_buckets(registered)
    summary = {
        "tracked": len(stats),
        "most": len(buckets["most"]), "often": len(buckets["often"]),
        "sometimes": len(buckets["sometimes"]), "rare": len(buckets["rare"]),
        "never": len(buckets["never"]),
        "top": sorted(stats.items(), key=lambda kv: -kv[1]["count"])[:10],
    }
    try:
        from core.services.central_core import central
        central().observe({
            "cluster": "tools", "nerve": "tool_usage_stats",
            "tracked": summary["tracked"], "never": summary["never"],
            "top": [{"tool": t, "count": d["count"]} for t, d in summary["top"][:10]],
        })
    except Exception:
        pass
    return summary


def build_tool_usage_store_surface() -> dict[str, Any]:
    """Mission Control-surface: hvad er der faktisk talt i `tool_usage`?

    READ-ONLY: `usage_stats()` kalder `_ensure` (CREATE TABLE) og sluger alle
    fejl til `{}` — begge dele ville goere en ulaeselig tabel til «ingen
    forbrug». Her tjekkes tabellens eksistens foerst, og fejl bliver en aarsag.
    """
    base = {"mode": "tool-usage-store"}
    try:
        from core.runtime.db import connect
        with connect() as conn:
            if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='tool_usage'").fetchone() is None:
                return {**base, "active": False, "reason": "tabellen tool_usage findes ikke endnu",
                        "signals": {}, "summary": "intet forbrug talt"}
            rows = conn.execute(
                "SELECT tool, call_count, error_count, last_used_at FROM tool_usage").fetchall()
    except Exception as exc:  # surface skal melde aarsagen, ikke kaste ind i MC
        return {**base, "active": False,
                "reason": f"tool_usage kunne ikke laeses: {type(exc).__name__}: {exc}"[:300],
                "signals": {}, "summary": "forbrugstaeller ulaeselig"}
    calls = sum(int(r[1] or 0) for r in rows)
    errors = sum(int(r[2] or 0) for r in rows)
    buckets = {"most": 0, "often": 0, "sometimes": 0, "rare": 0, "never": 0}
    for r in rows:
        buckets[_bucket_for(int(r[1] or 0))] += 1
    last = max((str(r[3]) for r in rows if r[3]), default=None)
    top = sorted(rows, key=lambda r: (-int(r[1] or 0), str(r[0])))[:5]
    return {
        "active": calls > 0, **base,
        **({} if calls else {"reason": "tool_usage har ingen talte kald"}),
        "signals": {"tracked_tools": len(rows), "total_calls": calls, "total_errors": errors,
                    "error_rate": round(errors / calls, 4) if calls else None,
                    "last_used_at": last, "buckets": buckets,
                    "top": [{"tool": str(r[0]), "count": int(r[1] or 0)} for r in top]},
        "summary": f"{len(rows)} vaerktoejer, {calls} kald, {errors} fejl; seneste {last or 'aldrig'}",
    }
