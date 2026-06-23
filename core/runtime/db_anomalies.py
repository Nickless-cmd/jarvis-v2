"""Central-anomalier — persistent register over UDEFINEREDE fejl Centralen ikke selv har
en nerve til endnu. Det er her Centralen "definerer nye fejl": hver unik fejl-signatur får
en række (kategori + importance + tæller + først/sidst set), så et nyt fejl-mønster bliver
til et kendt, rangeret, lærbart signal i stedet for at forsvinde usynligt.

UPSERT pr. signatur → recurring fejl bumper bare tælleren (ingen spam); første sigtning
returnerer is_new=True (Centralen lærte lige en ny fejl-type). Cross-proces + overlever
genstart. Selv-sikker: en anomali-log må ALDRIG vælte runtime.
"""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Any

from core.runtime.db_core import connect

_IMPORTANCE = ("low", "medium", "high", "critical")
_IMP_RANK = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def _ensure_anomalies_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS central_anomalies (
            signature TEXT PRIMARY KEY,
            category TEXT NOT NULL DEFAULT '',
            importance TEXT NOT NULL DEFAULT 'medium',
            source TEXT NOT NULL DEFAULT '',
            count INTEGER NOT NULL DEFAULT 0,
            first_seen TEXT NOT NULL DEFAULT '',
            last_seen TEXT NOT NULL DEFAULT '',
            sample TEXT NOT NULL DEFAULT '',
            resolved INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_anomalies_live "
        "ON central_anomalies (resolved, importance, last_seen DESC)"
    )


def record_anomaly_signature(
    *, signature: str, category: str, importance: str, source: str, sample: str,
) -> bool:
    """UPSERT en anomali-signatur. Returnerer True hvis det er FØRSTE gang (ny fejl-type
    Centralen netop definerede), ellers False (recurring → tæller bumpet). Selv-sikker."""
    try:
        imp = importance if importance in _IMPORTANCE else "medium"
        now = datetime.now(UTC).isoformat()
        with connect() as conn:
            _ensure_anomalies_table(conn)
            row = conn.execute(
                "SELECT count FROM central_anomalies WHERE signature = ?", (signature,)
            ).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO central_anomalies "
                    "(signature, category, importance, source, count, first_seen, last_seen, sample) "
                    "VALUES (?, ?, ?, ?, 1, ?, ?, ?)",
                    (signature, str(category or ""), imp, str(source or ""),
                     now, now, str(sample or "")[:500]),
                )
                return True
            # recurring: bump tæller + last_seen, og eskalér importance hvis denne
            # sigtning er alvorligere end den hidtil registrerede.
            conn.execute(
                "UPDATE central_anomalies SET count = count + 1, last_seen = ? WHERE signature = ?",
                (now, signature),
            )
            cur = conn.execute(
                "SELECT importance FROM central_anomalies WHERE signature = ?", (signature,)
            ).fetchone()
            if cur and _IMP_RANK.get(imp, 1) > _IMP_RANK.get(str(cur[0]), 1):
                conn.execute(
                    "UPDATE central_anomalies SET importance = ? WHERE signature = ?",
                    (imp, signature),
                )
            return False
    except Exception:
        return False


def list_anomalies(*, limit: int = 50, unresolved_only: bool = True,
                   min_importance: str | None = None) -> list[dict[str, Any]]:
    """Læs anomalier (nyeste først). Selv-sikker → [] ved fejl."""
    try:
        clauses: list[str] = []
        params: list[object] = []
        if unresolved_only:
            clauses.append("resolved = 0")
        if min_importance and min_importance in _IMP_RANK:
            allowed = [k for k, v in _IMP_RANK.items() if v >= _IMP_RANK[min_importance]]
            clauses.append("importance IN (%s)" % ",".join("?" * len(allowed)))
            params.extend(allowed)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with connect() as conn:
            _ensure_anomalies_table(conn)
            rows = conn.execute(
                f"SELECT signature, category, importance, source, count, first_seen, "
                f"last_seen, sample FROM central_anomalies {where} "
                f"ORDER BY last_seen DESC LIMIT ?",
                (*params, int(limit)),
            ).fetchall()
        return [
            {"signature": r[0], "category": r[1], "importance": r[2], "source": r[3],
             "count": int(r[4]), "first_seen": r[5], "last_seen": r[6], "sample": r[7]}
            for r in rows
        ]
    except Exception:
        return []


def resolve_anomaly(signature: str) -> bool:
    """Markér én anomali-signatur som håndteret (forsvinder fra det live register). Selv-sikker.

    Bruges når en signatur er afklaret (rettet, eller en testartefakt der skal væk)."""
    try:
        with connect() as conn:
            _ensure_anomalies_table(conn)
            conn.execute(
                "UPDATE central_anomalies SET resolved = 1 WHERE signature = ?",
                (str(signature or ""),),
            )
        return True
    except Exception:
        return False


def anomaly_counts() -> dict[str, int]:
    """Hurtig optælling pr. importance (til realtime-panelet). Selv-sikker."""
    out = {"critical": 0, "high": 0, "medium": 0, "low": 0, "total": 0}
    try:
        with connect() as conn:
            _ensure_anomalies_table(conn)
            for imp, n in conn.execute(
                "SELECT importance, COUNT(*) FROM central_anomalies WHERE resolved = 0 "
                "GROUP BY importance"
            ).fetchall():
                if str(imp) in out:
                    out[str(imp)] = int(n)
                out["total"] += int(n)
    except Exception:
        pass
    return out
