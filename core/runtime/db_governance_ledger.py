"""Governance-ledger — PERSISTENT log af governerede mutationer.

Hver gang en governance-flag toggles, en breaker nulstilles eller et healer-flag
skifter, kaldes ``record_mutation(area, key, value)`` i ``central_governance``.
Indtil nu gik mutationen KUN til eventbus + Central.observe — ingen af delene
overlever genstart.

Denne tabel PERSISTERER alle governerede mutationer i den fælles ``jarvis.db``
(samme DB som API-processen læser fra). Hver række er én mutation med timestamp,
så både API og runtime kan se historikken på tværs af processer og genstarter.

Self-sikker: alle skrive-/læse-fejl sluges (en audit-log må ALDRIG vælte runtime).
"""
from __future__ import annotations

import json as _json
from datetime import UTC, datetime
from typing import Any

from core.runtime.db_core import connect


def _ensure_table():
    """Opret governance_ledger-tabellen hvis den ikke findes. Idempotent."""
    try:
        with connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS governance_ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    area TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value_json TEXT NOT NULL DEFAULT '',
                    ts TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_governance_ledger_ts "
                "ON governance_ledger (ts DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_governance_ledger_area "
                "ON governance_ledger (area, ts DESC)"
            )
    except Exception:
        pass


def record_mutation(area: str, key: str, value: Any) -> None:
    """Skriv én række til governance_ledger. Self-safe — sluger fejl.

    ``area`` = "governance" | "healing" | "breaker" (domænet)
    ``key``  = flag-navn / nerve-navn
    ``value`` = ny værdi (JSON-serialiseres)
    """
    try:
        _ensure_table()
        ts = datetime.now(UTC).isoformat()
        value_json = _json.dumps(value, ensure_ascii=False, default=str)
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO governance_ledger (area, key, value_json, ts)
                VALUES (?, ?, ?, ?)
                """,
                (str(area or ""), str(key or ""), value_json, ts),
            )
    except Exception:
        pass


def read_ledger(area: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    """Læs seneste mutationer. Filtrér på area hvis givet. Selv-sikker → [] ved fejl."""
    try:
        _ensure_table()
        if area:
            sql = (
                "SELECT id, area, key, value_json, ts "
                "FROM governance_ledger WHERE area = ? "
                "ORDER BY ts DESC LIMIT ?"
            )
            params: tuple = (area, max(1, min(limit, 500)))
        else:
            sql = (
                "SELECT id, area, key, value_json, ts "
                "FROM governance_ledger ORDER BY ts DESC LIMIT ?"
            )
            params = (max(1, min(limit, 500)),)
        with connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        out: list[dict[str, Any]] = []
        for r in rows:
            try:
                parsed_value = _json.loads(str(r["value_json"]))
            except Exception:
                parsed_value = r["value_json"]
            out.append({
                "id": int(r["id"]),
                "area": str(r["area"]),
                "key": str(r["key"]),
                "value": parsed_value,
                "ts": str(r["ts"]),
            })
        return out
    except Exception:
        return []


def summary() -> dict[str, dict[str, Any]]:
    """Aggregér pr. area: {area: {total, latest_ts, keys: [distinkte nøgler]}}."""
    try:
        _ensure_table()
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT area,
                       COUNT(*) AS total,
                       MAX(ts) AS latest_ts
                FROM governance_ledger
                GROUP BY area
                ORDER BY latest_ts DESC
                """
            ).fetchall()
            keys_rows = conn.execute(
                """
                SELECT DISTINCT area, key
                FROM governance_ledger
                ORDER BY area, key
                """
            ).fetchall()
        keys_by_area: dict[str, list[str]] = {}
        for r in keys_rows:
            a = str(r["area"])
            keys_by_area.setdefault(a, []).append(str(r["key"]))
        out: dict[str, dict[str, Any]] = {}
        for r in rows:
            a = str(r["area"])
            out[a] = {
                "total": int(r["total"]),
                "latest_ts": str(r["latest_ts"]),
                "keys": keys_by_area.get(a, []),
            }
        return out
    except Exception:
        return {}
