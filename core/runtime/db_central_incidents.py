"""Central-incidents — persistent log af det Den Intelligente Central GRIBER.

Den in-memory trace-sink (central_trace) er en per-proces ring-buffer der tabes ved
genstart. Incidents (grebne fejl, circuit-breaker-åbninger, flags) skal PERSISTERE så
de kan fanges live + traces begge veje på tværs af processer (jarvis-api + jarvis-runtime)
og overlever genstart. Bjørn (owner) notificeres ved ALVORLIGE; Claude poller tabellen.

Selv-sikker: alle skrive-/læse-fejl sluges (en incident-log må aldrig vælte runtime).
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Any

from core.runtime.db_core import connect

_SEVERITIES = ("info", "error", "severe")


def _ensure_central_incidents_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS central_incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            cluster TEXT NOT NULL DEFAULT '',
            nerve TEXT NOT NULL DEFAULT '',
            kind TEXT NOT NULL DEFAULT 'error',
            severity TEXT NOT NULL DEFAULT 'error',
            message TEXT NOT NULL DEFAULT '',
            run_id TEXT NOT NULL DEFAULT '',
            session_id TEXT NOT NULL DEFAULT '',
            resolved INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_central_incidents_unresolved "
        "ON central_incidents (resolved, severity, id DESC)"
    )


def record_central_incident(
    *,
    cluster: str,
    nerve: str,
    kind: str,
    severity: str = "error",
    message: str = "",
    run_id: str = "",
    session_id: str = "",
) -> int | None:
    """Persistér én incident. Returnerer row-id (eller None ved fejl). Selv-sikker."""
    try:
        sev = severity if severity in _SEVERITIES else "error"
        with connect() as conn:
            _ensure_central_incidents_table(conn)
            cur = conn.execute(
                "INSERT INTO central_incidents "
                "(ts, cluster, nerve, kind, severity, message, run_id, session_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (datetime.now(UTC).isoformat(), str(cluster or ""), str(nerve or ""),
                 str(kind or "error"), sev, str(message or "")[:1000],
                 str(run_id or ""), str(session_id or "")),
            )
            return int(cur.lastrowid)
    except Exception:
        return None


def list_central_incidents(
    *,
    limit: int = 50,
    unresolved_only: bool = False,
    min_severity: str | None = None,
) -> list[dict[str, Any]]:
    """Læs incidents (nyeste først). Claude poller denne. Selv-sikker → [] ved fejl."""
    try:
        clauses: list[str] = []
        params: list[object] = []
        if unresolved_only:
            clauses.append("resolved = 0")
        if min_severity == "severe":
            clauses.append("severity = 'severe'")
        elif min_severity == "error":
            clauses.append("severity IN ('error', 'severe')")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with connect() as conn:
            _ensure_central_incidents_table(conn)
            rows = conn.execute(
                f"SELECT * FROM central_incidents {where} ORDER BY id DESC LIMIT ?",
                (*params, limit),
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


def resolve_central_incident(incident_id: int) -> bool:
    """Markér en incident som håndteret. Selv-sikker."""
    try:
        with connect() as conn:
            _ensure_central_incidents_table(conn)
            conn.execute(
                "UPDATE central_incidents SET resolved = 1 WHERE id = ?", (int(incident_id),)
            )
        return True
    except Exception:
        return False


def count_unresolved(*, min_severity: str | None = None) -> int:
    """Antal uhåndterede incidents (til hurtig live-status). Selv-sikker → 0."""
    try:
        clause = "resolved = 0"
        if min_severity == "severe":
            clause += " AND severity = 'severe'"
        elif min_severity == "error":
            clause += " AND severity IN ('error', 'severe')"
        with connect() as conn:
            _ensure_central_incidents_table(conn)
            return int(conn.execute(
                f"SELECT COUNT(*) FROM central_incidents WHERE {clause}"
            ).fetchone()[0])
    except Exception:
        return 0
