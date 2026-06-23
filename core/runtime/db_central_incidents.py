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


def resolve_central_incidents(*, cluster: str, nerve: str) -> int:
    """Auto-resolve ALLE uløste incidents for én (cluster, nerve). Returnerer antal lukkede.

    Bruges når en tilstand er rettet (fx config-drift forsvundet efter runtime.json-fix) —
    centralen lukker selv de forældede flag i stedet for at lade dem hænge uløst. Selv-sikker.
    """
    try:
        with connect() as conn:
            _ensure_central_incidents_table(conn)
            cur = conn.execute(
                "UPDATE central_incidents SET resolved = 1 "
                "WHERE resolved = 0 AND cluster = ? AND nerve = ?",
                (str(cluster or ""), str(nerve or "")),
            )
            return int(cur.rowcount or 0)
    except Exception:
        return 0


def has_unresolved_message(
    *, cluster: str, nerve: str, message: str, within_seconds: int = 3600
) -> bool:
    """True hvis en uløst incident med SAMME besked allerede findes inden for tidsvinduet.

    Dedup-gate (rate-limit): forhindrer at samme drift-besked oprettes igen og igen pr. check.
    Sammenligner på den fulde (trunkerede) besked-streng + tidsvindue. Selv-sikker → False
    (ved fejl hellere oprette end tabe et flag).
    """
    try:
        from datetime import timedelta

        cutoff = (datetime.now(UTC) - timedelta(seconds=int(within_seconds))).isoformat()
        with connect() as conn:
            _ensure_central_incidents_table(conn)
            row = conn.execute(
                "SELECT 1 FROM central_incidents "
                "WHERE resolved = 0 AND cluster = ? AND nerve = ? AND message = ? AND ts >= ? "
                "LIMIT 1",
                (str(cluster or ""), str(nerve or ""), str(message or "")[:1000], cutoff),
            ).fetchone()
            return row is not None
    except Exception:
        return False


def count_unresolved(*, min_severity: str | None = None,
                     exclude_nerve: str | None = None) -> int:
    """Antal uhåndterede incidents (til hurtig live-status). Selv-sikker → 0.

    exclude_nerve: udelad en bestemt nerve fra optællingen. Bruges af central_health så
    self-helbreds-alarmen IKKE tæller SINE EGNE severe self_health-incidents med (ellers
    avler hver alarm den næste — en selv-forstærkende loop).
    """
    try:
        clause = "resolved = 0"
        params: list[object] = []
        if min_severity == "severe":
            clause += " AND severity = 'severe'"
        elif min_severity == "error":
            clause += " AND severity IN ('error', 'severe')"
        if exclude_nerve:
            clause += " AND nerve <> ?"
            params.append(str(exclude_nerve))
        with connect() as conn:
            _ensure_central_incidents_table(conn)
            return int(conn.execute(
                f"SELECT COUNT(*) FROM central_incidents WHERE {clause}", tuple(params)
            ).fetchone()[0])
    except Exception:
        return 0


def has_open_incident(*, cluster: str, nerve: str) -> bool:
    """True hvis der allerede findes en uløst incident for (cluster, nerve). Selv-sikker.

    Dedup-gate uafhængig af besked-tekst (bruges af central_health hvor beskeden ændrer sig
    pr. tik, men vi kun vil have ÉN åben self_health-alarm ad gangen)."""
    try:
        with connect() as conn:
            _ensure_central_incidents_table(conn)
            row = conn.execute(
                "SELECT 1 FROM central_incidents "
                "WHERE resolved = 0 AND cluster = ? AND nerve = ? LIMIT 1",
                (str(cluster or ""), str(nerve or "")),
            ).fetchone()
            return row is not None
    except Exception:
        return False
